"""
Скрипт для тестування автоматичного продовження підписки
"""
import sys
from datetime import datetime, timedelta
from database.models import DatabaseManager, User, Payment, Reminder
import stripe
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key


def test_subscription_expiration_no_autopay(telegram_id: int):
    """
    Імітує закінчення підписки коли автоплатіж вимкнений
    
    Args:
        telegram_id: ID користувача в Telegram
    """
    try:
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                logger.error(f"Користувач {telegram_id} не знайдений")
                return
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ТЕСТУВАННЯ ЗАКІНЧЕННЯ ПІДПИСКИ БЕЗ АВТОПЛАТЕЖУ")
            logger.info(f"{'='*60}")
            logger.info(f"Користувач: {user.first_name} (@{user.username})")
            logger.info(f"Telegram ID: {telegram_id}")
            logger.info(f"Поточна дата закінчення: {user.subscription_end_date}")
            logger.info(f"Автоплатіж: {'❌ ВИМКНЕНИЙ' if user.subscription_cancelled else '✅ АКТИВНИЙ'}")
            logger.info(f"{'='*60}\n")
            
            # 1. Вимикаємо автоплатіж
            user.subscription_cancelled = True
            
            # 2. Встановлюємо дату закінчення підписки на вчора (вже закінчилась)
            yesterday = datetime.utcnow() - timedelta(days=1)
            user.subscription_end_date = yesterday
            user.next_billing_date = None  # Немає наступного списання
            
            logger.info(f"✓ Встановлено subscription_cancelled = True")
            logger.info(f"✓ Встановлено дату закінчення на вчора: {yesterday}")
            logger.info(f"✓ Наступне списання: None (автоплатіж вимкнений)")
            
            # 3. Створюємо нагадування про закінчення (яке мало б прийти за 7 днів)
            # Створимо його на зараз + 1 хвилину для тестування
            reminder_time = datetime.utcnow() + timedelta(minutes=1)
            
            # Видаляємо старі нагадування про продовження
            db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.reminder_type == "subscription_renewal",
                Reminder.is_active == True
            ).delete()
            
            # Коли підписка скасована, нагадування має бути про закінчення, а не продовження
            reminder = Reminder(
                user_id=user.id,
                reminder_type="subscription_expiration",  # Інший тип
                scheduled_at=reminder_time,
                max_attempts=1,
                is_active=True
            )
            db.add(reminder)
            
            logger.info(f"✓ Створено нагадування про закінчення на {reminder_time}")
            
            # 4. Деактивуємо підписку
            user.subscription_active = False
            
            db.commit()
            
            logger.info(f"\n📋 РЕЗУЛЬТАТ:")
            logger.info(f"  - Підписка деактивована (subscription_active=False)")
            logger.info(f"  - Автоплатіж вимкнений (subscription_cancelled=True)")
            logger.info(f"  - Дата закінчення: {yesterday}")
            logger.info(f"  - Наступне списання: None")
            logger.info(f"  - Користувач має продовжити підписку вручну")
            logger.info(f"  - Створено нагадування про закінчення підписки")
            
            logger.info(f"\n⚠️ ВАЖЛИВО:")
            logger.info(f"  - При наступному запуску scheduler.check_expired_subscriptions()")
            logger.info(f"  - Користувач буде автоматично видалений з каналу/чату")
            logger.info(f"  - Отримає повідомлення про закінчення підписки")
            
            # Якщо є Stripe subscription ID, можна скасувати і в Stripe
            if user.stripe_subscription_id:
                logger.info(f"\n💡 ПІДКАЗКА:")
                logger.info(f"  Щоб реально скасувати в Stripe, виконайте:")
                logger.info(f"  stripe.Subscription.modify('{user.stripe_subscription_id}',")
                logger.info(f"    cancel_at_period_end=True)")
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ТЕСТ ЗАВЕРШЕНО")
            logger.info(f"{'='*60}\n")
            
    except Exception as e:
        logger.error(f"Помилка при тестуванні: {e}")
        import traceback
        traceback.print_exc()


