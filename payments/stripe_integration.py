"""
Інтеграція з Stripe для обробки платежів та підписок
"""
import stripe
import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Optional, Dict, Any

from config import settings
from database import DatabaseManager, User, Payment

# Налаштування Stripe
stripe.api_key = settings.stripe_secret_key

logger = logging.getLogger(__name__)


class StripeManager:
    """Менеджер для роботи з Stripe API"""
    
    @staticmethod
    def _run_sync(func, *args, **kwargs):
        """Запустити синхронний Stripe виклик в thread executor (уникає блокування event loop)"""
        return func(*args, **kwargs)
    
    @staticmethod
    async def _stripe_call(func, *args, **kwargs):
        """Виконати синхронний Stripe виклик асинхронно через thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    @staticmethod
    async def create_customer(telegram_id: int, email: str = None, 
                            name: str = None) -> Optional[str]:
        """Створити клієнта в Stripe"""
        try:
            customer = await StripeManager._stripe_call(
                stripe.Customer.create,
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
            
            session_params = dict(
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
                        'recurring': {'interval': 'month'}
                    },
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={'telegram_id': str(telegram_id)}
            )
            
            # Створюємо Checkout Session
            try:
                session = await StripeManager._stripe_call(
                    stripe.checkout.Session.create, **session_params
                )
            except stripe.error.InvalidRequestError as e:
                # Якщо customer був видалений в Stripe - створюємо нового
                if 'No such customer' in str(e):
                    logger.warning(f"Customer {user.stripe_customer_id} не існує в Stripe, створюємо нового")
                    customer_id = await StripeManager.create_customer(
                        telegram_id=telegram_id,
                        name=user.first_name
                    )
                    if not customer_id:
                        return None
                    
                    # Оновлюємо user з новим customer_id
                    with DatabaseManager() as db:
                        db_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                        if db_user:
                            db_user.stripe_customer_id = customer_id
                            db.commit()
                    
                    session_params['customer'] = customer_id
                    session = await StripeManager._stripe_call(
                        stripe.checkout.Session.create, **session_params
                    )
                else:
                    raise
            
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
            subscription = await StripeManager._stripe_call(
                stripe.Subscription.retrieve,
                subscription_id
            )
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'customer_id': subscription.customer,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'pause_collection': subscription.get('pause_collection')
            }
        except Exception as e:
            logger.error(f"Помилка при отриманні підписки {subscription_id}: {e}")
            return None
    
    @staticmethod
    async def pause_subscription(subscription_id: str) -> bool:
        """Призупинити підписку (зупиняє майбутні платежі)"""
        try:
            result = await StripeManager._stripe_call(
                stripe.Subscription.modify,
                subscription_id,
                pause_collection={'behavior': 'void'}  # void = рахунки не виставляються
            )
            logger.info(f"Підписку {subscription_id} призупинено в Stripe, status={result.status}, pause_collection={result.get('pause_collection')}")
            return True
        except Exception as e:
            logger.error(f"Помилка при призупиненні підписки {subscription_id}: {e}")
            return False
    
    @staticmethod
    async def resume_subscription(subscription_id: str) -> bool:
        """Поновити підписку (прибирає паузу або cancel_at_period_end)"""
        try:
            result = await StripeManager._stripe_call(
                stripe.Subscription.modify,
                subscription_id,
                pause_collection='',  # Прибираємо паузу
                cancel_at_period_end=False  # Скасовуємо відкладене скасування
            )
            logger.info(f"Підписку {subscription_id} поновлено в Stripe, status={result.status}")
            return True
        except Exception as e:
            logger.error(f"Помилка при поновленні підписки {subscription_id}: {e}")
            return False
    
    @staticmethod
    async def cancel_subscription(subscription_id: str) -> bool:
        """Скасувати підписку наприкінці поточного оплаченого періоду"""
        try:
            result = await StripeManager._stripe_call(
                stripe.Subscription.modify,
                subscription_id,
                cancel_at_period_end=True  # Скасувати наприкінці поточного периоду (не одразу)
            )
            logger.info(f"Підписку {subscription_id} заплановано на скасування в Stripe, cancel_at_period_end={result.cancel_at_period_end}")
            return True
        except Exception as e:
            logger.error(f"Помилка при скасуванні підписки {subscription_id}: {e}")
            return False
    
    @staticmethod
    async def create_payment_method_update_session(customer_id: str) -> Optional[str]:
        """Створити Setup Intent для оновлення платіжного методу (без можливості скасувати підписку)"""
        try:
            # Створюємо Setup Intent для додавання/оновлення платіжного методу
            setup_intent = await StripeManager._stripe_call(
                stripe.SetupIntent.create,
                customer=customer_id,
                payment_method_types=['card'],
                usage='off_session',
                metadata={'type': 'payment_method_update'}
            )
            
            logger.info(f"Створено Setup Intent для оновлення платіжного методу customer {customer_id}")
            return setup_intent.client_secret
        except Exception as e:
            logger.error(f"Помилка при створенні Setup Intent: {e}")
            return None
    
    @staticmethod
    async def create_billing_portal_session(customer_id: str, return_url: str, allow_cancel: bool = False) -> Optional[str]:
        """Створити сесію Stripe Customer Portal для зміни платіжного методу
        
        Args:
            customer_id: ID клієнта в Stripe
            return_url: URL для повернення після завершення
            allow_cancel: Чи дозволити скасування підписки в порталі (за замовчуванням False)
        """
        try:
            # Налаштування конфігурації порталу
            portal_config = {
                'customer': customer_id,
                'return_url': return_url,
            }
            
            # Якщо не дозволяємо скасування, використовуємо конфігурацію з обмеженими можливостями
            if not allow_cancel:
                # Створюємо тимчасову конфігурацію Billing Portal з обмеженими функціями
                try:
                    configuration = await StripeManager._stripe_call(
                        stripe.billing_portal.Configuration.create,
                        business_profile={'headline': 'Оновлення платіжного методу'},
                        features={
                            'customer_update': {'enabled': True, 'allowed_updates': ['email', 'address']},
                            'payment_method_update': {'enabled': True},
                            'subscription_cancel': {'enabled': False},
                            'subscription_pause': {'enabled': False},
                            'subscription_update': {'enabled': False},
                        },
                    )
                    portal_config['configuration'] = configuration.id
                    logger.info(f"Створено конфігурацію Billing Portal без можливості скасування: {configuration.id}")
                except Exception as config_error:
                    logger.warning(f"Не вдалося створити custom конфігурацію: {config_error}. Використовуємо default.")
            
            session = await StripeManager._stripe_call(
                stripe.billing_portal.Session.create,
                **portal_config
            )
            logger.info(f"Створено Billing Portal сесію для customer {customer_id} (allow_cancel={allow_cancel})")
            return session.url
        except Exception as e:
            logger.error(f"Помилка при створенні Billing Portal сесії: {e}")
            return None
    
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