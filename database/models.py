"""
Моделі бази даних для бота
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from config import settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Стан користувача
    state = Column(String(100), default="registration")
    role = Column(String(20), default="user")  # "user" або "admin"
    
    # Дані опитування
    goals = Column(Text, nullable=True)
    injuries = Column(Text, nullable=True)
    
    # Підписка
    subscription_active = Column(Boolean, default=False)
    subscription_status = Column(String(20), default="inactive")  # 'active', 'inactive', 'paused', 'cancelled'
    subscription_paused = Column(Boolean, default=False)
    subscription_cancelled = Column(Boolean, default=False)
    subscription_end_date = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    
    # Членство в каналах
    joined_channel = Column(Boolean, default=False)
    joined_chat = Column(Boolean, default=False)
    
    # Статистика
    workouts_completed = Column(Integer, default=0)
    member_since = Column(DateTime, default=datetime.utcnow)
    
    # Службові поля
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Зв'язки
    reminders = relationship("Reminder", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    def is_admin(self) -> bool:
        """Перевірити, чи є користувач адміном"""
        return self.role == "admin"


class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Тип нагадування
    reminder_type = Column(String(100), nullable=False)  # 'join_channel', 'subscription_renewal', 'payment_retry'
    
    # Час надсилання
    scheduled_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Статус
    is_active = Column(Boolean, default=True)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Додаткові дані
    data = Column(Text, nullable=True)  # JSON для зберігання додаткових даних
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Зв'язки
    user = relationship("User", back_populates="reminders")
    
    def __repr__(self):
        return f"<Reminder(user_id={self.user_id}, type={self.reminder_type}, scheduled_at={self.scheduled_at})>"


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Stripe дані
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    stripe_response_log = Column(Text, nullable=True)  # Повний JSON лог відповіді від Stripe
    
    # Деталі платежу
    amount = Column(Integer, nullable=False)  # в центах
    currency = Column(String(10), default="eur")
    status = Column(String(50), nullable=False)  # 'pending', 'succeeded', 'failed', 'cancelled'
    
    # Дати
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    # Зв'язки
    user = relationship("User", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(user_id={self.user_id}, amount={self.amount}, status={self.status})>"


class InviteLink(Base):
    __tablename__ = "invite_links"
    
    id = Column(Integer, primary_key=True)
    
    # ID чату
    chat_id = Column(String(50), nullable=False)
    
    # Тип чату/посилання
    link_type = Column(String(20), nullable=False)  # 'channel' або 'chat'
    
    # Назва чату/каналу
    chat_title = Column(String(255), nullable=True)
    
    # Посилання запрошення
    invite_link = Column(String(255), nullable=False)
    
    # Статус активності
    is_active = Column(Boolean, default=True)
    
    # Хто створив посилання
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Час закінчення дії (опціонально)
    expires_at = Column(DateTime, nullable=True)
    
    # Дати
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_expired(self):
        """Перевірити, чи закінчився час дії посилання"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
        
    def __repr__(self):
        return f"<InviteLink(id={self.id}, link_type={self.link_type}, invite_link={self.invite_link})>"


