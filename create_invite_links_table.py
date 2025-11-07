#!/usr/bin/env python3
"""
Створення таблиці invite_links та додавання початкових даних
"""

from database import DatabaseManager, create_tables, InviteLink

def main():
    """Створити таблиці та додати початкові дані"""
    print("Створення таблиць...")
    create_tables()
    
    print("Додавання початкових посилань запрошення...")
    
    # Додаємо тестові посилання (замініть на реальні)
    channel_link = DatabaseManager.add_invite_link(
        chat_type="channel",
        invite_link="https://t.me/+YOUR_CHANNEL_INVITE_LINK",
        chat_id="-1002747224769",
        chat_title="Основний канал UPGRADE STUDIO"
    )
    
    chat_link = DatabaseManager.add_invite_link(
        chat_type="chat",
        invite_link="https://t.me/+YOUR_CHAT_INVITE_LINK", 
        chat_id="-5046931710",
        chat_title="Чат спільноти UPGRADE STUDIO"
    )
    
    print(f"Додано посилання каналу: {channel_link.chat_title}")
    print(f"Додано посилання чату: {chat_link.chat_title}")
    
    print("Готово! Тепер оновіть посилання в базі даних:")
    print("1. Увійдіть в адмін панель бота")
    print("2. Або оновіть посилання через SQL:")
    print(f"   UPDATE invite_links SET invite_link='https://t.me/+REAL_CHANNEL_LINK' WHERE id={channel_link.id};")
    print(f"   UPDATE invite_links SET invite_link='https://t.me/+REAL_CHAT_LINK' WHERE id={chat_link.id};")

if __name__ == "__main__":
    main()