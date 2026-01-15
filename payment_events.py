"""
Система подій для обробки платежів
"""
import json
from datetime import datetime
from database.models import get_database

def create_payment_success_event(telegram_id: int):
    """Створити подію про успішну оплату"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Перевіряємо чи існує таблиця (тільки якщо потрібно)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                processed BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME NULL,
                INDEX idx_processed (processed, created_at)
            )
        """)
        
        cursor.execute("""
            INSERT INTO payment_events (telegram_id, event_type)
            VALUES (%s, %s)
        """, (telegram_id, 'payment_success'))
        db.commit()
        
        return True
    except Exception as e:
        print(f"Error creating payment event: {e}")
        if db:
            db.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

def get_pending_payment_events():
    """Отримати необроблені події оплат"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, telegram_id, event_type, created_at
            FROM payment_events
            WHERE processed = FALSE
            ORDER BY created_at ASC
            LIMIT 5
        """)
        
        events = cursor.fetchall()
        return events
    except Exception as e:
        print(f"Error getting payment events: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

def mark_event_processed(event_id: int):
    """Позначити подію як оброблену"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE payment_events
            SET processed = TRUE, processed_at = NOW()
            WHERE id = %s
        """, (event_id,))
        db.commit()
        return True
    except Exception as e:
        print(f"Error marking event as processed: {e}")
        if db:
            db.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def cleanup_old_events(days: int = 7):
    """Видалити старі оброблені події"""
    from datetime import datetime, timedelta
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            DELETE FROM payment_events
            WHERE processed = TRUE
            AND processed_at < %s
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        db.commit()
        
        return deleted_count
    except Exception as e:
        print(f"Error cleaning up old events: {e}")
        if db:
            db.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
