"""
Утиліти для шифрування налаштувань
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Union, Any
import json


class SettingsEncryption:
    """Клас для шифрування/дешифрування налаштувань"""
    
    def __init__(self, master_key: str = None):
        """
        Ініціалізація з мастер-ключем
        Якщо ключ не вказано, використовується з змінної оточення
        """
        if master_key is None:
            master_key = os.getenv('SETTINGS_MASTER_KEY', 'default-key-change-in-production')
        
        self.master_key = master_key.encode()
        self._fernet = None
    
    def _get_fernet(self) -> Fernet:
        """Отримати екземпляр Fernet для шифрування"""
        if self._fernet is None:
            # Генеруємо ключ з мастер-ключа
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'upgrade_studio_salt',  # В продакшені використовуйте випадкову сіль
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
            self._fernet = Fernet(key)
        
        return self._fernet
    
    def encrypt_value(self, value: Any) -> str:
        """Зашифрувати значення"""
        if value is None:
            return ""
        
        # Конвертуємо в строку
        if isinstance(value, (dict, list)):
            str_value = json.dumps(value)
        elif isinstance(value, bool):
            str_value = "true" if value else "false"
        elif isinstance(value, (int, float)):
            str_value = str(value)
        else:
            str_value = str(value)
        
        # Шифруємо
        fernet = self._get_fernet()
        encrypted_bytes = fernet.encrypt(str_value.encode())
        
        # Повертаємо як base64 строку
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt_value(self, encrypted_value: str, value_type: str = "string") -> Any:
        """Дешифрувати значення"""
        if not encrypted_value:
            return None
        
        try:
            # Декодуємо з base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            
            # Дешифруємо
            fernet = self._get_fernet()
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            str_value = decrypted_bytes.decode()
            
            # Конвертуємо назад в потрібний тип
            if value_type == "boolean":
                return str_value.lower() == "true"
            elif value_type == "integer":
                return int(str_value)
            elif value_type == "float":
                return float(str_value)
            elif value_type == "json":
                return json.loads(str_value)
            else:  # string
                return str_value
                
        except Exception as e:
            print(f"Error decrypting value: {e}")
            return None


# Глобальний екземпляр для використання
encryption = SettingsEncryption()


def encrypt_setting(value: Any) -> str:
    """Зашифрувати налаштування"""
    return encryption.encrypt_value(value)


def decrypt_setting(encrypted_value: str, value_type: str = "string") -> Any:
    """Дешифрувати налаштування"""
    return encryption.decrypt_value(encrypted_value, value_type)


class SettingsManager:
    """Менеджер для роботи з налаштуваннями системи"""
    
    def __init__(self):
        self._cache = {}
        self._cache_loaded = False
    
    def _load_cache(self):
        """Завантажити всі налаштування в кеш"""
        if self._cache_loaded:
            return
            
        from database.models import DatabaseManager, SystemSettings
        
        with DatabaseManager() as db:
            settings = db.query(SystemSettings).all()
            
            for setting in settings:
                decrypted_value = decrypt_setting(setting.encrypted_value, setting.value_type)
                self._cache[setting.key] = {
                    'value': decrypted_value,
                    'type': setting.value_type,
                    'category': setting.category,
                    'is_sensitive': setting.is_sensitive,
                    'description': setting.description
                }
        
        self._cache_loaded = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Отримати налаштування за ключем"""
        self._load_cache()
        
        if key in self._cache:
            return self._cache[key]['value']
        
        return default
    
    def set(self, key: str, value: Any, value_type: str = None, 
            category: str = "general", is_sensitive: bool = False,
            description: str = None, updated_by: int = None) -> bool:
        """Встановити налаштування"""
        from database.models import DatabaseManager, SystemSettings
        
        # Автоматично визначаємо тип якщо не вказано
        if value_type is None:
            if isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, int):
                value_type = "integer"
            elif isinstance(value, float):
                value_type = "float"
            elif isinstance(value, (dict, list)):
                value_type = "json"
            else:
                value_type = "string"
        
        # Шифруємо значення
        encrypted_value = encrypt_setting(value)
        
        try:
            with DatabaseManager() as db:
                # Шукаємо існуюче налаштування
                setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
                
                if setting:
                    # Оновлюємо існуюче
                    setting.encrypted_value = encrypted_value
                    setting.value_type = value_type
                    setting.category = category
                    setting.is_sensitive = is_sensitive
                    if description:
                        setting.description = description
                    if updated_by:
                        setting.updated_by = updated_by
                    setting.updated_at = datetime.utcnow()
                else:
                    # Створюємо нове
                    setting = SystemSettings(
                        key=key,
                        encrypted_value=encrypted_value,
                        value_type=value_type,
                        category=category,
                        is_sensitive=is_sensitive,
                        description=description,
                        updated_by=updated_by
                    )
                    db.add(setting)
                
                db.commit()
                
                # Оновлюємо кеш
                self._cache[key] = {
                    'value': value,
                    'type': value_type,
                    'category': category,
                    'is_sensitive': is_sensitive,
                    'description': description
                }
                
                return True
                
        except Exception as e:
            print(f"Error setting configuration {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Видалити налаштування"""
        from database.models import DatabaseManager, SystemSettings
        
        try:
            with DatabaseManager() as db:
                setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
                if setting:
                    db.delete(setting)
                    db.commit()
                    
                    # Видаляємо з кешу
                    if key in self._cache:
                        del self._cache[key]
                    
                    return True
                
        except Exception as e:
            print(f"Error deleting configuration {key}: {e}")
        
        return False
    
    def get_category(self, category: str) -> dict:
        """Отримати всі налаштування категорії"""
        self._load_cache()
        
        result = {}
        for key, data in self._cache.items():
            if data['category'] == category:
                result[key] = data['value']
        
        return result
    
    def get_all_settings(self, include_sensitive: bool = False) -> dict:
        """Отримати всі налаштування"""
        self._load_cache()
        
        result = {}
        for key, data in self._cache.items():
            if not include_sensitive and data['is_sensitive']:
                result[key] = "***HIDDEN***"
            else:
                result[key] = data['value']
        
        return result
    
    def refresh_cache(self):
        """Оновити кеш налаштувань"""
        self._cache.clear()
        self._cache_loaded = False
        self._load_cache()


# Глобальний екземпляр менеджера налаштувань
settings_manager = SettingsManager()


def init_default_settings():
    """Ініціалізувати дефолтні налаштування системи"""
    from datetime import datetime
    
    default_settings = {
        # Bot settings
        'bot_token': {
            'value': os.getenv('BOT_TOKEN', ''),
            'category': 'bot',
            'is_sensitive': True,
            'description': 'Telegram Bot Token'
        },
        'webhook_url': {
            'value': os.getenv('WEBHOOK_URL', ''),
            'category': 'bot',
            'is_sensitive': False,
            'description': 'Webhook URL for bot'
        },
        
        # Payment settings
        'stripe_secret_key': {
            'value': os.getenv('STRIPE_SECRET_KEY', ''),
            'category': 'payment',
            'is_sensitive': True,
            'description': 'Stripe Secret Key'
        },
        'stripe_publishable_key': {
            'value': os.getenv('STRIPE_PUBLISHABLE_KEY', ''),
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Stripe Publishable Key'
        },
        'stripe_webhook_secret': {
            'value': os.getenv('STRIPE_WEBHOOK_SECRET', ''),
            'category': 'payment',
            'is_sensitive': True,
            'description': 'Stripe Webhook Secret'
        },
        'subscription_price': {
            'value': 1500,
            'value_type': 'integer',
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Subscription price in cents'
        },
        'subscription_currency': {
            'value': 'eur',
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Subscription currency'
        },
        
        # Database settings
        'database_url': {
            'value': os.getenv('DATABASE_URL', ''),
            'category': 'database',
            'is_sensitive': True,
            'description': 'Database connection URL'
        },
        
        # General settings
        'app_name': {
            'value': 'Upgrade Studio Bot',
            'category': 'general',
            'is_sensitive': False,
            'description': 'Application name'
        },
        'support_email': {
            'value': 'support@upgradestudio.com',
            'category': 'general',
            'is_sensitive': False,
            'description': 'Support email address'
        },
        'maintenance_mode': {
            'value': False,
            'value_type': 'boolean',
            'category': 'general',
            'is_sensitive': False,
            'description': 'Maintenance mode status'
        }
    }
    
    for key, config in default_settings.items():
        if config['value']:  # Тільки якщо значення не пусте
            settings_manager.set(
                key=key,
                value=config['value'],
                value_type=config.get('value_type', 'string'),
                category=config['category'],
                is_sensitive=config['is_sensitive'],
                description=config['description']
            )


# Імпорти для використання в моделях
from datetime import datetime