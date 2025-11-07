"""
Основний файл телеграм бота upgrade studio
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.error import TelegramError

from config import settings, UserState, Messages, Buttons
from database import DatabaseManager, User, create_tables
from payments import StripeManager
from tasks import TaskScheduler
from bot.keyboards import (
    get_main_menu_keyboard, get_welcome_keyboard, get_survey_goals_keyboard,
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
            
            # Спробуємо очистити останні 15 повідомлень
            for i in range(1, 16):
                try:
                    if current_message_id:
                        message_id_to_process = current_message_id - i
                        if message_id_to_process > 0:
                            # Спочатку пробуємо видалити повідомлення
                            try:
                                # Отримуємо інформацію про повідомлення щоб перевірити тип
                                chat_member = await self.bot.get_chat_member(chat_id, self.bot.id)
                                if chat_member.status in ['administrator', 'creator']:
                                    # Якщо бот має права адміна, може видаляти повідомлення
                                    await self.bot.delete_message(
                                        chat_id=chat_id,
                                        message_id=message_id_to_process
                                    )
                                    logger.debug(f"Видалено повідомлення {message_id_to_process}")
                                else:
                                    # Якщо немає прав - тільки очищаємо кнопки
                                    await self.bot.edit_message_reply_markup(
                                        chat_id=chat_id,
                                        message_id=message_id_to_process,
                                        reply_markup=None
                                    )
                                    logger.debug(f"Очищено кнопки повідомлення {message_id_to_process}")
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
        telegram_user = DatabaseManager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Перевіряємо параметри start команди
        if context.args:
            start_param = context.args[0]
            if start_param == "payment_success":
                await update.message.reply_text(
                    "🎉 **Дякуємо за оплату!**\n\n"
                    "Ваша підписка успішно оформлена. Зараз ви отримаєте доступ до приватних каналів та чатів.\n\n"
                    "Ласкаво просимо до UPGRADE STUDIO! 💪",
                    parse_mode='Markdown'
                )
                return
            elif start_param == "payment_cancelled":
                await update.message.reply_text(
                    "😔 **Оплата скасована**\n\n"
                    "Нічого страшного! Ви можете оформити підписку пізніше.\n\n"
                    "Напишіть /start щоб повернутися до головного меню.",
                    parse_mode='Markdown'
                )
                return
        
        # Логіка для існуючих користувачів
        if telegram_user.subscription_active:
            # Користувач з активною підпискою - показуємо головне меню
            await self.show_main_menu(update, context)
        elif telegram_user.goals or telegram_user.injuries:
            # Користувач пройшов опитування, але немає підписки - показуємо пропозицію підписки
            await update.message.reply_text(
                f"Привіт знову, {user.first_name}! 👋\n\n"
                f"Я пам'ятаю наше знайомство. Ви готові оформити підписку і приєднатися до UPGRADE STUDIO?",
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
            text=Messages.SURVEY_GOALS,
            reply_markup=get_survey_goals_keyboard()
        )
    

    
    async def handle_goal_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка вибору цілей"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update)
        
        goal_data = query.data.replace("goal_", "")
        
        # Знаходимо повний текст цілі за ключовим словом
        full_goal = self.find_goal_by_key(goal_data)
        DatabaseManager.save_survey_data(query.from_user.id, goals=full_goal)
        DatabaseManager.update_user_state(query.from_user.id, UserState.SURVEY_INJURIES)
        
        await query.edit_message_text(
            text=Messages.SURVEY_INJURIES,
            reply_markup=get_survey_injuries_keyboard(),
            parse_mode='Markdown'
        )
    
    async def handle_injury_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка вибору травм/обмежень"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update)
        
        injury_data = query.data.replace("injury_", "")
        
        if injury_data == "Так":
            # Просимо користувача описати травму детальніше
            DatabaseManager.update_user_state(query.from_user.id, UserState.SURVEY_INJURIES_CUSTOM)
            
            await query.edit_message_text(
                text="Опиши, будь ласка, свою травму детальніше.",
                parse_mode='Markdown'
            )
        else:  # "Ні"
            # Зберігаємо вибір "Немає травм" і переходимо до оформлення підписки
            DatabaseManager.save_survey_data(query.from_user.id, injuries="Немає травм")
            DatabaseManager.update_user_state(query.from_user.id, UserState.SUBSCRIPTION_OFFER)
            
            await self.show_subscription_offer(query.from_user.id, query)
    
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

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати головне меню"""
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        if update.callback_query:
            await update.callback_query.answer()
            await self.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🏠 Головне меню",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "🏠 Головне меню",
                reply_markup=get_main_menu_keyboard()
            )
    
    async def handle_subscription_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Керування підпискою"""
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        user_id = update.effective_user.id
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        if not user:
            error_text = "❌ Користувача не знайдено"
            if update.callback_query:
                await update.callback_query.message.reply_text(error_text)
            else:
                await update.message.reply_text(error_text)
            return
        
        await self._show_subscription_management_menu(user_id, user)
    
    async def handle_subscription_management_from_callback(self, user_id: int):
        """Керування підпискою через callback (без Update об'єкта)"""
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        if not user:
            await self.bot.send_message(
                chat_id=user_id,
                text="❌ Користувача не знайдено"
            )
            return
        
        await self._show_subscription_management_menu(user_id, user)
    
    async def _show_subscription_management_menu(self, user_id: int, user):
        """Показати меню керування підпискою"""
        keyboard = get_subscription_management_keyboard(
            subscription_active=user.subscription_active,
            subscription_paused=user.subscription_paused,
            joined_channel=user.joined_channel,
            joined_chat=user.joined_chat
        )
        
        # Формуємо текст з інформацією про підписку
        if user.subscription_active:
            # Використовуємо дані з бази даних
            subscription_end_date = user.subscription_end_date
            next_billing_date = user.next_billing_date
            
            if user.is_admin() and (user.stripe_subscription_id or "").startswith("sub_test_"):
                # Для тестових підписок адміна
                if user.subscription_paused:
                    text = "⏸️ **Ваша підписка призупинена** (тестовий режим)\n\n"
                    if subscription_end_date:
                        text += f"📅 Дія до: {subscription_end_date.strftime('%d.%m.%Y')}\n"
                    text += "Автоплатіж: неактивний"
                elif user.subscription_cancelled:
                    text = f"❌ **Підписка скасована** (тестовий режим)\n\n"
                    if subscription_end_date:
                        text += f"📅 Закінчення підписки: {subscription_end_date.strftime('%d.%m.%Y')}\n"
                    text += "Автоплатіж: неактивний"
                else:
                    text = f"✅ **Ваша підписка активна** (тестовий режим)\n\n"
                    if next_billing_date:
                        text += f"📅 Наступне поновлення: {next_billing_date.strftime('%d.%m.%Y')}\n"
                    text += "Автоплатіж: активний"
            else:
                # Для реальних підписок
                autopay_status = "неактивний"
                
                # Перевіряємо статус автоплатежу через Stripe (якщо потрібно)
                if user.stripe_subscription_id and not user.subscription_cancelled and not user.subscription_paused:
                    try:
                        subscription_info = await StripeManager.get_subscription(user.stripe_subscription_id)
                        if subscription_info and not subscription_info.get('cancel_at_period_end', False):
                            autopay_status = "активний"
                    except Exception as e:
                        logger.warning(f"Не вдалося отримати статус автоплатежу: {e}")
                        autopay_status = "активний"  # Припускаємо активний, якщо не скасований
                
                if user.subscription_paused:
                    text = f"⏸️ **Ваша підписка призупинена**\n\n"
                    if subscription_end_date:
                        text += f"📅 Дія до: {subscription_end_date.strftime('%d.%m.%Y')}\n"
                    text += "Автоплатіж: неактивний"
                elif user.subscription_cancelled:
                    text = f"❌ **Підписка скасована**\n\n"
                    if subscription_end_date:
                        text += f"📅 Закінчення підписки: {subscription_end_date.strftime('%d.%m.%Y')}\n"
                    text += "Автоплатіж: неактивний"
                else:
                    text = f"✅ **Ваша підписка активна**\n\n"
                    if next_billing_date:
                        text += f"📅 Наступне поновлення: {next_billing_date.strftime('%d.%m.%Y')}\n"
                    text += f"Автоплатіж: {autopay_status}"
        else:
            text = "❌ У вас немає активної підписки"
        
        # Відправляємо повідомлення
        await self.bot.send_message(
            chat_id=user_id, 
            text=text, 
            reply_markup=keyboard, 
            parse_mode='Markdown'
        )
    
    async def handle_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати дашборд користувача"""
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        user_id = update.effective_user.id
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        # Визначаємо, чи це callback query чи звичайне повідомлення
        is_callback = update.callback_query is not None
        
        if not user:
            error_text = "❌ Користувача не знайдено"
            if is_callback:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
            return
        
        if not user.subscription_active:
            # Користувач без активної підписки
            dashboard_text = (
                "📊 **Дашборд недоступний**\n\n"
                "❌ Для доступу до дашборду потрібна активна підписка\n\n"
                "💡 Оформіть підписку, щоб отримати:\n"
                "• Детальну статистику тренувань\n"
                "• Прогрес-трекінг\n"
                "• Персональні рекомендації\n"
                "• Доступ до спільноти\n\n"
                "Натисніть /start для оформлення підписки"
            )
            
            if is_callback:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(dashboard_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(dashboard_text, parse_mode='Markdown')
            return
        
        # Рахуємо дні членства
        days_member = (datetime.utcnow() - user.member_since).days
        
        # Додаємо часову мітку для відстеження оновлень
        current_time = datetime.now().strftime("%H:%M")
        
        dashboard_text = f"""📊 **Ваша статистика** (оновлено о {current_time})

👤 Ім'я: {user.first_name or 'Не вказано'}
📅 З нами: {days_member} днів
💪 Виконано тренувань: {user.workouts_completed}
✅ Статус підписки: {'Активна' if user.subscription_active else 'Неактивна'}
🎯 Ваша ціль: {user.goals[:50] + '...' if user.goals and len(user.goals) > 50 else user.goals or 'Не вказана'}

Продовжуйте тренуватися! 🔥"""
        
        if is_callback:
            await update.callback_query.answer("📊 Статистика оновлена!")
            try:
                await update.callback_query.edit_message_text(
                    dashboard_text,
                    parse_mode='Markdown',
                    reply_markup=get_dashboard_keyboard()
                )
            except Exception as e:
                # Якщо не вдалося відредагувати (наприклад, контент ідентичний), просто відповідаємо
                logger.warning(f"Не вдалося відредагувати повідомлення дашборду: {e}")
        else:
            await update.message.reply_text(
                dashboard_text,
                parse_mode='Markdown',
                reply_markup=get_dashboard_keyboard()
            )
    
    async def handle_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати контакти підтримки"""
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        support_text = """
💬 **Підтримка**

Якщо у вас виникли питання або потрібна допомога, зв'яжіться з нашою командою підтримки.

Ми завжди готові допомогти! 😊
"""
        
        if update.callback_query:
            await self.bot.send_message(
                chat_id=update.effective_chat.id,
                text=support_text,
                parse_mode='Markdown',
                reply_markup=get_support_keyboard()
            )
        else:
            await update.message.reply_text(
                support_text,
                parse_mode='Markdown',
                reply_markup=get_support_keyboard()
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Загальний обробник callback запитів"""
        query = update.callback_query
        data = query.data
        
        if data.startswith("goal_"):
            await self.handle_goal_selection(update, context)
        elif data.startswith("injury_"):
            await self.handle_injury_selection(update, context)
        elif data == "create_subscription":
            await self.create_subscription(update, context)
        elif data == "more_info":
            await self.show_more_info(update, context)
        elif data == "remind_later":
            await self.set_reminder(update, context)
        elif data == "main_menu":
            await self.show_main_menu(update, context)
        elif data == "pause_subscription":
            await self.pause_subscription(update, context)
        elif data == "resume_subscription":
            await self.resume_subscription(update, context)
        elif data == "cancel_subscription":
            await self.cancel_subscription(update, context)
        elif data == "refresh_dashboard":
            await self.handle_dashboard(update, context)
        elif data == "join_channel_access":
            await self.handle_channel_access_request(update, context)
        elif data == "join_chat_access":
            await self.handle_chat_access_request(update, context)
        elif data == "go_to_channel":
            await self.handle_go_to_channel(update, context)
        elif data == "go_to_chat":
            await self.handle_go_to_chat(update, context)
        elif data == "channel_joined":
            await self.handle_channel_joined(update, context)
        elif data == "chat_joined":
            await self.handle_chat_joined(update, context)
        elif data.startswith("join_"):
            await self.handle_join_request(update, context)
        else:
            await query.answer("Функція в розробці 🚧")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробка текстових повідомлень (для довільних відповідей в опитуванні)"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            return
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update)
        
        user_text = update.message.text
        
        if user.state == UserState.SURVEY_INJURIES_CUSTOM:
            # Зберігаємо опис травми
            DatabaseManager.save_survey_data(update.effective_user.id, injuries=f"Травма: {user_text}")
            DatabaseManager.update_user_state(update.effective_user.id, UserState.SUBSCRIPTION_OFFER)
            
            await update.message.reply_text(
                f"✅ Дякую за інформацію! Це буде враховано при складанні програми тренувань.",
                parse_mode='Markdown'
            )
            
            # Показуємо пропозицію підписки
            await self.show_subscription_offer(update.effective_user.id)
    
    async def show_subscription_offer(self, telegram_id: int, query=None):
        """Показати пропозицію підписки після завершення опитування"""
        user = DatabaseManager.get_user_by_telegram_id(telegram_id)
        if not user:
            return
        
        # Формуємо персоналізоване повідомлення
        greeting = f"Чудово, {user.first_name}! 🎉"
        
        # Додаємо інформацію про цілі та особливості (коротко)
        personal_info = ""
        if user.goals:
            personal_info += f"\n🎯 Ваша ціль: {user.goals[:50]}{'...' if len(user.goals) > 50 else ''}"
        if user.injuries and "Немає" not in user.injuries:
            personal_info += f"\n🩺 Врахуємо: {user.injuries[:50]}{'...' if len(user.injuries) > 50 else ''}"
        
        # Форматуємо основне повідомлення про підписку
        price_formatted = f"{settings.subscription_price/100:.0f} {settings.subscription_currency.upper()}"
        
        offer_text = f"""{greeting}

Дякую за відповіді! Тепер я краще розумію ваші потреби.{personal_info}

{Messages.SUBSCRIPTION_OFFER.format(price=price_formatted, currency=settings.subscription_currency.upper())}"""
        
        if query:
            # Якщо це callback query, редагуємо повідомлення
            await query.edit_message_text(
                text=offer_text,
                reply_markup=get_subscription_offer_keyboard(),
                parse_mode='Markdown'
            )
        else:
            # Якщо це звичайне повідомлення, надсилаємо нове
            await self.bot.send_message(
                chat_id=telegram_id,
                text=offer_text,
                reply_markup=get_subscription_offer_keyboard(),
                parse_mode='Markdown'
            )
    
    async def create_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Створити підписку через Stripe"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update)
        
        user_id = query.from_user.id
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        
        # Перевіряємо, чи це адмін (тестовий режим)
        if user and user.is_admin():
            await query.edit_message_text("🧪 Тестовий режим для адміна - імітуємо успішну оплату...")
            
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
        bot_username = "upgrade_std_bot"  # Правильний username бота
        success_url = f"https://t.me/{bot_username}?start=payment_success"
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
            
            payment_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатити підписку", url=checkout_data['url'])]
            ])
            
            await query.edit_message_text(
                text="💳 **Оформлення підписки UPGRADE STUDIO**\n\n"
                     "🎯 Натисніть кнопку нижче для безпечної оплати через Stripe\n\n"
                     "🔒 Всі платежі захищені банківським рівнем безпеки\n"
                     "� Оплата відкриється прямо в Telegram",
                reply_markup=payment_keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Виникла помилка при створенні платежу. Спробуйте пізніше або зверніться до підтримки."
            )
    
    async def pause_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Призупинити підписку"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Активна підписка не знайдена"
            )
            return
        
        # Перевіряємо, чи це адмін з тестовими даними
        if user.is_admin() and user.stripe_subscription_id.startswith("sub_test_"):
            # Імітуємо призупинення для адміна
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = True
                    db_user.subscription_cancelled = False  # Скасовуємо статус скасування при призупиненні
                    # При призупиненні скидаємо статуси приєднання
                    db_user.joined_channel = False
                    db_user.joined_chat = False
                    db.commit()
                    logger.info(f"Оновлено subscription_paused=True та скинуто joined статуси для користувача {query.from_user.id} (тестовий режим)")
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="⏸️ **Підписка призупинена** (тестовий режим адміна)\n\n"
                     "Ваша тестова підписка була призупинена. "
                     "Ви можете поновити її в будь-який час.",
                parse_mode='Markdown'
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
            return
        
        # Звичайна обробка для реальних користувачів
        success = await StripeManager.pause_subscription(user.stripe_subscription_id)
        
        if success:
            # Оновлюємо статус в базі
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = True
                    db_user.subscription_cancelled = False  # Скасовуємо статус скасування при призупиненні
                    # При призупиненні скидаємо статуси приєднання
                    db_user.joined_channel = False
                    db_user.joined_chat = False
                    db.commit()
                    logger.info(f"Оновлено subscription_paused=True та скинуто joined статуси для користувача {query.from_user.id}")
                else:
                    logger.error(f"Користувач {query.from_user.id} не знайдений в базі при призупиненні підписки")
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="⏸️ Підписка призупинена"
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Помилка при призупиненні підписки"
            )
    
    async def resume_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поновити підписку"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Підписка не знайдена"
            )
            return
        
        # Перевіряємо, чи це адмін з тестовими даними
        if user.is_admin() and user.stripe_subscription_id.startswith("sub_test_"):
            # Імітуємо поновлення для адміна
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = False  # Скасовуємо статус скасування
                    db_user.subscription_end_date = None  # Очищаємо дату закінчення
                    db.commit()
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="▶️ **Підписка поновлена** (тестовий режим адміна)\n\n"
                     "Ваша тестова підписка була поновлена і знову активна.",
                parse_mode='Markdown'
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
            return
        
        # Звичайна обробка для реальних користувачів
        success = await StripeManager.resume_subscription(user.stripe_subscription_id)
        
        if success:
            # Оновлюємо статус в базі
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = False  # Скасовуємо статус скасування
                    db_user.subscription_end_date = None  # Очищаємо дату закінчення
                    db.commit()
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="▶️ Підписка поновлена"
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Помилка при поновленні підписки"
            )
    
    async def cancel_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Скасувати підписку"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.stripe_subscription_id:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Активна підписка не знайдена"
            )
            return
        
        # Перевіряємо, чи це адмін з тестовими даними
        if user.is_admin() and user.stripe_subscription_id.startswith("sub_test_"):
            # Імітуємо скасування для адміна з підтримкою доступу до кінця періоду
            # Встановлюємо дату закінчення через 30 днів (тестовий період)
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
            
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    # Не видаляємо активність негайно, але позначаємо як скасовану
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = True
                    db_user.subscription_end_date = subscription_end_date
                    db.commit()
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text=f"❌ **Підписка скасована** (тестовий режим адміна)\n\n"
                     f"Ваша підписка скасована, але доступ залишається до {subscription_end_date.strftime('%d.%m.%Y')}.\n\n"
                     f"Після цієї дати доступ до приватних каналів буде заблокований.\n\n"
                     f"Ви можете оформити нову підписку в будь-який час через /start",
                parse_mode='Markdown'
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
            return
        
        # Звичайна обробка для реальних користувачів
        # Спочатку отримуємо інформацію про підписку з Stripe для визначення дати закінчення
        try:
            subscription_info = await StripeManager.get_subscription_info(user.stripe_subscription_id)
            if subscription_info and 'current_period_end' in subscription_info:
                # Конвертуємо timestamp в datetime
                subscription_end_date = datetime.fromtimestamp(subscription_info['current_period_end'])
            else:
                # Fallback: додаємо 30 днів від поточної дати
                subscription_end_date = datetime.utcnow() + timedelta(days=30)
        except Exception as e:
            logger.error(f"Помилка отримання інформації про підписку: {e}")
            subscription_end_date = datetime.utcnow() + timedelta(days=30)
        
        success = await StripeManager.cancel_subscription(user.stripe_subscription_id)
        
        if success:
            # Оновлюємо статус в базі - не видаляємо активність до кінця періоду
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                if db_user:
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = True
                    db_user.subscription_end_date = subscription_end_date
                    db.commit()
            
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text=f"❌ **Підписка скасована**\n\n"
                     f"Ваша підписка скасована, але доступ залишається до {subscription_end_date.strftime('%d.%m.%Y')}.\n\n"
                     f"Після цієї дати доступ до приватних каналів буде заблокований.\n\n"
                     f"Дякуємо, що були з нами! Ви можете оформити нову підписку в будь-який час через /start",
                parse_mode='Markdown'
            )
            
            # Автоматично відкриваємо меню керування підпискою
            await self.handle_subscription_management_from_callback(query.from_user.id)
        else:
            await self.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Помилка при скасуванні підписки"
            )
    
    async def handle_successful_payment(self, telegram_id: int):
        """Обробити успішну оплату - надіслати кнопки для приєднання"""
        try:
            user = DatabaseManager.get_user_by_telegram_id(telegram_id)
            if not user:
                return
            
            # Оновлюємо статус підписки - активуємо та скидаємо всі негативні статуси
            with DatabaseManager() as db:
                db_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if db_user:
                    db_user.subscription_active = True
                    db_user.subscription_paused = False
                    db_user.subscription_cancelled = False
                    db_user.subscription_end_date = None  # Очищаємо дату закінчення
                    db.commit()
                    logger.info(f"Оновлено статус підписки для користувача {telegram_id}")
            
            # Скасовуємо всі нагадування про підписку, оскільки оплата пройшла
            cancelled_count = DatabaseManager.cancel_subscription_reminders_if_active(telegram_id)
            if cancelled_count > 0:
                logger.info(f"Скасовано {cancelled_count} нагадувань про підписку для користувача {telegram_id}")
            
            # Надсилаємо подяку
            await self.bot.send_message(
                chat_id=telegram_id,
                text=Messages.PAYMENT_SUCCESS
            )
            
            # Надсилаємо повідомлення про успішну оплату спочатку
            await self.bot.send_message(
                chat_id=telegram_id,
                text="🎉 **Оплата успішна!**\n\n"
                     "Дякуємо! Ваша підписка активована.\n"
                     "Тепер ви маєте доступ до всіх можливостей UPGRADE STUDIO! 💪",
                parse_mode='Markdown'
            )
            
            # Отримуємо активні посилання з бази
            invite_links = DatabaseManager.get_active_invite_links()
            
            if invite_links:
                # Створюємо кнопки для приєднання
                keyboard = []
                for link in invite_links:
                    if link.chat_type == "channel":
                        button_text = f"🔒 Приєднатися до каналу"
                    else:
                        button_text = f"💬 Приєднатися до чату"
                    
                    keyboard.append([InlineKeyboardButton(
                        text=button_text,
                        url=link.invite_link
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="📱 Ось ваші посилання:\n\n"
                         "Приєднуйтеся до наших приватних спільнот! 💪\n\n"
                         "❗️ Важливо: приєднайтеся протягом доби, інакше буду нагадувати 😊",
                    reply_markup=reply_markup
                )
            else:
                # Якщо немає посилань у базі, створюємо кнопки з settings
                keyboard = [
                    [InlineKeyboardButton(
                        text="🔒 Приєднатися до каналу",
                        url=f"https://t.me/{settings.private_channel_id}"
                    )],
                    [InlineKeyboardButton(
                        text="💬 Приєднатися до чату", 
                        url=f"https://t.me/{settings.private_chat_id}"
                    )]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="📱 Ось ваші посилання:\n\n"
                         "Приєднуйтеся до наших приватних спільнот! 💪\n\n"
                         "❗️ Важливо: приєднайтеся протягом доби, інакше буду нагадувати 😊",
                    reply_markup=reply_markup
                )
            
            # Плануємо нагадування про приєднання (якщо користувач не приєднається протягом доби)
            if self.task_scheduler:
                await self.task_scheduler.schedule_join_reminders(user.id)
            
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
                await query.edit_message_text("❌ Неправильний формат запиту")
                return
            
            chat_type = data_parts[1]  # "channel" або "group"
            chat_id = data_parts[2]    # ID чату
            
            # Перевіряємо, чи користувач має активну підписку
            user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
            if not user or not user.subscription_active:
                await query.edit_message_text("❌ Для приєднання потрібна активна підписка")
                return
            
            # Отримуємо посилання з бази
            invite_link_obj = DatabaseManager.get_invite_link_by_chat(chat_id, chat_type)
            
            if invite_link_obj and invite_link_obj.is_active:
                # Створюємо кнопку для приєднання
                chat_name = invite_link_obj.chat_title or ("канал" if chat_type == "channel" else "чат")
                
                join_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        f"� Приєднатися до {chat_name}",
                        url=invite_link_obj.invite_link
                    )]
                ])
                
                await query.edit_message_text(
                    f"🎉 **Готово!**\n\n"
                    f"Натисніть кнопку нижче для приєднання до {chat_name}\n\n"
                    f"📋 Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                    f"⚠️ Не передавайте це посилання іншим користувачам",
                    reply_markup=join_keyboard,
                    parse_mode='Markdown'
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
                            f"� Приєднатися до {chat_info.title}",
                            url=invite_link.invite_link
                        )]
                    ])
                    
                    await query.edit_message_text(
                        f"🎉 **Готово!**\n\n"
                        f"Натисніть кнопку нижче для приєднання до {chat_info.title}\n\n"
                        f"📋 Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                        f"⚠️ Не передавайте це посилання іншим користувачам",
                        reply_markup=join_keyboard,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    logger.error(f"Помилка створення invite link: {e}")
                    await query.edit_message_text(
                        f"❌ Не вдалося створити посилання для приєднання. "
                        f"Зверніться до адміністратора або спробуйте пізніше."
                    )
                    
        except Exception as e:
            logger.error(f"Помилка обробки запиту на приєднання: {e}")
            await query.edit_message_text("❌ Виникла помилка. Спробуйте пізніше.")
    
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
                    
                    # Створюємо запис про тестовий платіж
                    from database.models import Payment
                    payment = Payment(
                        user_id=user.id,
                        amount=settings.subscription_price,
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
            await update.message.reply_text("❌ У вас немає прав адміністратора")
            return
        
        admin_text = """
🔧 **Адмін панель**

Доступні команди:
• `/admin` - показати цю панель
• `/set_admin <telegram_id>` - надати права адміна користувачу

**Особливості адмін режиму:**
• Тестова оплата (без Stripe)
• Доступ до всіх функцій
• Імітація успішних платежів
"""
        
        await update.message.reply_text(admin_text, parse_mode='Markdown')
    
    async def set_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Встановити роль адміна користувачу"""
        # Перевіряємо, чи користувач сам є адміном або це власник бота
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or (not user.is_admin() and update.effective_user.id != int(settings.admin_chat_id)):
            await update.message.reply_text("❌ У вас немає прав для цієї команди")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Вкажіть Telegram ID користувача: `/set_admin 123456789`")
            return
        
        try:
            target_telegram_id = int(context.args[0])
            success = DatabaseManager.set_user_role(target_telegram_id, "admin")
            
            if success:
                await update.message.reply_text(f"✅ Користувач {target_telegram_id} отримав права адміна")
            else:
                await update.message.reply_text(f"❌ Користувач {target_telegram_id} не знайдений")
                
        except ValueError:
            await update.message.reply_text("❌ Невірний формат Telegram ID")
    
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
        
        username_display = f"@{chat.username}" if chat.username else "немає"
        user_username_display = f"@{user.username}" if user.username else "немає"
        
        info = f"""🏷 Інформація про чат:
• ID: {chat.id}
• Тип: {chat_type_names.get(chat.type, chat.type)}
• Назва: {chat.title or 'N/A'}
• Username: {username_display}

👤 Ваша інформація:
• ID: {user.id}
• Username: {user_username_display}
• Ім'я: {user.first_name}

💡 Підказка:
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
            await update.message.reply_text("❌ Доступ заборонено. Ця команда тільки для адміністраторів.")
            return
        
        links = DatabaseManager.get_active_invite_links()
        
        if not links:
            await update.message.reply_text(
                "📋 Поточні посилання відсутні.\n\n"
                "Використовуйте:\n"
                "• `/create_invite <chat_id> <chat_type> <invite_link> [назва]` - створити посилання\n"
                "• `/list_invites` - показати всі посилання",
                parse_mode='Markdown'
            )
            return
        
        message = "📋 **Активні посилання:**\n\n"
        for link in links:
            status = "✅" if link.is_active else "❌"
            message += f"{status} **{link.chat_title or 'Без назви'}**\n"
            message += f"   • ID: `{link.chat_id}`\n"
            message += f"   • Тип: {link.chat_type}\n"
            message += f"   • Створено: {link.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        message += "\n💡 Команди:\n"
        message += "• `/create_invite` - створити нове посилання\n"
        message += "• `/list_invites` - детальний список"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def create_invite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Створити invite посилання для чату/каналу"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or not user.is_admin():
            await update.message.reply_text("❌ Доступ заборонено. Ця команда тільки для адміністраторів.")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "❌ Неправильний формат команди.\n\n"
                "**Використання:**\n"
                "`/create_invite <chat_id> <chat_type> <invite_link> [назва]`\n\n"
                "**Приклад:**\n"
                "`/create_invite -1002747224769 channel https://t.me/+AbCdEfGhIjKl Приватний канал`",
                parse_mode='Markdown'
            )
            return
        
        try:
            chat_id = context.args[0]
            chat_type = context.args[1]
            invite_link = context.args[2]
            chat_title = " ".join(context.args[3:]) if len(context.args) > 3 else None
            
            if chat_type not in ["channel", "group"]:
                await update.message.reply_text("❌ Тип чату має бути 'channel' або 'group'")
                return
            
            # Створюємо або оновлюємо посилання
            link_obj = DatabaseManager.create_invite_link(
                chat_id=chat_id,
                chat_type=chat_type,
                invite_link=invite_link,
                chat_title=chat_title
            )
            
            await update.message.reply_text(
                f"✅ Посилання успішно створено!\n\n"
                f"**Деталі:**\n"
                f"• Chat ID: `{link_obj.chat_id}`\n"
                f"• Тип: {link_obj.chat_type}\n"
                f"• Назва: {link_obj.chat_title or 'Не вказана'}\n"
                f"• Посилання: `{link_obj.invite_link}`",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Помилка створення посилання: {e}")
            await update.message.reply_text("❌ Помилка при створенні посилання. Перевірте параметри.")
    
    async def list_invites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати детальний список всіх посилань"""
        user = DatabaseManager.get_user_by_telegram_id(update.effective_user.id)
        if not user or not user.is_admin():
            await update.message.reply_text("❌ Доступ заборонено. Ця команда тільки для адміністраторів.")
            return
        
        links = DatabaseManager.get_active_invite_links()
        
        if not links:
            await update.message.reply_text("📋 Посилання відсутні.")
            return
        
        for link in links:
            status = "✅ Активне" if link.is_active else "❌ Неактивне"
            message = f"**{link.chat_title or 'Без назви'}**\n\n"
            message += f"**Статус:** {status}\n"
            message += f"**Chat ID:** `{link.chat_id}`\n"
            message += f"**Тип:** {link.chat_type}\n"
            message += f"**Посилання:** `{link.invite_link}`\n"
            message += f"**Створено:** {link.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += f"**Оновлено:** {link.updated_at.strftime('%d.%m.%Y %H:%M')}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
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
            await update.message.reply_text("❌ Перешліть повідомлення з каналу/групи для отримання ID")
            return
        
        forward_chat = update.message.forward_from_chat
        
        info = f"""📨 Інформація про пересланий чат:
• ID: {forward_chat.id}
• Тип: {forward_chat.type}
• Назва: {forward_chat.title or 'N/A'}
• Username: @{forward_chat.username or 'немає'}

💡 Використовуйте цей ID в .env файлі:
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
                    "😅 Вибачте, сталася помилка. Спробуйте ще раз або зверніться до підтримки."
                )
            except Exception as e:
                logger.error(f"Не вдалося надіслати повідомлення про помилку: {e}")
    
    
    async def handle_channel_access_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити запит доступу до каналу"""
        query = update.callback_query
        await query.answer()
        
        # Перевіряємо підписку
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user or not user.subscription_active:
            await query.edit_message_text("❌ Для доступу потрібна активна підписка")
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
            await query.edit_message_text("❌ Для доступу потрібна активна підписка")
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
                chat_name = invite_link_obj.chat_title or ("канал" if chat_type == "channel" else "чат")
                
                join_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        f"🚀 Приєднатися до {chat_name}",
                        url=invite_link_obj.invite_link
                    )]
                ])
                
                await query.edit_message_text(
                    f"🎉 **Готово!**\n\n"
                    f"Натисніть кнопку нижче для приєднання до {chat_name}\n\n"
                    f"📋 Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                    f"⚠️ Не передавайте це посилання іншим користувачам",
                    reply_markup=join_keyboard,
                    parse_mode='Markdown'
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
                            f"🚀 Приєднатися до {chat_info.title}",
                            url=invite_link.invite_link
                        )]
                    ])
                    
                    await query.edit_message_text(
                        f"🎉 **Готово!**\n\n"
                        f"Натисніть кнопку нижче для приєднання до {chat_info.title}\n\n"
                        f"📋 Після переходу надішліть запит на приєднання - він буде автоматично схвалений!\n\n"
                        f"⚠️ Не передавайте це посилання іншим користувачам",
                        reply_markup=join_keyboard,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    logger.error(f"Помилка створення invite link: {e}")
                    await query.edit_message_text(
                        f"❌ Не вдалося створити посилання для приєднання. "
                        f"Зверніться до адміністратора або спробуйте пізніше."
                    )
                    
        except Exception as e:
            logger.error(f"Помилка обробки запиту на приєднання: {e}")
            await query.edit_message_text("❌ Виникла помилка. Спробуйте пізніше.")

    async def handle_channel_joined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити підтвердження приєднання до каналу"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Очищаємо попередні повідомлення та видаляємо поточне
        await self.cleanup_previous_messages(update, delete_current=True)
        
        # Скасовуємо нагадування про приєднання до каналу
        DatabaseManager.cancel_user_reminders(user_id, "join_channel")
        
        # Оновлюємо статус приєднання до каналу
        with DatabaseManager() as db:
            db_user = db.query(User).filter(User.telegram_id == user_id).first()
            if db_user:
                db_user.joined_channel = True
                db.commit()
                logger.info(f"Оновлено joined_channel=True для користувача {user_id}")
            else:
                logger.error(f"Користувач {user_id} не знайдений при оновленні joined_channel")
        
        # Відправляємо повідомлення про успішне схвалення каналу
        await self.bot.send_message(
            chat_id=user_id,
            text="✅ **Відмінно!** Ви приєдналися до каналу!\n\n"
                 "Тепер у вас є доступ до всіх тренувань та корисної інформації 📺",
            parse_mode='Markdown'
        )
        
        # Встановлюємо стан очікування приєднання до чату
        DatabaseManager.update_user_state(user_id, UserState.CHAT_JOIN_PENDING)
        
        # Отримуємо посилання на чат з бази
        invite_links = DatabaseManager.get_active_invite_links()
        chat_link = None
        
        for link in invite_links:
            if link.chat_type == "chat":
                chat_link = link
                break
        
        if chat_link:
            keyboard = [[InlineKeyboardButton(
                text="💬 Приєднатися до чату",
                url=chat_link.invite_link
            )]]
        else:
            # Fallback
            keyboard = [[InlineKeyboardButton(
                text="💬 Приєднатися до чату",
                url=f"https://t.me/{settings.private_chat_id.lstrip('-')}"
            )]]
        
        # Додаємо кнопку "Я приєднався"
        keyboard.append([InlineKeyboardButton(
            text="✅ Я приєднався до чату",
            callback_data="chat_joined"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=user_id,
            text="💬 **Крок 2: Приєднання до чату**\n\n"
                 "Тепер приєднайтеся до нашого приватного чату для спілкування з іншими учасниками та тренерами.\n\n"
                 "Після приєднання натисніть кнопку '✅ Я приєднався до чату'",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_chat_joined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обробити підтвердження приєднання до чату"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Очищаємо попередні повідомлення та видаляємо поточне
        await self.cleanup_previous_messages(update, delete_current=True)
        
        # Скасовуємо всі залишкові нагадування про приєднання
        DatabaseManager.cancel_user_reminders(user_id, "join_channel")
        
        # Оновлюємо статус приєднання до чату
        with DatabaseManager() as db:
            db_user = db.query(User).filter(User.telegram_id == user_id).first()
            if db_user:
                db_user.joined_chat = True
                db.commit()
                logger.info(f"Оновлено joined_chat=True для користувача {user_id}")
            else:
                logger.error(f"Користувач {user_id} не знайдений при оновленні joined_chat")
        
        # Відправляємо повідомлення про успішне завершення приєднання
        await self.bot.send_message(
            chat_id=user_id,
            text="🎉 **Вітаємо у UPGRADE STUDIO!**\n\n"
                 "✅ Ви успішно приєдналися до каналу та чату!\n"
                 "💪 Тепер у вас є повний доступ до всіх можливостей нашої спільноти!\n\n"
                 "Переходимо до керування вашою підпискою...",
            parse_mode='Markdown'
        )
        
        # Встановлюємо стан активної підписки
        DatabaseManager.update_user_state(user_id, UserState.ACTIVE_SUBSCRIPTION)
        
        # Автоматично відкриваємо меню керування підпискою
        await asyncio.sleep(2)  # Коротка затримка для читабельності
        await self.handle_subscription_management(update, context)

    async def handle_go_to_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти в канал (користувач вже приєднаний)"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        # Отримуємо посилання на канал з бази
        invite_links = DatabaseManager.get_active_invite_links()
        channel_link = None
        
        for link in invite_links:
            if link.chat_type == "channel":
                channel_link = link
                break
        
        if channel_link:
            # Для приєднаних користувачів використовуємо прямі посилання
            # Якщо в базі зберігається invite_link, перетворюємо його на прямий
            if channel_link.chat_title:
                # Використовуємо chat_id для прямого посилання (прибираємо -100 префікс)
                chat_id_clean = channel_link.chat_id.lstrip('-')
                if chat_id_clean.startswith('100'):
                    chat_id_clean = chat_id_clean[3:]  # Прибираємо "100"
                direct_link = f"https://t.me/c/{chat_id_clean}"
            else:
                # Fallback до збереженого посилання
                direct_link = channel_link.invite_link
            
            keyboard = [[InlineKeyboardButton(
                text="📺 Перейти в канал",
                url=direct_link
            )]]
        else:
            # Fallback
            from config import settings
            channel_id_clean = settings.private_channel_id.lstrip('-')
            if channel_id_clean.startswith('100'):
                channel_id_clean = channel_id_clean[3:]
            keyboard = [[InlineKeyboardButton(
                text="📺 Перейти в канал",
                url=f"https://t.me/c/{channel_id_clean}"
            )]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text="📺 **Перехід до каналу**\n\n"
                 "Ви вже приєднані до нашого приватного каналу!\n"
                 "Натисніть кнопку нижче, щоб перейти в канал та переглянути останні матеріали.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Повертаємося до меню керування підпискою через кілька секунд
        await asyncio.sleep(3)
        await self.handle_subscription_management_from_callback(query.from_user.id)

    async def handle_go_to_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти в чат (користувач вже приєднаний)"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update, delete_current=True)
        
        # Отримуємо посилання на чат з бази
        invite_links = DatabaseManager.get_active_invite_links()
        chat_link = None
        
        for link in invite_links:
            if link.chat_type == "chat":
                chat_link = link
                break
        
        if chat_link:
            # Для приєднаних користувачів використовуємо прямі посилання
            # Якщо в базі зберігається invite_link, перетворюємо його на прямий
            if chat_link.chat_title:
                # Використовуємо chat_id для прямого посилання (прибираємо -100 префікс)
                chat_id_clean = chat_link.chat_id.lstrip('-')
                if chat_id_clean.startswith('100'):
                    chat_id_clean = chat_id_clean[3:]  # Прибираємо "100"
                direct_link = f"https://t.me/c/{chat_id_clean}"
            else:
                # Fallback до збереженого посилання
                direct_link = chat_link.invite_link
            
            keyboard = [[InlineKeyboardButton(
                text="💬 Перейти в чат",
                url=direct_link
            )]]
        else:
            # Fallback
            from config import settings
            chat_id_clean = settings.private_chat_id.lstrip('-')
            if chat_id_clean.startswith('100'):
                chat_id_clean = chat_id_clean[3:]
            keyboard = [[InlineKeyboardButton(
                text="💬 Перейти в чат",
                url=f"https://t.me/c/{chat_id_clean}"
            )]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=query.from_user.id,
            text="💬 **Перехід до чату**\n\n"
                 "Ви вже приєднані до нашого приватного чату!\n"
                 "Натисніть кнопку нижче, щоб перейти в чат та поспілкуватися з іншими учасниками.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Повертаємося до меню керування підпискою через кілька секунд
        await asyncio.sleep(3)
        await self.handle_subscription_management_from_callback(query.from_user.id)

    async def show_more_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показати додаткову інформацію про підписку"""
        query = update.callback_query
        await query.answer()
        
        # Очищаємо попередні повідомлення
        await self.cleanup_previous_messages(update)
        
        info_text = f"""📋 **Детальна інформація про UPGRADE STUDIO:**

🏋️ **Що включає підписка:**
• Персоналізовані тренування під ваші цілі та фізичну підготовку
• Доступ до приватної спільноти однодумців 
• Підтримка професійних тренерів 24/7
• Прогрес-трекінг та мотивація від команди
• Ексклюзивний контент та майстер-класи
• Харчування та рекомендації від дієтологів

💰 **Умови підписки:**
• Вартість: {settings.subscription_price/100:.0f} {settings.subscription_currency.upper()} на місяць
• Автоматичне продовження кожен місяць
• Можливість призупинити або скасувати в будь-який час
• Безпечна оплата через Stripe

🔒 **Безпека:**
• Захищені платежі через світову систему Stripe
• Ваші дані під надійним захистом
• Можливість керувати підпискою через бот

Готові приєднатися до нашої фітнес-спільноти? 💪"""

        await query.edit_message_text(
            text=info_text,
            reply_markup=get_subscription_offer_keyboard(),
            parse_mode='Markdown'
        )
    
    async def set_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Встановити нагадування про підписку"""
        query = update.callback_query
        await query.answer()
        
        user = DatabaseManager.get_user_by_telegram_id(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ Користувач не знайдений")
            return
        
        # Встановлюємо стан "нагадати пізніше"
        DatabaseManager.update_user_state(query.from_user.id, UserState.REMINDER_SET)
        
        await query.edit_message_text(
            f"⏰ **Нагадування встановлено!**\n\n"
            f"Ми нагадаємо вам про підписку через 24 години.\n\n"
            f"У будь-який час ви можете оформити підписку, написавши /start\n\n"
            f"Дякуємо за інтерес до UPGRADE STUDIO! 💪",
            parse_mode='Markdown'
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
        
        # Запити на приєднання до чатів/каналів - видалено автоматичні сповіщення
        
        # Текстові повідомлення (меню)
        app.add_handler(MessageHandler(
            filters.Regex(f"^{Buttons.MANAGE_SUBSCRIPTION}$"), 
            self.handle_subscription_management
        ))
        app.add_handler(MessageHandler(
            filters.Regex(f"^{Buttons.DASHBOARD}$"), 
            self.handle_dashboard
        ))
        app.add_handler(MessageHandler(
            filters.Regex(f"^{Buttons.SUPPORT}$"), 
            self.handle_support
        ))
        
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
        
        # Створюємо додаток
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        self.bot = self.application.bot
        
        # Ініціалізуємо планувальник задач
        self.task_scheduler = TaskScheduler(self.bot)
        
        # Налаштовуємо обробники
        self.setup_handlers()
        
        logger.info("Бот ініціалізовано")
    

    
    async def initialize(self):
        """Ініціалізація бота"""
        # Створюємо таблиці бази даних
        create_tables()
        
        # Створюємо додаток
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        self.bot = self.application.bot
        
        # Ініціалізуємо планувальник задач
        self.task_scheduler = TaskScheduler(self.bot)
        
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
            logger.error(f"Помилка при запуску бота: {e}")
        finally:
            # Зупиняємо планувальник при завершенні
            if self.task_scheduler:
                try:
                    self.task_scheduler.stop_sync()
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