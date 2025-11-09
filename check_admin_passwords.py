#!/usr/bin/env python3
"""
Скрипт для створення/оновлення пароля адміна
"""
import sys
import bcrypt
from pathlib import Path

# Додаємо шлях до проєкту
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import get_database

def hash_password(password: str) -> str:
    """Захешувати пароль"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевірити пароль"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def main():
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        print("=" * 50)
        print("ПЕРЕВІРКА ТА ОНОВЛЕННЯ ПАРОЛІВ АДМІНІВ")
        print("=" * 50)
        
        # Отримуємо всіх адмінів
        cursor.execute("SELECT * FROM admins")
        admins = cursor.fetchall()
        
        print(f"\nЗнайдено адмінів: {len(admins)}")
        
        for admin in admins:
            print(f"\n👤 Адмін ID: {admin['id']}")
            print(f"Username: {admin['username']}")
            print(f"Email: {admin['email']}")
            print(f"Ім'я: {admin['first_name']} {admin['last_name'] or ''}")
            print(f"Роль: {admin['role']}")
            print(f"Статус: {'Активний' if admin['is_active'] else 'Неактивний'}")
            
            # Тестуємо різні паролі
            test_passwords = ['admin', 'admin123', 'Qwerty21']
            
            print("\nПеревірка паролів:")
            for pwd in test_passwords:
                is_valid = verify_password(pwd, admin['password_hash'])
                status = "✅ ПІДХОДИТЬ" if is_valid else "❌ НЕ ПІДХОДИТЬ"
                print(f"  '{pwd}': {status}")
            
            # Пропонуємо оновити пароль
            print(f"\nПоточний хеш: {admin['password_hash'][:50]}...")
            
            update_choice = input(f"\nОновити пароль для {admin['username']}? (y/N): ").strip().lower()
            if update_choice == 'y':
                new_password = input("Введіть новий пароль: ").strip()
                if new_password:
                    new_hash = hash_password(new_password)
                    
                    cursor.execute(
                        "UPDATE admins SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                        (new_hash, admin['id'])
                    )
                    db.commit()
                    
                    print(f"✅ Пароль оновлено для {admin['username']}")
                    
                    # Перевіряємо новий пароль
                    if verify_password(new_password, new_hash):
                        print("✅ Новий пароль працює коректно")
                    else:
                        print("❌ Помилка при перевірці нового пароля")
            
            print("-" * 40)
        
        # Можливість створити нового адміна
        create_new = input("\nСтворити нового тестового адміна? (y/N): ").strip().lower()
        if create_new == 'y':
            username = input("Username: ").strip() or 'testadmin'
            email = input("Email: ").strip() or 'test@admin.com'
            password = input("Password: ").strip() or 'admin123'
            first_name = input("Ім'я: ").strip() or 'Test'
            last_name = input("Прізвище: ").strip() or 'Admin'
            
            password_hash = hash_password(password)
            
            try:
                cursor.execute("""
                    INSERT INTO admins (username, email, password_hash, first_name, last_name, role, is_superadmin, can_manage_users, can_manage_payments, can_manage_settings, can_manage_admins)
                    VALUES (%s, %s, %s, %s, %s, 'admin', 1, 1, 1, 1, 1)
                """, (username, email, password_hash, first_name, last_name))
                
                db.commit()
                admin_id = cursor.lastrowid
                
                print(f"\n✅ Створено нового адміна:")
                print(f"   ID: {admin_id}")
                print(f"   Username: {username}")
                print(f"   Password: {password}")
                print(f"   Email: {email}")
                
            except Exception as e:
                print(f"❌ Помилка при створенні адміна: {e}")
        
        print(f"\n✅ Готово!")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()