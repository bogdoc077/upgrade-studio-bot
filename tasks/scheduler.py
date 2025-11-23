"""
Планувальник задач для нагадувань та автоматичних дій
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import settings, Messages
from database import DatabaseManager, Reminder, User
# from database.chain_loader import get_text  # Removed - chain_loader doesn't exist
from payments import StripeManager

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Планувальник задач та нагадувань"""
    
    def __init__(self, bot: Bot, bot_instance=None):
        self.bot = bot
        self.bot_instance = bot_instance  # Зберігаємо посилання на UpgradeBot
        self.scheduler = AsyncIOScheduler()
        
    async def start(self):
        """Запустити планувальник"""
        # Планувальник перевірки нагадувань кожну хвилину
        self.scheduler.add_job(
            self.process_reminders,
            CronTrigger(minute='*'),
            id='process_reminders'
        )
        
        # Планувальник нагадувань про підписку кожен день о 10:00
        self.scheduler.add_job(
            self.schedule_subscription_reminders,
            CronTrigger(hour=10, minute=0),
            id='subscription_reminders'
        )
        
        # Планувальник очищення старих нагадувань кожен день о 02:00
        self.scheduler.add_job(
            self.cleanup_old_reminders,
            CronTrigger(hour=2, minute=0),
            id='cleanup_reminders'
        )
        
        # Планувальник перевірки закінчених підписок кожен день о 01:00
        self.scheduler.add_job(
            self.check_expired_subscriptions,
            CronTrigger(hour=1, minute=0),
            id='check_expired_subscriptions'
        )
        
        # Планувальник обробки подій оплат кожні 10 секунд
        self.scheduler.add_job(
            self.process_payment_events,
            'interval',
            seconds=10,
            id='process_payment_events'
        )
        
        # Планувальник обробки розсилок кожні 30 секунд
        self.scheduler.add_job(
            self.process_broadcasts,
            'interval',
            seconds=30,
            id='process_broadcasts'
        )
        
        self.scheduler.start()
        logger.info("Планувальник задач запущено")
    
    async def stop(self):
        """Зупинити планувальник"""
        self.scheduler.shutdown()
        logger.info("Планувальник задач зупинено")
    
    def stop_sync(self):
        """Синхронна зупинка планувальника"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        logger.info("Планувальник задач зупинено")
    
    async def process_reminders(self):
        """Обробити всі нагадування"""
        try:
            reminders = DatabaseManager.get_pending_reminders()
            
            for reminder in reminders:
                await self.send_reminder(reminder)
                
        except Exception as e:
            logger.error(f"Помилка при обробці нагадувань: {e}")
    
    async def send_reminder(self, reminder: Reminder):
        """Надіслати нагадування користувачу"""
        try:
            # Отримуємо користувача заново через telegram_id
            user = DatabaseManager.get_user_by_telegram_id(reminder.user.telegram_id)
            if not user:
                logger.error(f"Користувача для нагадування {reminder.id} не знайдено")
                return
            
            message_text = ""
            reply_markup = None
            
            if reminder.reminder_type == "join_channel":
                message_text, reply_markup = await self._get_join_channel_reminder(reminder, user)
            elif reminder.reminder_type == "subscription_renewal":
                message_text = await self._get_subscription_renewal_reminder(reminder, user)
            elif reminder.reminder_type == "subscription_expiration":
                message_text = await self._get_subscription_expiration_reminder(reminder, user)
            elif reminder.reminder_type == "payment_retry":
                message_text = await self._get_payment_retry_reminder(reminder, user)
            
            if message_text:
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                # Позначаємо нагадування як надіслане
                DatabaseManager.mark_reminder_sent(reminder.id)
                logger.info(f"Нагадування {reminder.id} надіслано користувачу {user.telegram_id}")
                
                # Якщо це останнє нагадування про приєднання до каналу
                if (reminder.reminder_type == "join_channel" and 
                    reminder.attempts >= reminder.max_attempts - 1):
                    await self._notify_admin_about_user(user)
                
        except TelegramError as e:
            logger.error(f"Помилка Telegram при надсиланні нагадування {reminder.id}: {e}")
        except Exception as e:
            logger.error(f"Помилка при надсиланні нагадування {reminder.id}: {e}")
    
    async def _get_join_channel_reminder(self, reminder: Reminder, user: User) -> Tuple[str, Any]:
        """Отримати текст нагадування про приєднання до каналу та клавіатуру"""
        # Отримуємо активні посилання з бази
        from database.models import DatabaseManager
        
        invite_links = DatabaseManager.get_active_invite_links()
        
        if invite_links:
            # Створюємо кнопки для приєднання
            keyboard = []
            for link in invite_links:
                if link.chat_type == "channel":
                    button_text = f" Приєднатися до каналу"
                else:
                    button_text = f" Приєднатися до чату"
                
                keyboard.append([InlineKeyboardButton(
                    text=button_text,
                    url=link.invite_link
                )])
        else:
            # Fallback кнопки з settings
            keyboard = [
                [InlineKeyboardButton(
                    text=" Приєднатися до каналу",
                    url=f"https://t.me/{settings.private_channel_id}"
                )],
                [InlineKeyboardButton(
                    text=" Приєднатися до чату", 
                    url=f"https://t.me/{settings.private_chat_id}"
                )]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Текст нагадування
        text = """⏰ Нагадування!

