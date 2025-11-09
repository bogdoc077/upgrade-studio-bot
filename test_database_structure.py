#!/usr/bin/env python3
"""
Скрипт для перевірки повної структури бази даних
"""
import sys
from pathlib import Path

# Додаємо шлях до проєкту
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import get_database

def get_table_structure(cursor, table_name):
    """Отримати структуру таблиці"""
    cursor.execute(f"DESCRIBE {table_name}")
    return cursor.fetchall()

def get_table_sample_data(cursor, table_name, limit=3):
    """Отримати зразкові дані з таблиці"""
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        return cursor.fetchall()
    except Exception as e:
        return f"Помилка: {e}"

def main():
    try:
        db = get_database()
        cursor = db.cursor()
        
        print("=" * 60)
        print("СТРУКТУРА БАЗИ ДАНИХ UPGRADE STUDIO BOT")
        print("=" * 60)
        
        # Отримуємо список всіх таблиць
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\nЗнайдено таблиць: {len(tables)}")
        print("-" * 40)
        
        for (table_name,) in tables:
            print(f"\n📋 ТАБЛИЦЯ: {table_name}")
            print("-" * 30)
            
            # Структура таблиці
            structure = get_table_structure(cursor, table_name)
            print("Структура:")
            for field in structure:
                field_name = field[0]
                field_type = field[1]
                null_allowed = field[2]
                key_info = field[3]
                default_value = field[4]
                extra = field[5]
                
                key_symbol = ""
                if key_info == "PRI":
                    key_symbol = " 🔑"
                elif key_info == "UNI":
                    key_symbol = " 🔗"
                elif key_info == "MUL":
                    key_symbol = " 🔗"
                
                null_info = "NULL" if null_allowed == "YES" else "NOT NULL"
                
                print(f"  • {field_name:<20} {field_type:<15} {null_info:<8} {key_symbol}")
                if default_value is not None:
                    print(f"    DEFAULT: {default_value}")
                if extra:
                    print(f"    EXTRA: {extra}")
            
            # Кількість записів
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\nКількість записів: {count}")
            
            # Зразкові дані (якщо є)
            if count > 0:
                print("Зразкові дані:")
                sample_data = get_table_sample_data(cursor, table_name)
                if isinstance(sample_data, str):
                    print(f"  {sample_data}")
                else:
                    for i, row in enumerate(sample_data, 1):
                        print(f"  Запис {i}: {row}")
            
            print("-" * 50)
        
        print(f"\n✅ Аналіз завершено!")
        
    except Exception as e:
        print(f"❌ Помилка підключення до бази даних: {e}")
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()