#!/usr/bin/env python3
"""
Скрипт для видалення старих і створення нових invite links з правильними параметрами
"""
import asyncio
from telegram import Bot
from config import settings
from database import DatabaseManager

async def recreate_invite_links():
    bot = Bot(token=settings.telegram_bot_token)
    
    async with bot:
        print("🗑️  Видалення старих посилань з бази даних...")
        
        # Видаляємо всі старі посилання
        with DatabaseManager() as db:
            from database.models import InviteLink
            old_links = db.query(InviteLink).all()
            for link in old_links:
                print(f"   Видалення: {link.link_type} - {link.invite_link}")
                db.delete(link)
            db.commit()
        
        print("\n✨ Створення нових invite links...\n")
        
        # Створюємо invite link для каналу
        print("📺 Канал:")
        try:
            channel_chat = await bot.get_chat(settings.private_channel_id)
            print(f"   Назва: {channel_chat.title}")
            
            channel_invite = await bot.create_chat_invite_link(
                chat_id=settings.private_channel_id,
                creates_join_request=True,
                name="Invite для каналу UPGRADE STUDIO"
            )
            
            # Зберігаємо в БД
            DatabaseManager.create_invite_link(
                chat_id=settings.private_channel_id,
                chat_type="channel",
                invite_link=channel_invite.invite_link,
                chat_title=channel_chat.title
            )
            
            print(f"   ✅ Створено: {channel_invite.invite_link}")
            print(f"   creates_join_request: True")
            
        except Exception as e:
            print(f"   ❌ Помилка: {e}")
        
        print("\n💬 Чат:")
        try:
            chat_chat = await bot.get_chat(settings.private_chat_id)
            print(f"   Назва: {chat_chat.title}")
            
            chat_invite = await bot.create_chat_invite_link(
                chat_id=settings.private_chat_id,
                creates_join_request=True,
                name="Invite для чату UPGRADE STUDIO"
            )
            
            # Зберігаємо в БД
            DatabaseManager.create_invite_link(
                chat_id=settings.private_chat_id,
                chat_type="group",
                invite_link=chat_invite.invite_link,
                chat_title=chat_chat.title
            )
            
            print(f"   ✅ Створено: {chat_invite.invite_link}")
            print(f"   creates_join_request: True")
            
        except Exception as e:
            print(f"   ❌ Помилка: {e}")
        
        print("\n" + "="*60)
        print("✅ Готово! Нові посилання створено та збережено в БД")

if __name__ == "__main__":
    asyncio.run(recreate_invite_links())
