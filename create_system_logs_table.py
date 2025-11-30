"""
Створення таблиці system_logs для логування автоматичних задач
"""
from database.models import Base, engine, SystemLog

def create_system_logs_table():
    """Створити таблицю system_logs"""
    try:
        # Створюємо таблицю
        SystemLog.__table__.create(engine, checkfirst=True)
        print("✓ Таблиця system_logs успішно створена")
        return True
    except Exception as e:
        print(f"✗ Помилка при створенні таблиці system_logs: {e}")
        return False

if __name__ == "__main__":
    print("Створення таблиці system_logs...")
    create_system_logs_table()
