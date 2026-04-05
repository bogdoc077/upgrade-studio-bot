#!/usr/bin/env python3
"""
Скрипт для перевірки прав бота в каналі та чаті
"""
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from config import settings
from database import DatabaseManager

async def check_permissions():
    bot = Bot(token=settings.telegram_bot_token)
    
    # Ініціалізуємо бота
    async with bot:
        print("🔍 Перевірка прав бота...\n")
        await _check_permissions(bot)

async def _check_permissions(bot):
    """Внутрішня функція для перевірки"""
    
    # Перевіряємо канал
    print(f"📺 Канал (ID: {settings.private_channel_id}):")
    try:
        chat = await bot.get_chat(settings.private_channel_id)
        print(f"   Назва: {chat.title}")
        print(f"   Тип: {chat.type}")
        
        member = await bot.get_chat_member(settings.private_channel_id, bot.id)
        print(f"   Статус бота: {member.status}")
        
        if member.status == "administrator":
            print(f"   ✅ Бот є адміністратором")
            print(f"   Права:")
            print(f"     - can_invite_users: {member.can_invite_users}")
            print(f"     - can_restrict_members: {member.can_restrict_members}")
        else:
            print(f"   ❌ Бот НЕ є адміністратором!")
    except TelegramError as e:
        print(f"   ❌ Помилка: {e}")
    
    print()
    
    # Перевіряємо чат
    print(f"💬 Чат (ID: {settings.private_chat_id}):")
    try:
        chat = await bot.get_chat(settings.private_chat_id)
        print(f"   Назва: {chat.title}")
        print(f"   Тип: {chat.type}")
        
        member = await bot.get_chat_member(settings.private_chat_id, bot.id)
        print(f"   Статус бота: {member.status}")
        
        if member.status == "administrator":
            print(f"   ✅ Бот є адміністратором")
            print(f"   Права:")
            print(f"     - can_invite_users: {member.can_invite_users}")
            print(f"     - can_restrict_members: {member.can_restrict_members}")
        else:
            print(f"   ❌ Бот НЕ є адміністратором!")
    except TelegramError as e:
        print(f"   ❌ Помилка: {e}")
    
    print("\n" + "="*60)
    print("📋 Посилання в базі даних:\n")
    
    # Перевіряємо посилання в БД
    links = DatabaseManager.get_active_invite_links()
    if links:
        for link in links:
            print(f"   Тип: {link.link_type}")
            print(f"   Chat ID: {link.chat_id}")
            print(f"   Назва: {link.chat_title}")
            print(f"   Посилання: {link.invite_link}")
            print(f"   Активне: {link.is_active}")
            print(f"   Прострочене: {link.is_expired}")
            print()
    else:
        print("   ❌ Посилання не знайдено в базі даних!")

if __name__ == "__main__":
    asyncio.run(check_permissions())