Ви ще не приєдналися до каналу та чату. 
Для участі у тренуваннях обов'язково приєднайтеся:

⚠️ Важливо: приєднайтеся протягом доби, інакше буду нагадувати"""
        
        return text, reply_markup
    
    async def _get_subscription_renewal_reminder(self, reminder: Reminder, user: User) -> str:
        """Отримати текст нагадування про продовження підписки"""
        if user.subscription_end_date:
            days_left = (user.subscription_end_date - datetime.utcnow()).days
            return f"""🔔 **Нагадування про підписку**

Ваша підписка закінчується через **{days_left} днів**.

📅 Дата наступного списання: {user.next_billing_date.strftime('%d.%m.%Y')}

{'✅ Автоматичне продовження активне' if not user.subscription_cancelled else '⚠️ Автоматичне продовження вимкнене'}

Переконайтеся, що на вашій картці достатньо коштів для автоматичного продовження.

Якщо у вас виникли питання, зв'яжіться з підтримкою"""
        return Messages.SUBSCRIPTION_REMINDER
    
    async def _get_subscription_expiration_reminder(self, reminder: Reminder, user: User) -> str:
        """Отримати текст нагадування про закінчення підписки (без автоплатежу)"""
        if user.subscription_end_date:
            # Якщо підписка вже закінчилась
            if user.subscription_end_date < datetime.utcnow():
                return f"""⚠️ **Ваша підписка закінчилась**

Ваша підписка була активна до {user.subscription_end_date.strftime('%d.%m.%Y')}.

Автоматичне продовження було вимкнене, тому списання не відбулось.

Щоб продовжити користуватися сервісом:
1. Поновіть підписку в особистому кабінеті
2. Або зв'яжіться з нашою підтримкою

📞 Підтримка: [посилання на підтримку]"""
            else:
                # Підписка ще активна, але скоро закінчиться
                days_left = (user.subscription_end_date - datetime.utcnow()).days
                return f"""⚠️ **Ваша підписка закінчується**

Ваша підписка закінчується через **{days_left} днів** ({user.subscription_end_date.strftime('%d.%m.%Y')}).

❌ Автоматичне продовження вимкнене

Для продовження доступу вам потрібно:
1. Поновити підписку вручну
2. Або увімкнути автоматичне продовження

📞 Зв'яжіться з підтримкою для допомоги"""
        return "Ваша підписка закінчується. Зверніться до підтримки."
    
    async def _get_payment_retry_reminder(self, reminder: Reminder, user: User) -> str:
        """Отримати текст нагадування про повторну оплату"""
        return Messages.PAYMENT_FAILED
    
    async def _notify_admin_about_user(self, user: User):
        """Сповістити адміна про користувача що не приєднався до каналу"""
        try:
            admin_message = f"""
 Увага! Користувач не приєднався до каналу

 Користувач: {user.first_name} {user.last_name or ''}
 Telegram ID: {user.telegram_id}
 Username: @{user.username or 'не вказано'}
 Дата реєстрації: {user.created_at.strftime('%d.%m.%Y %H:%M')}

Користувач оплатив підписку, але не приєднався до каналу протягом 3 днів.
"""
            
            await self.bot.send_message(
                chat_id=settings.admin_chat_id,
                text=admin_message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Помилка при сповіщенні адміна: {e}")
    
    async def schedule_subscription_reminders(self):
        """Запланувати нагадування про продовження підписки"""
        try:
            # Знаходимо всіх користувачів з активними підписками
            with DatabaseManager() as db:
                users = db.query(User).filter(
                    User.subscription_active == True,
                    User.stripe_subscription_id.isnot(None)
                ).all()
                
                for user in users:
                    # Отримуємо інформацію про підписку з Stripe
                    subscription_info = await StripeManager.get_subscription(user.stripe_subscription_id)
                    
                    if subscription_info:
                        # Рахуємо дату нагадування (за 7 днів до списання)
                        next_billing = subscription_info['current_period_end']
                        reminder_date = next_billing - timedelta(days=settings.subscription_reminder_days)
                        
                        # Перевіряємо чи потрібно створити нагадування
                        now = datetime.utcnow()
                        if reminder_date > now and reminder_date <= now + timedelta(days=1):
                            # Створюємо нагадування якщо його ще немає
                            existing_reminder = db.query(Reminder).filter(
                                Reminder.user_id == user.id,
                                Reminder.reminder_type == "subscription_renewal",
                                Reminder.is_active == True,
                                Reminder.scheduled_at >= now
                            ).first()
                            
                            if not existing_reminder:
                                DatabaseManager.create_reminder(
                                    user_id=user.id,
                                    reminder_type="subscription_renewal",
                                    scheduled_at=reminder_date,
                                    max_attempts=1
                                )
                                logger.info(f"Заплановано нагадування про підписку для користувача {user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Помилка при плануванні нагадувань про підписку: {e}")
    
    async def schedule_join_reminders(self, user_id: int):
        """Заплановати нагадування про приєднання до каналу"""
        try:
            now = datetime.utcnow()
            
            # Створюємо нагадування на 1 та 2 день
            for day in settings.reminder_intervals:
                reminder_time = now + timedelta(days=day)
                
                DatabaseManager.create_reminder(
                    user_id=user_id,
                    reminder_type="join_channel",
                    scheduled_at=reminder_time,
                    max_attempts=3
                )
                
            logger.info(f"Заплановано нагадування про приєднання для користувача {user_id}")
            
        except Exception as e:
            logger.error(f"Помилка при плануванні нагадувань про приєднання: {e}")
    
    async def schedule_subscription_reminder(self, user_id: int, hours: int = 24):
        """Заплановати одиночне нагадування про підписку"""
        try:
            now = datetime.utcnow()
            reminder_time = now + timedelta(hours=hours)
            
            DatabaseManager.create_reminder(
                user_id=user_id,
                reminder_type="subscription_renewal",
                scheduled_at=reminder_time,
                max_attempts=1
            )
            
            logger.info(f"Заплановано нагадування про підписку для користувача {user_id} через {hours} годин")
            
        except Exception as e:
            logger.error(f"Помилка при плануванні нагадування про підписку: {e}")
    
    async def cleanup_old_reminders(self):
        """Очистити старі нагадування"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            with DatabaseManager() as db:
                # Видаляємо старі неактивні нагадування
                deleted_count = db.query(Reminder).filter(
                    Reminder.is_active == False,
                    Reminder.created_at < cutoff_date
                ).delete()
                
                db.commit()
                logger.info(f"Видалено {deleted_count} старих нагадувань")
                
        except Exception as e:
            logger.error(f"Помилка при очищенні старих нагадувань: {e}")
    
    async def handle_successful_payment(self, user_id: int):
        """Обробити успішну оплату - запланувати нагадування про приєднання"""
        await self.schedule_join_reminders(user_id)
    
    async def handle_failed_payment(self, user_id: int, retry_in_hours: int = 24):
        """Обробити невдалу оплату - запланувати нагадування про повторну спробу"""
        try:
            retry_time = datetime.utcnow() + timedelta(hours=retry_in_hours)
            
            DatabaseManager.create_reminder(
                user_id=user_id,
                reminder_type="payment_retry",
                scheduled_at=retry_time,
                max_attempts=1
            )
            
            logger.info(f"Заплановано нагадування про повторну оплату для користувача {user_id}")
            
        except Exception as e:
            logger.error(f"Помилка при плануванні нагадування про повторну оплату: {e}")
    
    async def _remove_user_from_chats(self, telegram_id: int):
        """Видалити користувача з приватних каналів та чатів"""
        try:
            # Видаляємо з приватного каналу
            if settings.private_channel_id:
                try:
                    await self.bot.ban_chat_member(
                        chat_id=settings.private_channel_id,
                        user_id=telegram_id
                    )
                    # Одразу розбаніваємо, щоб користувач міг приєднатися знову при поновленні
                    await self.bot.unban_chat_member(
                        chat_id=settings.private_channel_id,
                        user_id=telegram_id
                    )
                    logger.info(f"Видалено користувача {telegram_id} з каналу {settings.private_channel_id}")
                except Exception as e:
                    # Якщо користувач не в каналі, це нормально
                    logger.warning(f"Помилка при видаленні з каналу {telegram_id}: {e}")
            
            # Видаляємо з приватного чату
            if settings.private_chat_id:
                try:
                    await self.bot.ban_chat_member(
                        chat_id=settings.private_chat_id,
                        user_id=telegram_id
                    )
                    logger.info(f"Видалено користувача {telegram_id} з чату {settings.private_chat_id}")
                    
                    # Одразу розбаніваємо (для звичайних груп це може не працювати - це нормально)
                    try:
                        await self.bot.unban_chat_member(
                            chat_id=settings.private_chat_id,
                            user_id=telegram_id
                        )
                    except Exception as unban_error:
                        # Ігноруємо помилки unban для звичайних груп
                        logger.debug(f"Unban не спрацював (можливо звичайна група): {unban_error}")
                except Exception as e:
                    logger.warning(f"Помилка при видаленні з чату {telegram_id}: {e}")
            
            # Надсилаємо повідомлення користувачу
            try:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="""⚠️ **Ваша підписка закінчилась**

Доступ до приватних каналів та чатів було закрито.

Щоб продовжити користуватися сервісом:
1. Поновіть підписку через /start
2. Або зв'яжіться з підтримкою

Дякуємо, що були з нами! 💙""",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Не вдалось надіслати повідомлення користувачу {telegram_id}: {e}")
                
        except Exception as e:
            logger.error(f"Помилка при видаленні користувача {telegram_id} з чатів: {e}")
    
    async def check_expired_subscriptions(self):
        """Перевірити та оновити статуси закінчених підписок"""
        try:
            now = datetime.utcnow()
            
            # Знаходимо користувачів з закінченими підписками
            with DatabaseManager() as db:
                expired_users = db.query(User).filter(
                    User.subscription_end_date.isnot(None),
                    User.subscription_end_date <= now,
                    User.subscription_active == True
                ).all()
                
                for user in expired_users:
                    # Видаляємо з каналів/чатів
                    if user.joined_channel or user.joined_chat:
                        await self._remove_user_from_chats(user.telegram_id)
                    
                    # Скидаємо статуси доступу
                    user.subscription_active = False
                    user.joined_channel = False
                    user.joined_chat = False
                    
                    logger.info(f"Скинуто статуси для користувача {user.telegram_id} - підписка закінчена {user.subscription_end_date}")
                
                if expired_users:
                    db.commit()
                    logger.info(f"Оброблено {len(expired_users)} закінчених підписок")
                
                # Також перевіряємо користувачів з призупиненими підписками без end_date
                paused_users = db.query(User).filter(
                    User.subscription_paused == True,
                    User.subscription_active == True
                ).all()
                
                for user in paused_users:
                    # Для призупинених підписок теж видаляємо з чатів
                    if user.joined_channel or user.joined_chat:
                        await self._remove_user_from_chats(user.telegram_id)
                    
                    # Для призупинених підписок теж скидаємо joined статуси
                    user.subscription_active = False
                    user.joined_channel = False
                    user.joined_chat = False
                    
                    logger.info(f"Скинуто joined статуси для призупиненого користувача {user.telegram_id}")
                
                if paused_users:
                    db.commit()
                    logger.info(f"Оброблено {len(paused_users)} призупинених підписок")
                    
        except Exception as e:
            logger.error(f"Помилка при перевірці закінчених підписок: {e}")
    
    async def process_payment_events(self):
        """Обробити події успішних оплат"""
        try:
            from payment_events import get_pending_payment_events, mark_event_processed
            
            events = get_pending_payment_events()
            
            if not events:
                return  # Немає подій для обробки
                
            if not self.bot_instance:
                logger.error("bot_instance не передано в TaskScheduler - не можу обробити події оплат")
                return
            
            for event in events:
                try:
                    logger.info(f"Обробка події оплати для користувача {event['telegram_id']}")
                    
                    # Викликаємо обробник успішної оплати
                    await self.bot_instance.handle_successful_payment(event['telegram_id'])
                    
                    # Позначаємо подію як оброблену
                    mark_event_processed(event['id'])
                    logger.info(f"Подія оплати {event['id']} оброблена успішно")
                    
                except Exception as e:
                    logger.error(f"Помилка обробки події оплати {event['id']}: {e}")
                    # Не позначаємо як оброблену, щоб спробувати знову
                    
        except Exception as e:
            logger.error(f"Помилка при обробці подій оплат: {e}")    
    async def process_broadcasts(self):
        """Обробити pending розсилки"""
        try:
            from bot.broadcast_handler import BroadcastHandler
            
            handler = BroadcastHandler(self.bot)
            await handler.process_pending_broadcasts()
            
        except Exception as e:
            logger.error(f"Помилка при обробці розсилок: {e}")
