"""
Скрипт оптимізації пам'яті та очищення старих даних
"""
import sys
from datetime import datetime, timedelta
from database.models import get_database

def cleanup_old_payment_events():
    """Очистити старі оброблені події оплат"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Видаляємо оброблені події старші за 7 днів
        cutoff_date = datetime.now() - timedelta(days=7)
        
        cursor.execute("""
            DELETE FROM payment_events
            WHERE processed = TRUE
            AND processed_at < %s
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        db.commit()
        
        print(f"✅ Видалено {deleted_count} старих подій оплат")
        return deleted_count
        
    except Exception as e:
        print(f"❌ Помилка при очищенні подій оплат: {e}")
        if db:
            db.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def cleanup_old_system_logs():
    """Очистити старі системні логи"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Видаляємо логи старші за 30 днів
        cutoff_date = datetime.now() - timedelta(days=30)
        
        cursor.execute("""
            DELETE FROM system_logs
            WHERE created_at < %s
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        db.commit()
        
        print(f"✅ Видалено {deleted_count} старих системних логів")
        return deleted_count
        
    except Exception as e:
        print(f"❌ Помилка при очищенні системних логів: {e}")
        if db:
            db.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def optimize_database_tables():
    """Оптимізувати таблиці бази даних"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor()
        
        tables = ['payment_events', 'system_logs', 'reminders', 'payments']
        
        for table in tables:
            try:
                cursor.execute(f"OPTIMIZE TABLE {table}")
                print(f"✅ Оптимізовано таблицю {table}")
            except Exception as e:
                print(f"⚠️  Не вдалося оптимізувати {table}: {e}")
        
        db.commit()
        
    except Exception as e:
        print(f"❌ Помилка при оптимізації таблиць: {e}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def show_memory_stats():
    """Показати статистику використання пам'яті"""
    db = None
    cursor = None
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        print("\n📊 Статистика бази даних:")
        print("=" * 50)
        
        # Кількість необроблених подій
        cursor.execute("SELECT COUNT(*) as count FROM payment_events WHERE processed = FALSE")
        pending_events = cursor.fetchone()['count']
        print(f"Необроблені події оплат: {pending_events}")
        
        # Кількість оброблених подій
        cursor.execute("SELECT COUNT(*) as count FROM payment_events WHERE processed = TRUE")
        processed_events = cursor.fetchone()['count']
        print(f"Оброблені події оплат: {processed_events}")
        
        # Активні нагадування
        cursor.execute("SELECT COUNT(*) as count FROM reminders WHERE is_active = TRUE")
        active_reminders = cursor.fetchone()['count']
        print(f"Активні нагадування: {active_reminders}")
        
        # Системні логи за останній тиждень
        cursor.execute("""
            SELECT COUNT(*) as count FROM system_logs 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        recent_logs = cursor.fetchone()['count']
        print(f"Системні логи (останній тиждень): {recent_logs}")
        
        # Всього користувачів
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        print(f"Всього користувачів: {total_users}")
        
        # Активні підписки
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE subscription_active = TRUE")
        active_subs = cursor.fetchone()['count']
        print(f"Активні підписки: {active_subs}")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Помилка при отриманні статистики: {e}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def main():
    """Головна функція"""
    print("\n🚀 Запуск оптимізації пам'яті...")
    print()
    
    # Показуємо статистику до очищення
    show_memory_stats()
    
    print("\n🧹 Очищення старих даних...")
    
    # Очищуємо старі події
    cleanup_old_payment_events()
    
    # Очищуємо старі логи
    cleanup_old_system_logs()
    
    # Оптимізуємо таблиці
    print("\n⚡ Оптимізація таблиць...")
    optimize_database_tables()
    
    # Показуємо статистику після очищення
    print("\n📈 Статистика після очищення:")
    show_memory_stats()
    
    print("\n✅ Оптимізація завершена!")


if __name__ == "__main__":
    main()
