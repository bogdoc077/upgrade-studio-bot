"""
Виправлення проблем з високим трафіком
"""
from database.models import get_database

def fix_stuck_broadcasts():
    """Виправити застряглі розсилки"""
    print("🔧 Виправлення застряглих розсилок...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Скидаємо розсилки що застрягли більше години
        cursor.execute("""
            UPDATE broadcasts
            SET status = 'failed', 
                updated_at = NOW()
            WHERE status = 'in_progress'
            AND updated_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        
        stuck_count = cursor.rowcount
        db.commit()
        
        print(f"✅ Скинуто {stuck_count} застряглих розсилок")
        return stuck_count
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        if db:
            db.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def fix_overdue_reminders():
    """Виправити прострочені нагадування"""
    print("\n🔧 Виправлення прострочених нагадувань...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Деактивуємо нагадування що застрягли більше 3 днів
        cursor.execute("""
            UPDATE reminders
            SET is_active = FALSE,
                sent_at = NOW()
            WHERE is_active = TRUE
            AND scheduled_at < DATE_SUB(NOW(), INTERVAL 3 DAY)
            AND sent_at IS NULL
        """)
        
        fixed_count = cursor.rowcount
        db.commit()
        
        print(f"✅ Деактивовано {fixed_count} прострочених нагадувань")
        return fixed_count
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        if db:
            db.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def clear_broadcast_queue():
    """Очистити застряглу чергу розсилок"""
    print("\n🔧 Очищення черги розсилок...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Очищаємо failed повідомлення старші за день
        cursor.execute("""
            DELETE FROM broadcast_queue
            WHERE status = 'failed'
            AND created_at < DATE_SUB(NOW(), INTERVAL 1 DAY)
        """)
        
        deleted_count = cursor.rowcount
        db.commit()
        
        print(f"✅ Видалено {deleted_count} failed повідомлень з черги")
        return deleted_count
        
    except Exception as e:
        print(f"ℹ️  Таблиця broadcast_queue не знайдена або пуста")
        return 0
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def optimize_log_level():
    """Перевірити і рекомендувати оптимізацію логування"""
    print("\n🔧 Перевірка рівня логування...")
    
    try:
        from config import settings
        
        if settings.log_level == "DEBUG":
            print("⚠️  КРИТИЧНО: LOG_LEVEL=DEBUG")
            print("\n📝 Інструкція для виправлення:")
            print("1. Відредагувати .env файл:")
            print("   LOG_LEVEL=INFO")
            print("\n2. Або встановити через змінну середовища:")
            print("   export LOG_LEVEL=INFO")
            print("\n3. Перезапустити сервіси:")
            print("   sudo systemctl restart upgrade-bot upgrade-api upgrade-webhook")
            return False
        else:
            print(f"✅ LOG_LEVEL={settings.log_level} (оптимально)")
            return True
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False


def show_traffic_recommendations():
    """Показати рекомендації для зменшення трафіку"""
    print("\n" + "=" * 60)
    print("💡 РЕКОМЕНДАЦІЇ ДЛЯ ЗМЕНШЕННЯ ТРАФІКУ")
    print("=" * 60)
    
    print("""
1. 🔧 ВИМКНУТИ DEBUG ЛОГУВАННЯ (НАЙВАЖЛИВІШЕ!)
   - echo=True в SQLAlchemy логує ВСІ SQL запити
   - Це може генерувати десятки ГБ трафіку
   - Виправлення: LOG_LEVEL=INFO

2. 📊 ОПТИМІЗУВАТИ БД ЗАПИТИ
   - Вже додано connection pooling
   - Вже обмежено кількість запитів
   - Перевірити: python diagnose_traffic.py

3. 🚫 ВИМКНУТИ ЗАЙВІ НАГАДУВАННЯ
   - Деактивувати прострочені нагадування
   - Виправлення: вже в цьому скрипті

4. 📤 ПЕРЕВІРИТИ РОЗСИЛКИ
   - Зупинити застряглі розсилки
   - Видалити старі failed повідомлення
   - Виправлення: вже в цьому скрипті

5. 📝 РОТАЦІЯ ЛОГІВ
   - Налаштувати logrotate для обмеження розміру
   - Стискати старі логи
   - Видаляти логи старші 7 днів

6. 🌐 МОНІТОРИНГ ТРАФІКУ
   - Встановити: apt-get install iftop nethogs
   - Перевірити: iftop -i eth0
   - Перевірити процеси: nethogs

7. 🔍 ПЕРЕВІРИТИ ЗОВНІШНІ API
   - Stripe webhooks (має бути мінімум трафіку)
   - Telegram API (має бути мінімум без користувачів)
   - Перевірити логи: journalctl -u upgrade-bot -f
""")


def main():
    """Головна функція виправлення"""
    print("🚀 ВИПРАВЛЕННЯ ПРОБЛЕМ З ТРАФІКОМ")
    print("=" * 60)
    print()
    
    # Виправляємо проблеми
    total_fixed = 0
    
    total_fixed += fix_stuck_broadcasts()
    total_fixed += fix_overdue_reminders()
    total_fixed += clear_broadcast_queue()
    
    log_ok = optimize_log_level()
    
    # Підсумок
    print("\n" + "=" * 60)
    print("📊 ПІДСУМОК ВИПРАВЛЕНЬ")
    print("=" * 60)
    
    print(f"\n✅ Виправлено записів у БД: {total_fixed}")
    
    if not log_ok:
        print("⚠️  КРИТИЧНО: Потрібно вручну виправити LOG_LEVEL!")
    
    show_traffic_recommendations()
    
    print("\n🔄 Наступні кроки:")
    print("1. Перевірити діагностику: python diagnose_traffic.py")
    print("2. Застосувати RAM оптимізації: ./apply_ram_optimization.sh")
    print("3. Перезапустити сервіси: sudo systemctl restart upgrade-bot")
    print("4. Моніторити трафік: iftop або nethogs")
    print()


if __name__ == "__main__":
    main()
