"""
Конфігурація бота
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram Bot
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    
    # Stripe
    stripe_secret_key: str = Field(..., env="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(..., env="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    
    # Subscription settings
    subscription_price: int = Field(default=1500, env="SUBSCRIPTION_PRICE")  # в центах
    subscription_currency: str = Field(default="eur", env="SUBSCRIPTION_CURRENCY")
    
    # Telegram channels and groups
    private_channel_id: str = Field(..., env="PRIVATE_CHANNEL_ID")
    private_chat_id: str = Field(..., env="PRIVATE_CHAT_ID")
    admin_chat_id: str = Field(..., env="ADMIN_CHAT_ID")
    
    # Database
    database_url: str = Field(default="sqlite:///./upgrade_studio_bot.db", env="DATABASE_URL")
    
    # Web server for webhooks
    webhook_host: str = Field(default="0.0.0.0", env="WEBHOOK_HOST")
    webhook_port: int = Field(default=8000, env="WEBHOOK_PORT")
    webhook_path: str = Field(default="/webhook", env="WEBHOOK_PATH")
    webhook_url: str = Field(..., env="WEBHOOK_URL")  # https://yourdomain.com/webhook
    
    # Bot settings
    reminder_intervals: list[int] = Field(default=[1, 2], env="REMINDER_INTERVALS")  # дні
    subscription_reminder_days: int = Field(default=7, env="SUBSCRIPTION_REMINDER_DAYS")
    payment_retry_hours: int = Field(default=24, env="PAYMENT_RETRY_HOURS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальні налаштування
settings = Settings()

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
    BACK = "🔙 Назад"
    MAIN_MENU = "🏠 Головне меню"
    JOIN = "🎯 Приєднатися"
    SUBSCRIBE = "💳 Оформити підписку"
    MANAGE_SUBSCRIPTION = "⚙️ Керувати підпискою"
    SUPPORT = "💬 Підтримка"
    DASHBOARD = "📊 Дашборд"
    PAUSE_SUBSCRIPTION = "⏸️ Призупинити підписку"
    CANCEL_SUBSCRIPTION = "❌ Скасувати підписку"
    RESUME_SUBSCRIPTION = "▶️ Поновити підписку"

# Тексти повідомлень
class Messages:
    WELCOME = """
🎉 Вітаю у студії UPGRADE!

Я допоможу вам розпочати ваш фітнес-шлях та підключитися до нашої спільноти.

Давайте знайомитися! 👋
"""
    
    SURVEY_GOALS = """
🎯 **Яку ключову ціль занять ти переслідуєш?**

Оберіть те, що найкраще підходить 👇
"""
    
    SURVEY_INJURIES = """
🩺 **Чи є у тебе травми про які мені варто знати?**

Це допоможе краще підібрати програму тренувань для тебе.
"""
    
    SUBSCRIPTION_OFFER = """
💪 **Готові змінити своє життя?**

🔥 **UPGRADE STUDIO** — це не просто фітнес, це ваша трансформація!

✨ **Що вас чекає:**
• 🏋️‍♀️ Персональні тренування під ваші цілі
• 🍏 Індивідуальний план харчування  
• 👥 Приватна спільнота однодумців
• 📱 24/7 підтримка професійних тренерів
• 📊 Трекінг прогресу та досягнень
• 🎯 Мотивація та підзвітність

💳 **Щомісячна підписка:** {price} {currency}

🔄 **Гнучкість:**
• Можна скасувати будь-коли
• Призупинити на час відпустки  
• Керувати прямо в боті

🛡️ **Безпечна оплата через Stripe**
Ваші дані захищені банківським рівнем безпеки.

Почніть свій шлях до ідеальної форми вже сьогодні! 🚀
"""
    
    PAYMENT_SUCCESS = """
🎉 **Вітаю! Оплата успішна!**

Ваша підписка активована! Тепер ви — частина UPGRADE STUDIO.

📲 Що далі:
1. Приєднайтеся до наших приватних спільнот
2. Знайдіться з тренером  
3. Почніть свою трансформацію!

Ласкаво просимо в родину UPGRADE! 💪
"""
    
    CHANNEL_LINKS = """
📱 Ось ваші посилання:

Приєднуйтеся до наших приватних спільнот! 💪

❗️ Важливо: приєднайтеся протягом доби, інакше буду нагадувати 😊
"""
    
    REMINDER_JOIN = """
⏰ Нагадування!

Ви ще не приєдналися до каналу та чату. 
Для участі у тренуваннях обов'язково приєднайтеся!

❗️ Важливо: приєднайтеся протягом доби, інакше буду нагадувати 😊
"""
    
    SUBSCRIPTION_REMINDER = """
💳 Нагадування про оплату

Через 7 днів спишеться оплата за наступний місяць підписки.

Якщо потрібно щось змінити, скористайтеся меню "Керувати підпискою".
"""
    
    PAYMENT_FAILED = """
❌ Оплата не пройшла

У вас є 24 години для повторної спроби оплати.
Якщо оплата не пройде, підписка буде скасована.
"""
    
    SUBSCRIPTION_CANCELLED = """
😢 Підписка скасована

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
        "Всі пункти"
    ]
    
    INJURIES = [
        "Так",
        "Ні"
    ]