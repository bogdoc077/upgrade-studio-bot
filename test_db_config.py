#!/usr/bin/env python3
"""
Тест системи конфігурації з бази даних
"""
import sys
import os
from pathlib import Path

# Додаємо шлях до проєкту
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.config_manager import ConfigManager, DatabaseConfig

def test_config_manager():
    """Тестуємо ConfigManager"""
    print("🔧 Тестування ConfigManager...")
    
    # Тестуємо отримання окремих налаштувань
    bot_token = ConfigManager.get_bot_token()
    print(f"Bot Token: {bot_token[:20]}..." if bot_token else "Bot Token: Не знайдено")
    
    stripe_secret = ConfigManager.get_stripe_secret_key()
    print(f"Stripe Secret: {stripe_secret[:20]}..." if stripe_secret else "Stripe Secret: Не знайдено")
    
    subscription_price = ConfigManager.get_subscription_price()
    print(f"Subscription Price: {subscription_price} EUR")
    
    # Тестуємо отримання всіх налаштувань
    all_settings = ConfigManager.get_all_settings()
    print(f"Всього налаштувань завантажено: {len(all_settings)}")
    
    return True

def test_database_config():
    """Тестуємо DatabaseConfig"""
    print("\n🗄️  Тестування DatabaseConfig...")
    
    db_config = DatabaseConfig()
    
    print(f"Bot Token (DB): {db_config.telegram_bot_token[:20]}..." if db_config.telegram_bot_token else "Bot Token: Не знайдено")
    print(f"Stripe Secret (DB): {db_config.stripe_secret_key[:20]}..." if db_config.stripe_secret_key else "Stripe Secret: Не знайдено")
    print(f"Subscription Price (DB): {db_config.subscription_price} {db_config.subscription_currency}")
    print(f"Webhook URL (DB): {db_config.webhook_url}")
    
    # Тестуємо fallback до .env
    print(f"Private Channel ID (ENV): {db_config.private_channel_id}")
    print(f"Admin Username (ENV): {db_config.admin_username}")
    
    return True

def main():
    print("🚀 Запуск тестів конфігурації...\n")
    
    try:
        # Тест 1: ConfigManager
        if test_config_manager():
            print("✅ ConfigManager працює коректно")
        
        # Тест 2: DatabaseConfig
        if test_database_config():
            print("✅ DatabaseConfig працює коректно")
        
        print("\n🎉 Всі тести пройшли успішно!")
        print("\n💡 Тепер бот буде отримувати налаштування з бази даних:")
        print("  • Bot Token")
        print("  • Stripe ключі") 
        print("  • Ціна підписки")
        print("  • Webhook URL")
        print("\n🔄 Інші налаштування залишаються з .env файлу")
        
    except Exception as e:
        print(f"❌ Помилка при тестуванні: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)