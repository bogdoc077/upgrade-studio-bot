#!/usr/bin/env python3
"""
Міграція для очищення і додавання тільки необхідних параметрів в system_settings
"""
import os
import sys
from datetime import datetime

# Додаємо шлях до проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.encryption import settings_manager
from database.models import DatabaseManager, SystemSettings

def cleanup_and_migrate_settings():
    """Очищає таблицю і додає тільки необхідні налаштування"""
    
    print("🧹 Очищення існуючих налаштувань...")
    
    with DatabaseManager() as db:
        # Очищаємо всі існуючі налаштування
        db.query(SystemSettings).delete()
        db.commit()
        print("✅ Таблиця system_settings очищена")
    
    print("\n📝 Додавання необхідних налаштувань...")
    
    # Список тестових налаштувань
    required_settings = [
        # Bot settings
        {
            'key': 'bot_token',
            'value': '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz',
            'category': 'bot',
            'is_sensitive': True,
            'description': 'Telegram Bot Token'
        },
        {
            'key': 'webhook_url',
            'value': 'https://example.com/webhook',
            'category': 'bot',
            'is_sensitive': False,
            'description': 'Webhook URL for Telegram bot'
        },
        
        # Stripe settings
        {
            'key': 'stripe_publishable_key',
            'value': 'pk_test_1234567890abcdef',
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Stripe Publishable Key'
        },
        {
            'key': 'stripe_secret_key',
            'value': 'sk_test_1234567890abcdef',
            'category': 'payment',
            'is_sensitive': True,
            'description': 'Stripe Secret Key'
        },
        {
            'key': 'stripe_webhook_secret',
            'value': 'whsec_1234567890abcdef',
            'category': 'payment',
            'is_sensitive': True,
            'description': 'Stripe Webhook Secret'
        },
        
        # Subscription settings
        {
            'key': 'subscription_price',
            'value': 15.00,  # EUR (без центів)
            'value_type': 'float',
            'category': 'payment',
            'is_sensitive': False,
            'description': 'Subscription price in EUR'
        }
    ]
    
    success_count = 0
    
    for setting in required_settings:
        success = settings_manager.set(
            key=setting['key'],
            value=setting['value'],
            value_type=setting.get('value_type', 'string'),
            category=setting['category'],
            is_sensitive=setting['is_sensitive'],
            description=setting['description'],
            updated_by=1  # Системний користувач
        )
        
        if success:
            print(f"✅ {setting['key']}: {'***HIDDEN***' if setting['is_sensitive'] else setting['value']}")
            success_count += 1
        else:
            print(f"❌ Помилка додавання {setting['key']}")
    
    print(f"\n🎉 Міграція завершена! Додано {success_count} налаштувань")
    
    # Виводимо поточні налаштування для перевірки
    print("\n📋 Поточні налаштування в базі:")
    all_settings = settings_manager.get_all_settings(include_sensitive=False)
    
    for key, value in all_settings.items():
        print(f"   {key}: {value}")

if __name__ == "__main__":
    cleanup_and_migrate_settings()