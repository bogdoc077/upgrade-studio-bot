"""
Конфігурація бота
"""
import os
import logging
from typing import Optional, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Telegram Bot - береться з БД якщо доступний, інакше з .env
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    
    # Stripe - беруться з БД якщо доступні, інакше з .env
    stripe_secret_key: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    stripe_publishable_key: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    
    # Subscription - береться з БД якщо доступна, інакше з .env
    subscription_price: int = Field(default=1500, env="SUBSCRIPTION_PRICE")  # в центах
    subscription_currency: str = Field(default="eur", env="SUBSCRIPTION_CURRENCY")
    
    # Webhook URL - береться з БД якщо доступний, інакше з .env
    webhook_url: Optional[str] = Field(default=None, env="WEBHOOK_URL")
    
    # Всі інші налаштування ТІЛЬКИ з .env (не керуються через адмін панель)
    private_channel_id: str = Field(..., env="PRIVATE_CHANNEL_ID")
    private_chat_id: str = Field(..., env="PRIVATE_CHAT_ID")
    admin_chat_id: str = Field(..., env="ADMIN_CHAT_ID")
    database_url: str = Field(default="sqlite:///./upgrade_studio_bot.db", env="DATABASE_URL")
    webhook_host: str = Field(default="0.0.0.0", env="WEBHOOK_HOST")
    webhook_port: int = Field(default=8000, env="WEBHOOK_PORT")
    webhook_path: str = Field(default="/webhook", env="WEBHOOK_PATH")
    reminder_intervals: List[int] = Field(default=[1, 2], env="REMINDER_INTERVALS")
    subscription_reminder_days: int = Field(default=7, env="SUBSCRIPTION_REMINDER_DAYS")
    payment_retry_hours: int = Field(default=24, env="PAYMENT_RETRY_HOURS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    admin_username: str = Field(default="admin", env="ADMIN_USERNAME")
    admin_password: str = Field(..., env="ADMIN_PASSWORD")
    admin_host: str = Field(default="0.0.0.0", env="ADMIN_HOST")
    admin_port: int = Field(default=8001, env="ADMIN_PORT")
    
    # Додаткові поля для production
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    admin_panel_port: int = Field(default=3000, env="ADMIN_PANEL_PORT")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    db_encryption_key: Optional[str] = Field(default=None, env="DB_ENCRYPTION_KEY")
    jwt_secret: Optional[str] = Field(default=None, env="JWT_SECRET")
    admin_default_password: str = Field(default="admin123", env="ADMIN_DEFAULT_PASSWORD")
    
    # Використовуємо model_config замість Config class
    model_config = {"extra": "allow", "env_file": ".env", "env_file_encoding": "utf-8"}
        
    def __init__(self, **kwargs):
        """Ініціалізуємо з автоматичним заповненням полів з БД"""
        # Спочатку ініціалізуємо базові налаштування
        super().__init__(**kwargs)
        
        # Заповнюємо обов'язкові поля з БД якщо вони не встановлені
        if not self.telegram_bot_token:
            self.telegram_bot_token = self._get_db_setting_simple('bot_token')
        if not self.stripe_secret_key:
            self.stripe_secret_key = self._get_db_setting_simple('stripe_secret_key')
        if not self.stripe_publishable_key:
            self.stripe_publishable_key = self._get_db_setting_simple('stripe_publishable_key')
        if not self.stripe_webhook_secret:
            self.stripe_webhook_secret = self._get_db_setting_simple('stripe_webhook_secret')
        if not self.webhook_url:
            self.webhook_url = self._get_db_setting_simple('webhook_url')
    
    def _get_db_setting_simple(self, key: str) -> Optional[str]:
        """Простий метод для отримання налаштування з БД без fallback"""
        try:
            from database.models import get_database
            from database.encryption import decrypt_setting
            
            db = get_database()
            cursor = db.cursor(dictionary=True)
            
            try:
                cursor.execute(
                    "SELECT value_type, encrypted_value FROM system_settings WHERE `key` = %s",
                    (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    return decrypt_setting(
                        result['encrypted_value'], 
                        result['value_type']
                    )
                return None
                    
            finally:
                cursor.close()
                db.close()
                
        except Exception as e:
            logger.debug(f"Помилка при отриманні налаштування '{key}' з БД: {e}")
            return None
    
    def _get_db_setting(self, key: str, fallback_value: Any) -> Any:
        """Отримати налаштування з бази даних з fallback до .env"""
        try:
            from database.models import get_database
            from database.encryption import decrypt_setting
            
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
                    return decrypted_value
                else:
                    logger.debug(f"Налаштування '{key}' не знайдено в базі, використовуємо .env")
                    return fallback_value
                    
            finally:
                cursor.close()
                db.close()
                
        except Exception as e:
            logger.debug(f"Помилка при отриманні налаштування '{key}' з БД: {e}, використовуємо .env")
            return fallback_value
    
    # Перевизначаємо ТІЛЬКИ ті поля, що керуються через адмін панель (6 штук)
    def __getattribute__(self, name):
        """Перехоплюємо доступ до полів, що керуються через адмін панель"""
        # Поля з адмін панелі - беремо з БД
        if name == 'telegram_bot_token':
            return self._get_db_setting('bot_token', super().__getattribute__(name))
        elif name == 'stripe_secret_key':
            return self._get_db_setting('stripe_secret_key', super().__getattribute__(name))
        elif name == 'stripe_publishable_key':
            return self._get_db_setting('stripe_publishable_key', super().__getattribute__(name))
        elif name == 'stripe_webhook_secret':
            return self._get_db_setting('stripe_webhook_secret', super().__getattribute__(name))
        elif name == 'subscription_price':
            # Особлива логіка для ціни - в БД в євро, в .env в центах
            db_price = self._get_db_setting('subscription_price', None)
            if db_price is not None:
                return float(db_price)  # З БД - вже в євро
            else:
                return super().__getattribute__(name) / 100.0  # З .env - конвертуємо центи в євро
        elif name == 'webhook_url':
            return self._get_db_setting('webhook_url', super().__getattribute__(name))
        
        # Всі інші поля - беремо з .env як завжди
        return super().__getattribute__(name)


    def invalidate_cache(self):
        """Очистити кеш налаштувань (просто recreate екземпляр)"""
        # Pydantic автоматично перезавантажить .env, а БД буде перевірена знову
        self.__init__()
        logger.info("Кеш налаштувань очищено")


# Глобальні налаштування - тепер з автоматичною підтримкою БД
settings = Settings()

# Admin panel settings (for convenience)
ADMIN_USERNAME = settings.admin_username
ADMIN_PASSWORD = settings.admin_password

# Константи для стану користувачів
class UserState:
    REGISTRATION = "registration"
    SURVEY_GOALS = "survey_goals"
    SURVEY_GOALS_CUSTOM = "survey_goals_custom"
    SURVEY_INJURIES = "survey_injuries"
    SURVEY_INJURIES_CUSTOM = "survey_injuries_custom"
    SUBSCRIPTION_OFFER = "subscription_offer"
    REMINDER_SET = "reminder_set"
    ACTIVE_SUBSCRIPTION = "active_subscription"
    PAYMENT_PENDING = "payment_pending"
    SUBSCRIPTION_PAUSED = "subscription_paused"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    CHANNEL_JOIN_PENDING = "channel_join_pending"
    CHAT_JOIN_PENDING = "chat_join_pending"

# Константи для кнопок
class Buttons:
    BACK = "↩️ Назад"
    MAIN_MENU = "🎛 Головне меню"
    JOIN = "Приєднатися"
    SUBSCRIBE = "🟢 Оформити підписку"
    MANAGE_SUBSCRIPTION = "⚙️ Керувати підпискою"
    SUPPORT = "⁉️ Підтримка"
    DASHBOARD = "📊 Дашборд"
    PAUSE_SUBSCRIPTION = "🟠 Призупинити підписку"
    CANCEL_SUBSCRIPTION = "🔴 Скасувати підписку"
    RESUME_SUBSCRIPTION = "🟢 Поновити підписку"

# Тексти повідомлень
class Messages:
    WELCOME = """
 Вітаю у студії UPGRADE!

Я допоможу вам розпочати ваш фітнес-шлях та підключитися до нашої спільноти.

Давайте знайомитися! 
"""
    
    SURVEY_GOALS = """
Яку ключову ціль занять ти переслідуєш?
"""
    
    SURVEY_INJURIES = """
Чи є у тебе травми про які мені варто знати?
"""
    
    SUBSCRIPTION_OFFER = """
 **Готові змінити своє життя?**

 **UPGRADE STUDIO** — це не просто фітнес, це ваша трансформація!

 **Що вас чекає:**
• ‍ Персональні тренування під ваші цілі
•  Індивідуальний план харчування  
•  Приватна спільнота однодумців
•  24/7 підтримка професійних тренерів
•  Трекінг прогресу та досягнень
•  Мотивація та підзвітність

 **Щомісячна підписка:** {price} {currency}

 **Гнучкість:**
• Можна скасувати будь-коли
• Призупинити на час відпустки  
• Керувати прямо в боті

 **Безпечна оплата через Stripe**
Ваші дані захищені банківським рівнем безпеки.

Почніть свій шлях до ідеальної форми вже сьогодні! 
"""
    
    PAYMENT_SUCCESS = """
 **Вітаю! Оплата успішна!**

Ваша підписка активована! Тепер ви — частина UPGRADE STUDIO.

 Що далі:
1. Приєднайтеся до наших приватних спільнот
2. Знайдіться з тренером  
3. Почніть свою трансформацію!

Ласкаво просимо в родину UPGRADE! 
"""
    
    CHANNEL_LINKS = """
 Ось ваші посилання:

Приєднуйтеся до наших приватних спільнот! 

 Важливо: приєднайтеся протягом доби, інакше буду нагадувати 
"""
    
    REMINDER_JOIN = """
⏰ Нагадування!

Ви ще не приєдналися до каналу та чату. 
Для участі у тренуваннях обов'язково приєднайтеся!

 Важливо: приєднайтеся протягом доби, інакше буду нагадувати 
"""
    
    SUBSCRIPTION_REMINDER = """
 Нагадування про оплату

Через 7 днів спишеться оплата за наступний місяць підписки.

Якщо потрібно щось змінити, скористайтеся меню "Керувати підпискою".
"""
    
    PAYMENT_FAILED = """
 Оплата не пройшла

У вас є 24 години для повторної спроби оплати.
Якщо оплата не пройде, підписка буде скасована.
"""
    
    SUBSCRIPTION_CANCELLED = """
 Підписка скасована

Ви були видалені з приватного каналу та чату.
Для поновлення підписки скористайтеся кнопкою нижче.
"""

# Варіанти відповідей для опитування
class SurveyOptions:
    GOALS = [
        "Підтягнути тіло",
        "Зменшити стрес",
        "Здоров'я спини",
        "Жіноче здоров'я",
        "Всі пункти",
        "Свій варіант"
    ]
    
    INJURIES = [
        "Так",
        "Ні"
    ]