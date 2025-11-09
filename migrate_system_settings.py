#!/usr/bin/env python3
"""
Міграція для додавання тестових налаштувань у таблицю system_settings
"""
import os
import sys
from datetime import datetime
from database.encryption import settings_manager, encrypt_setting
from database.models import DatabaseManager, SystemSettings, get_database

def create_system_settings_test_data():
    """Створити тестові дані для налаштувань системи"""
    
    print("🚀 Початок міграції system_settings...")
    
    # Дефолтні налаштування з .env файлу та додаткові тестові
    default_settings = {
        # Bot settings
        'bot_token': {
            'value': os.getenv('TELEGRAM_BOT_TOKEN', '8337284451:AAHKz-zoAdB3J6RpsAronFhVzaYl8i-HKGY'),
            'category': 'bot',
            'is_sensitive': True,
            'description': 'Telegram Bot Token отриманий у @BotFather'
        },
        'webhook_url': {
            'value': os.getenv('WEBHOOK_URL', 'https://sherice-unhot-maliyah.ngrok-free.dev/webhook'),
            'category': 'bot', 
            'is_sensitive': False,
            'description': 'URL webhook для Telegram бота'
        },
        
        # Stripe settings
        'stripe_secret_key': {
            'value': os.getenv('STRIPE_SECRET_KEY', 'sk_test_51SPUxNRdq7wlUZXE2mBV6x3iODBC5UarT92AlHJMB8cVE1PFRb0Ka4QOx28GIuzEZEz44DFBzC8bKjd9xJoxQyps00HBQzoiTK'),
            'category': 'payment',
            'is_sensitive': True,
            'description': 'Stripe Secret Key для обробки платежів'
        },
        'stripe_publishable_key': {
            'value': os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_51SPUxNRdq7wlUZXEOglTtiOkKhGx9cM9ElUIzoEiqLU8naUKS4tXEq2oaQLqa7u0t4hu1eSMJx9yt0DJyg7dBjMv00GsN04KEc'),
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Stripe Publishable Key для фронтенду'
        },
        'stripe_webhook_secret': {
            'value': os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_2VpuZg2oSVs6sJMMdTXnFRgvXkvBgfTT'),
            'category': 'payment',
            'is_sensitive': True,
            'description': 'Stripe Webhook Secret для верифікації подій'
        },
        
        # Subscription settings
        'subscription_price': {
            'value': int(os.getenv('SUBSCRIPTION_PRICE', '1500')),  # 15.00 EUR у центах
            'value_type': 'integer',
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Вартість підписки у центах (1500 = 15.00 EUR)'
        },
        'subscription_currency': {
            'value': os.getenv('SUBSCRIPTION_CURRENCY', 'eur'),
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Валюта підписки'
        },
        
        # Database settings
        'database_url': {
            'value': os.getenv('DATABASE_URL', ''),
            'category': 'database',
            'is_sensitive': True,
            'description': 'URL підключення до бази даних'
        },
        
        # General settings
        'app_name': {
            'value': 'Upgrade Studio Bot',
            'category': 'general',
            'is_sensitive': False,
            'description': 'Назва додатку'
        },
        'support_email': {
            'value': 'support@upgradestudio.com',
            'category': 'general',
            'is_sensitive': False,
            'description': 'Email для підтримки'
        },
        'maintenance_mode': {
            'value': False,
            'value_type': 'boolean',
            'category': 'general',
            'is_sensitive': False,
            'description': 'Режим технічного обслуговування'
        },
        
        # JWT settings
        'jwt_secret': {
            'value': 'upgrade-studio-jwt-secret-key-change-in-production-2024',
            'category': 'auth',
            'is_sensitive': True,
            'description': 'Секретний ключ для JWT токенів'
        },
        
        # Admin settings
        'admin_session_timeout': {
            'value': 24,
            'value_type': 'integer',
            'category': 'admin',
            'is_sensitive': False,
            'description': 'Час життя адмін сесії у годинах'
        },
        
        # Channel/Chat settings
        'private_channel_id': {
            'value': os.getenv('PRIVATE_CHANNEL_ID', '-1002747224769'),
            'category': 'channels',
            'is_sensitive': False,
            'description': 'ID приватного каналу'
        },
        'private_chat_id': {
            'value': os.getenv('PRIVATE_CHAT_ID', '-5046931710'),
            'category': 'channels',
            'is_sensitive': False,
            'description': 'ID приватного чату'
        },
        'admin_chat_id': {
            'value': os.getenv('ADMIN_CHAT_ID', '578080052'),
            'category': 'channels',
            'is_sensitive': False,
            'description': 'ID адмін чату'
        },
        
        # Reminder settings
        'reminder_intervals': {
            'value': '[1,2]',
            'value_type': 'json',
            'category': 'reminders',
            'is_sensitive': False,
            'description': 'Інтервали нагадувань у днях (JSON array)'
        },
        'subscription_reminder_days': {
            'value': int(os.getenv('SUBSCRIPTION_REMINDER_DAYS', '7')),
            'value_type': 'integer',
            'category': 'reminders',
            'is_sensitive': False,
            'description': 'Нагадування про підписку за скільки днів'
        },
        'payment_retry_hours': {
            'value': int(os.getenv('PAYMENT_RETRY_HOURS', '24')),
            'value_type': 'integer',
            'category': 'reminders',
            'is_sensitive': False,
            'description': 'Через скільки годин повторити спробу платежу'
        }
    }
    
    try:
        # Використовуємо прямий доступ до бази для міграції
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        added_count = 0
        updated_count = 0
        
        for key, config in default_settings.items():
            # Перевіряємо чи існує налаштування
            cursor.execute("SELECT id, encrypted_value FROM system_settings WHERE `key` = %s", (key,))
            existing = cursor.fetchone()
            
            # Шифруємо значення
            encrypted_value = encrypt_setting(config['value'])
            
            if existing:
                # Оновлюємо існуюче налаштування
                cursor.execute("""
                    UPDATE system_settings 
                    SET encrypted_value = %s, 
                        description = %s,
                        value_type = %s,
                        category = %s,
                        is_sensitive = %s,
                        updated_at = %s
                    WHERE `key` = %s
                """, (
                    encrypted_value,
                    config['description'],
                    config.get('value_type', 'string'),
                    config['category'],
                    config['is_sensitive'],
                    datetime.utcnow(),
                    key
                ))
                updated_count += 1
                print(f"✅ Оновлено: {key}")
            else:
                # Створюємо нове налаштування
                cursor.execute("""
                    INSERT INTO system_settings 
                    (`key`, encrypted_value, description, value_type, category, is_sensitive, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    key,
                    encrypted_value,
                    config['description'],
                    config.get('value_type', 'string'),
                    config['category'],
                    config['is_sensitive'],
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                added_count += 1
                print(f"➕ Додано: {key}")
        
        # Комітимо зміни
        db.commit()
        
        print(f"\n🎉 Міграція завершена успішно!")
        print(f"📊 Статистика:")
        print(f"   • Додано нових налаштувань: {added_count}")
        print(f"   • Оновлено існуючих: {updated_count}")
        print(f"   • Загалом налаштувань: {len(default_settings)}")
        
        # Перевіримо що все збереглося
        cursor.execute("SELECT COUNT(*) as count FROM system_settings")
        total_count = cursor.fetchone()['count']
        print(f"   • Всього в базі: {total_count}")
        
        # Показати категорії
        cursor.execute("SELECT category, COUNT(*) as count FROM system_settings GROUP BY category ORDER BY category")
        categories = cursor.fetchall()
        print(f"\n📋 По категоріях:")
        for cat in categories:
            cursor.execute("SELECT `key` FROM system_settings WHERE category = %s ORDER BY `key`", (cat['category'],))
            keys = [row['key'] for row in cursor.fetchall()]
            print(f"   • {cat['category']}: {cat['count']} ({', '.join(keys)})")
        
    except Exception as e:
        print(f"❌ Помилка міграції: {e}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

def verify_settings():
    """Перевірити що налаштування доступні через SettingsManager"""
    print("\n🔍 Перевірка доступності налаштувань через SettingsManager...")
    
    # Очистити кеш щоб перезавантажити дані
    settings_manager.refresh_cache()
    
    # Тестові ключі для перевірки
    test_keys = [
        ('bot_token', 'bot'),
        ('webhook_url', 'bot'), 
        ('stripe_secret_key', 'payment'),
        ('stripe_publishable_key', 'payment'),
        ('stripe_webhook_secret', 'payment'),
        ('subscription_price', 'payment'),
        ('subscription_currency', 'payment')
    ]
    
    print("📋 Тестування ключових налаштувань:")
    for key, category in test_keys:
        value = settings_manager.get(key)
        if value is not None:
            if key in ['bot_token', 'stripe_secret_key', 'stripe_webhook_secret']:
                # Не показуємо повні чутливі дані
                display_value = f"{str(value)[:10]}..." if len(str(value)) > 10 else "***"
            else:
                display_value = str(value)
            print(f"   ✅ {key} ({category}): {display_value}")
        else:
            print(f"   ❌ {key} ({category}): НЕ ЗНАЙДЕНО")
    
    # Перевірка по категоріях
    print(f"\n📂 Перевірка по категоріях:")
    categories = ['bot', 'payment', 'general', 'channels', 'reminders']
    for category in categories:
        category_settings = settings_manager.get_category(category)
        print(f"   • {category}: {len(category_settings)} налаштувань")

if __name__ == "__main__":
    print("🔧 Міграція налаштувань системи (system_settings)")
    print("=" * 50)
    
    try:
        # Створюємо тестові дані
        create_system_settings_test_data()
        
        # Перевіряємо що все працює
        verify_settings()
        
        print(f"\n✨ Всі операції завершені успішно!")
        print(f"🎯 Тепер можна тестувати налаштування в адмін-панелі")
        
    except Exception as e:
        print(f"\n💥 Критична помилка: {e}")
        sys.exit(1)