def test_subscription_renewal(telegram_id: int, simulate_success: bool = True):
    """
    Імітує закінчення підписки та спробу автоплатежу
    
    Args:
        telegram_id: ID користувача в Telegram
        simulate_success: True для успішної оплати, False для невдалої
    """
    try:
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                logger.error(f"Користувач {telegram_id} не знайдений")
                return
            
            if not user.stripe_subscription_id:
                logger.error(f"У користувача {telegram_id} немає активної підписки Stripe")
                return
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ТЕСТУВАННЯ АВТОМАТИЧНОГО ПРОДОВЖЕННЯ ПІДПИСКИ")
            logger.info(f"{'='*60}")
            logger.info(f"Користувач: {user.first_name} (@{user.username})")
            logger.info(f"Telegram ID: {telegram_id}")
            logger.info(f"Subscription ID: {user.stripe_subscription_id}")
            logger.info(f"Поточна дата закінчення: {user.subscription_end_date}")
            logger.info(f"Сценарій: {'✅ УСПІШНА ОПЛАТА' if simulate_success else '❌ НЕВДАЛА ОПЛАТА'}")
            logger.info(f"{'='*60}\n")
            
            # Отримуємо поточну підписку з Stripe
            try:
                subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                logger.info(f"Статус підписки в Stripe: {subscription.status}")
                logger.info(f"Дата наступного списання: {datetime.fromtimestamp(subscription.current_period_end)}")
            except Exception as e:
                logger.error(f"Помилка отримання підписки з Stripe: {e}")
            
            # 1. Встановлюємо дату закінчення підписки на завтра (імітуємо наближення кінця)
            tomorrow = datetime.utcnow() + timedelta(days=1)
            user.subscription_end_date = tomorrow
            user.next_billing_date = tomorrow
            db.commit()
            
            logger.info(f"✓ Встановлено дату закінчення на завтра: {tomorrow}")
            
            # 2. Створюємо нагадування за 7 днів (імітуємо що воно має бути)
            # Але оскільки ми встановили завтра, створимо нагадування на зараз + 1 хвилину
            reminder_time = datetime.utcnow() + timedelta(minutes=1)
            
            # Видаляємо старі нагадування
            db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.reminder_type == "subscription_renewal",
                Reminder.is_active == True
            ).delete()
            
            reminder = Reminder(
                user_id=user.id,
                reminder_type="subscription_renewal",
                scheduled_at=reminder_time,
                max_attempts=1,
                is_active=True
            )
            db.add(reminder)
            db.commit()
            
            logger.info(f"✓ Створено тестове нагадування на {reminder_time}")
            
            # 3. Імітуємо webhook від Stripe
            if simulate_success:
                # Успішна оплата
                logger.info("\n📝 Створюємо імітацію invoice.payment_succeeded...")
                
                invoice_data = {
                    'id': f'in_test_{int(datetime.utcnow().timestamp())}',
                    'object': 'invoice',
                    'amount_paid': 2000,  # 20 EUR в центах
                    'currency': 'eur',
                    'subscription': user.stripe_subscription_id,
                    'payment_intent': f'pi_test_{int(datetime.utcnow().timestamp())}',
                    'status': 'paid',
                    'customer': user.stripe_customer_id
                }
                
                # Створюємо новий платіж
                payment = Payment(
                    user_id=user.id,
                    amount=invoice_data['amount_paid'],
                    currency=invoice_data['currency'],
                    status="succeeded",
                    stripe_payment_intent_id=invoice_data['payment_intent'],
                    stripe_subscription_id=invoice_data['subscription'],
                    stripe_invoice_id=invoice_data['id'],
                    stripe_response_log=str(invoice_data),
                    paid_at=datetime.utcnow()
                )
                db.add(payment)
                
                # Продовжуємо підписку на 30 днів
                new_end_date = datetime.utcnow() + timedelta(days=30)
                user.subscription_end_date = new_end_date
                user.next_billing_date = new_end_date
                user.subscription_active = True
                user.subscription_cancelled = False
                
                # Створюємо нагадування на 7 днів до нового списання
                new_reminder_date = new_end_date - timedelta(days=7)
                new_reminder = Reminder(
                    user_id=user.id,
                    reminder_type="subscription_renewal",
                    scheduled_at=new_reminder_date,
                    max_attempts=1,
                    is_active=True
                )
                db.add(new_reminder)
                
                db.commit()
                
                logger.info(f"\n✅ УСПІШНО:")
                logger.info(f"  - Створено платіж на суму €{invoice_data['amount_paid']/100}")
                logger.info(f"  - Підписка продовжена до {new_end_date}")
                logger.info(f"  - Створено нагадування на {new_reminder_date}")
                logger.info(f"  - Наступне списання: {new_end_date}")
                
            else:
                # Невдала оплата
                logger.info("\n📝 Імітуємо invoice.payment_failed...")
                
                invoice_data = {
                    'id': f'in_test_failed_{int(datetime.utcnow().timestamp())}',
                    'object': 'invoice',
                    'amount_due': 2000,
                    'currency': 'eur',
                    'subscription': user.stripe_subscription_id,
                    'status': 'open',
                    'attempt_count': 1,
                    'customer': user.stripe_customer_id
                }
                
                # Створюємо failed платіж
                payment = Payment(
                    user_id=user.id,
                    amount=invoice_data['amount_due'],
                    currency=invoice_data['currency'],
                    status="failed",
                    stripe_subscription_id=invoice_data['subscription'],
                    stripe_invoice_id=invoice_data['id'],
                    stripe_response_log=str(invoice_data),
                    paid_at=None
                )
                db.add(payment)
                
                # Stripe зазвичай дає кілька спроб списання, але ми можемо встановити прапорець
                # що підписка під загрозою
                user.subscription_paused = True
                
                db.commit()
                
                logger.info(f"\n❌ НЕВДАЛА ОПЛАТА:")
                logger.info(f"  - Створено failed платіж")
                logger.info(f"  - Підписка призупинена (subscription_paused=True)")
                logger.info(f"  - Користувач має оновити спосіб оплати")
                logger.info(f"  - Stripe спробує знову згідно налаштувань")
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ТЕСТ ЗАВЕРШЕНО")
            logger.info(f"{'='*60}\n")
            
    except Exception as e:
        logger.error(f"Помилка при тестуванні: {e}")
        import traceback
        traceback.print_exc()


