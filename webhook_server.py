"""
Веб-сервер для обробки Stripe та Telegram webhooks
"""
import json
import stripe
import logging
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.request import HTTPXRequest
from stripe.error import StripeError

from config import settings
from payments import StripeManager
from database import DatabaseManager, User

# Створюємо FastAPI додаток
app = FastAPI(title="Upgrade Studio Bot Webhooks")

# Налаштування логування
logging.basicConfig(level=getattr(logging, settings.log_level or "INFO"))
logger = logging.getLogger(__name__)

# Налаштування Stripe
stripe.api_key = settings.stripe_secret_key

# Ініціалізуємо Telegram бота для відправки повідомлень з налаштованим timeout
request = HTTPXRequest(
    connect_timeout=10.0,  # Timeout на з'єднання
    read_timeout=30.0,     # Timeout на читання відповіді
    write_timeout=30.0,    # Timeout на запис
    pool_timeout=10.0      # Timeout на отримання з'єднання з пулу
)
telegram_bot = Bot(token=settings.telegram_bot_token, request=request)

# Імпортуємо бот для обробки Telegram updates
try:
    from main import bot_instance
    TELEGRAM_BOT_AVAILABLE = True
    logger.info("Telegram bot instance завантажено для webhook обробки")
except ImportError as e:
    TELEGRAM_BOT_AVAILABLE = False
    logger.warning(f"Не вдалося завантажити telegram bot instance: {e}")


async def send_telegram_notification(telegram_id: int, message: str):
    """Надіслати повідомлення користувачу через Telegram"""
    try:
        await telegram_bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"Повідомлення надіслано користувачу {telegram_id}")
    except Exception as e:
        logger.error(f"Помилка надсилання повідомлення: {e}")

