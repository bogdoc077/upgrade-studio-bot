"""
Система подій для обробки платежів
"""
import json
from datetime import datetime
from database.models import get_database

def create_payment_success_event(telegram_id: int):
    """Створити подію про успішну оплату"""
    db = get_database()
    cursor = db.cursor()
    
    try:
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
        db.commit()
        
        cursor.execute("""
            INSERT INTO payment_events (telegram_id, event_type)
            VALUES (%s, %s)
        """, (telegram_id, 'payment_success'))
        db.commit()
        
        return True
    except Exception as e:
        print(f"Error creating payment event: {e}")
        return False
    finally:
        cursor.close()
        db.close()

def get_pending_payment_events():
    """Отримати необроблені події оплат"""
    db = get_database()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT id, telegram_id, event_type, created_at
            FROM payment_events
            WHERE processed = FALSE
            ORDER BY created_at ASC
            LIMIT 10
        """)
        
        events = cursor.fetchall()
        return events
    except Exception as e:
        print(f"Error getting payment events: {e}")
        return []
    finally:
        cursor.close()
        db.close()

def mark_event_processed(event_id: int):
    """Позначити подію як оброблену"""
    db = get_database()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            UPDATE payment_events
            SET processed = TRUE, processed_at = NOW()
            WHERE id = %s
        """, (event_id,))
        db.commit()
        return True
    except Exception as e:
        print(f"Error marking event as processed: {e}")
        return False
    finally:
        cursor.close()
        db.close()