def show_user_subscription_info(telegram_id: int):
    """Показати інформацію про підписку користувача"""
    try:
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                logger.error(f"Користувач {telegram_id} не знайдений")
                return
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ІНФОРМАЦІЯ ПРО ПІДПИСКУ")
            logger.info(f"{'='*60}")
            logger.info(f"Користувач: {user.first_name} (@{user.username})")
            logger.info(f"Telegram ID: {telegram_id}")
            logger.info(f"Subscription ID: {user.stripe_subscription_id}")
            logger.info(f"Customer ID: {user.stripe_customer_id}")
            logger.info(f"\nСтатус підписки:")
            logger.info(f"  - Активна: {user.subscription_active}")
            logger.info(f"  - Призупинена: {user.subscription_paused}")
            logger.info(f"  - Скасована: {user.subscription_cancelled}")
            logger.info(f"\nДоступ до чатів:")
            logger.info(f"  - Joined channel: {user.joined_channel}")
            logger.info(f"  - Joined chat: {user.joined_chat}")
            logger.info(f"\nДати:")
            logger.info(f"  - Закінчення підписки: {user.subscription_end_date}")
            logger.info(f"  - Наступне списання: {user.next_billing_date}")
            
            # Платежі
            payments = db.query(Payment).filter(Payment.user_id == user.id).order_by(Payment.created_at.desc()).limit(5).all()
            logger.info(f"\nОстанні платежі ({len(payments)}):")
            for p in payments:
                logger.info(f"  - {p.created_at}: €{p.amount/100:.2f} [{p.status}]")
            
            # Нагадування
            reminders = db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.is_active == True
            ).all()
            logger.info(f"\nАктивні нагадування ({len(reminders)}):")
            for r in reminders:
                logger.info(f"  - {r.reminder_type}: {r.scheduled_at}")
            
            logger.info(f"{'='*60}\n")
            
    except Exception as e:
        logger.error(f"Помилка: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Використання:")
        print("  python test_subscription_renewal.py <telegram_id> [success|fail|expired]")
        print("  python test_subscription_renewal.py <telegram_id> info")
        print("\nПриклади:")
        print("  python test_subscription_renewal.py 578080052 success  # Тест успішної оплати")
        print("  python test_subscription_renewal.py 578080052 fail     # Тест невдалої оплати")
        print("  python test_subscription_renewal.py 578080052 expired  # Підписка закінчилась (автоплатіж вимкнений)")
        print("  python test_subscription_renewal.py 578080052 info     # Показати інфо")
        sys.exit(1)
    
    telegram_id = int(sys.argv[1])
    action = sys.argv[2] if len(sys.argv) > 2 else "success"
    
    if action == "info":
        show_user_subscription_info(telegram_id)
    elif action == "fail":
        test_subscription_renewal(telegram_id, simulate_success=False)
    elif action == "expired":
        test_subscription_expiration_no_autopay(telegram_id)
    else:
        test_subscription_renewal(telegram_id, simulate_success=True)
