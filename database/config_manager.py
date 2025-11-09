"""
Менеджер конфігурації для отримання налаштувань з бази даних
"""
import logging
from typing import Optional, Dict, Any
from database import get_database
from database.encryption import decrypt_setting

logger = logging.getLogger(__name__)


class ConfigManager:
    """Менеджер для роботи з конфігурацією з бази даних"""
    
    _cache = {}
    _cache_valid = False
    
    @classmethod
    def get_setting(cls, key: str, default_value: Any = None) -> Any:
        """Отримати налаштування за ключем"""
        try:
            # Спочатку перевіряємо кеш
            if cls._cache_valid and key in cls._cache:
                return cls._cache[key]
            
            db = get_database()
            cursor = db.cursor(dictionary=True)
            
            try:
                cursor.execute(
                    "SELECT value_type, encrypted_value FROM system_settings WHERE `key` = %s",
                    (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Дешифруємо значення
                    decrypted_value = decrypt_setting(
                        result['encrypted_value'], 
                        result['value_type']
                    )
                    
                    # Зберігаємо в кеш
                    cls._cache[key] = decrypted_value
                    
                    return decrypted_value
                else:
                    logger.warning(f"Налаштування '{key}' не знайдено в базі, використовуємо default: {default_value}")
                    return default_value
                    
            finally:
                cursor.close()
                db.close()
                
        except Exception as e:
            logger.error(f"Помилка при отриманні налаштування '{key}': {e}")
            return default_value
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Отримати всі налаштування"""
        try:
            if cls._cache_valid and cls._cache:
                return cls._cache.copy()
            
            db = get_database()
            cursor = db.cursor(dictionary=True)
            
            try:
                cursor.execute(
                    "SELECT `key`, value_type, encrypted_value FROM system_settings"
                )
                results = cursor.fetchall()
                
                settings_dict = {}
                for result in results:
                    key = result['key']
                    decrypted_value = decrypt_setting(
                        result['encrypted_value'], 
                        result['value_type']
                    )
                    settings_dict[key] = decrypted_value
                
                # Оновлюємо кеш
                cls._cache = settings_dict
                cls._cache_valid = True
                
                return settings_dict.copy()
                
            finally:
                cursor.close()
                db.close()
                
        except Exception as e:
            logger.error(f"Помилка при отриманні всіх налаштувань: {e}")
            return {}
    
    @classmethod
    def get_bot_token(cls) -> Optional[str]:
        """Отримати токен бота"""
        return cls.get_setting('bot_token')
    
    @classmethod
    def get_stripe_secret_key(cls) -> Optional[str]:
        """Отримати секретний ключ Stripe"""
        return cls.get_setting('stripe_secret_key')
    
    @classmethod
    def get_stripe_publishable_key(cls) -> Optional[str]:
        """Отримати публічний ключ Stripe"""
        return cls.get_setting('stripe_publishable_key')
    
    @classmethod
    def get_stripe_webhook_secret(cls) -> Optional[str]:
        """Отримати webhook secret Stripe"""
        return cls.get_setting('stripe_webhook_secret')
    
    @classmethod
    def get_subscription_price(cls) -> float:
        """Отримати ціну підписки в євро"""
        return cls.get_setting('subscription_price', 15.0)
    
    @classmethod
    def get_subscription_currency(cls) -> str:
        """Отримати валюту підписки"""
        return cls.get_setting('subscription_currency', 'eur')
    
    @classmethod
    def get_webhook_url(cls) -> Optional[str]:
        """Отримати URL webhook"""
        return cls.get_setting('webhook_url')
    
    @classmethod
    def invalidate_cache(cls):
        """Очистити кеш налаштувань"""
        cls._cache.clear()
        cls._cache_valid = False
        logger.info("Кеш налаштувань очищено")
    
    @classmethod
    def refresh_cache(cls):
        """Оновити кеш налаштувань"""
        cls.invalidate_cache()
        cls.get_all_settings()
        logger.info("Кеш налаштувань оновлено")
    
    @classmethod
    def get_subscription_info(cls) -> dict:
        """Отримати інформацію про підписку"""
        return {
            'price': cls.get_subscription_price(),
            'currency': cls.get_subscription_currency()
        }


class DatabaseConfig:
    """Клас для заміщення налаштувань з .env на налаштування з БД"""
    
    def __init__(self):
        # Завантажуємо всі налаштування з БД
        self._db_settings = ConfigManager.get_all_settings()
        
        # Fallback значення з .env (якщо БД недоступна)
        from config import settings
        self._env_settings = settings
    
    @property
    def telegram_bot_token(self) -> str:
        """Токен телеграм бота"""
        token = ConfigManager.get_bot_token()
        return token if token else self._env_settings.telegram_bot_token
    
    @property
    def stripe_secret_key(self) -> str:
        """Секретний ключ Stripe"""
        key = ConfigManager.get_stripe_secret_key()
        return key if key else self._env_settings.stripe_secret_key
    
    @property
    def stripe_publishable_key(self) -> str:
        """Публічний ключ Stripe"""
        key = ConfigManager.get_stripe_publishable_key()
        return key if key else self._env_settings.stripe_publishable_key
    
    @property
    def stripe_webhook_secret(self) -> str:
        """Webhook secret Stripe"""
        secret = ConfigManager.get_stripe_webhook_secret()
        return secret if secret else self._env_settings.stripe_webhook_secret
    
    @property
    def subscription_price(self) -> float:
        """Ціна підписки (в євро)"""
        return ConfigManager.get_subscription_price()
    
    @property
    def subscription_currency(self) -> str:
        """Валюта підписки"""
        return ConfigManager.get_subscription_currency()
    
    @property
    def webhook_url(self) -> str:
        """URL webhook"""
        url = ConfigManager.get_webhook_url()
        return url if url else self._env_settings.webhook_url
    
    # Інші налаштування залишаємо з .env
    @property
    def private_channel_id(self) -> str:
        return self._env_settings.private_channel_id
    
    @property
    def private_chat_id(self) -> str:
        return self._env_settings.private_chat_id
    
    @property
    def admin_chat_id(self) -> str:
        return self._env_settings.admin_chat_id
    
    @property
    def database_url(self) -> str:
        return self._env_settings.database_url
    
    @property
    def webhook_host(self) -> str:
        return self._env_settings.webhook_host
    
    @property
    def webhook_port(self) -> int:
        return self._env_settings.webhook_port
    
    @property
    def webhook_path(self) -> str:
        return self._env_settings.webhook_path
    
    @property
    def reminder_intervals(self) -> list[int]:
        return self._env_settings.reminder_intervals
    
    @property
    def subscription_reminder_days(self) -> int:
        return self._env_settings.subscription_reminder_days
    
    @property
    def payment_retry_hours(self) -> int:
        return self._env_settings.payment_retry_hours
    
    @property
    def log_level(self) -> str:
        return self._env_settings.log_level
    
    @property
    def admin_username(self) -> str:
        return self._env_settings.admin_username
    
    @property
    def admin_password(self) -> str:
        return self._env_settings.admin_password
    
    @property
    def admin_host(self) -> str:
        return self._env_settings.admin_host
    
    @property
    def admin_port(self) -> int:
        return self._env_settings.admin_port


# Створюємо глобальний екземпляр конфігурації на основі БД
db_config = DatabaseConfig()