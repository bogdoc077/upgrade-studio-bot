"""
Основний файл телеграм бота UPGRADE21 STUDIO
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

from config import settings, UserState, Messages, Buttons
from database import DatabaseManager, User, create_tables
from payments import StripeManager
from tasks import TaskScheduler
from bot.keyboards import (
    get_main_menu_keyboard, get_cancelled_subscription_keyboard, get_welcome_keyboard, get_survey_goals_keyboard,
    get_survey_injuries_keyboard, get_subscription_offer_keyboard,
    get_subscription_management_keyboard, get_back_keyboard,
    get_support_keyboard, get_dashboard_keyboard
)

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level)
)
logger = logging.getLogger(__name__)

# Стани розмови
CHOOSING_GOAL, CHOOSING_INJURY = range(2)


class UpgradeStudioBot:
    """Основний клас бота"""
    
    def __init__(self):
        self.application = None
        self.bot = None
        self.task_scheduler = None
        # Словник для відстеження ID повідомлень з платіжними посиланнями
        self.payment_message_ids = {}
        # Словник для відстеження ID повідомлень з кроками приєднання
        self.join_step_messages = {}  # {user_id: [message_id1, message_id2, ...]}
        # Словник для відстеження повідомлень про помилки в опитуванні
        self.survey_error_messages = {}  # {user_id: [message_id1, message_id2]}
        # Словник для відстеження останнього повідомлення меню для кожного користувача
        self.last_menu_messages = {}  # {user_id: message_id}
    
    async def send_admin_notification(self, message: str):
        """Відправити повідомлення адміністратору"""
        try:
            await self.bot.send_message(
                chat_id=settings.admin_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Повідомлення адміну надіслано: {message[:50]}...")
        except Exception as e:
            logger.error(f"Помилка відправки повідомлення адміну: {e}")
    
    async def send_tech_notification(self, message: str):
        """Відправити повідомлення в Tech групу"""
        try:
            await self.bot.send_message(
                chat_id=settings.tech_notifications_chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Повідомлення в Tech групу надіслано: {message[:50]}...")
        except Exception as e:
            logger.error(f"Помилка відправки повідомлення в Tech групу: {e}")
    
    async def clear_previous_inline_keyboards(self, chat_id: int, exclude_message_id: int = None):
        """Очистити inline кнопки з попередніх повідомлень"""
        try:
            # Отримуємо останні 20 повідомлень для очищення кнопок
            # Це допоможе очистити кнопки з недавніх повідомлень
            for i in range(1, 21):
                try:
                    # Пробуємо видалити кнопки з повідомлення
                    # Віднімаємо від поточного message_id, щоб отримати попередні
                    if exclude_message_id:
                        message_id_to_edit = exclude_message_id - i
                        if message_id_to_edit > 0:
                            await self.bot.edit_message_reply_markup(
                                chat_id=chat_id,
                                message_id=message_id_to_edit,
                                reply_markup=None
                            )
                except Exception:
                    # Ігноруємо помилки - повідомлення може не існувати або не мати кнопок
                    continue
        except Exception as e:
            logger.debug(f"Помилка при очищенні inline кнопок: {e}")
    
    async def clear_previous_keyboards_from_update(self, update: Update):
        """Очистити попередні inline кнопки використовуючи update"""
        try:
            chat_id = update.effective_chat.id
            current_message_id = None
            
            if update.callback_query and update.callback_query.message:
                current_message_id = update.callback_query.message.message_id
            elif update.message:
                current_message_id = update.message.message_id
            
            await self.clear_previous_inline_keyboards(chat_id, current_message_id)
        except Exception as e:
            logger.debug(f"Помилка при очищенні попередніх кнопок: {e}")
    
    async def cleanup_previous_messages(self, update: Update, delete_current: bool = False, skip_video_notes: bool = True):
        """Очистити попередні повідомлення - видалити або прибрати кнопки"""
        try:
            chat_id = update.effective_chat.id
            current_message_id = None
            
            if update.callback_query and update.callback_query.message:
                current_message_id = update.callback_query.message.message_id
            elif update.message:
                current_message_id = update.message.message_id
            
            # Спробуємо очистити останні 20 повідомлень (збільшено для захоплення помилок)
            for i in range(1, 21):
                try:
                    if current_message_id:
                        message_id_to_process = current_message_id - i
                        if message_id_to_process > 0:
                            # Пробуємо видалити повідомлення (бот може видаляти свої власні повідомлення)
                            try:
                                await self.bot.delete_message(
                                    chat_id=chat_id,
                                    message_id=message_id_to_process
                                )
                                logger.debug(f"Видалено повідомлення {message_id_to_process}")
                            except Exception:
                                # Якщо не вдалося видалити - пробуємо очистити кнопки
                                try:
                                    await self.bot.edit_message_reply_markup(
                                        chat_id=chat_id,
                                        message_id=message_id_to_process,
                                        reply_markup=None
                                    )
                                    logger.debug(f"Очищено кнопки повідомлення {message_id_to_process}")
                                except Exception:
                                    # Повідомлення може не існувати або не мати кнопок
                                    continue
                                    
                except Exception:
                    continue
            
            # Якщо потрібно видалити поточне повідомлення
            if delete_current and current_message_id and update.callback_query:
                try:
                    await update.callback_query.message.delete()
                    logger.debug(f"Видалено поточне повідомлення {current_message_id}")
                except Exception as e:
                    logger.debug(f"Не вдалося видалити поточне повідомлення: {e}")
                    
        except Exception as e:
            logger.debug(f"Помилка при очищенні повідомлень: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник команди /start"""
        user = update.effective_user
        
        # Перевіряємо чи це новий користувач
        existing_user = DatabaseManager.get_user_by_telegram_id(user.id)
        is_new_user = existing_user is None
        
        telegram_user = DatabaseManager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Якщо новий користувач - відправляємо повідомлення в Tech групу
        if is_new_user:
            user_info = f"@{user.username}" if user.username else user.full_name or f"ID: {user.id}"
            await self.send_tech_notification(
                f"👤 <b>Авторизація в боті</b>\n\n"
                f"Користувач: {user_info}\n"
                f"ID: {user.id}\n"
                f"Ім'я: {user.first_name} {user.last_name or ''}\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        
        # Перевірка на застарілий запит фідбеку (7 днів)
        if telegram_user.state == UserState.WAITING_CANCEL_FEEDBACK:
            # Перевіряємо чи минуло 7 днів
            feedback_requested_at = None
            if 'cancel_feedback_requested_at' in context.user_data:
                try:
                    feedback_requested_at = datetime.fromisoformat(context.user_data['cancel_feedback_requested_at'])
                except:
                    pass
            
            # Якщо минуло 7+ днів або немає збереженого часу, скидаємо стан
            if not feedback_requested_at or (datetime.now() - feedback_requested_at).days >= 7:
                # Скидаємо стан на SUBSCRIPTION_CANCELLED для показу статусу скасування
                DatabaseManager.update_user_state(user.id, UserState.SUBSCRIPTION_CANCELLED)
                if 'cancel_feedback_requested_at' in context.user_data:
                    del context.user_data['cancel_feedback_requested_at']
                # Оновлюємо локальний об'єкт
                telegram_user.state = UserState.SUBSCRIPTION_CANCELLED
            else:
                # Якщо ще не минуло 7 днів, показуємо повідомлення про скасування з датою
                subscription_end_date = telegram_user.subscription_end_date
                if subscription_end_date:
                    end_date_str = subscription_end_date.strftime('%d.%m.%Y')
                    await update.message.reply_text(
                        f"<b>Підписку скасовано</b> ❌\n\n"
                        f"Доступ до студії та спільноти залишається до <b>{end_date_str}</b>\n\n"
                        f"Якщо хочеш поділитися відгуком про студію, просто напиши мені повідомлення.",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        f"<b>Підписку скасовано</b> ❌\n\n"
                        f"Якщо хочеш поділитися відгуком про студію, просто напиши мені повідомлення.",
                        parse_mode='HTML'
                    )
                return
        
        # Перевіряємо параметри start команди
        if context.args:
            start_param = context.args[0]
            if start_param == "payment_success":
                await update.message.reply_text(
                    "<b>Дякуємо за оплату!</b>\n\n"
                    "Ваша підписка успішно оформлена. Зараз ви отримаєте доступ до приватних каналів та чатів.\n\n"
                    "Ласкаво просимо до UPGRADE21 STUDIO! ",
                    parse_mode='HTML'
                )
                return
            elif start_param == "payment_cancelled":
                await update.message.reply_text(
                    "<b>Оплата скасована</b>\n\n"
                    "Нічого страшного! Ви можете оформити підписку пізніше.\n\n"
                    "Напишіть /start щоб повернутися до головного меню.",
                    parse_mode='HTML'
                )
                return
            elif start_param == "subscription_offer":
                # Показуємо опис підписки з кнопками оплати
                await self.show_subscription_offer_with_payment(user.id)
                return
        
        # Логіка для існуючих користувачів
        if telegram_user.subscription_active:
            # Перевіряємо чи користувач приєднався до каналу та чату
            if not telegram_user.joined_channel or not telegram_user.joined_chat:
                # Користувач має підписку, але не приєднався - запускаємо процес приєднання
                logger.info(f"Користувач {user.id} має підписку, але не приєднався (channel={telegram_user.joined_channel}, chat={telegram_user.joined_chat})")
                
                # Перевіряємо чи вже був показаний welcome відео кружечок
                # Якщо користувач ще не бачив кружечок (member_since дуже недавно - менше 5 хвилин)
                time_since_member = (datetime.utcnow() - telegram_user.member_since).total_seconds() / 60 if telegram_user.member_since else 999
                show_welcome_video = time_since_member < 5  # Показуємо тільки якщо менше 5 хвилин після оплати
                
                if show_welcome_video:
                    # Надсилаємо відео кружечок
                    video_path = "assets/welcome_video.mp4"
                    if os.path.exists(video_path):
                        await self.bot.send_video_note(
                            chat_id=user.id,
                            video_note=open(video_path, "rb")
                        )
                        # Затримка 5 секунд
                        await asyncio.sleep(5)
                
                # Запускаємо процес приєднання (викликаємо handle_successful_payment знову)
                await self.send_join_invitations(user.id)
                return
            
            # Користувач з активною підпискою і приєднався - показуємо базове меню
            await self.show_active_subscription_menu(user.id)
        elif telegram_user.goals or telegram_user.injuries:
            # Користувач пройшов опитування, але немає підписки - одразу створюємо платіжну сесію
            price_formatted = f"{settings.subscription_price:.0f}"
            currency_symbol = "€" if settings.subscription_currency.lower() == "eur" else settings.subscription_currency.upper()
            
            subscription_text = f"""<b>Що тебе чекає у студії 🩵</b>

• 3 тренування на тиждень які ніколи не повторюються
• Доступ до тренувань поточного та попереднього місяця
• Тренування виходять о 19:00 за Києвом (Пн, Ср, Пт)
• Тривалість 30–45 хв

<b>Додатково:</b> 3 руханки та лекції від нутриціолога.

<b>Ком'юніті неймовірних дівчат</b>
• підтримка в чаті та натхнення
• практика з нутріціологом

Підписка продовжується автоматично, а керування буде доступне у твоєму особистому кабінеті в цьому боті.

<b>Вартість:</b> {price_formatted}{currency_symbol}/місяць 🎀

Якщо у тебе виникнуть будь-які питання — звертайся до мене за контактами нижче✨"""
            
            # Створюємо платіжну сесію одразу
            bot_username = "upgrade21studio_bot"
            success_url = f"https://t.me/{bot_username}"
            cancel_url = f"https://t.me/{bot_username}?start=payment_cancelled"
            
            checkout_data = await StripeManager.create_checkout_session(
                telegram_id=user.id,
                success_url=success_url,
                cancel_url=cancel_url
            )
            
            if checkout_data:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                payment_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Оплатити", url=checkout_data['url'])],
                    [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")]
                ])
                
                await update.message.reply_text(
                    text=subscription_text,
                    reply_markup=payment_keyboard,
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    text=subscription_text + "\n\n⚠️ Виникла помилка при створенні платежу. Спробуйте пізніше.",
                    reply_markup=get_subscription_offer_keyboard()
                )
        else:
            # Новий користувач або користувач без завершеного опитування - показуємо привітання
            await self.send_welcome_intro(update, context)
    
    async def send_welcome_intro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Відправка відео-привітання та показ питання про цілі"""
        import os
        user = update.effective_user
        
        # Надсилаємо відео-привітання (кружечок)
        video_path = "assets/welcome_video.mp4"
        if os.path.exists(video_path):
            await update.message.reply_video_note(
                video_note=open(video_path, "rb")
            )
        
        # Оновлюємо стан користувача на вибір цілей
        DatabaseManager.update_user_state(user.id, UserState.SURVEY_GOALS)
        
        # Показуємо питання про цілі одразу після відео
        await update.message.reply_text(
            text="Яку основну ціль занять ти переслідуєш?",
            reply_markup=get_survey_goals_keyboard()
        )
    

    
    async def handle_goal_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка вибору цілей"""
        query = update.callback_query
        await query.answer()
        
        # Видаляємо збережені повідомлення про помилки (якщо є)
        if query.from_user.id in self.survey_error_messages:
            for msg_id in self.survey_error_messages[query.from_user.id]:
                try:
                    await self.bot.delete_message(
                        chat_id=query.from_user.id,
                        message_id=msg_id
                    )
                except Exception:
                    pass
            del self.survey_error_messages[query.from_user.id]
        
        goal_data = query.data.replace("goal_", "")
        
        # Видаляємо попереднє повідомлення
        try:
            await query.message.delete()
        except Exception:
            pass
        
        # Якщо вибрано "Свій варіант" - просимо ввести текст
        if goal_data == "Свій варіант":
            DatabaseManager.update_user_state(query.from_user.id, UserState.SURVEY_GOALS_CUSTOM)
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Напиши, будь ласка, свою ціль у довільній формі 🎀"
            )
            return
        
        # Зберігаємо вибір
        DatabaseManager.save_survey_data(query.from_user.id, goals=goal_data)
        
        # Різні відповіді залежно від цілі
        response_text = ""
        
        if goal_data == "Підтягнути тіло":
            response_text = """🩵 Дякую за відповідь. Підтягнуте тіло — це і естетика, і здоров'я.

Починай із занять рівня <b>Pilates</b> — вони закладуть надійну базу та допоможуть краще відчути тіло.
Потім додавай <b>Power Pilates</b> — саме цей рівень допоможе сформувати м'язи, покращити рельєф та загальний тонус.

Працюй у своєму темпі, прислухайся до себе — це найважливіше.🕊️

<b>Чи є у тебе травми про які мені варто знати?</b>"""
        
        elif goal_data == "Зменшити стрес":
            response_text = """🩵 Дякую за відповідь. Хронічний стрес справді впливає і на самопочуття, і на тіло, тому м'які тренування тут особливо цінні.

Усі типи занять мають свою мету й працюють у комплексі, але для зниження стресу найкраще підійдуть рівень <b>Pilates</b> та <b>Stretching</b> — вони допомагають заспокоїти нервову систему, зняти напругу та повернути внутрішній спокій.🕊️

<b>Чи є у тебе травми про які мені варто знати?</b>"""
        
        elif goal_data == "Здоров'я спини":
            response_text = """🩵 Дякую за відповідь. Здоров'я спини це справді фундамент щоденного комфорту.

Починай із рівня <b>Pilates</b> — він м'яко активує глибокі м'язи та формує правильні патерни руху, щоб тіло вчилося правильно рухатись у звичайному житті. Далі поступово додавай <b>Power Pilates</b>, щоб зміцнити м'язи й підвищити витривалість. Працюй у своєму темпі — це головне.🕊️

<b>Чи є у тебе травми про які мені варто знати?</b>"""
        
        elif goal_data == "Жіноче здоров'я":
            response_text = """🩵 Дякую за відповідь. Підтримка жіночого здоров'я це важлива частина щоденного комфорту.

Для твоєї цілі раджу робити акцент на тренуваннях рівня <b>Pilates</b> — вони м'яко зміцнюють м'язи тазового дна, формують тонус та стабільність.🕊️

<b>Чи є у тебе травми про які мені варто знати?</b>"""
        
        elif goal_data == "Всі пункти":
            response_text = """🩵 Дякую за відповідь. Комплексна робота з тілом це найефективніший підхід.

Починай із <b>Pilates</b> — він закладе базу та допоможе увімкнути тіло. Потім додавай <b>Power Pilates</b>, щоб зміцнити м'язи й покращити витривалість. А <b>Stretching</b> включай для розслаблення та гнучкості 🕊️

<b>Чи є у тебе травми про які мені варто знати?</b>"""
        
        # Оновлюємо стан
        DatabaseManager.update_user_state(query.from_user.id, UserState.SURVEY_INJURIES)
        
        # Відправляємо відповідь з питанням про травми
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text=response_text,
            reply_markup=get_survey_injuries_keyboard(),
            parse_mode='HTML'
        )
    
    async def handle_injury_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка вибору травм/обмежень"""
        query = update.callback_query
        await query.answer()
        
        # Видаляємо збережені повідомлення про помилки (якщо є)
        if query.from_user.id in self.survey_error_messages:
            for msg_id in self.survey_error_messages[query.from_user.id]:
                try:
                    await self.bot.delete_message(
                        chat_id=query.from_user.id,
                        message_id=msg_id
                    )
                except Exception:
                    pass
            del self.survey_error_messages[query.from_user.id]
        
        injury_data = query.data.replace("injury_", "")
        
        # Видаляємо попереднє повідомлення
        try:
            await query.message.delete()
        except Exception:
            pass
        
        if injury_data == "Так":
            # Просимо користувача описати травму детальніше
            DatabaseManager.update_user_state(query.from_user.id, UserState.SURVEY_INJURIES_CUSTOM)
            
            # Запит деталей
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Опиши, будь ласка, свою травму або проблему детальніше."
            )
        else:  # "Ні"
            # Зберігаємо вибір "Немає травм"
            DatabaseManager.save_survey_data(query.from_user.id, injuries="Немає травм")
            DatabaseManager.update_user_state(query.from_user.id, UserState.SUBSCRIPTION_OFFER)
            
            # Повідомлення для випадку без травм
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="🩵 Дякую за відповідь. У такому разі всі типи тренувань доступні без обмежень — головне працювати у комфортному темпі.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Оформити підписку", callback_data="create_subscription")
                ]])
            )
    
    def find_goal_by_key(self, key: str) -> str:
        """Знайти повний текст цілі за ключовим словом"""
        from config import SurveyOptions
        # Key тепер містить повний текст цілі
        return key
    
    def find_injury_by_key(self, key: str) -> str:
        """Знайти повний текст травми за ключовим словом"""
        from config import SurveyOptions
        for injury in SurveyOptions.INJURIES:
            if key.lower() in injury.lower():
                return injury
        return key

    async def show_subscription_offer_with_payment(self, user_id: int):
        """Показати опис підписки з кнопками оплати (для розсилок)"""
        price_formatted = f"{settings.subscription_price:.0f}"
        currency_symbol = "€" if settings.subscription_currency.lower() == "eur" else settings.subscription_currency.upper()
        
        subscription_text = f"""<b>Що тебе чекає у студії 🩵</b>

