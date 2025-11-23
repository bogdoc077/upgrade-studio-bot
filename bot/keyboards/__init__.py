"""
Клавіатури для телеграм бота
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import Buttons, SurveyOptions


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Головне меню бота"""
    keyboard = [
        [KeyboardButton(Buttons.MANAGE_SUBSCRIPTION)],
        [KeyboardButton(Buttons.DASHBOARD), KeyboardButton(Buttons.SUPPORT)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура привітання (не використовується - переходимо одразу до цілей)"""
    keyboard = []
    return InlineKeyboardMarkup(keyboard)


def get_survey_goals_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору цілей"""
    keyboard = []
    for goal in SurveyOptions.GOALS:
        # Використовуємо весь текст як callback_data (коротше за 64 символи)
        keyboard.append([InlineKeyboardButton(goal, callback_data=f"goal_{goal}")])
    
    return InlineKeyboardMarkup(keyboard)


def get_survey_injuries_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору травм/обмежень"""
    keyboard = []
    for injury in SurveyOptions.INJURIES:
        keyboard.append([InlineKeyboardButton(injury, callback_data=f"injury_{injury}")])
    
    return InlineKeyboardMarkup(keyboard)


def get_subscription_offer_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура пропозиції підписки"""
    keyboard = [
        [InlineKeyboardButton("Оформити підписку", callback_data="create_subscription")],
        [InlineKeyboardButton("Дізнатися більше", callback_data="more_info")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_subscription_management_keyboard(subscription_active: bool = True, 
                                       subscription_paused: bool = False,
                                       subscription_cancelled: bool = False,
                                       joined_channel: bool = False,
                                       joined_chat: bool = False) -> InlineKeyboardMarkup:
    """Клавіатура керування підпискою"""
    keyboard = []
    
    if subscription_active:
        # Додаємо кнопки доступу до каналів для активних підписників (по одній вниз)
        # Якщо підписка скасована але ще активна - показуємо кнопки "Перейти"
        if subscription_cancelled or subscription_paused:
            # Користувач має доступ але підписка призупинена/скасована
            keyboard.append([InlineKeyboardButton("📣 Перейти в канал", callback_data="go_to_channel")])
            keyboard.append([InlineKeyboardButton("💬 Перейти в чат", callback_data="go_to_chat")])
        else:
            # Звичайний режим - показуємо статус приєднання
            if not joined_channel:
                keyboard.append([InlineKeyboardButton("📣 Приєднатися до каналу", callback_data="join_channel_access")])
            else:
                keyboard.append([InlineKeyboardButton("📣 Перейти в канал", callback_data="go_to_channel")])
                
            if not joined_chat:
                keyboard.append([InlineKeyboardButton("💬 Приєднатися до чату", callback_data="join_chat_access")])
            else:
                keyboard.append([InlineKeyboardButton("💬 Перейти в чат", callback_data="go_to_chat")])
        
        # Управління підпискою - не показуємо якщо підписка вже призупинена/скасована
        if not subscription_paused and not subscription_cancelled:
            keyboard.append([InlineKeyboardButton(Buttons.PAUSE_SUBSCRIPTION, callback_data="pause_subscription")])
            keyboard.append([InlineKeyboardButton(Buttons.CANCEL_SUBSCRIPTION, callback_data="cancel_subscription")])
        elif subscription_paused and not subscription_cancelled:
            keyboard.append([InlineKeyboardButton(Buttons.RESUME_SUBSCRIPTION, callback_data="resume_subscription")])
    else:
        keyboard.append([InlineKeyboardButton(Buttons.SUBSCRIBE, callback_data="create_subscription")])
    
    keyboard.append([InlineKeyboardButton(Buttons.BACK, callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура з кнопкою "Назад" """
    keyboard = [
        [InlineKeyboardButton(Buttons.BACK, callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура підтримки"""
    keyboard = [
        [InlineKeyboardButton("⁉️ Написати в підтримку", url="https://t.me/alionakovaliova")],
        [InlineKeyboardButton(Buttons.BACK, callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура дашборду"""
    keyboard = [
        [InlineKeyboardButton("🔄 Оновити статистику", callback_data="refresh_dashboard")],
        [InlineKeyboardButton(Buttons.BACK, callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_text_or_button_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору: написати текст або вибрати варіант"""
    keyboard = [
        [InlineKeyboardButton("Написати свій варіант", callback_data="custom_text")],
        [InlineKeyboardButton(Buttons.BACK, callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавіатура підтвердження дії"""
    keyboard = [
        [
            InlineKeyboardButton("Так", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("Ні", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)