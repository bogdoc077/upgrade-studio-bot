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
        # Планувальник перевірки нагадувань кожну годину (замість кожної хвилини)
        # При масштабуванні: нагадування створюються з точним часом,
        # а цей job тільки перевіряє та надсилає їх партіями
        self.scheduler.add_job(
            self.process_reminders,
            CronTrigger(minute=0),  # Кожну годину
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
        
        # Планувальник перевірки закінчених підписок кожен день о 07:00 (з чергою)
        self.scheduler.add_job(
            self.check_expired_subscriptions,
            CronTrigger(hour=7, minute=0),
            id='check_expired_subscriptions'
        )
        
        # Планувальник нагадувань про наближення оплати (7 днів) кожен день о 10:00
        self.scheduler.add_job(
            self.check_upcoming_payments,
            CronTrigger(hour=10, minute=0),
            id='check_upcoming_payments'
        )
        
        # ❌ ВИДАЛЕНО process_payment_events - використовуємо Stripe webhooks!
        # Stripe надсилає події payment.succeeded напряму в webhook_server.py
        # Це економить ~200 запитів/годину та усуває затримки
        
        # ✅ Планувальник обробки розсилок кожні 5 хвилин
        self.scheduler.add_job(
            self.process_broadcasts,
            CronTrigger(minute='*/5'),  # Кожні 5 хвилин
            id='process_broadcasts'
        )
        
        # Планувальник очищення старих подій оплат кожен день о 03:00
        self.scheduler.add_job(
            self.cleanup_old_payment_events,
            CronTrigger(hour=3, minute=0),
            id='cleanup_payment_events'
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
            # Отримуємо тільки перші 10 нагадувань для економії пам'яті
            # Тепер це список словників, а не об'єктів Reminder
            reminder_data_list = DatabaseManager.get_pending_reminders_limited(limit=10)
            
            for reminder_data in reminder_data_list:
                await self.send_reminder(reminder_data)
                
        except Exception as e:
            logger.error(f"Помилка при обробці нагадувань: {e}")
    
    async def send_reminder(self, reminder_data: dict):
        """Надіслати нагадування користувачу"""
        try:
            # Отримуємо користувача через user_id з даних нагадування
            with DatabaseManager() as db:
                user = db.query(User).filter(User.id == reminder_data['user_id']).first()
                if not user:
                    logger.error(f"Користувача для нагадування {reminder_data['id']} не знайдено")
                    return
                
                telegram_id = user.telegram_id
            
            message_text = ""
            reply_markup = None
            
            if reminder_data['reminder_type'] == "join_channel":
                message_text, reply_markup = await self._get_join_channel_reminder(reminder_data, telegram_id)
            elif reminder_data['reminder_type'] == "subscription_renewal":
                message_text = await self._get_subscription_renewal_reminder(reminder_data, telegram_id)
            elif reminder_data['reminder_type'] == "subscription_expiration":
                message_text = await self._get_subscription_expiration_reminder(reminder_data, telegram_id)
            elif reminder_data['reminder_type'] == "payment_retry":
                message_text = await self._get_payment_retry_reminder(reminder_data, telegram_id)
            
            if message_text:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=message_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                # Позначаємо нагадування як надіслане
                DatabaseManager.mark_reminder_sent(reminder_data['id'])
                logger.info(f"Нагадування {reminder_data['id']} надіслано користувачу {telegram_id}")
                
                # Якщо це останнє нагадування про приєднання до каналу
                if (reminder_data['reminder_type'] == "join_channel" and 
                    reminder_data['attempts'] >= reminder_data['max_attempts'] - 1):
                    # Отримуємо користувача для повідомлення адміну
                    user = DatabaseManager.get_user_by_id(reminder_data['user_id'])
                    if user:
                        await self._notify_admin_about_user(user)
                
        except TelegramError as e:
            logger.error(f"Помилка Telegram при надсиланні нагадування {reminder_data['id']}: {e}")
        except Exception as e:
            logger.error(f"Помилка при надсиланні нагадування {reminder_data['id']}: {e}")
    
    async def _get_join_channel_reminder(self, reminder_data: dict, telegram_id: int) -> Tuple[str, Any]:
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
    
    async def _get_subscription_renewal_reminder(self, reminder_data: dict, telegram_id: int) -> str:
        """Отримати текст нагадування про продовження підписки"""
        # Отримуємо користувача для інформації про підписку
        user = DatabaseManager.get_user_by_telegram_id(telegram_id)
        if user and user.subscription_end_date:
            days_left = (user.subscription_end_date - datetime.utcnow()).days
            return f"""🔔 **Нагадування про підписку**

Ваша підписка закінчується через **{days_left} днів**.

📅 Дата наступного списання: {user.next_billing_date.strftime('%d.%m.%Y')}

{'✅ Автоматичне продовження активне' if not user.subscription_cancelled else '⚠️ Автоматичне продовження вимкнене'}

Переконайтеся, що на вашій картці достатньо коштів для автоматичного продовження.

Якщо у вас виникли питання, зв'яжіться з підтримкою"""
        return Messages.SUBSCRIPTION_REMINDER
    
    async def _get_subscription_expiration_reminder(self, reminder_data: dict, telegram_id: int) -> str:
        """Отримати текст нагадування про закінчення підписки (без автоплатежу)"""
        # Отримуємо користувача для інформації про підписку
        user = DatabaseManager.get_user_by_telegram_id(telegram_id)
        if user and user.subscription_end_date:
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
    
    async def _get_payment_retry_reminder(self, reminder_data: dict, telegram_id: int) -> str:
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
        start_time = datetime.utcnow()
        try:
            DatabaseManager.create_system_log(
                task_type='cleanup_old_reminders',
                status='started',
                message='Розпочато очищення старих нагадувань'
            )
            cutoff_date = datetime.utcnow() - timedelta(days=5)
            
            with DatabaseManager() as db:
                # Видаляємо старі неактивні нагадування
                deleted_count = db.query(Reminder).filter(
                    Reminder.is_active == False,
                    Reminder.created_at < cutoff_date
                ).delete()
                
                db.commit()
                logger.info(f"Видалено {deleted_count} старих нагадувань")
                
                duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                DatabaseManager.create_system_log(
                    task_type='cleanup_old_reminders',
                    status='completed',
                    message=f'Видалено {deleted_count} старих нагадувань',
                    details={'deleted_count': deleted_count},
                    duration_ms=duration
                )
                
        except Exception as e:
            logger.error(f"Помилка при очищенні старих нагадувань: {e}")
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='cleanup_old_reminders',
                status='failed',
                message=f'Помилка: {str(e)}',
                duration_ms=duration
            )
    
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
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Оформити підписку", callback_data="create_subscription")],
                    [InlineKeyboardButton("Задати питання", url="https://t.me/alionakovaliova")]
                ])
                
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="🎀 Твоя підписка закінчилась.\n\nЩоб відновити доступ до студії та спільноти, потрібно оформити нову підписку. Якщо у тебе виникли будь-які питання — буду рада відповісти.",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.warning(f"Не вдалось надіслати повідомлення користувачу {telegram_id}: {e}")
                
        except Exception as e:
            logger.error(f"Помилка при видаленні користувача {telegram_id} з чатів: {e}")
    
    async def check_expired_subscriptions(self):
        """Перевірити та оновити статуси закінчених підписок
        
        ВАЖЛИВО: Виконується 1 раз на добу о 07:00
        Обробляє користувачів ПАКЕТАМИ для масштабованості
        """
        start_time = datetime.utcnow()
        try:
            DatabaseManager.create_system_log(
                task_type='check_expired_subscriptions',
                status='started',
                message='Розпочато перевірку закінчених підписок о 07:00'
            )
            
            now = datetime.utcnow()
            expired_count = 0
            paused_reminded_count = 0
            
            # ЧЕРГА 1: Обробка закінчених підписок
            # Обробляємо пакетами по 100 користувачів для масштабованості
            batch_size = 100
            offset = 0
            
            while True:
                with DatabaseManager() as db:
                    expired_batch = db.query(User).filter(
                        User.subscription_end_date.isnot(None),
                        User.subscription_end_date <= now,
                        User.subscription_active == True
                    ).limit(batch_size).offset(offset).all()
                    
                    if not expired_batch:
                        break  # Немає більше користувачів
                    
                    for user in expired_batch:
                        try:
                            # Видаляємо з каналів/чатів
                            if user.joined_channel or user.joined_chat:
                                await self._remove_user_from_chats(user.telegram_id)
                            
                            # Скидаємо статуси доступу
                            user.subscription_active = False
                            user.joined_channel = False
                            user.joined_chat = False
                            expired_count += 1
                            
                            logger.info(f"Скинуто статуси для користувача {user.telegram_id}")
                            
                            # Відправляємо пропозицію оформити підписку знову
                            try:
                                if self.bot_instance:
                                    await self.bot_instance.show_subscription_offer(user.telegram_id)
                                    logger.info(f"Відправлено пропозицію підписки користувачу {user.telegram_id}")
                                else:
                                    logger.warning(f"bot_instance не встановлено, не можемо відправити пропозицію підписки для {user.telegram_id}")
                            except Exception as e:
                                logger.error(f"Помилка відправки пропозиції підписки користувачу {user.telegram_id}: {e}")
                            
                            # Невелика затримка між користувачами (50ms)
                            await asyncio.sleep(0.05)
                            
                        except Exception as e:
                            logger.error(f"Помилка обробки користувача {user.telegram_id}: {e}")
                            continue
                    
                    db.commit()
                    logger.info(f"Оброблено пакет з {len(expired_batch)} закінчених підписок (offset: {offset})")
                    
                    offset += batch_size
                    
                    # Затримка між пакетами (100ms)
                    await asyncio.sleep(0.1)
            
            # ЧЕРГА 2: Нагадування про призупинені підписки
            # Обробляємо також пакетами
            offset = 0
            
            while True:
                with DatabaseManager() as db:
                    paused_batch = db.query(User).filter(
                        User.subscription_paused == True,
                        User.subscription_active == True,
                        User.auto_payment_enabled == False,
                        User.subscription_end_date.isnot(None)
                    ).limit(batch_size).offset(offset).all()
                    
                    if not paused_batch:
                        break
                    
                    for user in paused_batch:
                        try:
                            days_left = (user.subscription_end_date - now).days
                            if 0 <= days_left <= 3:
                                # Нагадуємо тільки якщо залишилось 0-3 дні
                                paused_reminded_count += 1
                                logger.info(f"Призупинена підписка користувача {user.telegram_id} закінчується через {days_left} днів")
                                
                                try:
                                    await self.bot.send_message(
                                        chat_id=user.telegram_id,
                                        text=f"""⚠️ **Нагадування про підписку**

Ваша підписка закінчується через **{days_left} {'день' if days_left == 1 else 'дні'}** ({user.subscription_end_date.strftime('%d.%m.%Y')}).

❌ Автоматичне продовження вимкнене (підписка призупинена)

Щоб продовжити доступ:
1. Відновіть підписку через /subscription
2. Або зв'яжіться з підтримкою

📞 Підтримка: @{settings.support_username if hasattr(settings, 'support_username') else 'support'}""",
                                        parse_mode='Markdown'
                                    )
                                    
                                    # Затримка між повідомленнями (100ms) - 10 msg/sec
                                    await asyncio.sleep(0.1)
                                    
                                except Exception as e:
                                    logger.error(f"Помилка надсилання нагадування користувачу {user.telegram_id}: {e}")
                                    continue
                        except Exception as e:
                            logger.error(f"Помилка обробки призупиненого користувача {user.telegram_id}: {e}")
                            continue
                    
                    offset += batch_size
                    logger.info(f"Оброблено пакет призупинених підписок (offset: {offset})")
                    
                    # Затримка між пакетами
                    await asyncio.sleep(0.1)
            
            # Логуємо успішне виконання
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='check_expired_subscriptions',
                status='completed',
                message=f'Перевірку закінчених підписок завершено о 07:00',
                details={
                    'expired_count': expired_count,
                    'paused_reminded': paused_reminded_count,
                    'execution_time_ms': duration
                },
                duration_ms=duration
            )
            
            logger.info(f"✅ Закінчено перевірку підписок: expired={expired_count}, reminded={paused_reminded_count}, time={duration}ms")
                    
        except Exception as e:
            logger.error(f"Помилка при перевірці закінчених підписок: {e}")
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='check_expired_subscriptions',
                status='failed',
                message=f'Помилка: {str(e)}',
                duration_ms=duration
            )
    
    async def check_upcoming_payments(self):
        """Перевірити підписки з наближенням оплати (7 днів)
        
        Виконується щодня о 10:00
        Відправляє нагадування про автоматичне продовження підписки
        """
        start_time = datetime.utcnow()
        try:
            DatabaseManager.create_system_log(
                task_type='check_upcoming_payments',
                status='started',
                message='Розпочато перевірку наближення оплат о 10:00'
            )
            
            now = datetime.utcnow()
            target_date = now + timedelta(days=7)
            # Діапазон: від target_date до target_date + 1 день
            date_from = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to = date_from + timedelta(days=1)
            
            notified_count = 0
            batch_size = 100
            offset = 0
            
            while True:
                with DatabaseManager() as db:
                    users_batch = db.query(User).filter(
                        User.subscription_active == True,
                        User.subscription_cancelled == False,
                        User.subscription_paused == False,
                        User.auto_payment_enabled == True,
                        User.next_billing_date.isnot(None),
                        User.next_billing_date >= date_from,
                        User.next_billing_date < date_to
                    ).limit(batch_size).offset(offset).all()
                    
                    if not users_batch:
                        break
                    
                    for user in users_batch:
                        try:
                            # Перевіряємо чи це не тестова підписка адміна
                            if user.stripe_subscription_id and user.stripe_subscription_id.startswith("sub_test_"):
                                logger.info(f"Пропускаємо повідомлення для тестової підписки адміна {user.telegram_id}")
                                continue
                            
                            # Відправляємо нагадування
                            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                            
                            keyboard = InlineKeyboardMarkup([
                                [InlineKeyboardButton("✨ В головне меню", callback_data="main_menu_after_cancel")]
                            ])
                            
                            await self.bot.send_message(
                                chat_id=user.telegram_id,
                                text="🩵 Підписка буде автоматично продовжена через 7 днів.",
                                reply_markup=keyboard,
                                parse_mode='Markdown'
                            )
                            
                            notified_count += 1
                            logger.info(f"Надіслано нагадування про оплату користувачу {user.telegram_id}")
                            
                            # Затримка між повідомленнями (100ms)
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            logger.error(f"Помилка відправки нагадування користувачу {user.telegram_id}: {e}")
                            continue
                    
                    offset += batch_size
                    logger.info(f"Оброблено пакет наближень оплат (offset: {offset})")
                    
                    # Затримка між пакетами
                    await asyncio.sleep(0.1)
            
            # Логуємо успішне виконання
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='check_upcoming_payments',
                status='completed',
                message=f'Перевірку наближення оплат завершено о 10:00',
                details={
                    'notified_count': notified_count,
                    'execution_time_ms': duration
                },
                duration_ms=duration
            )
            
            logger.info(f"✅ Перевірка наближення оплат: notified={notified_count}, time={duration}ms")
            
        except Exception as e:
            logger.error(f"Помилка при перевірці наближення оплат: {e}")
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='check_upcoming_payments',
                status='failed',
                message=f'Помилка: {str(e)}',
                duration_ms=duration
            )
    
    # ❌ ВИДАЛЕНО process_payment_events
    # Замість polling використовуємо Stripe webhooks напряму
    # Події обробляються в webhook_server.py при отриманні payment.succeeded
    
    async def process_broadcasts(self):
        """Обробити pending розсилки"""
        start_time = datetime.utcnow()
        try:
            DatabaseManager.create_system_log(
                task_type='process_broadcasts',
                status='started',
                message='Розпочато обробку розсилок'
            )
            
            # Імпорт тут щоб уникнути circular imports
            from bot.broadcast_handler import BroadcastHandler
            
            handler = BroadcastHandler(self.bot)
            await handler.process_pending_broadcasts()
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='process_broadcasts',
                status='completed',
                message='Обробку розсилок завершено',
                duration_ms=duration
            )
            
            logger.info(f"✅ Broadcasts processed, time={duration}ms")
            
        except Exception as e:
            logger.error(f"Помилка при обробці розсилок: {e}")
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='process_broadcasts',
                status='failed',
                message=f'Помилка: {str(e)}',
                duration_ms=duration
            )
    
    async def cleanup_old_payment_events(self):
        """Очистити старі оброблені події оплат"""
        start_time = datetime.utcnow()
        try:
            DatabaseManager.create_system_log(
                task_type='cleanup_payment_events',
                status='started',
                message='Розпочато очищення старих подій оплат'
            )
            
            from payment_events import cleanup_old_events
            deleted_count = cleanup_old_events(days=7)
            
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='cleanup_payment_events',
                status='completed',
                message=f'Видалено {deleted_count} старих подій оплат',
                details={'deleted_count': deleted_count},
                duration_ms=duration
            )
            
            logger.info(f"Видалено {deleted_count} старих подій оплат")
            
        except Exception as e:
            logger.error(f"Помилка при очищенні подій оплат: {e}")
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            DatabaseManager.create_system_log(
                task_type='cleanup_payment_events',
                status='failed',
                message=f'Помилка: {str(e)}',
                duration_ms=duration
            )
