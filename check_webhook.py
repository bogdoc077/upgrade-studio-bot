#!/usr/bin/env python3
"""
Скрипт для перевірки налаштувань webhook
"""
import asyncio
from telegram import Bot
from config import settings

async def check_webhook():
    bot = Bot(token=settings.telegram_bot_token)
    
    print("Отримання інформації про webhook...")
    webhook_info = await bot.get_webhook_info()
    
    print(f"\n📌 Webhook Info:")
    print(f"  URL: {webhook_info.url}")
    print(f"  Has custom certificate: {webhook_info.has_custom_certificate}")
    print(f"  Pending update count: {webhook_info.pending_update_count}")
    print(f"  Last error date: {webhook_info.last_error_date}")
    print(f"  Last error message: {webhook_info.last_error_message}")
    print(f"  Max connections: {webhook_info.max_connections}")
    print(f"  Allowed updates: {webhook_info.allowed_updates}")
    print(f"  IP address: {webhook_info.ip_address}")
    
    if "chat_join_request" in (webhook_info.allowed_updates or []):
        print("\n✅ chat_join_request увімкнено в allowed_updates")
    else:
        print("\n❌ chat_join_request ВІДСУТНІЙ в allowed_updates!")
        print("   Потрібно оновити webhook з правильними allowed_updates")

if __name__ == "__main__":
    asyncio.run(check_webhook())