async def send_payment_success_notification(telegram_id: int):
    """Надіслати повідомлення про успішну оплату та розпочати процес приєднання"""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from database.models import DatabaseManager
        from config import UserState
        
        # Надсилаємо повідомлення про успішну оплату
        await telegram_bot.send_message(
            chat_id=telegram_id,
            text="Оплата успішна!\n\n"
                 "Дякуємо! Ваша підписка активована.\n"
                 "Тепер ви маєте доступ до всіх можливостей UPGRADE STUDIO!",
            parse_mode='Markdown'
        )
        
        # Встановлюємо стан очікування приєднання до каналу
        DatabaseManager.update_user_state(telegram_id, UserState.CHANNEL_JOIN_PENDING)
        
        # Отримуємо посилання на канал з бази
        invite_links = DatabaseManager.get_active_invite_links()
        channel_link = None
        
        for link in invite_links:
            if link.chat_type == "channel":
                channel_link = link
                break
        
        if channel_link:
            keyboard = [[InlineKeyboardButton(
                text="Приєднатися до каналу",
                url=channel_link.invite_link
            )]]
        else:
            # Fallback
            from config import settings
            keyboard = [[InlineKeyboardButton(
                text="Приєднатися до каналу",
                url=f"https://t.me/{settings.private_channel_id.lstrip('-')}"
            )]]
        
        # Додаємо кнопку "Я приєднався"
        keyboard.append([InlineKeyboardButton(
            text="Я приєднався до каналу",
            callback_data="channel_joined"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await telegram_bot.send_message(
            chat_id=telegram_id,
            text="Крок 1: Приєднання до каналу\n\n"
                 "Спочатку приєднайтеся до нашого приватного каналу з тренуваннями та корисною інформацією.\n\n"
                 "Після приєднання натисніть кнопку 'Я приєднався до каналу'",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"Розпочато процес послідовного приєднання для користувача {telegram_id}")
        
    except Exception as e:
        logger.error(f"Помилка надсилання повідомлення про оплату: {e}")

async def delete_payment_message(telegram_id: int):
    """Видалити попереднє повідомлення з платіжним посиланням"""
    try:
        # Замість видалення конкретного повідомлення, надішлемо нове повідомлення
        # що перекриє попереднє в контексті розмови з ботом
        # Це більш надійний підхід, ніж спроба вгадати ID повідомлення
        
        logger.info(f"Підготовка до очищення інтерфейсу для користувача {telegram_id}")
        
        # Нічого не робимо тут - очищення відбудеться через нове повідомлення
        # з результатом оплати в send_payment_success_notification
        
    except Exception as e:
        logger.error(f"Помилка підготовки очищення для користувача {telegram_id}: {e}")
        
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення про оплату для користувача {telegram_id}: {e}")

async def handle_checkout_session_completed(session):
    """Обробити завершення checkout сесії"""
    try:
        logger.info(f"Обробка checkout.session.completed: {session['id']}")
        logger.info(f"Session data: payment_intent={session.get('payment_intent')}, "
                   f"subscription={session.get('subscription')}, "
                   f"amount_total={session.get('amount_total')}, "
                   f"customer={session.get('customer')}")
        
        # Отримуємо telegram_id з метаданих
        telegram_id = session.get('metadata', {}).get('telegram_id')
        if not telegram_id:
            logger.error("Telegram ID не знайдено в метаданих")
            return False
        
        telegram_id = int(telegram_id)
        
        # Оновлюємо користувача в БД
        with DatabaseManager() as db:
            from database.models import Payment
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                # Отримуємо payment_intent_id (може бути об'єктом або рядком)
                payment_intent = session.get('payment_intent')
                if isinstance(payment_intent, dict):
                    payment_intent_id = payment_intent.get('id')
                else:
                    payment_intent_id = payment_intent
                
                # Отримуємо subscription_id (може бути об'єктом або рядком)
                subscription = session.get('subscription')
                if isinstance(subscription, dict):
                    subscription_id = subscription.get('id')
                else:
                    subscription_id = subscription
                
                # Логуємо що отримали
                logger.info(f"Extracted IDs: payment_intent_id={payment_intent_id}, subscription_id={subscription_id}")
                
                # Зберігаємо повний лог відповіді Stripe як JSON
                import json
                stripe_log = json.dumps(session, indent=2, default=str)
                
                # Зберігаємо дані про платіж
                payment = Payment(
                    user_id=user.id,
                    amount=session.get('amount_total', 0),  # Зберігаємо в центах (Integer)
                    currency=session.get('currency', 'eur'),
                    status="succeeded",  # Stripe використовує 'succeeded' для успішних платежів
                    stripe_payment_intent_id=payment_intent_id,
                    stripe_subscription_id=subscription_id,
                    stripe_invoice_id=session.get('invoice'),
                    stripe_response_log=stripe_log,  # Зберігаємо повний лог
                    paid_at=datetime.utcnow()
                )
                db.add(payment)
                
                logger.info(f"Збережено платіж: amount={session.get('amount_total')} центів, "
                          f"payment_intent={payment_intent_id}, "
                          f"subscription={subscription_id}")
                
                # Оновлюємо користувача
                user.subscription_active = True
                user.subscription_paused = False
                user.subscription_cancelled = False
                user.auto_payment_enabled = True
                user.stripe_customer_id = session.get('customer')
                user.stripe_subscription_id = subscription_id
                
                # Встановлюємо дати підписки
                date_set = False
                
                if subscription_id:
                    try:
                        # Отримуємо деталі підписки безпосередньо через Stripe API
                        subscription_obj = stripe.Subscription.retrieve(subscription_id)
                        
                        if subscription_obj and subscription_obj.current_period_end:
                            # Встановлюємо дати на основі інформації з Stripe
                            end_date = datetime.fromtimestamp(subscription_obj.current_period_end)
                            user.next_billing_date = end_date
                            user.subscription_end_date = end_date
                            date_set = True
                            logger.info(f"Дати підписки встановлено з Stripe для користувача {telegram_id}: "
                                      f"subscription_end_date={user.subscription_end_date}, "
                                      f"next_billing_date={user.next_billing_date}")
                                
                    except Exception as e:
                        logger.error(f"Не вдалося отримати деталі підписки {subscription_id}: {e}")
                
                # Якщо не вдалося отримати дати з Stripe - встановлюємо дефолтні (30 днів)
                if not date_set:
                    end_date = datetime.utcnow() + timedelta(days=30)
                    user.next_billing_date = end_date
                    user.subscription_end_date = end_date
                    logger.info(f"Встановлено дефолтні дати підписки (30 днів) для користувача {telegram_id}: "
                              f"subscription_end_date={user.subscription_end_date}, "
                              f"next_billing_date={user.next_billing_date}")
                
                user.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Користувача {telegram_id} оновлено: subscription_active=True, "
                          f"subscription_end_date={user.subscription_end_date}, "
                          f"stripe_payment_intent_id={payment_intent_id}")
                
                # Скасовуємо нагадування про підписку
                DatabaseManager.cancel_subscription_reminders_if_active(telegram_id)
                
                # Надсилаємо повідомлення про успішну оплату через bot_instance
                # який має всю логіку автоматичного схвалення join requests
                logger.info(f"Надсилаю повідомлення про успішну оплату користувачу {telegram_id}")
                if TELEGRAM_BOT_AVAILABLE and bot_instance:
                    try:
                        await bot_instance.handle_successful_payment(telegram_id)
                        logger.info(f"Викликано handle_successful_payment для користувача {telegram_id}")
                    except Exception as e:
                        logger.error(f"Помилка виклику handle_successful_payment: {e}")
                        # Fallback - надсилаємо просте повідомлення
                        await send_payment_success_notification(telegram_id)
                else:
                    logger.warning("bot_instance недоступний, використовуємо fallback")
                    await send_payment_success_notification(telegram_id)
                
                # Надсилаємо повідомлення в Tech групу про успішну оплату
                try:
                    user_info = f"@{user.username}" if user.username else user.full_name or f"ID: {telegram_id}"
                    
                    # Підраховуємо кількість успішних оплат
                    from database.models import Payment
                    with DatabaseManager() as db:
                        payment_count = db.query(Payment).filter(
                            Payment.user_id == user.id,
                            Payment.status.in_(["succeeded", "completed"])
                        ).count()
                    
                    # Формуємо повідомлення
                    message_text = (
                        f"✅ **Нова підписка**\n\n"
                        f"Користувач: {user_info}\n"
                        f"ID: `{telegram_id}`\n"
                        f"Ім'я: {user.first_name} {user.last_name or ''}\n"
                        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                        f"Успішних оплат: {payment_count}"
                    )
                    
                    # Додаємо травми якщо є
                    if user.injuries and user.injuries.strip() and "Немає" not in user.injuries:
                        message_text += f"\nТравми: \"{user.injuries}\""
                    
                    await telegram_bot.send_message(
                        chat_id=settings.tech_notifications_chat_id,
                        text=message_text,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Повідомлення про оплату надіслано в Tech групу")
                except Exception as e:
                    logger.error(f"Помилка відправки повідомлення в Tech групу: {e}")
                
                logger.info(f"Підписка активована для користувача {telegram_id}, платіж збережено")
                return True
        
        logger.error(f"Користувач {telegram_id} не знайдений")
        return False
        
    except Exception as e:
        logger.error(f"Помилка обробки checkout.session.completed: {e}")
        return False

async def handle_customer_subscription_updated(subscription):
    """Обробити оновлення підписки"""
    try:
        logger.info(f"Обробка customer.subscription.updated: {subscription['id']}")
        
        subscription_id = subscription['id']
        user = DatabaseManager.get_user_by_stripe_subscription_id(subscription_id)
        
        if not user:
            logger.warning(f"Користувач з subscription_id {subscription_id} не знайдений")
            return False
        
        # Оновлюємо статус підписки
        with DatabaseManager() as db:
            db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
            if db_user:
                # Перевіряємо, чи це не тестова підписка адміна
                if db_user.stripe_subscription_id and db_user.stripe_subscription_id.startswith("sub_test_"):
                    logger.info(f"Пропускаємо оновлення тестової підписки адміна {user.telegram_id}")
                    return True
                status = subscription.get('status')
                cancel_at_period_end = subscription.get('cancel_at_period_end', False)
                
                if status == 'active':
                    db_user.subscription_active = True
                    db_user.subscription_paused = False
                    db_user.subscription_status = 'active'
                    if not cancel_at_period_end:
                        db_user.subscription_cancelled = False
                        db_user.auto_payment_enabled = True  # Включаємо автоплатіж при активації
                    logger.info(f"Webhook: Статус підписки 'active' для користувача {user.telegram_id}")
                elif status == 'paused':
                    db_user.subscription_paused = True
                    db_user.auto_payment_enabled = False  # Вимикаємо автоплатіж при паузі
                    # subscription_active залишається True до subscription_end_date
                    # joined_channel/chat НЕ скидаємо - доступ до end_date
                    logger.info(f"Webhook: Підписка призупинена для користувача {user.telegram_id}, доступ до end_date")
                elif status in ['canceled', 'cancelled']:
                    db_user.subscription_cancelled = True
                    db_user.auto_payment_enabled = False  # Вимикаємо автоплатіж
                    # subscription_active залишається True до subscription_end_date
                    # joined_channel/chat НЕ скидаємо - доступ до end_date
                    logger.info(f"Webhook: Підписка скасована для користувача {user.telegram_id}, доступ до end_date")
                
                # Оновлюємо дати
                if 'current_period_end' in subscription:
                    period_end = datetime.fromtimestamp(subscription['current_period_end'])
                    if status == 'active' and not cancel_at_period_end:
                        # Для активних підписок встановлюємо обидві дати
                        db_user.next_billing_date = period_end
                        db_user.subscription_end_date = period_end  # Дата до якої активна підписка
                    elif cancel_at_period_end or status in ['canceled', 'cancelled']:
                        # Для скасованих підписок - це дата закінчення
                        db_user.subscription_end_date = period_end
                        db_user.next_billing_date = None  # Немає наступного списання
                    elif status == 'paused':
                        # Для призупинених підписок зберігаємо кінцеву дату
                        db_user.subscription_end_date = period_end
                        db_user.next_billing_date = None  # Немає списання поки призупинено
                
                db_user.updated_at = datetime.utcnow()
                db.commit()
                
                # Перевіряємо чи скасування відбулося через невдалу оплату
                cancellation_details = subscription.get('cancellation_details', {})
                cancellation_reason = cancellation_details.get('reason') if cancellation_details else None
                
                # Надсилаємо повідомлення користувачу тільки для певних випадків
                if status in ['canceled', 'cancelled'] and cancellation_reason == 'payment_failed':
                    # Скасування через невдалу оплату
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🩵 Оформити підписку", callback_data="create_subscription")],
                        [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")]
                    ])
                    
                    await telegram_bot.send_message(
                        chat_id=user.telegram_id,
                        text="Підписку було скасовано ❌\n\n"
                             "На жаль, підписку було скасовано, оскільки не вдалося здійснити списання коштів.\n\n"
                             "Якщо у тебе виникли будь-які питання, напиши мені.\n\n"
                             "Щоб створити нову підписку, натисни кнопку нижче.",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    
                    # Відправляємо в Tech групу
                    user_info = f"@{user.username}" if user.username else user.full_name or f"ID: {user.telegram_id}"
                    
                    # Підраховуємо кількість успішних оплат
                    from database.models import Payment
                    with DatabaseManager() as db_temp:
                        payment_count = db_temp.query(Payment).filter(
                            Payment.user_id == db_user.id,
                            Payment.status.in_(["succeeded", "completed"])
                        ).count()
                    
                    await telegram_bot.send_message(
                        chat_id=settings.tech_notifications_chat_id,
                        text=f"❌ **Скасована автоматично**\n\n"
                             f"Користувач: {user_info}\n"
                             f"ID: `{user.telegram_id}`\n"
                             f"Ім'я: {user.first_name} {user.last_name or ''}\n"
                             f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                             f"Успішних оплат: {payment_count}",
                        parse_mode='Markdown'
                    )
                elif cancel_at_period_end:
                    await send_telegram_notification(
                        user.telegram_id,
                        f"⚠️ **Підписка скасована**\n\n"
                        f"Ваша підписка буде активна до {period_end.strftime('%d.%m.%Y')}.\n"
                        "Після цієї дати доступ до каналів буде припинено.\n\n"
                        "❌ Автоматичне продовження вимкнено\n\n"
                        "Ви можете поновити підписку у будь-який момент!"
                    )
                elif status == 'paused':
                    await send_telegram_notification(
                        user.telegram_id,
                        f"⏸️ **Підписка призупинена**\n\n"
                        f"Ваша підписка залишається активною до {period_end.strftime('%d.%m.%Y')}.\n"
                        "Доступ до каналів зберігається до цієї дати.\n\n"
                        "❌ Автоматичне продовження вимкнено\n\n"
                        "Ви можете відновити автоплатіж через /subscription"
                    )
                elif status == 'active' and not db_user.subscription_paused:
                    # Перевіряємо чи це поновлення існуючої підписки (а не перша активація)
                    # Для цього дивимося чи були раніше платежі
                    from database.models import Payment
                    payment_count = db.query(Payment).filter(
                        Payment.user_id == db_user.id,
                        Payment.status == "completed"
                    ).count()
                    
                    # Надсилаємо повідомлення про поновлення тільки якщо це не перша оплата
                    if payment_count > 1:
                        await send_telegram_notification(
                            user.telegram_id,
                            " **Підписка поновлена**\n\n"
                            "Ваша підписка знову активна!\n"
                            "Тепер ви маєте повний доступ до всіх можливостей UPGRADE STUDIO! "
                        )
                
                logger.info(f"Статус підписки оновлено для користувача {user.telegram_id}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Помилка обробки customer.subscription.updated: {e}")
        return False

async def handle_payment_method_attached(payment_method):
    """Обробити прив'язку нового платіжного методу"""
    try:
        logger.info(f"Обробка payment_method.attached: {payment_method['id']}")
        
        customer_id = payment_method.get('customer')
        if not customer_id:
            logger.warning("Немає customer_id в payment_method")
            return False
        
        user = DatabaseManager.get_user_by_stripe_customer_id(customer_id)
        if not user:
            logger.warning(f"Користувач з customer_id {customer_id} не знайдений")
            return False
        
        # Перевіряємо чи це не тестова підписка адміна
        if user.stripe_subscription_id and user.stripe_subscription_id.startswith("sub_test_"):
            logger.info(f"Пропускаємо оновлення тестової підписки адміна {user.telegram_id}")
            return True
        
        # Отримуємо дату наступного списання
        next_billing_str = "кінця поточного періоду"
        if user.next_billing_date:
            next_billing_str = user.next_billing_date.strftime('%d.%m')
        
        # Надсилаємо повідомлення про успішну зміну платіжного методу
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ В головне меню", callback_data="main_menu_after_cancel")]
        ])
        
        await telegram_bot.send_message(
            chat_id=user.telegram_id,
            text=f"✅ Платіжний метод успішно оновлено.\n\n"
                 f"Наступне списання відбудеться {next_billing_str}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Відправляємо повідомлення в Tech групу
        try:
            user_info = f"@{user.username}" if user.username else user.full_name or f"ID: {user.telegram_id}"
            await telegram_bot.send_message(
                chat_id=settings.tech_notifications_chat_id,
                text=f"💳 **Платіжний метод оновлено**\n\n"
                     f"Користувач: {user_info}\n"
                     f"ID: `{user.telegram_id}`\n"
                     f"Ім'я: {user.first_name} {user.last_name or ''}\n"
                     f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode='Markdown'
            )
            logger.info(f"Повідомлення про зміну платіжного методу надіслано в Tech групу")
        except Exception as e:
            logger.error(f"Помилка відправки повідомлення в Tech групу: {e}")
        
        logger.info(f"Платіжний метод оновлено для користувача {user.telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"Помилка обробки payment_method.attached: {e}")
        return False

async def handle_invoice_payment_failed(invoice):
    """Обробити невдалу оплату"""
    try:
        logger.info(f"Обробка invoice.payment_failed: {invoice['id']}")
        
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return False
        
        user = DatabaseManager.get_user_by_stripe_subscription_id(subscription_id)
        if not user:
            logger.warning(f"Користувач з subscription_id {subscription_id} не знайдений")
            return False
        
        # Перевіряємо чи це не тестова підписка адміна
        if user.stripe_subscription_id and user.stripe_subscription_id.startswith("sub_test_"):
            logger.info(f"Пропускаємо повідомлення для тестової підписки адміна {user.telegram_id}")
            return True
        
        # Отримуємо дату наступної спроби оплати
        next_payment_attempt = invoice.get('next_payment_attempt')
        next_attempt_str = "найближчим часом"
        
        if next_payment_attempt:
            next_attempt_date = datetime.fromtimestamp(next_payment_attempt)
            next_attempt_str = next_attempt_date.strftime('%d.%m')
            
            # Оновлюємо дату наступного платежу в базі
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
                if db_user:
                    db_user.next_billing_date = next_attempt_date
                    db.commit()
                    logger.info(f"Оновлено next_billing_date для {user.telegram_id} на {next_attempt_str}")
        
        # Надсилаємо повідомлення про невдалу оплату з кнопками
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Керувати підпискою", callback_data="manage_subscription")],
            [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main_menu")]
        ])
        
        await telegram_bot.send_message(
            chat_id=user.telegram_id,
            text=f"💳 Виникла помилка при спробі списання оплати за підписку.\n\n"
                 f"Наступна спроба: {next_attempt_str}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Відправляємо повідомлення в Tech групу
        try:
            user_info = f"@{user.username}" if user.username else user.full_name or f"ID: {user.telegram_id}"
            amount = invoice.get('amount_due', 0) / 100
            currency = invoice.get('currency', 'eur').upper()
            attempt_count = invoice.get('attempt_count', 1)
            
            await telegram_bot.send_message(
                chat_id=settings.tech_notifications_chat_id,
                text=f"❌ **Невдала оплата**\n\n"
                     f"Користувач: {user_info}\n"
                     f"ID: `{user.telegram_id}`\n"
                     f"Ім'я: {user.first_name} {user.last_name or ''}\n"
                     f"Сума: {amount:.2f} {currency}\n"
                     f"Спроба: {attempt_count}\n"
                     f"Наступна спроба: {next_attempt_str}\n"
                     f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode='Markdown'
            )
            logger.info(f"Повідомлення про невдалу оплату надіслано в Tech групу")
        except Exception as e:
            logger.error(f"Помилка відправки повідомлення в Tech групу: {e}")
        
        logger.info(f"Повідомлення про невдалу оплату надіслано користувачу {user.telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"Помилка обробки invoice.payment_failed: {e}")
        return False

async def handle_invoice_payment_succeeded(invoice):
    """Обробити успішну оплату (продовження підписки)"""
    try:
        logger.info(f"Обробка invoice.payment_succeeded: {invoice['id']}")
        
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            logger.info("Не subscription invoice - пропускаємо")
            return True
        
        user = DatabaseManager.get_user_by_stripe_subscription_id(subscription_id)
        if not user:
            logger.warning(f"Користувач з subscription_id {subscription_id} не знайдений")
            return False
        
        with DatabaseManager() as db:
            from database.models import Payment
            db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
            
            if db_user:
                # Зберігаємо повний лог
                import json
                stripe_log = json.dumps(invoice, indent=2, default=str)
                
                # Зберігаємо платіж
                payment = Payment(
                    user_id=db_user.id,
                    amount=invoice.get('amount_paid', 0),
                    currency=invoice.get('currency', 'eur'),
                    status="succeeded",
                    stripe_payment_intent_id=invoice.get('payment_intent'),
                    stripe_subscription_id=subscription_id,
                    stripe_invoice_id=invoice.get('id'),
                    stripe_response_log=stripe_log,
                    paid_at=datetime.utcnow()
                )
                db.add(payment)
                
                # Оновлюємо дати підписки
                try:
                    subscription_obj = stripe.Subscription.retrieve(subscription_id)
                    if subscription_obj and subscription_obj.current_period_end:
                        end_date = datetime.fromtimestamp(subscription_obj.current_period_end)
                        db_user.next_billing_date = end_date
                        db_user.subscription_end_date = end_date
                        db_user.subscription_active = True
                        db_user.auto_payment_enabled = True  # Успішна оплата = автоплатіж працює
                        
                        # Якщо була призупинена або скасована - знімаємо ці статуси
                        if db_user.subscription_paused:
                            db_user.subscription_paused = False
                            logger.info(f"Знято статус 'paused' після успішної оплати для {user.telegram_id}")
                        if db_user.subscription_cancelled:
                            db_user.subscription_cancelled = False
                            logger.info(f"Знято статус 'cancelled' після успішної оплати для {user.telegram_id}")
                        
                        logger.info(f"Оновлено дати підписки до {end_date} для користувача {user.telegram_id}")
                        
                        # Створюємо нагадування за 7 днів до списання
                        reminder_date = end_date - timedelta(days=7)
                        if reminder_date > datetime.utcnow():
                            from database.models import Reminder
                            # Перевіряємо чи немає вже такого нагадування
                            existing = db.query(Reminder).filter(
                                Reminder.user_id == db_user.id,
                                Reminder.reminder_type == "subscription_renewal",
                                Reminder.is_active == True,
                                Reminder.scheduled_at >= datetime.utcnow()
                            ).first()
                            
                            if not existing:
                                reminder = Reminder(
                                    user_id=db_user.id,
                                    reminder_type="subscription_renewal",
                                    scheduled_at=reminder_date,
                                    max_attempts=1,
                                    is_active=True
                                )
                                db.add(reminder)
                                logger.info(f"Створено нагадування на {reminder_date} для користувача {user.telegram_id}")
                
                except Exception as e:
                    logger.error(f"Помилка при оновленні дат підписки: {e}")
                
                db.commit()
                
                # Надсилаємо повідомлення про успішне продовження
                await send_telegram_notification(
                    user.telegram_id,
                    "✅ **Підписка продовжена**\n\n"
                    f"Ваша підписка успішно продовжена.\n"
                    f"Дякуємо за довіру! 🎉"
                )
                
                # Відправляємо повідомлення в Tech групу
                try:
                    user_info = f"@{user.username}" if user.username else user.full_name or f"ID: {user.telegram_id}"
                    
                    # Підраховуємо кількість успішних оплат
                    payment_count = db.query(Payment).filter(
                        Payment.user_id == db_user.id,
                        Payment.status.in_(["succeeded", "completed"])
                    ).count()
                    
                    await telegram_bot.send_message(
                        chat_id=settings.tech_notifications_chat_id,
                        text=f"✅ **Автоматично продовжена**\n\n"
                             f"Користувач: {user_info}\n"
                             f"ID: `{user.telegram_id}`\n"
                             f"Ім'я: {user.first_name} {user.last_name or ''}\n"
                             f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                             f"Успішних оплат: {payment_count}",
                        parse_mode='Markdown'
                    )
                    logger.info(f"Повідомлення про продовження підписки надіслано в Tech групу")
                except Exception as e:
                    logger.error(f"Помилка відправки повідомлення в Tech групу: {e}")
                
                logger.info(f"Оброблено успішну оплату для користувача {user.telegram_id}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Помилка обробки invoice.payment_succeeded: {e}")
        return False


@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Обробник Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    # Перевіряємо чи це запит від Stripe (має stripe-signature header)
    if not sig_header:
        logger.warning(f"Отримано запит без Stripe підпису від {request.client.host} - ігнорується")
        return JSONResponse(content={"status": "ignored", "reason": "Not a Stripe webhook"}, status_code=200)
    
    # Перевіряємо підпис тільки якщо налаштований справжній webhook secret
    if (settings.stripe_webhook_secret and 
        settings.stripe_webhook_secret != "whsec_mock_secret_for_testing" and
        not settings.stripe_webhook_secret.startswith("whsec_mock")):
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
            logger.info("Webhook підпис перевірено успішно")
        except ValueError as e:
            logger.error(f"Невалідний payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Невалідна підпис: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Режим розробки - пропускаємо перевірку підпису
        try:
            event = json.loads(payload.decode('utf-8'))
            logger.warning("Режим розробки - підпис webhook'а не перевіряється!")
        except json.JSONDecodeError as e:
            logger.error(f"Невалідний JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Обробляємо подію
    event_type = event['type']
    event_data = event['data']['object']
    
    logger.info(f"Отримано Stripe webhook: {event_type}")
    
    # Обробка різних типів подій
    success = False
    try:
        if event_type == 'checkout.session.completed':
            success = await handle_checkout_session_completed(event_data)
        elif event_type == 'customer.subscription.updated':
            success = await handle_customer_subscription_updated(event_data)
        elif event_type == 'invoice.payment_succeeded':
            success = await handle_invoice_payment_succeeded(event_data)
        elif event_type == 'invoice.payment_failed':
            success = await handle_invoice_payment_failed(event_data)
        elif event_type == 'payment_method.attached':
            success = await handle_payment_method_attached(event_data)
        else:
            logger.info(f"Тип події {event_type} не обробляється")
            success = True  # Не вважаємо це помилкою
            
    except Exception as e:
        logger.error(f"Помилка обробки webhook події {event_type}: {e}")
        success = False
    
    if success:
        return JSONResponse(content={"status": "success", "event_type": event_type})
    else:
        raise HTTPException(status_code=500, detail=f"Failed to process {event_type}")


@app.get("/health")
async def health_check():
    """Перевірка стану сервера"""
    return {"status": "healthy", "service": "upgrade-studio-bot-webhooks"}


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """Обробник Telegram webhooks"""
    if not TELEGRAM_BOT_AVAILABLE:
        logger.error("Telegram bot не ініціалізовано")
        return JSONResponse(content={"status": "error", "message": "Bot not available"}, status_code=503)
    
    try:
        # Ініціалізуємо bot application якщо ще не зроблено
        if bot_instance.application is None:
            logger.info("Ініціалізація bot application при першому запиті...")
            await bot_instance.initialize()
            logger.info("Bot application ініціалізовано")
        
        # Отримуємо update від Telegram
        update_data = await request.json()
        logger.info(f"Отримано Telegram update: {update_data.get('update_id', 'unknown')}")
        
        # Створюємо Update об'єкт
        update = Update.de_json(update_data, bot_instance.bot)
        
        # Обробляємо update через application
        if bot_instance.application:
            await bot_instance.application.process_update(update)
            return JSONResponse(content={"status": "ok"}, status_code=200)
        else:
            logger.error("Bot application не ініціалізовано")
            return JSONResponse(content={"status": "error", "message": "App not initialized"}, status_code=503)
            
    except Exception as e:
        logger.error(f"Помилка обробки Telegram webhook: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.get("/")
async def root():
    """Головна сторінка"""
    return {"message": "Upgrade Studio Bot Webhook Server", "version": "2.0"}


async def startup_event():
    """Ініціалізація при запуску сервера"""
    if TELEGRAM_BOT_AVAILABLE and bot_instance.application is None:
        logger.info("Ініціалізація Telegram bot application...")
        await bot_instance.initialize()
        logger.info("Telegram bot application ініціалізовано")
        
        # Встановлюємо Telegram webhook
        try:
            # Правильний URL без подвійного /webhook
            base_url = settings.webhook_url.rstrip('/') if settings.webhook_url else None
            # Видаляємо /webhook якщо він вже є в base_url
            if base_url and base_url.endswith('/webhook'):
                base_url = base_url[:-8]  # Видаляємо останні 8 символів '/webhook'
            
            webhook_url = f"{base_url}/telegram-webhook" if base_url else None
            
            if webhook_url and 'ngrok' not in webhook_url.lower():
                await bot_instance.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=["message", "callback_query", "chat_join_request"]
                )
                logger.info(f"Telegram webhook встановлено на {webhook_url}")
            else:
                logger.warning(f"Telegram webhook НЕ встановлено (URL: {webhook_url})")
        except Exception as e:
            logger.error(f"Помилка встановлення Telegram webhook: {e}")


async def shutdown_event():
    """Очищення при зупинці сервера"""
    if TELEGRAM_BOT_AVAILABLE and bot_instance.application:
        logger.info("Зупинка Telegram bot application...")
        await bot_instance.application.stop()
        await bot_instance.application.shutdown()


app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


if __name__ == "__main__":
    import uvicorn
    
    # Перевіряємо налаштування
    if not settings.stripe_secret_key:
        logger.error("STRIPE_SECRET_KEY не налаштований")
        exit(1)
    
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не налаштований") 
        exit(1)
    
    logger.info("Запуск webhook сервера...")
    uvicorn.run(
        "webhook_server:app",
        host=settings.webhook_host or "0.0.0.0",
        port=settings.webhook_port or 8000,
        reload=False  # Вимкнено reload для production
    )