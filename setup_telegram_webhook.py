#!/usr/bin/env python3
"""
Налаштування Telegram webhook для production
"""
import asyncio
import sys
from telegram import Bot
from config import settings

async def setup_telegram_webhook():
    """Встановити Telegram webhook"""
    bot = Bot(token=settings.telegram_bot_token)
    
    # Формуємо URL для webhook
    webhook_url = settings.webhook_url
    if not webhook_url:
        print("❌ WEBHOOK_URL не налаштовано в .env або БД")
        print("   Додайте: WEBHOOK_URL=https://yourdomain.com")
        return False
    
    # Видаляємо /webhook якщо є в кінці
    if webhook_url.endswith('/webhook'):
        webhook_url = webhook_url[:-8]
    
    telegram_webhook_url = f"{webhook_url}/telegram-webhook"
    
    print(f"🔧 Налаштування Telegram webhook...")
    print(f"   URL: {telegram_webhook_url}")
    
    try:
        # Видаляємо старий webhook (якщо є)
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Старий webhook видалено")
        
        # Встановлюємо новий webhook
        await bot.set_webhook(
            url=telegram_webhook_url,
            max_connections=100,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "my_chat_member"]
        )
        print("✅ Новий webhook встановлено")
        
        # Перевіряємо webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n📊 Інформація про webhook:")
        print(f"   URL: {webhook_info.url}")
        print(f"   Pending updates: {webhook_info.pending_update_count}")
        print(f"   Max connections: {webhook_info.max_connections}")
        
        if webhook_info.last_error_date:
            print(f"   ⚠️ Остання помилка: {webhook_info.last_error_message}")
        else:
            print(f"   ✅ Помилок немає")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка налаштування webhook: {e}")
        return False


async def delete_webhook():
    """Видалити Telegram webhook (повернутись до polling)"""
    bot = Bot(token=settings.telegram_bot_token)
    
    print("🔧 Видалення Telegram webhook...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook видалено. Бот повернувся до polling режиму.")
        return True
    except Exception as e:
        print(f"❌ Помилка видалення webhook: {e}")
        return False


async def check_webhook():
    """Перевірити статус Telegram webhook"""
    bot = Bot(token=settings.telegram_bot_token)
    
    print("🔍 Перевірка Telegram webhook...")
    try:
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url:
            print(f"✅ Webhook активний:")
            print(f"   URL: {webhook_info.url}")
            print(f"   Pending updates: {webhook_info.pending_update_count}")
            print(f"   Max connections: {webhook_info.max_connections}")
            
            if webhook_info.last_error_date:
                from datetime import datetime
                error_date = datetime.fromtimestamp(webhook_info.last_error_date)
                print(f"   ⚠️ Остання помилка ({error_date}):")
                print(f"      {webhook_info.last_error_message}")
            else:
                print(f"   ✅ Помилок немає")
        else:
            print("❌ Webhook не налаштовано (використовується polling)")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка перевірки webhook: {e}")
        return False


def main():
    """Головна функція"""
    if len(sys.argv) < 2:
        print("Використання:")
        print("  python setup_telegram_webhook.py setup   - Встановити webhook")
        print("  python setup_telegram_webhook.py delete  - Видалити webhook")
        print("  python setup_telegram_webhook.py check   - Перевірити webhook")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        result = asyncio.run(setup_telegram_webhook())
    elif command == "delete":
        result = asyncio.run(delete_webhook())
    elif command == "check":
        result = asyncio.run(check_webhook())
    else:
        print(f"❌ Невідома команда: {command}")
        return 1
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
