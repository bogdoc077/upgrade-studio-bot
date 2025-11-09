"""
Інтеграція з Stripe для обробки платежів та підписок
"""
import stripe
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from config import settings
from database import DatabaseManager, User, Payment

# Налаштування Stripe
stripe.api_key = settings.stripe_secret_key

logger = logging.getLogger(__name__)


class StripeManager:
    """Менеджер для роботи з Stripe API"""
    
    @staticmethod
    async def create_customer(telegram_id: int, email: str = None, 
                            name: str = None) -> Optional[str]:
        """Створити клієнта в Stripe"""
        try:
            customer = stripe.Customer.create(
                metadata={'telegram_id': str(telegram_id)},
                email=email,
                name=name
            )
            logger.info(f"Створено Stripe customer: {customer.id} для telegram_id: {telegram_id}")
            return customer.id
        except Exception as e:
            logger.error(f"Помилка при створенні Stripe customer: {e}")
            return None
    
    @staticmethod
    async def create_checkout_session(telegram_id: int, 
                                    success_url: str, 
                                    cancel_url: str) -> Optional[Dict[str, Any]]:
        """Створити Checkout Session для підписки"""
        try:
            user = DatabaseManager.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"Користувача з telegram_id {telegram_id} не знайдено")
                return None
            
            # Створюємо customer якщо його немає
            if not user.stripe_customer_id:
                customer_id = await StripeManager.create_customer(
                    telegram_id=telegram_id,
                    name=user.first_name
                )
                if not customer_id:
                    return None
                
                # Оновлюємо user з customer_id
                with DatabaseManager() as db:
                    db_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                    if db_user:
                        db_user.stripe_customer_id = customer_id
                        db.commit()
                
                user.stripe_customer_id = customer_id
            
            # Отримуємо ціну в центах
            price_in_cents = int(settings.subscription_price * 100)
            
            # Створюємо Checkout Session
            session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price_data': {
                        'currency': settings.subscription_currency,
                        'product_data': {
                            'name': 'Upgrade Studio - Місячна підписка',
                            'description': 'Доступ до тренувань та спільноти Upgrade Studio'
                        },
                        'unit_amount': price_in_cents,
                        'recurring': {
                            'interval': 'month'
                        }
                    },
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'telegram_id': str(telegram_id)
                }
            )
            
            logger.info(f"Створено Checkout Session: {session.id} для telegram_id: {telegram_id}")
            return {
                'session_id': session.id,
                'url': session.url
            }
            
        except Exception as e:
            logger.error(f"Помилка при створенні Checkout Session: {e}")
            return None
    
    @staticmethod
    async def get_subscription(subscription_id: str) -> Optional[Dict[str, Any]]:
        """Отримати інформацію про підписку"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                'customer_id': subscription.customer
            }
        except Exception as e:
            logger.error(f"Помилка при отриманні підписки {subscription_id}: {e}")
            return None
    
    @staticmethod
    async def pause_subscription(subscription_id: str) -> bool:
        """Призупинити підписку"""
        try:
            stripe.Subscription.modify(
                subscription_id,
                pause_collection={
                    'behavior': 'mark_uncollectible'
                }
            )
            logger.info(f"Підписку {subscription_id} призупинено")
            return True
        except Exception as e:
            logger.error(f"Помилка при призупиненні підписки {subscription_id}: {e}")
            return False
    
    @staticmethod
    async def resume_subscription(subscription_id: str) -> bool:
        """Поновити підписку"""
        try:
            stripe.Subscription.modify(
                subscription_id,
                pause_collection=''  # Прибираємо паузу
            )
            logger.info(f"Підписку {subscription_id} поновлено")
            return True
        except Exception as e:
            logger.error(f"Помилка при поновленні підписки {subscription_id}: {e}")
            return False
    
    @staticmethod
    async def cancel_subscription(subscription_id: str) -> bool:
        """Скасувати підписку"""
        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Підписку {subscription_id} скасовано")
            return True
        except Exception as e:
            logger.error(f"Помилка при скасуванні підписки {subscription_id}: {e}")
            return False
    
    @staticmethod
    async def handle_webhook_event(event_type: str, data: Dict[str, Any]) -> bool:
        """Обробити вебхук від Stripe"""
        try:
            if event_type == 'checkout.session.completed':
                return await StripeManager._handle_checkout_completed(data)
            elif event_type == 'invoice.payment_succeeded':
                return await StripeManager._handle_payment_succeeded(data)
            elif event_type == 'invoice.payment_failed':
                return await StripeManager._handle_payment_failed(data)
            elif event_type == 'customer.subscription.deleted':
                return await StripeManager._handle_subscription_deleted(data)
            else:
                logger.info(f"Необроблений тип події: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Помилка при обробці вебхука {event_type}: {e}")
            return False
    
    @staticmethod
    async def _handle_checkout_completed(data: Dict[str, Any]) -> bool:
        """Обробити успішну оплату"""
        try:
            session = data['object']
            telegram_id = int(session['metadata']['telegram_id'])
            customer_id = session['customer']
            subscription_id = session['subscription']
            
            logger.info(f"Обробка успішної оплати для користувача {telegram_id}")
            
            # Оновлюємо користувача
            with DatabaseManager() as db:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    user.subscription_active = True
                    user.subscription_paused = False
                    user.subscription_cancelled = False
                    user.stripe_customer_id = customer_id
                    user.stripe_subscription_id = subscription_id
                    user.updated_at = datetime.utcnow()
                    
                    # Створюємо запис про платіж (зберігаємо в центах)
                    payment = Payment(
                        user_id=user.id,
                        amount=int(settings.subscription_price * 100),
                        currency=settings.subscription_currency,
                        status="succeeded",
                        stripe_subscription_id=subscription_id,
                        paid_at=datetime.utcnow()
                    )
                    db.add(payment)
                    db.commit()
                    
                    # Скасовуємо нагадування про підписку
                    DatabaseManager.cancel_subscription_reminders_if_active(telegram_id)
                    
                    logger.info(f"Підписка активована для користувача {telegram_id}")
                    return True
                else:
                    logger.error(f"Користувач {telegram_id} не знайдений в БД")
                    return False
            
        except Exception as e:
            logger.error(f"Помилка при обробці checkout.session.completed: {e}")
            return False
    
    @staticmethod
    async def _handle_payment_succeeded(data: Dict[str, Any]) -> bool:
        """Обробити успішну оплату по підписці"""
        try:
            invoice = data['object']
            subscription_id = invoice['subscription']
            
            # Знаходимо користувача по subscription_id
            with DatabaseManager() as db:
                user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
                if user:
                    # Створюємо запис про платіж
                    payment = Payment(
                        user_id=user.id,
                        amount=invoice['amount_paid'],
                        currency=invoice['currency'],
                        status="succeeded",
                        stripe_subscription_id=subscription_id,
                        stripe_invoice_id=invoice['id'],
                        paid_at=datetime.utcnow()
                    )
                    db.add(payment)
                    
                    # Оновлюємо статус підписки
                    user.subscription_active = True
                    user.updated_at = datetime.utcnow()
                    db.commit()
                    
                    logger.info(f"Платіж успішний для subscription_id: {subscription_id}")
                    return True
            
            logger.error(f"Користувача з subscription_id {subscription_id} не знайдено")
            return False
            
        except Exception as e:
            logger.error(f"Помилка при обробці invoice.payment_succeeded: {e}")
            return False
    
    @staticmethod
    async def _handle_payment_failed(data: Dict[str, Any]) -> bool:
        """Обробити невдалу оплату"""
        try:
            invoice = data['object']
            subscription_id = invoice['subscription']
            
            # Знаходимо користувача по subscription_id
            with DatabaseManager() as db:
                user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
                if user:
                    # Створюємо запис про невдалий платіж
                    payment = Payment(
                        user_id=user.id,
                        amount=invoice['amount_due'],
                        currency=invoice['currency'],
                        status="failed",
                        stripe_subscription_id=subscription_id,
                        stripe_invoice_id=invoice['id']
                    )
                    db.add(payment)
                    
                    # Призначаємо нагадування про повторну оплату
                    reminder_time = datetime.utcnow() + timedelta(hours=settings.payment_retry_hours)
                    DatabaseManager.create_reminder(
                        user_id=user.id,
                        reminder_type="payment_retry",
                        scheduled_at=reminder_time,
                        data=f'{{"subscription_id": "{subscription_id}"}}'
                    )
                    
                    db.commit()
                    logger.info(f"Платіж невдалий для subscription_id: {subscription_id}")
                    return True
            
            logger.error(f"Користувача з subscription_id {subscription_id} не знайдено")
            return False
            
        except Exception as e:
            logger.error(f"Помилка при обробці invoice.payment_failed: {e}")
            return False
    
    @staticmethod
    async def _handle_subscription_deleted(data: Dict[str, Any]) -> bool:
        """Обробити скасування підписки"""
        try:
            subscription = data['object']
            subscription_id = subscription['id']
            
            # Знаходимо користувача по subscription_id
            with DatabaseManager() as db:
                user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
                if user:
                    user.subscription_active = False
                    user.subscription_paused = False
                    user.stripe_subscription_id = None
                    user.state = "subscription_cancelled"
                    user.updated_at = datetime.utcnow()
                    db.commit()
                    
                    logger.info(f"Підписку скасовано для subscription_id: {subscription_id}")
                    return True
            
            logger.error(f"Користувача з subscription_id {subscription_id} не знайдено")
            return False
            
        except Exception as e:
            logger.error(f"Помилка при обробці customer.subscription.deleted: {e}")
            return False