"""
Скрипт для тестування автоматичного видалення користувачів з закінченою підпискою
"""
import asyncio
import sys
from datetime import datetime
from database.models import DatabaseManager, User
from config import settings
from telegram import Bot
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def remove_user_from_chats(bot: Bot, telegram_id: int):
    """Видалити користувача з приватних каналів та чатів"""
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"ВИДАЛЕННЯ КОРИСТУВАЧА З ПРИВАТНИХ ЧАТІВ")
        logger.info(f"{'='*60}")
        logger.info(f"Telegram ID: {telegram_id}")
        
        # Видаляємо з приватного каналу
        if settings.private_channel_id:
            try:
                logger.info(f"Видалення з каналу {settings.private_channel_id}...")
                await bot.ban_chat_member(
                    chat_id=settings.private_channel_id,
                    user_id=telegram_id
                )
                # Одразу розбаніваємо, щоб користувач міг приєднатися знову при поновленні
                await bot.unban_chat_member(
                    chat_id=settings.private_channel_id,
                    user_id=telegram_id
                )
                logger.info(f"✅ Користувача видалено з каналу")
            except Exception as e:
                logger.error(f"❌ Помилка при видаленні з каналу: {e}")
        
        # Видаляємо з приватного чату
        if settings.private_chat_id:
            try:
                logger.info(f"Видалення з чату {settings.private_chat_id}...")
                await bot.ban_chat_member(
                    chat_id=settings.private_chat_id,
                    user_id=telegram_id
                )
                logger.info(f"✅ Користувача видалено з чату")
                
                # Одразу розбаніваємо (для звичайних груп це може не працювати - це нормально)
                try:
                    await bot.unban_chat_member(
                        chat_id=settings.private_chat_id,
                        user_id=telegram_id
                    )
                    logger.info(f"✅ Користувача розбановано (може приєднатися знову)")
                except Exception as unban_error:
                    # Ігноруємо помилки unban для звичайних груп
                    logger.info(f"ℹ️ Unban не підтримується для цього типу чату (це нормально)")
            except Exception as e:
                logger.error(f"❌ Помилка при видаленні з чату: {e}")
        
        # Надсилаємо повідомлення користувачу
        try:
            logger.info(f"Надсилання повідомлення користувачу...")
            await bot.send_message(
                chat_id=telegram_id,
                text="""⚠️ **Ваша підписка закінчилась**

Доступ до приватних каналів та чатів було закрито.

Щоб продовжити користуватися сервісом:
1. Поновіть підписку через /start
2. Або зв'яжіться з підтримкою

Дякуємо, що були з нами! 💙""",
                parse_mode='Markdown'
            )
            logger.info(f"✅ Повідомлення надіслано")
        except Exception as e:
            logger.error(f"❌ Не вдалось надіслати повідомлення: {e}")
        
        logger.info(f"{'='*60}\n")
                
    except Exception as e:
        logger.error(f"Помилка при видаленні користувача {telegram_id} з чатів: {e}")


async def test_remove_expired_user(telegram_id: int):
    """Тестувати видалення конкретного користувача"""
    try:
        # Перевіряємо користувача в БД
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                logger.error(f"Користувач {telegram_id} не знайдений")
                return
            
            logger.info(f"\nКористувач: {user.first_name} (@{user.username})")
            logger.info(f"Підписка активна: {user.subscription_active}")
            logger.info(f"Joined channel: {user.joined_channel}")
            logger.info(f"Joined chat: {user.joined_chat}")
            logger.info(f"Дата закінчення: {user.subscription_end_date}")
        
        # Створюємо бот
        bot = Bot(token=settings.telegram_bot_token)
        
        # Видаляємо з чатів
        await remove_user_from_chats(bot, telegram_id)
        
        # Оновлюємо статуси в БД
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.subscription_active = False
                user.joined_channel = False
                user.joined_chat = False
                db.commit()
                logger.info(f"✅ Статуси в БД оновлено")
        
    except Exception as e:
        logger.error(f"Помилка: {e}")
        import traceback
        traceback.print_exc()


async def test_all_expired():
    """Перевірити всіх користувачів з закінченими підписками"""
    try:
        now = datetime.utcnow()
        
        with DatabaseManager() as db:
            expired_users = db.query(User).filter(
                User.subscription_end_date.isnot(None),
                User.subscription_end_date <= now,
                User.subscription_active == True
            ).all()
            
            if not expired_users:
                logger.info("Користувачів з закінченими підписками не знайдено")
                return
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ЗНАЙДЕНО {len(expired_users)} КОРИСТУВАЧІВ З ЗАКІНЧЕНИМИ ПІДПИСКАМИ")
            logger.info(f"{'='*60}")
            
            for user in expired_users:
                logger.info(f"\n{user.first_name} (@{user.username})")
                logger.info(f"  Telegram ID: {user.telegram_id}")
                logger.info(f"  Дата закінчення: {user.subscription_end_date}")
                logger.info(f"  Joined channel: {user.joined_channel}")
                logger.info(f"  Joined chat: {user.joined_chat}")
        
        # Питаємо чи обробляти всіх
        response = input("\nОбробити всіх користувачів? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Скасовано")
            return
        
        # Створюємо бот
        bot = Bot(token=settings.telegram_bot_token)
        
        # Обробляємо кожного
        for user in expired_users:
            logger.info(f"\n\nОбробка користувача {user.telegram_id}...")
            await remove_user_from_chats(bot, user.telegram_id)
            
            # Оновлюємо статуси
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.id == user.id).first()
                if db_user:
                    db_user.subscription_active = False
                    db_user.joined_channel = False
                    db_user.joined_chat = False
                    db.commit()
        
        logger.info(f"\n✅ Оброблено {len(expired_users)} користувачів")
        
    except Exception as e:
        logger.error(f"Помилка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Використання:")
        print("  python test_remove_expired_users.py <telegram_id>  # Видалити конкретного користувача")
        print("  python test_remove_expired_users.py all            # Показати всіх з закінченими підписками")
        print("\nПриклад:")
        print("  python test_remove_expired_users.py 578080052")
        print("  python test_remove_expired_users.py all")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "all":
        asyncio.run(test_all_expired())
    else:
        telegram_id = int(action)
        asyncio.run(test_remove_expired_user(telegram_id))