• 3 тренування на тиждень які ніколи не повторюються
• Доступ до тренувань поточного та попереднього місяця
• Тренування виходять о 19:00 за Києвом (Пн, Ср, Пт)
• Тривалість 30–45 хв

<b>Додатково:</b> 3 руханки та лекції від нутриціолога.

<b>Ком'юніті неймовірних дівчат</b>
• підтримка в чаті та натхнення
• практика з нутріціологом

Підписка продовжується автоматично, а керування буде доступне у твоєму особистому кабінеті в цьому боті.

<b>Вартість:</b> {price_formatted}{currency_symbol}/місяць 🎀

Якщо у тебе виникнуть будь-які питання — звертайся до мене за контактами нижче✨"""
        
        # Створюємо платіжну сесію
        bot_username = (await self.bot.get_me()).username
        success_url = f"https://t.me/{bot_username}"
        cancel_url = f"https://t.me/{bot_username}?start=payment_cancelled"
        
        checkout_data = await StripeManager.create_checkout_session(
            telegram_id=user_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if checkout_data:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            payment_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатити", url=checkout_data['url'])],
                [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")]
            ])
            
            await self.bot.send_message(
                chat_id=user_id,
                text=subscription_text,
                reply_markup=payment_keyboard,
                parse_mode='HTML'
            )
        else:
            await self.bot.send_message(
                chat_id=user_id,
                text=subscription_text + "\n\n⚠️ Виникла помилка при створенні платежу. Спробуйте пізніше.",
                parse_mode='HTML'
            )

    async def show_active_subscription_menu(self, user_id: int):
        """Показати базове меню для користувачів з активною підпискою"""
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        if not user:
            return
        
        # Отримуємо посилання на канал та чат з бази даних
        invite_links = DatabaseManager.get_active_invite_links()
        channel_url = None
        chat_url = None
        
        for link in invite_links:
            if link.link_type == "channel":
                channel_url = link.invite_link
            elif link.link_type == "group":
                chat_url = link.invite_link
        
        # Fallback якщо посилання не знайдені
        if not channel_url:
            from config import settings
            channel_url = f"https://t.me/c/{settings.private_channel_id.replace('-100', '')}"
        if not chat_url:
            from config import settings
            chat_url = f"https://t.me/c/{settings.private_chat_id.replace('-100', '')}"
        
        # Рахуємо дні членства
        days_member = (datetime.utcnow() - user.member_since).days
        
        # Перевіряємо статус підписки
        if user.subscription_paused and not user.subscription_active:
            # Підписка призупинена і доступ пропав - гібридне меню
            menu_text = f"Підписку призупинено ⏸️"
            
            # Гібридна клавіатура: кнопки керування підпискою + задати питання
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Поновити підписку", callback_data="resume_subscription")],
                [InlineKeyboardButton("❌ Скасувати підписку", callback_data="cancel_subscription")],
                [InlineKeyboardButton("💳 Змінити платіжний метод", callback_data="change_payment_method")],
                [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")]
            ])
        elif user.subscription_paused:
            # Підписка призупинена (незалежно від active) - показуємо статус призупинення
            subscription_end_date = user.subscription_end_date
            if subscription_end_date and user.subscription_active:
                menu_text = f"<b>Підписку призупинено</b> ⏸️\n\nДоступ до студії та спільноти залишається до <b>{subscription_end_date.strftime('%d.%m')}</b>"
            else:
                menu_text = f"<b>Підписку призупинено</b> ⏸️"
            keyboard = get_main_menu_keyboard(channel_url, chat_url)
        elif user.subscription_cancelled:
            # Підписка скасована - показуємо меню БЕЗ керування підпискою
            subscription_end_date = user.subscription_end_date
            if subscription_end_date:
                menu_text = f"<b>Підписку скасовано</b> ❌\n\nДоступ до студії та спільноти залишається до <b>{subscription_end_date.strftime('%d.%m')}</b>"
            else:
                menu_text = f"<b>Підписку скасовано</b> ❌"
            keyboard = get_cancelled_subscription_keyboard(channel_url, chat_url)
        else:
            # Підписка активна
            menu_text = f"<b>Підписка активна</b> ✅\n\nТи зі мною вже: <b>{days_member} днів</b>"
            keyboard = get_main_menu_keyboard(channel_url, chat_url)
        
        await self.bot.send_message(
            chat_id=user_id,
            text=menu_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати головне меню"""
        user_id = update.effective_user.id
        
        # Отримуємо посилання на канал та чат з бази даних
        invite_links = DatabaseManager.get_active_invite_links()
        channel_url = None
        chat_url = None
        
        for link in invite_links:
            if link.link_type == "channel":
                channel_url = link.invite_link
            elif link.link_type == "group":
                chat_url = link.invite_link
        
        # Видаляємо попереднє повідомлення меню
        if user_id in self.last_menu_messages:
            try:
                await self.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=self.last_menu_messages[user_id]
                )
            except Exception:
                pass
        
        if update.callback_query:
            await update.callback_query.answer()
            # Видаляємо повідомлення callback
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
            sent_message = await self.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Головне меню",
                reply_markup=get_main_menu_keyboard(channel_url, chat_url)
            )
        else:
            sent_message = await update.message.reply_text(
                "Головне меню",
                reply_markup=get_main_menu_keyboard(channel_url, chat_url)
            )
        
        # Зберігаємо ID нового повідомлення меню
        self.last_menu_messages[user_id] = sent_message.message_id
    
    async def handle_subscription_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Керування підпискою"""
        # Підтримка тільки callback
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception:
                pass
        else:
            # Якщо прийшло з text message (не повинно більше бути)
            user_id = update.effective_user.id
            
            # Видаляємо попереднє повідомлення меню
            if user_id in self.last_menu_messages:
                try:
                    await self.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=self.last_menu_messages[user_id]
                    )
                except Exception:
                    pass
        
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        if not user:
            error_text = "Користувача не знайдено"
            await self.bot.send_message(
                chat_id=user_id,
                text=error_text
            )
            return
        
        await self._show_subscription_management_menu(user_id, user)
    
    async def handle_subscription_management_from_callback(self, user_id: int):
        """Керування підпискою через callback (без Update об'єкта)"""
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        if not user:
            await self.bot.send_message(
                chat_id=user_id,
                text="Користувача не знайдено"
            )
            return
        
        await self._show_subscription_management_menu(user_id, user)
    
    async def _show_subscription_management_menu(self, user_id: int, user):
        """Показати меню керування підпискою"""
        # Якщо підписка активна І НЕ призупинена І НЕ скасована - перевіряємо реальний статус членства
        joined_channel = user.joined_channel
        joined_chat = user.joined_chat
        
        if user.subscription_active and not user.subscription_paused and not user.subscription_cancelled:
            # Перевіряємо членство в каналі
            try:
                channel_member = await self.bot.get_chat_member(
                    chat_id=settings.private_channel_id,
                    user_id=user_id
                )
                # Оновлюємо статус якщо користувач є членом
                is_member_channel = channel_member.status in ['member', 'administrator', 'creator']
                if is_member_channel != user.joined_channel:
                    DatabaseManager.update_channel_join_status(user_id, is_member_channel)
                    joined_channel = is_member_channel
                    logger.info(f"Updated channel membership for user {user_id}: {is_member_channel}")
            except Exception as e:
                logger.warning(f"Could not check channel membership for user {user_id}: {e}")
            
            # Перевіряємо членство в чаті
            try:
                chat_member = await self.bot.get_chat_member(
                    chat_id=settings.private_chat_id,
                    user_id=user_id
                )
                # Оновлюємо статус якщо користувач є членом
                is_member_chat = chat_member.status in ['member', 'administrator', 'creator']
                if is_member_chat != user.joined_chat:
                    DatabaseManager.update_chat_join_status(user_id, is_member_chat)
                    joined_chat = is_member_chat
                    logger.info(f"Updated chat membership for user {user_id}: {is_member_chat}")
            except Exception as e:
                logger.warning(f"Could not check chat membership for user {user_id}: {e}")
        
        keyboard = get_subscription_management_keyboard(
            subscription_active=user.subscription_active,
            subscription_paused=user.subscription_paused,
            subscription_cancelled=user.subscription_cancelled,
            joined_channel=joined_channel,
            joined_chat=joined_chat
        )
        
        # Логування для діагностики
        logger.info(f"Показуємо меню для користувача {user_id}: "
                   f"subscription_active={user.subscription_active}, "
                   f"joined_channel={joined_channel}, "
                   f"joined_chat={joined_chat}")
        
        # Формуємо текст з інформацією про підписку
        if user.subscription_active:
            # Отримуємо актуальну інформацію зі Stripe
            subscription_end_date = user.subscription_end_date
            next_billing_date = user.next_billing_date
            subscription_price = settings.subscription_price
            currency_symbol = "€" if settings.subscription_currency.lower() == "eur" else settings.subscription_currency.upper()
            
            if user.is_admin() and (user.stripe_subscription_id or "").startswith("sub_test_"):
                # Для тестових підписок адміна - використовуємо дані з БД
                if user.subscription_paused:
                    text = "Підписку призупинено ⏸️\n\n"
                    if subscription_end_date:
                        text += f"Доступ до студії та спільноти залишається до {subscription_end_date.strftime('%d.%m')}"
                    else:
                        text += "Доступ до студії та спільноти активний"
                elif user.subscription_cancelled:
                    text = f"<b>Підписку скасовано</b>\n\n"
                    if subscription_end_date:
                        text += f"Закінчення підписки: {subscription_end_date.strftime('%d.%m')}\n"
                    text += f"Сума оплати: {subscription_price:.0f}{currency_symbol}"
                else:
                    text = f"<b>Підписка активна</b> ✅\n\n"
                    if next_billing_date:
                        text += f"Наступний платіж: {next_billing_date.strftime('%d.%m')}\n"
                    text += f"Сума оплати: {subscription_price:.0f}{currency_symbol}"
            else:
                # Для реальних підписок - завжди отримуємо актуальні дані зі Stripe
                if user.stripe_subscription_id:
                    try:
                        subscription_info = await StripeManager.get_subscription(user.stripe_subscription_id)
                        if subscription_info:
                            # Отримуємо актуальну дату наступного платежу зі Stripe (використовуємо UTC)
                            next_billing_date = datetime.utcfromtimestamp(subscription_info['current_period_end'])
                            # subscription_end_date - дата кінцевого кіку після 3 невдалих спроб (+2 дні)
                            subscription_end_date = next_billing_date + timedelta(days=2)
                            
                            logger.info(f"Отримано актуальні дані зі Stripe для користувача {user_id}: next_billing={next_billing_date.strftime('%d.%m.%Y')}, end_date={subscription_end_date.strftime('%d.%m.%Y')}")
                    except Exception as e:
                        logger.warning(f"Не вдалося отримати дані зі Stripe для користувача {user_id}: {e}")
                
                if user.subscription_paused:
                    text = f"Підписку призупинено ⏸️\n\n"
                    if subscription_end_date:
                        text += f"Доступ до студії та спільноти залишається до {subscription_end_date.strftime('%d.%m')}"
                    else:
                        text += "Доступ до студії та спільноти активний"
                elif user.subscription_cancelled:
                    text = f"<b>Підписку скасовано</b> ❌\n\n"
                    if subscription_end_date:
                        text += f"Закінчення підписки: {subscription_end_date.strftime('%d.%m')}\n"
                    text += f"Сума оплати: {subscription_price:.0f}{currency_symbol}"
                else:
                    text = f"<b>Підписка активна</b> ✅\n\n"
                    if next_billing_date:
                        text += f"Наступний платіж: {next_billing_date.strftime('%d.%m')}\n"
                    text += f"Сума оплати: {subscription_price:.0f}{currency_symbol}"
        else:
            text = "У вас немає активної підписки"
        
        # Відправляємо повідомлення з inline кнопками
        sent_message = await self.bot.send_message(
            chat_id=user_id, 
            text=text, 
            reply_markup=keyboard, 
            parse_mode='HTML'
        )
        
        # Зберігаємо ID нового повідомлення меню
        self.last_menu_messages[user_id] = sent_message.message_id
    
    async def handle_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати дашборд користувача"""
        user_id = update.effective_user.id
        
        # Видаляємо попереднє повідомлення меню
        if user_id in self.last_menu_messages:
            try:
                await self.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=self.last_menu_messages[user_id]
                )
            except Exception:
                pass
        
        # Видаляємо попереднє повідомлення з кнопками
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.debug(f"Не вдалося видалити повідомлення: {e}")
        
        user_id = update.effective_user.id
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        # Визначаємо, чи це callback query чи звичайне повідомлення
        is_callback = update.callback_query is not None
        
        if not user:
            error_text = "Користувача не знайдено"
            if is_callback:
                sent_message = await self.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_text
                )
            else:
                sent_message = await update.message.reply_text(error_text)
            self.last_menu_messages[user_id] = sent_message.message_id
            return
        
        if not user.subscription_active:
            # Користувач без активної підписки
            dashboard_text = (
                "<b>Дашборд недоступний</b>\n\n"
                "Для доступу до дашборду потрібна активна підписка\n\n"
                "Оформіть підписку, щоб отримати:\n"
                "•Детальну статистику тренувань\n"
                "•Прогрес-трекінг\n"
                "•Персональні рекомендації\n"
                "•Доступ до спільноти\n\n"
                "Натисніть /start для оформлення підписки"
            )
            
            if is_callback:
                sent_message = await self.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=dashboard_text,
                    parse_mode='HTML'
                )
            else:
                sent_message = await update.message.reply_text(dashboard_text, parse_mode='HTML')
            self.last_menu_messages[user_id] = sent_message.message_id
            return
        
        # Рахуємо дні членства
        days_member = (datetime.utcnow() - user.member_since).days
        
        # Додаємо часову мітку для відстеження оновлень
        current_time = datetime.now().strftime("%H:%M")
        
        dashboard_text = f"""<b>Ваша статистика</b> (оновлено о {current_time})

 Ім'я: {user.first_name or 'Не вказано'}
 З нами: {days_member} днів
 Виконано тренувань: {user.workouts_completed}
 Статус підписки: {'Активна' if user.subscription_active else 'Неактивна'}
 Ваша ціль: {user.goals[:50] + '...' if user.goals and len(user.goals) > 50 else user.goals or 'Не вказана'}

Продовжуйте тренуватися! """
        
        if is_callback:
            sent_message = await self.bot.send_message(
                chat_id=update.effective_chat.id,
                text=dashboard_text,
                parse_mode='HTML',
                reply_markup=get_dashboard_keyboard()
            )

        else:
            sent_message = await update.message.reply_text(
                dashboard_text,
                parse_mode='HTML',
                reply_markup=get_dashboard_keyboard()
            )

        
        # Зберігаємо ID нового повідомлення меню
        self.last_menu_messages[user_id] = sent_message.message_id
    
    async def handle_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати контакти підтримки"""
        user_id = update.effective_user.id
        
        # Видаляємо попереднє повідомлення меню
        if user_id in self.last_menu_messages:
            try:
                await self.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=self.last_menu_messages[user_id]
                )
            except Exception:
                pass
        
        # Видаляємо попереднє повідомлення з кнопками
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
        
        support_text = """
⁉️ <b>Підтримка</b>

Якщо у вас виникли питання або потрібна допомога, зв'яжіться з нашою командою підтримки.

Ми завжди готові допомогти! 🙂
"""
        
        if update.callback_query:
            sent_message = await self.bot.send_message(
                chat_id=update.effective_chat.id,
                text=support_text,
                parse_mode='HTML',
                reply_markup=get_support_keyboard()
            )

        else:
            sent_message = await update.message.reply_text(
                support_text,
                parse_mode='HTML',
                reply_markup=get_support_keyboard()
            )

        
        # Зберігаємо ID нового повідомлення меню
        self.last_menu_messages[user_id] = sent_message.message_id
    
    async def handle_go_to_studio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти в студію (канал)"""
        # Підтримка callback та text message
        if update.callback_query:
            query = update.callback_query
            await query.answer()  # Спочатку відповідаємо на callback
            
            # Отримуємо посилання на канал з бази даних
            invite_links = DatabaseManager.get_active_invite_links()
            channel_link = None
            
            for link in invite_links:
                if link.link_type == "channel":
                    channel_link = link
                    break
            
            if channel_link:
                url = channel_link.invite_link
            else:
                # Fallback - використовуємо налаштування з .env
                logger.warning("Invite link для каналу не знайдено в БД, використовуємо налаштування")
                url = f"https://t.me/c/{settings.private_channel_id.replace('-100', '')}"
            
            # Відправляємо повідомлення з кнопкою для переходу
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("🩵 Перейти в студію", url=url)]]
            try:
                await query.edit_message_text(
                    "Натисни кнопку нижче, щоб перейти в студію 🎀",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                # Якщо не вдалося редагувати, відправляємо нове повідомлення
                await query.message.reply_text(
                    "Натисни кнопку нижче, щоб перейти в студію 🎀",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # Якщо викликано через текстове повідомлення - показуємо кнопку
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            invite_links = DatabaseManager.get_active_invite_links()
            channel_link = None
            
            for link in invite_links:
                if link.link_type == "channel":
                    channel_link = link
                    break
            
            if channel_link:
                url = channel_link.invite_link
            else:
                logger.warning("Invite link для каналу не знайдено в БД")
                url = f"https://t.me/c/{settings.private_channel_id.replace('-100', '')}"
            
            keyboard = [[InlineKeyboardButton("🩵 Перейти в студію", url=url)]]
            await update.message.reply_text(
                "Натисни кнопку нижче, щоб перейти в студію 🎀",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def handle_go_to_community(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти в спільноту (чат)"""
        # Підтримка callback та text message
        if update.callback_query:
            query = update.callback_query
            await query.answer()  # Спочатку відповідаємо на callback
            
            # Отримуємо посилання на чат з бази даних
            invite_links = DatabaseManager.get_active_invite_links()
            chat_link = None
            
            for link in invite_links:
                if link.link_type == "group":
                    chat_link = link
                    break
            
            if chat_link:
                url = chat_link.invite_link
            else:
                # Fallback - використовуємо налаштування з .env
                logger.warning("Invite link для чату не знайдено в БД, використовуємо налаштування")
                url = f"https://t.me/c/{settings.private_chat_id.replace('-100', '')}"
            
            # Відправляємо повідомлення з кнопкою для переходу
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("💬 Перейти в спільноту", url=url)]]
            try:
                await query.edit_message_text(
                    "Натисни кнопку нижче, щоб перейти в спільноту 🎀",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                # Якщо не вдалося редагувати, відправляємо нове повідомлення
                await query.message.reply_text(
                    "Натисни кнопку нижче, щоб перейти в спільноту 🎀",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # Якщо викликано через текстове повідомлення - показуємо кнопку
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            invite_links = DatabaseManager.get_active_invite_links()
            chat_link = None
            
            for link in invite_links:
                if link.link_type == "group":
                    chat_link = link
                    break
            
            if chat_link:
                url = chat_link.invite_link
            else:
                logger.warning("Invite link для чату не знайдено в БД")
                url = f"https://t.me/c/{settings.private_chat_id.replace('-100', '')}"
            
            keyboard = [[InlineKeyboardButton("💬 Перейти в спільноту", url=url)]]
            await update.message.reply_text(
                "Натисни кнопку нижче, щоб перейти в спільноту 🎀",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def handle_ask_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Задати питання"""
        # Підтримка callback та text message
        if update.callback_query:
            query = update.callback_query
            await query.answer()  # Спочатку відповідаємо на callback
            
            # Відправляємо повідомлення з кнопкою для переходу
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("Написати Альоні", url="https://t.me/alionakovaliova")]]
            try:
                await query.edit_message_text(
                    "Якщо у тебе виникли питання, напиши мені — з радістю допоможу! ✨",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                # Якщо не вдалося редагувати, відправляємо нове повідомлення
                await query.message.reply_text(
                    "Якщо у тебе виникли питання, напиши мені — з радістю допоможу! ✨",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # Якщо викликано через текстове повідомлення - показуємо кнопку
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = [[InlineKeyboardButton("Написати Альоні", url="https://t.me/alionakovaliova")]]
            await update.message.reply_text(
                "Якщо у тебе виникли питання, напиши мені — з радістю допоможу! ✨",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Загальний обробник callback запитів"""
        query = update.callback_query
        data = query.data
        
        # Логуємо callback для діагностики
        logger.info(f"Отримано callback: {data} від користувача {query.from_user.id}")
        
        if data.startswith("goal_"):
            await self.handle_goal_selection(update, context)
        elif data.startswith("injury_"):
            await self.handle_injury_selection(update, context)
        elif data == "create_subscription":
            await self.create_subscription(update, context)
        elif data == "more_info":
            await self.show_more_info(update, context)
        elif data == "main_menu":
            # Кнопка "Назад" або "Головне меню" - показуємо базове меню
            await query.answer()
            try:
                await query.message.delete()
            except Exception:
                pass
            await self.show_active_subscription_menu(query.from_user.id)
        elif data == "main_menu_after_cancel":
            # Після фідбеку показуємо базове меню
            await query.answer()
            try:
                await query.message.delete()
            except Exception:
                pass
            await self.show_active_subscription_menu(query.from_user.id)
        elif data == "pause_subscription":
            await self.pause_subscription(update, context)
        elif data == "confirm_pause_subscription":
            await self.confirm_pause_subscription(update, context)
        elif data == "back_to_subscription_menu":
            await query.answer()
            # Видаляємо попереднє повідомлення
            try:
                await query.message.delete()
            except Exception:
                pass
            # Повертаємось до меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
        elif data == "resume_subscription":
            await self.resume_subscription(update, context)
        elif data == "cancel_subscription":
            await self.cancel_subscription(update, context)
        elif data == "confirm_cancel_subscription":
            await self.confirm_cancel_subscription(update, context)
        elif data == "change_payment_method":
            await self.change_payment_method(update, context)
        elif data == "back_to_main_menu":
            # Кнопка "Назад" - повертає в головне меню
            await query.answer()
            try:
                await query.message.delete()
            except Exception:
                pass
            await self.show_active_subscription_menu(query.from_user.id)
        elif data == "manage_subscription":
            # Кнопка "Керувати підпискою"
            await query.answer()
            try:
                await query.message.delete()
            except Exception:
                pass
            await self.handle_subscription_management_from_callback(query.from_user.id)
        elif data == "refresh_dashboard":
            await self.handle_dashboard(update, context)
        elif data == "join_channel_access":
            await self.handle_channel_access_request(update, context)
        elif data == "join_chat_access":
            await self.handle_chat_access_request(update, context)
        elif data == "go_to_channel" or data == "go_to_chat":
            # Застаріла кнопка - оновлюємо меню
            await query.answer()
            user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
            if user:
                # Видаляємо попереднє повідомлення
                try:
                    await query.message.delete()
                except Exception as e:
                    logger.warning(f"Не вдалося видалити повідомлення: {e}")
                
                # Показуємо оновлене меню
                await self._show_subscription_management_menu(query.from_user.id, user)
        elif data == "channel_joined":
            await self.handle_channel_joined(update, context)
        elif data == "chat_joined":
            await self.handle_chat_joined(update, context)
        elif data.startswith("join_"):
            await self.handle_join_request(update, context)
        else:
            await query.answer("Функція в розробці ")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка текстових повідомлень (для довільних відповідей в опитуванні)"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            return
        
        user_text = update.message.text
        
        # Якщо користувач у стані вибору цілі - очікуємо тільки callback з кнопок
        if user.state == UserState.SURVEY_GOALS:
            # Видаляємо повідомлення користувача
            try:
                await update.message.delete()
            except Exception:
                pass
            
            # Повторно показуємо питання з варіантами та зберігаємо ID
            question_msg = await self.bot.send_message(
                chat_id=update.effective_user.id,
                text="Яку основну ціль занять ти переслідуєш?",
                reply_markup=get_survey_goals_keyboard()
            )
            
            # Зберігаємо ID повідомлення
            self.survey_error_messages[update.effective_user.id] = [question_msg.message_id]
            return
        
        # Якщо користувач у стані вибору травм - очікуємо тільки callback з кнопок
        if user.state == UserState.SURVEY_INJURIES:
            # Видаляємо повідомлення користувача
            try:
                await update.message.delete()
            except Exception:
                pass
            
            # Повторно показуємо питання з варіантами та зберігаємо ID
            question_msg = await self.bot.send_message(
                chat_id=update.effective_user.id,
                text="Чи є у тебе травми про які мені варто знати?",
                reply_markup=get_survey_injuries_keyboard()
            )
            
            # Зберігаємо ID повідомлення
            self.survey_error_messages[update.effective_user.id] = [question_msg.message_id]
            return
        
        # Якщо користувач вводить свою ціль
        if user.state == UserState.SURVEY_GOALS_CUSTOM:
            # Зберігаємо custom ціль
            custom_goal = f"Свій варіант: {user_text}"
            DatabaseManager.save_survey_data(update.effective_user.id, goals=custom_goal)
            DatabaseManager.update_user_state(update.effective_user.id, UserState.SURVEY_INJURIES)
            
            # Об'єднане повідомлення з подякою та питанням про травми
            await update.message.reply_text(
                text="Дякую за відповідь 🩵\n\nЧи є у тебе травми про які мені варто знати?",
                reply_markup=get_survey_injuries_keyboard()
            )
            return
        
        if user.state == UserState.SURVEY_INJURIES_CUSTOM:
            # Зберігаємо опис травми (будь-який текст)
            injuries_text = f"Травма: {user_text}"
            DatabaseManager.save_survey_data(update.effective_user.id, injuries=injuries_text)
            DatabaseManager.update_user_state(update.effective_user.id, UserState.SUBSCRIPTION_OFFER)
            
            # Повідомлення з кнопкою оформлення підписки
            await update.message.reply_text(
                "🩵 Дякую за відповідь. Я ознайомлюсь і, за потреби, зв'яжусь із тобою особисто.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Оформити підписку", callback_data="create_subscription")
                ]])
            )
            return
        
        # Обробка фідбеку після скасування підписки
        if user.state == UserState.WAITING_CANCEL_FEEDBACK:
            # Зберігаємо фідбек (відправимо в Tech групу)
            feedback_text = user_text
            
            # Підраховуємо кількість успішних оплат
            from database.models import Payment
            with DatabaseManager() as db:
                payment_count = db.query(Payment).filter(
                    Payment.user_id == user.id,
                    Payment.status.in_(["succeeded", "completed"])
                ).count()
            
            # Отримуємо дату скасування з контексту
            cancel_date_str = datetime.now().strftime('%d.%m.%Y %H:%M')
            if 'cancel_date' in context.user_data:
                try:
                    cancel_date = datetime.fromisoformat(context.user_data['cancel_date'])
                    cancel_date_str = cancel_date.strftime('%d.%m.%Y %H:%M')
                except:
                    pass
            
            # Відправляємо оновлене повідомлення в Tech групу з фідбеком
            user_info = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
            await self.send_tech_notification(
                f"💬 <b>Отримано фідбек про скасування</b>\n\n"
                f"Користувач: {user_info}\n"
                f"ID: {update.effective_user.id}\n"
                f"Ім'я: {update.effective_user.first_name} {update.effective_user.last_name or ''}\n"
                f"Дата скасування: {cancel_date_str}\n"
                f"Успішних оплат: {payment_count}\n"
                f"Побажання: {feedback_text}"
            )
            
            # Оновлюємо стан
            DatabaseManager.update_user_state(update.effective_user.id, UserState.SUBSCRIPTION_CANCELLED)
            
            # Очищуємо збережений час запиту фідбеку
            if 'cancel_feedback_requested_at' in context.user_data:
                del context.user_data['cancel_feedback_requested_at']
            
            # Отримуємо дату закінчення підписки
            subscription_end_date = user.subscription_end_date
            if subscription_end_date:
                end_date_str = subscription_end_date.strftime('%d.%m')
            else:
                end_date_str = "кінця поточного періоду"
            
            # Відправляємо подяку з кнопкою головного меню
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✨ Головне меню", callback_data="main_menu_after_cancel")
            ]])
            
            await update.message.reply_text(
                f"🩵 Щиро дякую.\n\n"
                f"Доступ до студії та спільноти залишатиметься до {end_date_str}, а нові списання не відбуватимуться.\n\n"
                f"Якщо захочеш поновити підписку, ти завжди зможеш зробити це в цьому боті.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return
    
    async def show_subscription_offer(self, telegram_id: int, query=None):
        """Показати пропозицію підписки після завершення опитування"""
        user = DatabaseManager.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        
        # Формуємо персоналізоване повідомлення
        greeting = f"Чудово, {user.first_name}! "
        
        # Додаємо інформацію про цілі та особливості (коротко)
        personal_info = ""
        if user.goals:
            personal_info += f"\n Ваша ціль: {user.goals[:50]}{'...' if len(user.goals) > 50 else ''}"
        if user.injuries and "Немає"not in user.injuries:
            personal_info += f"\n🩺 Врахуємо: {user.injuries[:50]}{'...' if len(user.injuries) > 50 else ''}"
        
        # Форматуємо основне повідомлення про підписку
        # subscription_price вже в євро (з БД), не потрібно ділити на 100
        price_formatted = f"{settings.subscription_price:.0f}"
        
        offer_text = f"""{greeting}

Дякую за відповіді! Тепер я краще розумію ваші потреби.{personal_info}

Готові змінити своє життя?

UPGRADE21 STUDIO — це не просто фітнес, це ваша трансформація!

Що вас чекає:
• Персональні тренування під ваші цілі
• Індивідуальний план харчування
• Приватна спільнота однодумців
• 24/7 підтримка професійних тренерів
• Трекінг прогресу та досягнень
• Мотивація та підзвітність

Щомісячна підписка: {price_formatted} {settings.subscription_currency.upper()}

Гнучкість:
• Можна скасувати будь-коли
• Призупинити на час відпустки
• Керувати прямо в боті

Безпечна оплата через Stripe
Ваші дані захищені банківським рівнем безпеки.

Почніть свій шлях до ідеальної форми вже сьогодні!"""
        
        if query:
            # Якщо це callback query, редагуємо повідомлення
            await query.edit_message_text(
                text=offer_text,
                reply_markup=get_subscription_offer_keyboard(),
                parse_mode='HTML'
            )
        else:
            # Якщо це звичайне повідомлення, надсилаємо нове
            await self.bot.send_message(
                chat_id=telegram_id,
                text=offer_text,
                reply_markup=get_subscription_offer_keyboard(),
                parse_mode='HTML'
            )
    
    async def create_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Створити підписку через Stripe"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        # Перевіряємо, чи це адмін (тестовий режим)
        if user and user.is_admin():
            await query.edit_message_text("Тестовий режим для адміна - імітуємо успішну оплату...")
            
            # Видаляємо повідомлення з кнопкою оплати через кілька секунд
            try:
                await asyncio.sleep(2)  # Невелика затримка, щоб користувач побачив повідомлення
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити повідомлення оплати: {e}")
            
            # Імітуємо успішну оплату для адміна
            await self.simulate_successful_payment(user_id)
            return
        
        # URL для повернення після оплати
        bot_username = "upgrade21studio_bot" # Правильний username бота
        success_url = f"https://t.me/{bot_username}"
        cancel_url = f"https://t.me/{bot_username}?start=payment_cancelled"
        
        # Створюємо Checkout Session
        checkout_data = await StripeManager.create_checkout_session(
            telegram_id=user_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if checkout_data:
            # Створюємо інлайн-кнопку для оплати
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            price_formatted = f"{settings.subscription_price:.0f}"
            currency_symbol = "€" if settings.subscription_currency.lower() == "eur" else settings.subscription_currency.upper()
            
            subscription_text = f"""<b>Що тебе чекає у студії 🩵</b>

• 3 тренування на тиждень які ніколи не повторюються
• Доступ до тренувань поточного та попереднього місяця
• Тренування виходять о 19:00 за Києвом (Пн, Ср, Пт)
• Тривалість 30–45 хв

<b>Додатково:</b> 3 руханки та лекції від нутриціолога.

<b>Ком'юніті неймовірних дівчат</b>
• підтримка в чаті та натхнення
• практика з нутріціологом

Підписка продовжується автоматично, а керування буде доступне у твоєму особистому кабінеті в цьому боті.

<b>Вартість:</b> {price_formatted}{currency_symbol}/місяць 🎀

Якщо у тебе виникнуть будь-які питання — звертайся до мене за контактами нижче✨"""
            
            payment_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатити", url=checkout_data['url'])],
                [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")]
            ])
            
            payment_msg = await query.edit_message_text(
                text=subscription_text,
                reply_markup=payment_keyboard,
                parse_mode='HTML'
            )
            
            # Зберігаємо ID повідомлення з оплатою для подальшого видалення
            self.payment_message_ids[user_id] = payment_msg.message_id
            logger.info(f"Збережено ID повідомлення оплати {payment_msg.message_id} для користувача {user_id}")
        else:
            await query.edit_message_text(
                "Виникла помилка при створенні платежу. Спробуйте пізніше або зверніться до підтримки."
            )
    
    async def pause_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати підтвердження призупинення підписки"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Активна підписка не знайдена"
            )
            return
        
        # Отримуємо дату закінчення доступу
        subscription_end_date = user.subscription_end_date or user.next_billing_date
        if not subscription_end_date:
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
        
        # Видаляємо попереднє повідомлення
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
        
        # Показуємо підтвердження
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        confirmation_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸️ Призупинити підписку", callback_data="confirm_pause_subscription")],
            [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_subscription_menu")]
        ])
        
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text=f"Після призупинення підписки доступ до студії та спільноти буде активним до {subscription_end_date.strftime('%d.%m')}.\n\n"
                 f"Оплата більше не списуватиметься. Ти зможеш поновити підписку в будь-який момент.",
            reply_markup=confirmation_keyboard
        )
    
    async def confirm_pause_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Підтвердити призупинення підписки"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Активна підписка не знайдена"
            )
            return
        
        # Перевіряємо, чи це адмін з тестовими даними
        if user.is_admin() and user.stripe_subscription_id.startswith("sub_test_"):
            # Імітуємо призупинення для адміна
            # Встановлюємо дату закінчення через 30 днів (тестовий період)
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
            
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    # Підписка залишається активною до subscription_end_date
                    db_user.subscription_active = True
                    db_user.subscription_paused = True
                    db_user.subscription_cancelled = False
                    db_user.subscription_end_date = subscription_end_date
                    db_user.next_billing_date = None  # Скасовуємо наступне списання
                    db_user.auto_payment_enabled = False  # Деактивуємо автоплатіж
                    db.commit()
                    logger.info(f"Призупинено підписку для {query.from_user.id}: active=True, paused=True, end_date={subscription_end_date}, auto_payment=False")
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
            
            # Показуємо базове меню з новим статусом
            await self.show_active_subscription_menu(query.from_user.id)
            return
        
        # Звичайна обробка для реальних користувачів
        logger.info(f"Підтвердження призупинення підписки для користувача {query.from_user.id}, stripe_sub_id={user.stripe_subscription_id}")
        
        # Отримуємо поточну дату закінчення підписки (до якої оплачено)
        subscription_end_date = user.subscription_end_date or user.next_billing_date
        if not subscription_end_date:
            # Якщо немає дати - встановлюємо 30 днів
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
        
        success = await StripeManager.pause_subscription(user.stripe_subscription_id)
        logger.info(f"Результат призупинення підписки в Stripe: {success}")
        
        if success:
            # Оновлюємо статус в базі - підписка залишається активною до кінця періоду
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_active = True  # Залишаємо активною
                    db_user.subscription_paused = True  # Позначаємо як призупинену
                    db_user.subscription_cancelled = False
                    db_user.subscription_end_date = subscription_end_date  # Доступ до цієї дати
                    db_user.next_billing_date = None  # Скасовуємо наступне списання
                    db_user.auto_payment_enabled = False  # Деактивуємо автоплатіж
                    db.commit()
                    logger.info(f"Призупинено підписку для {query.from_user.id}: active=True, paused=True, end_date={subscription_end_date}, auto_payment=False")
                else:
                    logger.error(f"Користувач {query.from_user.id} не знайдений в базі при призупиненні підписки")
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
            
            # Відправляємо повідомлення в Tech групу
            user_info = f"@{query.from_user.username}" if query.from_user.username else query.from_user.full_name
            await self.send_tech_notification(
                f"⏸️ <b>Підписку призупинено</b>\n\n"
                f"Користувач: {user_info}\n"
                f"ID: {query.from_user.id}\n"
                f"Ім'я: {query.from_user.first_name} {query.from_user.last_name or ''}\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Показуємо базове меню з новим статусом
            await self.show_active_subscription_menu(query.from_user.id)
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Помилка при призупиненні підписки"
            )
    
    async def resume_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поновити підписку"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Підписка не знайдена"
            )
            return
        
        # Перевіряємо, чи це адмін з тестовими даними
        if user.is_admin() and user.stripe_subscription_id.startswith("sub_test_"):
            # Перевіряємо чи був втрачений доступ
            had_no_access = not user.subscription_active
            
            # Імітуємо поновлення для адміна
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_active = True
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = False
                    db_user.subscription_end_date = None
                    db_user.auto_payment_enabled = True
                    # Встановлюємо дату наступного платежу (через 30 днів)
                    db_user.next_billing_date = datetime.utcnow() + timedelta(days=30)
                    db.commit()
                    logger.info(f"Поновлено підписку для {query.from_user.id}: paused=False, cancelled=False, auto_payment=True, next_billing={db_user.next_billing_date}")
            
            # Якщо доступ був втрачений - відправляємо запрошення для приєднання
            if had_no_access:
                logger.info(f"Адмін {query.from_user.id} втратив доступ, відправляємо запрошення для приєднання")
                await self.send_join_invitations(query.from_user.id)
                return
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
            
            # Отримуємо оновлені дані для показу дати
            user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
            next_billing_str = "найближчим часом"
            if user and user.next_billing_date:
                next_billing_str = user.next_billing_date.strftime('%d.%m')
            
            # Відправляємо повідомлення про поновлення з кнопкою
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ Головне меню", callback_data="main_menu")]
            ])
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text=f"Підписку поновлено ✅\n\n"
                     f"Наступний платіж відбудеться {next_billing_str}",
                reply_markup=keyboard
            )
            return
        
        # Звичайна обробка для реальних користувачів
        # Перевіряємо чи був втрачений доступ (щоб потім автоматично додати назад)
        had_no_access = not user.subscription_active
        
        success = await StripeManager.resume_subscription(user.stripe_subscription_id)
        
        if success:
            # Оновлюємо статус в базі
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = False
                    db_user.subscription_end_date = None
                    db_user.auto_payment_enabled = True
                    
                    # Отримуємо дату наступного платежу з Stripe
                    try:
                        subscription_obj = await StripeManager.get_subscription_info(user.stripe_subscription_id)
                        if subscription_obj and 'current_period_end' in subscription_obj:
                            db_user.next_billing_date = datetime.fromtimestamp(subscription_obj['current_period_end'])
                        else:
                            db_user.next_billing_date = datetime.utcnow() + timedelta(days=30)
                    except:
                        db_user.next_billing_date = datetime.utcnow() + timedelta(days=30)
                    
                    db.commit()
                    logger.info(f"Поновлено підписку для {query.from_user.id}: paused=False, cancelled=False, auto_payment=True, next_billing={db_user.next_billing_date}")
            
            # Якщо доступ був втрачений - відправляємо запрошення для приєднання
            if had_no_access:
                logger.info(f"Користувач {query.from_user.id} втратив доступ, відправляємо запрошення для приєднання")
                await self.send_join_invitations(query.from_user.id)
                # Не показуємо повідомлення про поновлення зараз, воно буде після приєднання
                return
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
            
            # Отримуємо оновлені дані користувача для показу дати
            user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
            next_billing_str = "найближчим часом"
            if user and user.next_billing_date:
                next_billing_str = user.next_billing_date.strftime('%d.%m')
            
            # Відправляємо повідомлення про поновлення з кнопкою
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ Головне меню", callback_data="main_menu")]
            ])
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text=f"Підписку поновлено ✅\n\n"
                     f"Наступний платіж відбудеться {next_billing_str}",
                reply_markup=keyboard
            )
            
            # Відправляємо повідомлення в Tech групу
            user_info = f"@{query.from_user.username}" if query.from_user.username else query.from_user.full_name
            await self.send_tech_notification(
                f"▶️ <b>Підписка поновлена</b>\n\n"
                f"Користувач: {user_info}\n"
                f"ID: {query.from_user.id}\n"
                f"Ім'я: {query.from_user.first_name} {query.from_user.last_name or ''}\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Помилка при поновленні підписки"
            )
    
    async def cancel_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати підтвердження скасування підписки"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Активна підписка не знайдена"
            )
            return
        
        # Отримуємо дату закінчення доступу
        subscription_end_date = user.subscription_end_date or user.next_billing_date
        if not subscription_end_date:
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
        
        # Видаляємо попереднє повідомлення
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
        
        # Показуємо підтвердження
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        confirmation_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Скасувати підписку", callback_data="confirm_cancel_subscription")],
            [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_subscription_menu")]
        ])
        
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text=f"Після скасування підписки доступ до студії та спільноти буде активним до {subscription_end_date.strftime('%d.%m')}.\n\n"
                 f"Оплата більше не списуватиметься. Щоб знову отримати доступ, потрібно буде оформити нову підписку.",
            reply_markup=confirmation_keyboard
        )
    
    async def confirm_cancel_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Підтвердити скасування підписки"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Активна підписка не знайдена"
            )
            return
        
        # Перевіряємо, чи це адмін з тестовими даними
        if user.is_admin() and user.stripe_subscription_id.startswith("sub_test_"):
            # Імітуємо скасування для адміна
            # Для скасованої підписки - доступ до next_billing_date (БЕЗ +2 днів)
            subscription_end_date = user.next_billing_date or (datetime.utcnow() + timedelta(days=30))
            
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = True
                    db_user.subscription_end_date = subscription_end_date
                    db_user.next_billing_date = None
                    db_user.auto_payment_enabled = False
                    db.commit()
                    logger.info(f"Скасовано підписку для {query.from_user.id}: cancelled=True, next_billing=None, auto_payment=False, end_date={subscription_end_date}")
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
            
            # Показуємо базове меню з новим статусом
            await self.show_active_subscription_menu(query.from_user.id)
            return
        
        # Звичайна обробка для реальних користувачів
        # Отримуємо дату закінчення поточного оплаченого періоду зі Stripe
        subscription_end_date = user.next_billing_date  # Це дата current_period_end з Stripe
        
        # Якщо немає next_billing_date, спробуємо отримати зі Stripe API
        if not subscription_end_date and user.stripe_subscription_id:
            try:
                subscription_info = await StripeManager.get_subscription(user.stripe_subscription_id)
                if subscription_info and 'current_period_end' in subscription_info:
                    subscription_end_date = datetime.utcfromtimestamp(subscription_info['current_period_end'])
                    logger.info(f"Отримано current_period_end зі Stripe: {subscription_end_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.warning(f"Не вдалося отримати дані зі Stripe: {e}")
        
        # Якщо все ще немає дати, використовуємо fallback
        if not subscription_end_date:
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
            logger.warning(f"Використано fallback дату закінчення: {subscription_end_date.strftime('%Y-%m-%d')}")
        
        success = await StripeManager.cancel_subscription(user.stripe_subscription_id)
        
        logger.info(f"Результат скасування підписки в Stripe: {success}")
        
        if success:
            # Оновлюємо статус в базі
            # При скасуванні підписки доступ до current_period_end (БЕЗ +2 днів на спроби оплати)
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    logger.info(f"До скасування: paused={db_user.subscription_paused}, cancelled={db_user.subscription_cancelled}, auto_payment={db_user.auto_payment_enabled}, end_date={db_user.subscription_end_date}")
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = True
                    # Встановлюємо дату закінчення БЕЗ +2 днів (бо не буде спроб автооплати)
                    db_user.subscription_end_date = subscription_end_date
                    db_user.next_billing_date = None
                    db_user.auto_payment_enabled = False
                    db.commit()
                    logger.info(f"Скасовано підписку для {query.from_user.id}: cancelled=True, next_billing=None, auto_payment=False, end_date={subscription_end_date.strftime('%Y-%m-%d')}")
                else:
                    logger.error(f"Користувач {query.from_user.id} не знайдений в базі при скасуванні підписки")
            
            # Видаляємо попереднє повідомлення з кнопками
            try:
                await query.message.delete()
            except Exception as e:
                logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
            
            # Підраховуємо кількість успішних оплат для повідомлення в Tech групу
            from database.models import Payment
            payment_count = 0
            with DatabaseManager() as db:
                payment_count = db.query(Payment).filter(
                    Payment.user_id == user.id,
                    Payment.status.in_(["succeeded", "completed"])
                ).count()
            
            # Відправляємо повідомлення в Tech групу одразу (без фідбеку)
            user_info = f"@{query.from_user.username}" if query.from_user.username else query.from_user.full_name
            await self.send_tech_notification(
                f"❌ <b>Скасована клієнтом</b>\n\n"
                f"Користувач: {user_info}\n"
                f"ID: {query.from_user.id}\n"
                f"Ім'я: {query.from_user.first_name} {query.from_user.last_name or ''}\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"Успішних оплат: {payment_count}"
            )
            
            # Зберігаємо дані для відправки фідбеку (якщо користувач його надасть)
            context.user_data['cancel_subscription_date'] = subscription_end_date.isoformat() if subscription_end_date else None
            context.user_data['cancel_date'] = datetime.now().isoformat()
            
            # Встановлюємо стан очікування фідбеку
            DatabaseManager.update_user_state(query.from_user.id, UserState.WAITING_CANCEL_FEEDBACK)
            
            # Зберігаємо час запиту фідбеку в контексті користувача
            context.user_data['cancel_feedback_requested_at'] = datetime.now().isoformat()
            
            # Відправляємо повідомлення з проханням фідбеку
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Підписку скасовано ❌\n\n"
                     "Дякую, що була зі мною 🕊️\n\n"
                     "Буду вдячна, якщо поділишся, що тобі сподобалося в студії та що можна покращити:",
                parse_mode='HTML'
            )
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Помилка при скасуванні підписки"
            )
    
    async def change_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Змінити платіжний метод через Stripe Billing Portal"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_customer_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Активна підписка не знайдена"
            )
            return
        
        # Видаляємо попереднє повідомлення з кнопками
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не вдалося видалити попереднє повідомлення: {e}")
        
        # Створюємо return URL для повернення після зміни платіжного методу
        bot_username = "upgrade21studio_bot"
        return_url = f"https://t.me/{bot_username}"
        
        # Створюємо Billing Portal сесію БЕЗ можливості скасування підписки
        portal_url = await StripeManager.create_billing_portal_session(
            customer_id=user.stripe_customer_id,
            return_url=return_url,
            allow_cancel=False  # Вимикаємо можливість скасування підписки в порталі
        )
        
        if portal_url:
            # Відправляємо посилання на портал
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Змінити платіжний метод", url=portal_url)],
                [InlineKeyboardButton("❓ Задати питання", url="https://t.me/alionakovaliova")],
                [InlineKeyboardButton("↩️ Назад", callback_data="back_to_subscription_menu")]
            ])
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="Щоб змінити платіжний метод, натисни кнопку нижче та введи нові платіжні дані.\n\n"
                     "Наступне списання відбудеться з урахуванням змін.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Виникла помилка при створенні посилання.\n\n"
                     "Будь ласка, зв'яжіться з підтримкою:\n"
                     "👉 @alionakovaliova",
                parse_mode='HTML'
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await asyncio.sleep(2)
            await self.handle_subscription_management_from_callback(query.from_user.id)
    
    async def send_join_invitations(self, telegram_id: int):
        """Відправити запрошення для приєднання до каналу та чату"""
        try:
            user = DatabaseManager.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"Користувач {telegram_id} не знайдений при відправці запрошень")
                return
            
            # Отримуємо активні посилання з бази
            invite_links = DatabaseManager.get_active_invite_links()
            active_links = [link for link in invite_links if not link.is_expired] if invite_links else []
            logger.info(f"Знайдено {len(active_links)} активних посилань для запрошення")
            
            # Перевіряємо що потрібно відправити
            send_channel_invite = not user.joined_channel
            send_chat_invite = not user.joined_chat
            
            if send_channel_invite:
                # Шукаємо посилання на канал
                channel_link = None
                for link in active_links:
                    if link.link_type == "channel":
                        channel_link = link
                        break
                
                if channel_link:
                    keyboard = [
                        [InlineKeyboardButton(
                            text="🎀 Приєднатися до студії",
                            url=channel_link.invite_link
                        )]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    msg = await self.bot.send_message(
                        chat_id=telegram_id,
                        text="✨ <b>Вітаю! Твою підписку активовано!</b>\n\n"
                             "Тепер ти — частина UPGRADE.21 🩵\n\n"
                             "<b>Крок 1:</b>\n"
                             "Натисни кнопку нижче та надішли запит на приєднання до онлайн-студії, де ти будеш тренуватися.",
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                    # Зберігаємо ID повідомлення
                    if telegram_id not in self.join_step_messages:
                        self.join_step_messages[telegram_id] = []
                    self.join_step_messages[telegram_id].append(msg.message_id)
                else:
                    # Fallback
                    channel_username = settings.private_channel_id.replace('-100', '')
                    keyboard = [
                        [InlineKeyboardButton(
                            text="🎀 Приєднатися до студії",
                            url=f"https://t.me/c/{channel_username}"
                        )]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await self.bot.send_message(
                        chat_id=telegram_id,
                        text="✨ <b>Вітаю! Твою підписку активовано!</b>\n\n"
                             "Тепер ти — частина UPGRADE.21 🩵\n\n"
                             "<b>Крок 1:</b>\n"
                             "Натисні кнопку нижче та надішли запит на приєднання до онлайн-студії, де ти будеш тренуватися.",
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            elif send_chat_invite:
                # Якщо вже приєднався до каналу, але не до чату
                chat_link = None
                for link in active_links:
                    if link.link_type == "group":
                        chat_link = link
                        break
                
                if chat_link:
                    keyboard = [
                        [InlineKeyboardButton(
                            text="💬 Приєднатися до спільноти",
                            url=chat_link.invite_link
                        )]
                    ]
                    msg = await self.bot.send_message(
                        chat_id=telegram_id,
                        text="🎉 <b>Чудово! Ти в студії!</b>\n\n"
                             "<b>Крок 2:</b>\n"
                             "Приєднайся до чату спільноти, де ми разом практикуємо, підтримуємо одна одну та ділимося досягненнями!",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                    if telegram_id not in self.join_step_messages:
                        self.join_step_messages[telegram_id] = []
                    self.join_step_messages[telegram_id].append(msg.message_id)
            
            # Плануємо нагадування про приєднання (якщо користувач не приєднається протягом доби)
            if send_channel_invite or send_chat_invite:
                if self.task_scheduler:
                    await self.task_scheduler.schedule_join_reminders(telegram_id)
            
        except Exception as e:
            logger.error(f"Помилка при відправці запрошень для {telegram_id}: {e}")
    
    async def handle_successful_payment(self, telegram_id: int):
        """Обробити успішну оплату - надіслати кнопки для приєднання"""
        try:
            user = DatabaseManager.get_user_by_telegram_id(telegram_id)
            if not user:
                return
            
            # Логуємо стан payment_message_ids
            logger.info(f"Payment message IDs словник: {self.payment_message_ids}")
            logger.info(f"Перевірка наявності ID для користувача {telegram_id}: {telegram_id in self.payment_message_ids}")
            
            # Видаляємо кнопки з попереднього повідомлення з оплатою (якщо є)
            if telegram_id in self.payment_message_ids:
                try:
                    # Спочатку пробуємо видалити кнопки (м'якіший варіант)
                    await self.bot.edit_message_reply_markup(
                        chat_id=telegram_id,
                        message_id=self.payment_message_ids[telegram_id],
                        reply_markup=None
                    )
                    logger.info(f"Видалено кнопки оплати для користувача {telegram_id}")
                except Exception as e:
                    logger.debug(f"Не вдалося видалити кнопки, спробуємо видалити все повідомлення: {e}")
                    try:
                        # Якщо не вдалося видалити кнопки - видаляємо все повідомлення
                        await self.bot.delete_message(
                            chat_id=telegram_id,
                            message_id=self.payment_message_ids[telegram_id]
                        )
                        logger.info(f"Видалено повідомлення оплати для користувача {telegram_id}")
                    except Exception as e2:
                        logger.warning(f"Не вдалося видалити повідомлення оплати: {e2}")
                finally:
                    # Видаляємо зі словника незалежно від результату
                    del self.payment_message_ids[telegram_id]
            else:
                logger.warning(f"ID повідомлення оплати для користувача {telegram_id} не знайдено в словнику")
            
            # Оновлюємо статус підписки - активуємо та скидаємо всі негативні статуси
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if db_user:
                    db_user.subscription_active = True
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = False
                    
                    # Встановлюємо дати підписки:
                    # next_billing_date - коли буде спроба оплати (через 30 днів)
                    next_billing = datetime.utcnow() + timedelta(days=30)
                    db_user.next_billing_date = next_billing
                    # subscription_end_date - коли кікнуть після невдалих спроб (+2 дні для 3 спроб)
                    db_user.subscription_end_date = next_billing + timedelta(days=2)
                    
                    db.commit()
                    logger.info(f"Оновлено статус підписки для користувача {telegram_id}, "
                              f"next_billing_date={next_billing.strftime('%Y-%m-%d')}, "
                              f"subscription_end_date={db_user.subscription_end_date.strftime('%Y-%m-%d')}")
            
            # Скасовуємо всі нагадування про підписку, оскільки оплата пройшла
            cancelled_count = DatabaseManager.cancel_subscription_reminders_if_active(telegram_id)
            if cancelled_count > 0:
                logger.info(f"Скасовано {cancelled_count} нагадувань про підписку для користувача {telegram_id}")
            
            # Відправляємо запрошення для приєднання
            await self.send_join_invitations(telegram_id)
            
            logger.info(f"Обробка успішної оплати для користувача {telegram_id}")
            
        except Exception as e:
            logger.error(f"Помилка при обробці успішної оплати для {telegram_id}: {e}")
    
    async def handle_join_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити запит на приєднання до каналу/чату"""
        query = update.callback_query
        await query.answer()
        
        try:
            # Парсимо дані з callback: join_channel_-1002747224769
            data_parts = query.data.split("_")
            if len(data_parts) != 3:
                await query.edit_message_text("Неправильний формат запиту")
                return
            
            chat_type = data_parts[1]  # "channel"або "group"
            chat_id = data_parts[2]    # ID чату
            
            # Перевіряємо, чи користувач має активну підписку
            user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
            if not user or not user.subscription_active:
                await query.edit_message_text("Для приєднання потрібна активна підписка")
                return
            
            # Отримуємо посилання з бази
            invite_link_obj = DatabaseManager.get_invite_link_by_chat(chat_id, chat_type)
            
            if invite_link_obj and invite_link_obj.is_active:
                # Створюємо кнопку для приєднання
                chat_name = invite_link_obj.chat_title or ("канал"if chat_type == "channel"else "чат")
                
                join_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        f"Приєднатися до {chat_name}",
                        url=invite_link_obj.invite_link
                    )]
                ])
                
                await query.edit_message_text(
                    f"<b>Готово!</b>\n\n"
                    f"Натисніть кнопку нижче для приєднання до {chat_name}\n\n"
                    f"Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                    f"Не передавайте це посилання іншим користувачам",
                    reply_markup=join_keyboard,
                    parse_mode='HTML'
                )
            else:
                # Спробуємо створити нове посилання через Telegram API
                try:
                    invite_link = await self.bot.create_chat_invite_link(
                        chat_id=chat_id,
                        creates_join_request=True,  # Вимагає підтвердження
                        name=f"Invite for user {query.from_user.id}"
                    )
                    
                    # Отримуємо інформацію про чат
                    chat_info = await self.bot.get_chat(chat_id)
                    
                    # Зберігаємо в базу
                    DatabaseManager.create_invite_link(
                        chat_id=chat_id,
                        chat_type=chat_type,
                        invite_link=invite_link.invite_link,
                        chat_title=chat_info.title
                    )
                    
                    join_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            f"Приєднатися до {chat_info.title}",
                            url=invite_link.invite_link
                        )]
                    ])
                    
                    await query.edit_message_text(
                        f"<b>Готово!</b>\n\n"
                        f"Натисніть кнопку нижче для приєднання до {chat_info.title}\n\n"
                        f"Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                        f"Не передавайте це посилання іншим користувачам",
                        reply_markup=join_keyboard,
                        parse_mode='HTML'
                    )
                    
                except Exception as e:
                    logger.error(f"Помилка створення invite link: {e}")
                    await query.edit_message_text(
                        f"Не вдалося створити посилання для приєднання. "
                        f"Зверніться до адміністратора або спробуйте пізніше."
                    )
                    
        except Exception as e:
            logger.error(f"Помилка обробки запиту на приєднання: {e}")
            await query.edit_message_text("Виникла помилка. Спробуйте пізніше.")
    
    async def simulate_successful_payment(self, telegram_id: int):
        """Симулювати успішну оплату для тестування (тільки для адмінів)"""
        try:
            # Створюємо унікальний тестовий ID
            test_subscription_id = f"sub_test_admin_{telegram_id}"
            test_customer_id = f"cus_test_admin_{telegram_id}"
            
            # Оновлюємо користувача в базі даних
            with DatabaseManager() as db:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    user.subscription_active = True
                    user.subscription_paused = False
                    user.state = "active_subscription"
                    user.stripe_customer_id = test_customer_id
                    user.stripe_subscription_id = test_subscription_id
                    user.updated_at = datetime.utcnow()
                    
                    # Встановлюємо дату закінчення підписки (через 30 днів для тестової підписки)
                    subscription_end = datetime.utcnow() + timedelta(days=30)
                    user.subscription_end_date = subscription_end
                    user.next_billing_date = subscription_end
                    
                    # Створюємо запис про тестовий платіж
                    from database.models import Payment
                    payment = Payment(
                        user_id=user.id,
                        amount=int(settings.subscription_price * 100),  # зберігаємо в центах як в БД
                        currency=settings.subscription_currency,
                        status="succeeded",
                        stripe_subscription_id=test_subscription_id,
                        paid_at=datetime.utcnow()
                    )
                    db.add(payment)
                    db.commit()
            
            # Викликаємо обробку успішної оплати
            await self.handle_successful_payment(telegram_id)
            
            logger.info(f"Симуляція успішної оплати для адміна {telegram_id} з ID {test_subscription_id}")
            
        except Exception as e:
            logger.error(f"Помилка при симуляції оплати для {telegram_id}: {e}")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати адмін панель"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        
        if not user or not user.is_admin():
            await update.message.reply_text("У вас немає прав адміністратора")
            return
        
        admin_text = """
 <b>Адмін панель</b>

Доступні команди:
• `/admin` - показати цю панель
• `/set_admin <telegram_id>` - надати права адміна користувачу

<b>Особливості адмін режиму:</b>
• Тестова оплата (без Stripe)
• Доступ до всіх функцій
• Імітація успішних платежів
"""
        
        await update.message.reply_text(admin_text, parse_mode='HTML')
    
    async def set_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Встановити роль адміна користувачу"""
        # Перевіряємо, чи користувач сам є адміном або це власник бота
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or (not user.is_admin() and update.effective_user.id != int(settings.admin_chat_id)):
            await update.message.reply_text("У вас немає прав для цієї команди")
            return
        
        if not context.args:
            await update.message.reply_text("Вкажіть Telegram ID користувача: `/set_admin 123456789`")
            return
        
        try:
            target_telegram_id = int(context.args[0])
            success = DatabaseManager.set_user_role(target_telegram_id, "admin")
            
            if success:
                await update.message.reply_text(f"Користувач {target_telegram_id} отримав права адміна")
            else:
                await update.message.reply_text(f"Користувач {target_telegram_id} не знайдений")
                
        except ValueError:
            await update.message.reply_text("Невірний формат Telegram ID")
    
    async def get_chat_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отримати інформацію про поточний чат"""
        chat = update.effective_chat
        user = update.effective_user
        
        chat_type_names = {
            'private': 'Приватний чат',
            'group': 'Група',
            'supergroup': 'Супергрупа',
            'channel': 'Канал'
        }
        
        # Для каналів бот не може надсилати повідомлення, тому логуємо інформацію
        if chat.type == 'channel':
            logger.info(f"Команда /get_chat_info викликана в каналі: ID={chat.id}, Title={chat.title}, Username={chat.username}")
            return
        
        username_display = f"@{chat.username}"if chat.username else "немає"
        user_username_display = f"@{user.username}"if user.username else "немає"
        
        info = f"""Інформація про чат:
• ID: {chat.id}
• Тип: {chat_type_names.get(chat.type, chat.type)}
• Назва: {chat.title or 'N/A'}
• Username: {username_display}

 Ваша інформація:
• ID: {user.id}
• Username: {user_username_display}
• Ім'я: {user.first_name}

 Підказка:
Для використання в .env файлі:

PRIVATE_CHANNEL_ID={chat.id}
PRIVATE_CHAT_ID={chat.id}
ADMIN_CHAT_ID={user.id}"""
        
        try:
            await update.message.reply_text(info)
        except Exception as e:
            logger.error(f"Помилка при надсиланні інформації про чат: {e}")
            # Спробуємо надіслати спрощену версію
            simple_info = f"Chat ID: {chat.id}\nUser ID: {user.id}\nType: {chat.type}"
            await update.message.reply_text(simple_info)
    
    # Видалено автоматичний обробник запитів на приєднання
    # Тепер приєднання відбувається тільки через ручний процес у боті
    
    async def manage_links_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для управління посиланнями (тільки для адмінів)"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or not user.is_admin():
            await update.message.reply_text("Доступ заборонено. Ця команда тільки для адміністраторів.")
            return
        
        links = DatabaseManager.get_active_invite_links()
        
        if not links:
            await update.message.reply_text(
                "Поточні посилання відсутні.\n\n"
                "Використовуйте:\n"
                "• `/create_invite <chat_id> <chat_type> <invite_link> [назва]` - створити посилання\n"
                "• `/list_invites` - показати всі посилання",
                parse_mode='HTML'
            )
            return
        
        message = "<b>Активні посилання:</b>\n\n"
        for link in links:
            status = ""if link.is_active else ""
            message += f"{status} <b>{link.chat_title or 'Без назви'}</b>\n"
            message += f"  • ID: {link.chat_id}\n"
            message += f"  • Тип: {link.link_type}\n"
            message += f"  • Створено: {link.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        message += "\n Команди:\n"
        message += "• `/create_invite` - створити нове посилання\n"
        message += "• `/list_invites` - детальний список"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def create_invite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Створити invite посилання для чату/каналу"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or not user.is_admin():
            await update.message.reply_text("Доступ заборонено. Ця команда тільки для адміністраторів.")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "Неправильний формат команди.\n\n"
                "<b>Використання:</b>\n"
                "`/create_invite <chat_id> <chat_type> <invite_link> [назва]`\n\n"
                "<b>Приклад:</b>\n"
                "`/create_invite -1002747224769 channel https://t.me/+AbCdEfGhIjKl Приватний канал`",
                parse_mode='HTML'
            )
            return
        
        try:
            chat_id = context.args[0]
            chat_type = context.args[1]
            invite_link = context.args[2]
            chat_title = "".join(context.args[3:]) if len(context.args) > 3 else None
            
            if chat_type not in ["channel", "group"]:
                await update.message.reply_text("Тип чату має бути 'channel' або 'group'")
                return
            
            # Створюємо або оновлюємо посилання
            link_obj = DatabaseManager.create_invite_link(
                chat_id=chat_id,
                chat_type=chat_type,
                invite_link=invite_link,
                chat_title=chat_title
            )
            
            await update.message.reply_text(
                f"Посилання успішно створено!\n\n"
                f"<b>Деталі:</b>\n"
                f"• Chat ID: {link_obj.chat_id}\n"
                f"• Тип: {link_obj.link_type}\n"
                f"• Назва: {link_obj.chat_title or 'Не вказана'}\n"
                f"• Посилання: `{link_obj.invite_link}`",
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Помилка створення посилання: {e}")
            await update.message.reply_text("Помилка при створенні посилання. Перевірте параметри.")
    
    async def list_invites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати детальний список всіх посилань"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or not user.is_admin():
            await update.message.reply_text("Доступ заборонено. Ця команда тільки для адміністраторів.")
            return
        
        links = DatabaseManager.get_active_invite_links()
        
        if not links:
            await update.message.reply_text("Посилання відсутні.")
            return
        
        for link in links:
            status = "Активне"if link.is_active else "Неактивне"
            message = f"<b>{link.chat_title or 'Без назви'}</b>\n\n"
            message += f"<b>Статус:</b> {status}\n"
            message += f"<b>Chat ID:</b> `{link.chat_id}`\n"
            message += f"<b>Тип:</b> {link.link_type}\n"
            message += f"<b>Посилання:</b> `{link.invite_link}`\n"
            message += f"<b>Створено:</b> {link.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += f"<b>Оновлено:</b> {link.updated_at.strftime('%d.%m.%Y %H:%M')}"
            
            await update.message.reply_text(message, parse_mode='HTML')
    
    async def log_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Коротка команда для отримання ID чату"""
        chat = update.effective_chat
        user = update.effective_user
        
        # Для каналів логуємо в консоль і надсилаємо користувачу в приватні повідомлення
        if chat.type == 'channel':
            logger.info(f"Channel ID: {chat.id}, Title: {chat.title}")
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"ID каналу '{chat.title}': {chat.id}"
                )
            except Exception as e:
                logger.error(f"Не вдалося надіслати приватне повідомлення користувачу {user.id}: {e}")
            return
        
        # Для груп та приватних чатів
        await update.message.reply_text(f"Chat ID: {chat.id}\nYour ID: {user.id}")
    
    async def forward_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отримати інформацію про пересланий чат"""
        if not update.message.forward_from_chat:
            await update.message.reply_text("Перешліть повідомлення з каналу/групи для отримання ID")
            return
        
        forward_chat = update.message.forward_from_chat
        
        info = f"""Інформація про пересланий чат:
• ID: {forward_chat.id}
• Тип: {forward_chat.type}
• Назва: {forward_chat.title or 'N/A'}
• Username: @{forward_chat.username or 'немає'}

 Використовуйте цей ID в .env файлі:
PRIVATE_CHANNEL_ID={forward_chat.id}"""
        
        await update.message.reply_text(info)
    
    async def chat_id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Коротка команда для отримання ID чату"""
        chat = update.effective_chat
        user = update.effective_user
        
        # Для каналів логуємо в консоль і надсилаємо користувачу в приватні повідомлення
        if chat.type == 'channel':
            logger.info(f"Channel ID: {chat.id}, Title: {chat.title}")
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"ID каналу '{chat.title}': {chat.id}"
                )
            except Exception as e:
                logger.error(f"Не вдалося надіслати приватне повідомлення користувачу {user.id}: {e}")
            return
        
        # Для груп та приватних чатів
        await update.message.reply_text(f"Chat ID: {chat.id}\nYour ID: {user.id}")
    
    async def log_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Логування всіх повідомлень для діагностики"""
        # Повідомлення від звичайних чатів (приватні, групи)
        if update.message:
            chat = update.effective_chat
            user = update.effective_user
            message_text = update.message.text or "[не текст]"

            logger.info(
                f"Повідомлення отримано: Chat ID: {chat.id}, Chat Type: {chat.type}, "
                f"Chat Title: {chat.title}, User ID: {user.id}, Username: @{user.username or 'немає'}, "
                f"Text: {message_text[:50]}..."
            )

            # Якщо це команда в каналі (переслане як message) — лог
            if chat.type == 'channel' and message_text.startswith('/'):
                logger.info(f"Команда в каналі: {message_text}")

        # Повідомлення від каналів приходять у полях channel_post або edited_channel_post
        if update.channel_post:
            post = update.channel_post
            chat = post.chat
            text = post.text or post.caption or "[не текст]"
            logger.info(
                f"Channel post: Chat ID: {chat.id}, Chat Type: {chat.type}, "
                f"Chat Title: {chat.title}, Text: {text[:50]}..."
            )

        if update.edited_channel_post:
            post = update.edited_channel_post
            chat = post.chat
            text = post.text or post.caption or "[не текст]"
            logger.info(
                f"Edited channel post: Chat ID: {chat.id}, Chat Type: {chat.type}, "
                f"Chat Title: {chat.title}, Text: {text[:50]}..."
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробник помилок"""
        error_message = str(context.error)
        
        # Ігноруємо стандартні помилки Telegram, які не є критичними
        if any(ignore_phrase in error_message for ignore_phrase in [
            "Message is not modified",
            "exactly the same as a current content",
            "Bad Request: message is not modified"
        ]):
            # Це нормальна ситуація, просто логуємо як warning
            logger.warning(f"Telegram API warning: {error_message}")
            return
        
        # Логуємо критичні помилки
        logger.error(f"Exception while handling an update: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "Вибачте, сталася помилка. Спробуйте ще раз або зверніться до підтримки."
                )
            except Exception as e:
                logger.error(f"Не вдалося надіслати повідомлення про помилку: {e}")
    
    async def handle_chat_join_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Автоматична обробка запитів на приєднання до каналу/чату"""
        try:
            chat_join_request = update.chat_join_request
            user_id = chat_join_request.from_user.id
            chat_id = chat_join_request.chat.id
            chat_title = chat_join_request.chat.title
            
            logger.info(f"Отримано запит на приєднання від користувача {user_id} до чату {chat_id} ({chat_title})")
            
            # Перевіряємо, чи користувач має активну підписку
            user = DatabaseManager.get_user_by_telegram_id(user_id)
            if not user or not user.subscription_active:
                logger.warning(f"Користувач {user_id} не має активної підписки, відхиляємо запит")
                await chat_join_request.decline()
                return
            
            # Схвалюємо запит
            await chat_join_request.approve()
            logger.info(f"Запит на приєднання від користувача {user_id} до {chat_title} схвалено")
            
            # Визначаємо тип чату (канал чи група)
            is_channel = chat_join_request.chat.type in ['channel', 'supergroup']
            
            # Оновлюємо статус приєднання в базі
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == user_id).first()
                if db_user:
                    if str(chat_id) == str(settings.private_channel_id):
                        # Це канал
                        db_user.joined_channel = True
                        db.commit()
                        logger.info(f"Оновлено joined_channel=True для користувача {user_id}")
                        
                        # Тепер надсилаємо посилання на групу
                        await asyncio.sleep(1)  # Невелика затримка
                        
                        # Шукаємо посилання на групу
                        invite_links = DatabaseManager.get_active_invite_links()
                        active_links = [link for link in invite_links if not link.is_expired] if invite_links else []
                        
                        chat_link = None
                        for link in active_links:
                            if link.link_type == "chat"or link.link_type == "group":
                                chat_link = link
                                break
                        
                        if chat_link:
                            keyboard = [
                                [InlineKeyboardButton(
                                    text="💬 Приєднатися до спільноти",
                                    url=chat_link.invite_link
                                )]
                            ]
                            
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            msg = await self.bot.send_message(
                                chat_id=user_id,
                                text="<b>Крок 2:</b>\n\n"
                                     "Приєднайся до спільноти. Тут проходить практика з нутріціологом, ми спілкуємось, також я ділюсь важливою інформацією.",
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                            # Зберігаємо ID повідомлення
                            if user_id not in self.join_step_messages:
                                self.join_step_messages[user_id] = []
                            self.join_step_messages[user_id].append(msg.message_id)
                        else:
                            # Fallback до .env
                            chat_username = settings.private_chat_id.replace('-100', '')
                            keyboard = [
                                [InlineKeyboardButton(
                                    text="💬 Приєднатися до спільноти",
                                    url=f"https://t.me/c/{chat_username}"
                                )]
                            ]
                            
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            msg = await self.bot.send_message(
                                chat_id=user_id,
                                text="<b>Крок 2:</b>\n\n"
                                     "Приєднайся до спільноти. Тут проходить практика з нутріціологом, ми спілкуємось, також я ділюсь важливою інформацією.",
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                            # Зберігаємо ID повідомлення
                            if user_id not in self.join_step_messages:
                                self.join_step_messages[user_id] = []
                            self.join_step_messages[user_id].append(msg.message_id)
                    
                    elif str(chat_id) == str(settings.private_chat_id):
                        # Це група/чат
                        db_user.joined_chat = True
                        db.commit()
                        logger.info(f"Оновлено joined_chat=True для користувача {user_id}")
                        
                        # Видаляємо попередні повідомлення Крок 1 та Крок 2
                        if user_id in self.join_step_messages:
                            for message_id in self.join_step_messages[user_id]:
                                try:
                                    await self.bot.delete_message(chat_id=user_id, message_id=message_id)
                                    logger.info(f"Видалено повідомлення {message_id} для користувача {user_id}")
                                except Exception as e:
                                    logger.warning(f"Не вдалося видалити повідомлення {message_id}: {e}")
                            # Очищаємо список
                            del self.join_step_messages[user_id]
                        
                        # Надсилаємо відео кружечок замість текстового повідомлення
                        video_path = "assets/welcome_video.mp4"
                        if os.path.exists(video_path):
                            await self.bot.send_video_note(
                                chat_id=user_id,
                                video_note=open(video_path, "rb")
                            )
                        
                        # Затримка 5 секунд, щоб людина встигла подивитись кружечок
                        await asyncio.sleep(5)
                        
                        # Відправляємо базове меню з підпискою
                        await self.show_active_subscription_menu(user_id)
                        
                        # Встановлюємо стан активної підписки
                        DatabaseManager.update_user_state(user_id, UserState.ACTIVE_SUBSCRIPTION)
                    else:
                        logger.warning(f"Невідомий chat_id: {chat_id}")
                else:
                    logger.error(f"Користувач {user_id} не знайдений при оновленні joined статусу")
            
        except Exception as e:
            logger.error(f"Помилка при обробці запиту на приєднання: {e}")
    
    
    async def handle_channel_access_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити запит доступу до каналу"""
        query = update.callback_query
        await query.answer()
        
        # Перевіряємо підписку
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.subscription_active:
            await query.edit_message_text("Для доступу потрібна активна підписка")
            return
        
        # Формуємо callback для приєднання до каналу
        await self.handle_join_request_by_type(update, context, "channel", settings.private_channel_id)
    
    async def handle_chat_access_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити запит доступу до чату"""
        query = update.callback_query
        await query.answer()
        
        # Перевіряємо підписку
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.subscription_active:
            await query.edit_message_text("Для доступу потрібна активна підписка")
            return
        
        # Формуємо callback для приєднання до чату
        await self.handle_join_request_by_type(update, context, "group", settings.private_chat_id)
    
    async def handle_join_request_by_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        chat_type: str, chat_id: str):
        """Універсальна функція для обробки запитів приєднання"""
        query = update.callback_query
        
        try:
            # Отримуємо або створюємо посилання для приєднання
            invite_link_obj = DatabaseManager.get_invite_link_by_chat(chat_id, chat_type)
            
            if invite_link_obj and invite_link_obj.is_active:
                # Використовуємо існуюче посилання
                chat_name = invite_link_obj.chat_title or ("канал"if chat_type == "channel"else "чат")
                
                join_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        f"Приєднатися до {chat_name}",
                        url=invite_link_obj.invite_link
                    )]
                ])
                
                await query.edit_message_text(
                    f"<b>Готово!</b>\n\n"
                    f"Натисніть кнопку нижче для приєднання до {chat_name}\n\n"
                    f"Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                    f"Не передавайте це посилання іншим користувачам",
                    reply_markup=join_keyboard,
                    parse_mode='HTML'
                )
            else:
                # Створюємо нове посилання
                try:
                    invite_link = await self.bot.create_chat_invite_link(
                        chat_id=int(chat_id),
                        creates_join_request=True,
                        name=f"Invite for user {query.from_user.id}"
                    )
                    
                    # Отримуємо інформацію про чат
                    chat_info = await self.bot.get_chat(int(chat_id))
                    
                    # Зберігаємо в базу
                    DatabaseManager.create_invite_link(
                        chat_id=chat_id,
                        chat_type=chat_type,
                        invite_link=invite_link.invite_link,
                        chat_title=chat_info.title
                    )
                    
                    join_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            f"Приєднатися до {chat_info.title}",
                            url=invite_link.invite_link
                        )]
                    ])
                    
                    await query.edit_message_text(
                        f"<b>Готово!</b>\n\n"
                        f"Натисніть кнопку нижче для приєднання до {chat_info.title}\n\n"
                        f"Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                        f"Не передавайте це посилання іншим користувачам",
                        reply_markup=join_keyboard,
                        parse_mode='HTML'
                    )
                    
                except Exception as e:
                    logger.error(f"Помилка створення invite link: {e}")
                    await query.edit_message_text(
                        f"Не вдалося створити посилання для приєднання. "
                        f"Зверніться до адміністратора або спробуйте пізніше."
                    )
                    
        except Exception as e:
            logger.error(f"Помилка обробки запиту на приєднання: {e}")
            await query.edit_message_text("Виникла помилка. Спробуйте пізніше.")

    async def handle_channel_joined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити підтвердження приєднання до каналу"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Видаляємо повідомлення з кнопкою
        try:
            await query.message.delete()
        except Exception:
            pass
        
        # Скасовуємо нагадування про приєднання до каналу
        DatabaseManager.cancel_user_reminders(user_id, "join_channel")
        
        # Перевіряємо чи це перше приєднання чи повторне
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        was_previously_joined = user.joined_channel if user else False
        
        # Оновлюємо статус приєднання до каналу
        with DatabaseManager() as db:
            db_user = db.query(User).filter(User.telegram_id == user_id).first()
            if db_user:
                db_user.joined_channel = True
                db.commit()
                logger.info(f"Оновлено joined_channel=True для користувача {user_id}, was_previously_joined={was_previously_joined}")
            else:
                logger.error(f"Користувач {user_id} не знайдений при оновленні joined_channel")
        
        # Якщо користувач вже був приєднаний раніше (повторне приєднання після виходу)
        if was_previously_joined:
            logger.info(f"Користувач {user_id} повторно приєднався до каналу - пропускаємо привітання")
            # Просто показуємо головне меню без додаткових повідомлень
            await self.show_active_subscription_menu(user_id)
            return
        
        # Перше приєднання - відправляємо повідомлення про успішне схвалення каналу
        await self.bot.send_message(
            chat_id=user_id,
            text="<b>Відмінно!</b> Ви приєдналися до каналу!\n\n"
                 "Тепер у вас є доступ до всіх тренувань та корисної інформації ",
            parse_mode='HTML'
        )
        
        # Встановлюємо стан очікування приєднання до чату
        DatabaseManager.update_user_state(user_id, UserState.CHAT_JOIN_PENDING)
        
        # Отримуємо посилання на чат з бази
        invite_links = DatabaseManager.get_active_invite_links()
        chat_link = None
        
        for link in invite_links:
            if link.link_type == "chat":
                chat_link = link
                break
        
        if chat_link:
            keyboard = [[InlineKeyboardButton(
                text="💬 Приєднатися до спільноти",
                url=chat_link.invite_link
            )]]
        else:
            # Fallback
            keyboard = [[InlineKeyboardButton(
                text="💬 Приєднатися до спільноти",
                url=f"https://t.me/{settings.private_chat_id.lstrip('-')}"
            )]]
        
        # Додаємо кнопку "Я приєднався"
        keyboard.append([InlineKeyboardButton(
            text="Я приєднався до чату",
            callback_data="chat_joined"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=user_id,
            text="<b>Крок 2:</b>\n\n"
                 "Приєднайся до спільноти. Тут проходить практика з нутріціологом, ми спілкуємось, також я ділюсь важливою інформацією.\n\n"
                 "Після приєднання натисніть кнопку 'Я приєднався до чату'",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def handle_chat_joined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити підтвердження приєднання до чату"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Видаляємо повідомлення з кнопкою
        try:
            await query.message.delete()
        except Exception:
            pass
        
        # Скасовуємо всі залишкові нагадування про приєднання
        DatabaseManager.cancel_user_reminders(user_id, "join_channel")
        
        # Перевіряємо чи це перше приєднання чи повторне
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        was_previously_joined = user.joined_chat if user else False
        
        # Оновлюємо статус приєднання до чату
        with DatabaseManager() as db:
            db_user = db.query(User).filter(User.telegram_id == user_id).first()
            if db_user:
                db_user.joined_chat = True
                db.commit()
                logger.info(f"Оновлено joined_chat=True для користувача {user_id}, was_previously_joined={was_previously_joined}")
            else:
                logger.error(f"Користувач {user_id} не знайдений при оновленні joined_chat")
        
        # Якщо користувач вже був приєднаний раніше (повторне приєднання після виходу)
        if was_previously_joined:
            logger.info(f"Користувач {user_id} повторно приєднався до чату - пропускаємо привітання")
            # Просто показуємо головне меню без кружечка та додаткових повідомлень
            await self.show_active_subscription_menu(user_id)
            # Встановлюємо стан активної підписки
            DatabaseManager.update_user_state(user_id, UserState.ACTIVE_SUBSCRIPTION)
            return
        
        # Перше приєднання - надсилаємо відео кружечок
        video_path = "assets/welcome_video.mp4"
        if os.path.exists(video_path):
            await self.bot.send_video_note(
                chat_id=user_id,
                video_note=open(video_path, "rb")
            )
        
        # Затримка 5 секунд, щоб людина встигла подивитись кружечок
        await asyncio.sleep(5)
        
        # Відправляємо базове меню з підпискою
        await self.show_active_subscription_menu(user_id)
        
        # Встановлюємо стан активної підписки
        DatabaseManager.update_user_state(user_id, UserState.ACTIVE_SUBSCRIPTION)

    async def handle_go_to_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти в канал (користувач вже приєднаний)"""
        query = update.callback_query
        await query.answer()
        
        # Видаляємо повідомлення з кнопкою
        try:
            await query.message.delete()
        except Exception:
            pass
        
        # Отримуємо посилання на канал з бази
        invite_links = DatabaseManager.get_active_invite_links()
        channel_link = None
        
        for link in invite_links:
            if link.link_type == "channel":
                channel_link = link
                break
        
        if channel_link:
            # Використовуємо посилання з бази даних
            keyboard = [[InlineKeyboardButton(
                text="Перейти в канал",
                url=channel_link.invite_link
            )]]
        else:
            # Fallback
            from config import settings
            channel_id_clean = settings.private_channel_id.lstrip('-')
            if channel_id_clean.startswith('100'):
                channel_id_clean = channel_id_clean[3:]
            keyboard = [[InlineKeyboardButton(
                text="Перейти в канал",
                url=f"https://t.me/c/{channel_id_clean}"
            )]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text="<b>Перехід до каналу</b>\n\n"
                 "Ви вже приєднані до нашого приватного каналу!\n"
                 "Натисніть кнопку нижче, щоб перейти в канал та переглянути останні матеріали.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        # Повертаємося до меню керування підпискою через кілька секунд
        await asyncio.sleep(3)
        await self.handle_subscription_management_from_callback(query.from_user.id)

    async def handle_go_to_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти в чат (користувач вже приєднаний)"""
        query = update.callback_query
        await query.answer()
        
        # Видаляємо повідомлення з кнопкою
        try:
            await query.message.delete()
        except Exception:
            pass
        
        # Отримуємо посилання на чат з бази
        invite_links = DatabaseManager.get_active_invite_links()
        chat_link = None
        
        for link in invite_links:
            if link.link_type == "chat":
                chat_link = link
                break
        
        if chat_link:
            # Використовуємо посилання з бази даних
            keyboard = [[InlineKeyboardButton(
                text="Перейти в чат",
                url=chat_link.invite_link
            )]]
        else:
            # Fallback
            from config import settings
            chat_id_clean = settings.private_chat_id.lstrip('-')
            if chat_id_clean.startswith('100'):
                chat_id_clean = chat_id_clean[3:]
            keyboard = [[InlineKeyboardButton(
                text="Перейти в чат",
                url=f"https://t.me/c/{chat_id_clean}"
            )]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text="<b>Перехід до чату</b>\n\n"
                 "Ви вже приєднані до нашого приватного чату!\n"
                 "Натисніть кнопку нижче, щоб перейти в чат та поспілкуватися з іншими учасниками.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        # Повертаємося до меню керування підпискою через кілька секунд
        await asyncio.sleep(3)
        await self.handle_subscription_management_from_callback(query.from_user.id)

    async def show_more_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати додаткову інформацію про підписку"""
        query = update.callback_query
        await query.answer()
        
        info_text = f"""<b>Детальна інформація про UPGRADE21 STUDIO:</b>

 <b>Що включає підписка:</b>
• Персоналізовані тренування під ваші цілі та фізичну підготовку
• Доступ до приватної спільноти однодумців 
• Підтримка професійних тренерів 24/7
• Прогрес-трекінг та мотивація від команди
• Ексклюзивний контент та майстер-класи
• Харчування та рекомендації від дієтологів

 <b>Умови підписки:</b>
• Вартість: {settings.subscription_price:.0f} {settings.subscription_currency.upper()} на місяць
• Автоматичне продовження кожен місяць
• Можливість призупинити або скасувати в будь-який час
• Безпечна оплата через Stripe

 <b>Безпека:</b>
• Захищені платежі через світову систему Stripe
• Ваші дані під надійним захистом
• Можливість керувати підпискою через бот

Готові приєднатися до нашої фітнес-спільноти? """

        # Клавіатура тільки з кнопкою оформлення підписки (без "Дізнатися більше")
        keyboard = [
            [InlineKeyboardButton("Оформити підписку", callback_data="create_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=info_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def set_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Встановити нагадування про підписку"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user:
            await query.edit_message_text("Користувач не знайдений")
            return
        
        # Встановлюємо стан "нагадати пізніше"
        DatabaseManager.update_user_state(query.from_user.id, UserState.REMINDER_SET)
        
        await query.edit_message_text(
            f"⏰ <b>Нагадування встановлено!</b>\n\n"
            f"Ми нагадаємо вам про підписку через 24 години.\n\n"
            f"У будь-який час ви можете оформити підписку, написавши /start\n\n"
            f"Дякуємо за інтерес до UPGRADE21 STUDIO! ",
            parse_mode='HTML'
        )
        
        # Плануємо нагадування (якщо є планувальник завдань)
        if hasattr(self, 'task_scheduler') and self.task_scheduler:
            await self.task_scheduler.schedule_subscription_reminder(user.id, hours=24)

    async def update_user_access_status(self, user_id: int, has_access: bool):
        """Оновити статус доступу користувача при втраті/поновленні підписки"""
        try:
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == user_id).first()
                if db_user:
                    if not has_access:
                        # Втрата доступу - скидаємо всі статуси
                        db_user.subscription_active = False
                        db_user.joined_channel = False
                        db_user.joined_chat = False
                        logger.info(f"Скинуто статуси доступу для користувача {user_id}")
                    else:
                        # Поновлення доступу
                        db_user.subscription_active = True
                        db_user.subscription_paused = False
                        db_user.subscription_cancelled = False
                        db_user.subscription_end_date = None
                        logger.info(f"Поновлено статуси доступу для користувача {user_id}")
                    
                    db.commit()
                else:
                    logger.error(f"Користувач {user_id} не знайдений при оновленні статусу доступу")
        except Exception as e:
            logger.error(f"Помилка при оновленні статусу доступу для користувача {user_id}: {e}")

    def setup_handlers(self):
        """Налаштування обробників"""
        app = self.application
        
        # Команди
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("admin", self.admin_command))
        app.add_handler(CommandHandler("set_admin", self.set_admin_command))
        app.add_handler(CommandHandler("get_chat_info", self.get_chat_info_command))
        app.add_handler(CommandHandler("chat_id", self.chat_id_command))
        app.add_handler(CommandHandler("forward_info", self.forward_info_command))
        app.add_handler(CommandHandler("manage_links", self.manage_links_command))
        app.add_handler(CommandHandler("create_invite", self.create_invite_command))
        app.add_handler(CommandHandler("list_invites", self.list_invites_command))
        
        # Callback запити
        app.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Обробник запитів на приєднання до каналів/чатів
        from telegram.ext import ChatJoinRequestHandler
        app.add_handler(ChatJoinRequestHandler(self.handle_chat_join_request))
        
        # Обробник текстових повідомлень для опитування
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_text_message
        ))
        
        # Загальний обробник всіх повідомлень для логування (з низьким пріоритетом)
        app.add_handler(MessageHandler(filters.ALL, self.log_all_messages), group=1)
        
        # Обробник помилок
        app.add_error_handler(self.error_handler)
    
    def initialize_sync(self):
        """Синхронна ініціалізація бота"""
        # Створюємо таблиці бази даних
        create_tables()
        
        # Створюємо request з налаштованими timeout
        request = HTTPXRequest(
            connect_timeout=10.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=10.0
        )
        
        # Створюємо додаток з налаштованим request
        self.application = Application.builder().token(settings.telegram_bot_token).request(request).build()
        self.bot = self.application.bot
        
        # Ініціалізуємо планувальник задач
        self.task_scheduler = TaskScheduler(self.bot, bot_instance=self)
        
        # Налаштовуємо обробники
        self.setup_handlers()
        
        logger.info("Бот ініціалізовано")
    
    async def initialize(self):
        """Ініціалізація бота"""
        # Створюємо таблиці бази даних
        create_tables()
        
        # Створюємо request з налаштованими timeout
        request = HTTPXRequest(
            connect_timeout=10.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=10.0
        )
        
        # Створюємо додаток з налаштованим request
        self.application = Application.builder().token(settings.telegram_bot_token).request(request).build()
        self.bot = self.application.bot
        
        # Ініціалізуємо application
        await self.application.initialize()
        
        # Ініціалізуємо планувальник задач з посиланням на bot_instance
        self.task_scheduler = TaskScheduler(self.bot, bot_instance=self)
        
        # Налаштовуємо обробники
        self.setup_handlers()
        
        # Запускаємо планувальник
        if self.task_scheduler:
            await self.task_scheduler.start()
            logger.info("Планувальник задач запущено")
        
        logger.info("Бот ініціалізовано")
    
    def start_polling(self):
        """Запуск бота в режимі polling"""
        try:
            if not self.application:
                # Синхронна ініціалізація
                self.initialize_sync()
            
            logger.info("Запуск бота...")
            
            # Додаємо post_init callback для запуску планувальника
            async def post_init(application):
                if self.task_scheduler:
                    await self.task_scheduler.start()
                    logger.info("Планувальник задач запущено")
            
            self.application.post_init = post_init
            
            # Запускаємо бот синхронно
            self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Помилка при запуску бота: {e}", exc_info=True)
        finally:
            # Зупиняємо планувальник при завершенні
            if self.task_scheduler:
                try:
                    self.task_scheduler.stop_sync()
                except RuntimeError as e:
                    # Ignore "Event loop is closed" error on shutdown
                    if "closed" not in str(e).lower():
                        logger.error(f"Помилка при зупинці планувальника: {e}")
                except Exception as e:
                    logger.error(f"Помилка при зупинці планувальника: {e}")
    
    async def start_webhook(self):
        """Запуск бота в режимі webhook"""
        if not self.application:
            await self.initialize()
        
        logger.info(f"Запуск бота з webhook на {settings.webhook_host}:{settings.webhook_port}")
        
        await self.application.run_webhook(
            listen=settings.webhook_host,
            port=settings.webhook_port,
            webhook_url=settings.webhook_url + settings.webhook_path,
            drop_pending_updates=True
        )


# Глобальний екземпляр бота
bot_instance = UpgradeStudioBot()


def main():
    """Головна функція"""
    try:
        bot_instance.start_polling()
    except KeyboardInterrupt:
        logger.info("Отримано сигнал переривання")
    finally:
        # Очищуємо ресурси
        if bot_instance.task_scheduler:
            try:
                bot_instance.task_scheduler.stop_sync()
            except:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот зупинено")