"""
Діагностика високого вихідного трафіку
"""
import sys
from datetime import datetime, timedelta
from database.models import get_database
from pathlib import Path

def check_database_logging():
    """Перевірити чи не ввімкнено echo для БД"""
    print("🔍 Перевірка налаштувань БД логування...")
    
    # Перевіряємо конфігурацію
    try:
        from config import settings
        if settings.log_level == "DEBUG":
            print("⚠️  ПРОБЛЕМА: LOG_LEVEL=DEBUG")
            print("   Це логує ВСІ SQL запити, що створює величезний трафік")
            print("   Рішення: змінити на INFO або WARNING")
            return False
        else:
            print(f"✅ LOG_LEVEL={settings.log_level}")
            return True
    except Exception as e:
        print(f"❌ Помилка перевірки: {e}")
        return False


def check_broadcasts():
    """Перевірити стан розсилок"""
    print("\n🔍 Перевірка розсилок...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        # Перевіряємо pending broadcasts
        cursor.execute("""
            SELECT COUNT(*) as count FROM broadcasts
            WHERE status = 'pending'
        """)
        pending = cursor.fetchone()['count']
        
        # Перевіряємо в процесі
        cursor.execute("""
            SELECT COUNT(*) as count FROM broadcasts
            WHERE status = 'in_progress'
        """)
        in_progress = cursor.fetchone()['count']
        
        # Перевіряємо за останні 24 години
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(sent_count) as total_sent
            FROM broadcasts
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        result = cursor.fetchone()
        recent_broadcasts = result['count']
        total_sent = result['total_sent'] or 0
        
        print(f"  Pending розсилок: {pending}")
        print(f"  В процесі: {in_progress}")
        print(f"  За 24 години: {recent_broadcasts} розсилок, {total_sent} повідомлень")
        
        if in_progress > 0 and pending == 0:
            print("⚠️  ПРОБЛЕМА: Розсилка застрягла в статусі 'in_progress'")
            print("   Це може створювати постійні спроби надсилання")
            return False
        
        if total_sent > 1000:
            print(f"⚠️  УВАГА: Надіслано {total_sent} повідомлень за 24 год")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def check_broadcast_queue():
    """Перевірити чергу розсилок"""
    print("\n🔍 Перевірка черги розсилок...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM broadcast_queue
            WHERE status = 'pending'
        """)
        pending_queue = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM broadcast_queue
            WHERE status = 'failed'
        """)
        failed_queue = cursor.fetchone()['count']
        
        print(f"  Pending в черзі: {pending_queue}")
        print(f"  Failed в черзі: {failed_queue}")
        
        if pending_queue > 1000:
            print(f"⚠️  ПРОБЛЕМА: {pending_queue} повідомлень в черзі")
            print("   Це може створювати постійні спроби надсилання")
            return False
            
        return True
        
    except Exception as e:
        print(f"ℹ️  Таблиця broadcast_queue не знайдена (це нормально якщо не використовуєте)")
        return True
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def check_reminders():
    """Перевірити кількість активних нагадувань"""
    print("\n🔍 Перевірка нагадувань...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM reminders
            WHERE is_active = TRUE
        """)
        active = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM reminders
            WHERE is_active = TRUE AND scheduled_at < NOW()
        """)
        overdue = cursor.fetchone()['count']
        
        print(f"  Активних нагадувань: {active}")
        print(f"  Прострочених: {overdue}")
        
        if overdue > 100:
            print(f"⚠️  ПРОБЛЕМА: {overdue} прострочених нагадувань")
            print("   Бот може постійно намагатися їх надіслати")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def check_log_files():
    """Перевірити розмір лог файлів"""
    print("\n🔍 Перевірка розміру логів...")
    
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print("  Папка logs не знайдена")
        return True
    
    total_size = 0
    large_files = []
    
    for log_file in logs_dir.glob("*.log"):
        size_mb = log_file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        
        if size_mb > 100:
            large_files.append((log_file.name, size_mb))
    
    print(f"  Загальний розмір логів: {total_size:.2f} MB")
    
    if large_files:
        print("  ⚠️  Великі лог файли:")
        for name, size in large_files:
            print(f"     - {name}: {size:.2f} MB")
            
    if total_size > 1000:  # 1GB
        print("⚠️  ПРОБЛЕМА: Логи займають більше 1GB")
        return False
        
    return True


def check_users_without_subscription():
    """Перевірити користувачів які отримують повідомлення але без підписки"""
    print("\n🔍 Перевірка користувачів...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM users
            WHERE subscription_active = TRUE
        """)
        active_subs = cursor.fetchone()['count']
        
        print(f"  Всього користувачів: {total_users}")
        print(f"  Активних підписок: {active_subs}")
        print(f"  Без підписки: {total_users - active_subs}")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def check_payment_events():
    """Перевірити події оплат"""
    print("\n🔍 Перевірка подій оплат...")
    db = None
    cursor = None
    
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM payment_events
            WHERE processed = FALSE
        """)
        pending = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM payment_events
            WHERE processed = TRUE
            AND processed_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        recent_processed = cursor.fetchone()['count']
        
        print(f"  Необроблених подій: {pending}")
        print(f"  Оброблено за 24 години: {recent_processed}")
        
        if pending > 100:
            print(f"⚠️  ПРОБЛЕМА: {pending} необроблених подій")
            return False
            
        return True
        
    except Exception as e:
        print(f"ℹ️  Таблиця payment_events не знайдена")
        return True
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def main():
    """Головна функція діагностики"""
    print("🚨 ДІАГНОСТИКА ВИСОКОГО ВИХІДНОГО ТРАФІКУ")
    print("=" * 60)
    print()
    
    issues_found = []
    
    # Перевірки
    if not check_database_logging():
        issues_found.append("DATABASE_LOGGING")
    
    if not check_broadcasts():
        issues_found.append("BROADCASTS")
    
    if not check_broadcast_queue():
        issues_found.append("BROADCAST_QUEUE")
    
    if not check_reminders():
        issues_found.append("REMINDERS")
    
    if not check_log_files():
        issues_found.append("LOG_FILES")
    
    check_users_without_subscription()
    check_payment_events()
    
    # Підсумок
    print("\n" + "=" * 60)
    print("📊 ПІДСУМОК ДІАГНОСТИКИ")
    print("=" * 60)
    
    if issues_found:
        print(f"\n❌ Знайдено проблем: {len(issues_found)}")
        for issue in issues_found:
            print(f"   - {issue}")
        
        print("\n🔧 РЕКОМЕНДАЦІЇ:")
        
        if "DATABASE_LOGGING" in issues_found:
            print("\n1. Вимкнути DEBUG логування БД:")
            print("   export LOG_LEVEL=INFO")
            print("   або в .env файлі: LOG_LEVEL=INFO")
        
        if "BROADCASTS" in issues_found:
            print("\n2. Очистити застряглі розсилки:")
            print("   python fix_broadcasts.py")
        
        if "REMINDERS" in issues_found:
            print("\n3. Очистити прострочені нагадування:")
            print("   python optimize_memory.py")
        
        if "LOG_FILES" in issues_found:
            print("\n4. Очистити великі лог файли:")
            print("   rm logs/*.log && systemctl restart upgrade-bot")
        
    else:
        print("\n✅ Очевидних проблем не знайдено")
        print("\nДодаткові перевірки:")
        print("1. Моніторинг трафіку: iftop або nethogs")
        print("2. Перевірка процесів: ps aux | grep python")
        print("3. Логи системи: journalctl -u upgrade-bot -f")
    
    print()


if __name__ == "__main__":
    main()
