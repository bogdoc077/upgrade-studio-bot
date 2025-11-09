#!/usr/bin/env python3
"""
Міграція бази даних для оновлення структури таблиць
"""
import sys
import logging
from pathlib import Path

# Додаємо шлях до проєкту
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import engine
from config import settings

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Виконати міграцію бази даних"""
    try:
        from sqlalchemy import text
        logger.info("🔄 Виконання міграції бази даних...")
        
        with engine.connect() as connection:
            # Додаємо відсутні поля до таблиці users
            logger.info("Додавання поля subscription_status до таблиці users...")
            try:
                connection.execute(text("ALTER TABLE users ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'inactive'"))
                connection.commit()
                logger.info("✅ Поле subscription_status додано")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    logger.info("⚠️  Поле subscription_status вже існує")
                else:
                    logger.error(f"❌ Помилка додавання subscription_status: {e}")
            
            # Додаємо відсутні поля до таблиці payments
            logger.info("Додавання поля updated_at до таблиці payments...")
            try:
                connection.execute(text("ALTER TABLE payments ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
                connection.commit()
                logger.info("✅ Поле updated_at додано до payments")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    logger.info("⚠️  Поле updated_at в payments вже існує")
                else:
                    logger.error(f"❌ Помилка додавання updated_at до payments: {e}")
            
            # Оновлюємо таблицю invite_links
            logger.info("Оновлення структури таблиці invite_links...")
            
            # Додаємо нові поля
            try:
                connection.execute(text("ALTER TABLE invite_links ADD COLUMN link_type VARCHAR(20)"))
                connection.commit()
                logger.info("✅ Поле link_type додано")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    logger.info("⚠️  Поле link_type вже існує")
                else:
                    logger.error(f"❌ Помилка додавання link_type: {e}")
                    
            try:
                connection.execute(text("ALTER TABLE invite_links ADD COLUMN link VARCHAR(255)"))
                connection.commit()
                logger.info("✅ Поле link додано")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    logger.info("⚠️  Поле link вже існує")
                else:
                    logger.error(f"❌ Помилка додавання link: {e}")
                    
            try:
                connection.execute(text("ALTER TABLE invite_links ADD COLUMN created_by INTEGER"))
                connection.commit()
                logger.info("✅ Поле created_by додано")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    logger.info("⚠️  Поле created_by вже існує")
                else:
                    logger.error(f"❌ Помилка додавання created_by: {e}")
                    
            try:
                connection.execute(text("ALTER TABLE invite_links ADD COLUMN expires_at DATETIME"))
                connection.commit()
                logger.info("✅ Поле expires_at додано")
            except Exception as e:
                if "Duplicate column name" in str(e):
                    logger.info("⚠️  Поле expires_at вже існує")
                else:
                    logger.error(f"❌ Помилка додавання expires_at: {e}")
            
            # Копіюємо дані зі старих полів у нові (якщо потрібно)
            logger.info("Копіювання даних зі старих полів...")
            try:
                # Копіюємо chat_type -> link_type
                connection.execute(text("UPDATE invite_links SET link_type = chat_type WHERE link_type IS NULL"))
                # Копіюємо invite_link -> link  
                connection.execute(text("UPDATE invite_links SET link = invite_link WHERE link IS NULL"))
                connection.commit()
                logger.info("✅ Дані скопійовані")
            except Exception as e:
                logger.error(f"❌ Помилка копіювання даних: {e}")
        
        logger.info("🎉 Міграція завершена успішно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Помилка міграції: {e}")
        return False

def main():
    """Головна функція"""
    logger.info("🚀 Міграція бази даних Upgrade Studio Bot")
    logger.info("=" * 50)
    
    if run_migration():
        logger.info("✅ Міграція виконана успішно!")
    else:
        logger.error("❌ Міграція не вдалася!")
        sys.exit(1)

if __name__ == "__main__":
    main()