class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True)
    
    # Дані для входу
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Персональні дані
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    
    # Права доступу
    role = Column(String(50), default="admin")  # 'superadmin', 'admin', 'moderator'
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
    
    # Права на функції
    can_manage_users = Column(Boolean, default=True)
    can_manage_payments = Column(Boolean, default=True)
    can_manage_settings = Column(Boolean, default=False)  # Тільки superadmin
    can_manage_admins = Column(Boolean, default=False)    # Тільки superadmin
    
    # Дати
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Admin(username={self.username}, email={self.email}, role={self.role})>"
    
    def check_permission(self, permission: str) -> bool:
        """Перевірити чи є у адміна дозвіл на дію"""
        if not self.is_active:
            return False
            
        if self.is_superadmin:
            return True
            
        permission_mapping = {
            'manage_users': self.can_manage_users,
            'manage_payments': self.can_manage_payments,
            'manage_settings': self.can_manage_settings,
            'manage_admins': self.can_manage_admins,
        }
        
        return permission_mapping.get(permission, False)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    
    # Ключ налаштування
    key = Column(String(100), unique=True, nullable=False)
    
    # Зашифроване значення
    encrypted_value = Column(Text, nullable=False)
    
    # Опис налаштування
    description = Column(Text, nullable=True)
    
    # Тип даних (для валідації)
    value_type = Column(String(20), default="string")  # 'string', 'integer', 'boolean', 'json'
    
    # Чи є значення чутливим (пароль, ключ)
    is_sensitive = Column(Boolean, default=False)
    
    # Категорія
    category = Column(String(50), default="general")  # 'bot', 'payment', 'database', 'general'
    
    # Хто останній змінював
    updated_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Дати
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Зв'язки
    updated_by_admin = relationship("Admin", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<SystemSettings(key={self.key}, category={self.category}, sensitive={self.is_sensitive})>"


# Створення підключення до бази даних
engine = create_engine(settings.database_url, echo=True if settings.log_level == "DEBUG" else False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Створити всі таблиці в базі даних"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Отримати сесію бази даних"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Не закриваємо тут, закриватимемо у викликаючому коді


class DatabaseManager:
    """Менеджер для роботи з базою даних"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self):
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()
        self.db.close()
    
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        """Отримати або створити користувача"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                # Відключаємо об'єкт від сесії для безпечного використання
                db.expunge(user)
            else:
                # Оновити дані користувача якщо вони змінилися
                updated = False
                if user.username != username:
                    user.username = username
                    updated = True
                if user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                
                if updated:
                    user.updated_at = datetime.utcnow()
                    db.commit()
                
                # Відключаємо об'єкт від сесії для безпечного використання
                db.expunge(user)
            
            return user
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Отримати користувача за Telegram ID"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                # Відключаємо об'єкт від сесії для безпечного використання
                db.expunge(user)
            return user
    
    @staticmethod
    def set_user_role(telegram_id: int, role: str):
        """Встановити роль користувача (user/admin)"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.role = role
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def update_user_state(telegram_id: int, state: str):
        """Оновити стан користувача"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.state = state
                user.updated_at = datetime.utcnow()
                db.commit()
    
    @staticmethod
    def save_survey_data(telegram_id: int, goals: str = None, injuries: str = None):
        """Зберегти дані опитування"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                if goals:
                    user.goals = goals
                if injuries:
                    user.injuries = injuries
                user.updated_at = datetime.utcnow()
                db.commit()
    
    @staticmethod
    def create_reminder(user_id: int, reminder_type: str, scheduled_at: datetime, 
                       data: str = None, max_attempts: int = 3) -> Reminder:
        """Створити нагадування"""
        with DatabaseManager() as db:
            reminder = Reminder(
                user_id=user_id,
                reminder_type=reminder_type,
                scheduled_at=scheduled_at,
                data=data,
                max_attempts=max_attempts
            )
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
            return reminder
    
    @staticmethod
    def get_pending_reminders() -> List[Reminder]:
        """Отримати нагадування для надсилання"""
        with DatabaseManager() as db:
            now = datetime.utcnow()
            reminders = db.query(Reminder).filter(
                Reminder.is_active == True,
                Reminder.sent_at.is_(None),
                Reminder.scheduled_at <= now,
                Reminder.attempts < Reminder.max_attempts
            ).all()
            
            # Відключаємо об'єкти від сесії
            for reminder in reminders:
                db.expunge(reminder)
                # Також відключаємо пов'язаного користувача
                if reminder.user:
                    db.expunge(reminder.user)
            
            return reminders
    
    @staticmethod
    def mark_reminder_sent(reminder_id: int):
        """Позначити нагадування як надіслане"""
        with DatabaseManager() as db:
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if reminder:
                reminder.sent_at = datetime.utcnow()
                reminder.attempts += 1
                if reminder.attempts >= reminder.max_attempts:
                    reminder.is_active = False
                db.commit()
    
    # Методи для роботи з посиланнями
    @staticmethod
    def create_invite_link(chat_id: str, chat_type: str, invite_link: str, 
                          chat_title: str = None) -> InviteLink:
        """Створити або оновити посилання для приєднання"""
        with DatabaseManager() as db:
            # Спочатку перевіряємо, чи існує посилання для цього чату
            existing_link = db.query(InviteLink).filter(
                InviteLink.chat_id == chat_id,
                InviteLink.link_type == chat_type
            ).first()
            
            if existing_link:
                # Оновлюємо існуюче посилання
                existing_link.invite_link = invite_link
                existing_link.chat_title = chat_title
                existing_link.is_active = True
                existing_link.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing_link)
                return existing_link
            else:
                # Створюємо нове посилання
                new_link = InviteLink(
                    chat_id=chat_id,
                    link_type=chat_type,
                    chat_title=chat_title,
                    invite_link=invite_link
                )
                db.add(new_link)
                db.commit()
                db.refresh(new_link)
                return new_link
    
    @staticmethod
    def get_active_invite_links() -> List[InviteLink]:
        """Отримати всі активні посилання"""
        with DatabaseManager() as db:
            links = db.query(InviteLink).filter(InviteLink.is_active == True).all()
            
            # Відключаємо об'єкти від сесії
            for link in links:
                db.expunge(link)
            
            return links
    
    @staticmethod
    def get_invite_link_by_chat(chat_id: str, chat_type: str) -> Optional[InviteLink]:
        """Отримати посилання для конкретного чату"""
        with DatabaseManager() as db:
            link = db.query(InviteLink).filter(
                InviteLink.chat_id == chat_id,
                InviteLink.link_type == chat_type,
                InviteLink.is_active == True
            ).first()
            
            if link:
                db.expunge(link)
            
            return link
    
    @staticmethod
    def update_invite_link_status(chat_id: str, chat_type: str, is_active: bool):
        """Оновити статус посилання"""
        with DatabaseManager() as db:
            link = db.query(InviteLink).filter(
                InviteLink.chat_id == chat_id,
                InviteLink.link_type == chat_type
            ).first()
            
            if link:
                link.is_active = is_active
                link.updated_at = datetime.utcnow()
                db.commit()
    
    @staticmethod
    def create_payment(user_id: int, amount: int, stripe_payment_intent_id: str = None,
                      currency: str = "eur") -> Payment:
        """Створити запис про платіж"""
        with DatabaseManager() as db:
            payment = Payment(
                user_id=user_id,
                amount=amount,
                currency=currency,
                status="pending",
                stripe_payment_intent_id=stripe_payment_intent_id
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)
            return payment
    
    @staticmethod
    def update_subscription_dates(telegram_id: int, subscription_end_date: datetime = None,
                                 next_billing_date: datetime = None, cancelled: bool = None):
        """Оновити дати підписки"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                if subscription_end_date is not None:
                    user.subscription_end_date = subscription_end_date
                if next_billing_date is not None:
                    user.next_billing_date = next_billing_date
                if cancelled is not None:
                    user.subscription_cancelled = cancelled
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def set_subscription_cancelled(telegram_id: int, end_date: datetime):
        """Позначити підписку як скасовану з датою закінчення"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.subscription_cancelled = True
                user.subscription_end_date = end_date
                user.subscription_active = False  # Підписка вже не активна
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def get_subscription_info(telegram_id: int) -> dict:
        """Отримати інформацію про підписку користувача"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                return {
                    'active': user.subscription_active,
                    'paused': user.subscription_paused,
                    'cancelled': user.subscription_cancelled,
                    'end_date': user.subscription_end_date,
                    'next_billing_date': user.next_billing_date,
                    'stripe_subscription_id': user.stripe_subscription_id,
                    'stripe_customer_id': user.stripe_customer_id
                }
            return None
    
    @staticmethod
    def cancel_user_reminders(telegram_id: int, reminder_type: str = None):
        """Скасувати нагадування для користувача за типом або всі"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
                
            query = db.query(Reminder).filter(
                Reminder.user_id == user.id,
                Reminder.status.in_(["pending", "scheduled"])
            )
            
            if reminder_type:
                query = query.filter(Reminder.reminder_type == reminder_type)
            
            reminders = query.all()
            
            for reminder in reminders:
                reminder.status = "cancelled"
                reminder.updated_at = datetime.utcnow()
            
            db.commit()
            return len(reminders)
    
    @staticmethod
    def cancel_join_reminders_if_joined(telegram_id: int):
        """Скасувати нагадування про приєднання, якщо користувач вже приєднався"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            # Перевіряємо, чи приєднався користувач до каналу або чату
            if user.joined_channel and user.joined_chat:
                # Скасовуємо всі нагадування про приєднання
                reminders = db.query(Reminder).filter(
                    Reminder.user_id == user.id,
                    Reminder.reminder_type == "join_channel",
                    Reminder.status.in_(["pending", "scheduled"])
                ).all()
                
                for reminder in reminders:
                    reminder.status = "cancelled"
                    reminder.updated_at = datetime.utcnow()
                
                db.commit()
                return len(reminders)
            
            return 0
    
    @staticmethod
    def cancel_subscription_reminders_if_active(telegram_id: int):
        """Скасувати нагадування про підписку, якщо вона вже активна"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            # Якщо підписка активна, скасовуємо нагадування про оплату
            if user.subscription_active:
                reminders = db.query(Reminder).filter(
                    Reminder.user_id == user.id,
                    Reminder.reminder_type.in_(["subscription_renewal", "payment_retry"]),
                    Reminder.is_active == True
                ).all()
                
                for reminder in reminders:
                    reminder.is_active = False
                
                db.commit()
                return len(reminders)
            
            return 0
    
    @staticmethod
    def update_channel_join_status(telegram_id: int, joined: bool):
        """Оновити статус приєднання до каналу"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.joined_channel = joined
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def update_chat_join_status(telegram_id: int, joined: bool):
        """Оновити статус приєднання до чату"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.joined_chat = joined
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def get_user_by_stripe_customer_id(customer_id: str) -> Optional[User]:
        """Отримати користувача за Stripe customer ID"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                db.expunge(user)
            return user
    
    @staticmethod 
    def get_user_by_stripe_subscription_id(subscription_id: str) -> Optional[User]:
        """Отримати користувача за Stripe subscription ID"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first()
            if user:
                db.expunge(user)
            return user
    
    @staticmethod
    def get_active_invite_links():
        """Отримати всі посилання запрошення (фільтрація по is_expired робиться в коді)"""
        with DatabaseManager() as db:
            invite_links = db.query(InviteLink).all()
            # Відключаємо об'єкти від сесії для безпечного використання
            for link in invite_links:
                db.expunge(link)
            return invite_links
    
    @staticmethod
    def add_invite_link(chat_type: str, invite_link: str, chat_id: str = None, chat_title: str = None):
        """Додати нове посилання запрошення"""
        with DatabaseManager() as db:
            link = InviteLink(
                link_type=chat_type,
                invite_link=invite_link,
                chat_id=chat_id or "",
                chat_title=chat_title
            )
            db.add(link)
            db.commit()
            db.refresh(link)
            db.expunge(link)
            return link
    
    @staticmethod
    def update_invite_link(link_id: int, **kwargs):
        """Оновити посилання запрошення"""
        with DatabaseManager() as db:
            link = db.query(InviteLink).filter(InviteLink.id == link_id).first()
            if link:
                for key, value in kwargs.items():
                    if hasattr(link, key):
                        setattr(link, key, value)
                link.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def deactivate_invite_link(link_id: int):
        """Деактивувати посилання запрошення"""
        return DatabaseManager.update_invite_link(link_id, is_active=False)
    
    @staticmethod
    def reset_user_access_statuses(telegram_id: int):
        """Скинути статуси доступу користувача (joined_channel, joined_chat)"""
        with DatabaseManager() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.joined_channel = False
                user.joined_chat = False
                user.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
    
    @staticmethod
    def update_expired_subscriptions():
        """Оновити статуси всіх закінчених підписок"""
        from datetime import datetime
        
        with DatabaseManager() as db:
            now = datetime.utcnow()
            
            # Знаходимо користувачів з закінченими підписками
            expired_users = db.query(User).filter(
                User.subscription_end_date.isnot(None),
                User.subscription_end_date <= now,
                User.subscription_active == True
            ).all()
            
            count = 0
            for user in expired_users:
                user.subscription_active = False
                user.joined_channel = False
                user.joined_chat = False
                user.updated_at = datetime.utcnow()
                count += 1
            
            if count > 0:
                db.commit()
            
            return count


class Broadcast(Base):
    """Модель для розсилок"""
    __tablename__ = "broadcasts"
    
    id = Column(Integer, primary_key=True)
    created_by = Column(Integer, ForeignKey('admins.id'), nullable=False)
    target_group = Column(String(50), nullable=False)  # 'active', 'inactive', 'no_payment'
    
    # Заголовок
    title = Column(String(255), nullable=True)  # Заголовок розсилки для відображення в адмінці
    
    # Контент повідомлення
    message_text = Column(Text, nullable=True)
    attachment_type = Column(String(20), nullable=True)  # 'image', 'file', 'link', None
    attachment_url = Column(String(500), nullable=True)
    button_text = Column(String(100), nullable=True)  # Для посилань
    button_url = Column(String(500), nullable=True)
    message_blocks = Column(Text, nullable=True)  # JSON з усіма блоками повідомлення
    
    # Статус та статистика
    status = Column(String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Час
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_log = Column(Text, nullable=True)  # Лог помилок
    full_log = Column(Text, nullable=True)  # Повний лог розсилки (успішні + помилки)


class BroadcastQueue(Base):
    """Черга для розсилок"""
    __tablename__ = "broadcast_queue"
    
    id = Column(Integer, primary_key=True)
    broadcast_id = Column(Integer, ForeignKey('broadcasts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    telegram_id = Column(Integer, nullable=False)
    
    status = Column(String(20), default='pending')  # 'pending', 'sent', 'failed'
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    broadcast = relationship("Broadcast")
    user = relationship("User")


def get_database():
    """
    Отримати з'єднання з базою даних для адмін-панелі
    Повертає raw MySQL connection для простих запитів
    """
    import mysql.connector
    from urllib.parse import urlparse
    
    # Парсимо DATABASE_URL
    parsed = urlparse(settings.database_url)
    
    config = {
        'host': parsed.hostname,
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/'),
        'charset': 'utf8mb4',
        'autocommit': False
    }
    
    return mysql.connector.connect(**config)