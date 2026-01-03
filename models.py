from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, BigInteger, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True) # Изменен тип на BigInteger
    telegram_user_name = Column(String, nullable=True) # Сделаем nullable на всякий случай
    phone_number = Column(String)
    balance = Column(Float, default=0)
    send_report_to = Column(String, nullable=True)  # Имя телеграм-пользователя для отправки отчетов
    VIP_level = Column(Integer, default=0)  # VIP уровень пользователя
    username = Column(String, nullable=True)  # Добавлено поле username
    first_name = Column(String, nullable=True)  # Добавлено поле first_name
    last_name = Column(String, nullable=True)  # Добавлено поле last_name
    is_superuser = Column(Boolean, nullable=True)  # Добавлено поле is_superuser
    avatar_url = Column(String, nullable=True)  # Добавлено поле avatar_url
    # password_hash = Column(String) # Удалено, т.к. вход через Telegram
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)
    is_newcomer = Column(Boolean, default=True)  # Статус новичка (первые 24 часа)
    language_code = Column(String, nullable=True, default='en')  # User's language preference
    bot_model_1 = Column(Integer, nullable=True)
    bot_model_2 = Column(Integer, nullable=True)
    bot_system_content = Column(Text, nullable=True)
    free_batteries_total = Column(Float, default=0.0)  # Total batteries earned
    time_of_last_earned_battery = Column(DateTime, nullable=True)  # When last battery was earned

    # Relationships
    bot_log_state = relationship("UserBotLogState", back_populates="user", uselist=False)

class TelegramSession(Base):
    __tablename__ = "telegram_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_path = Column(String, unique=True) # Путь должен быть уникальным
    created_at = Column(DateTime, server_default=func.now())
    session_last_used = Column(DateTime(timezone=True), nullable=True) # <--- ИЗМЕНЕНО ЗДЕСЬ

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True) # Один воркер на пользователя
    session_id = Column(Integer, ForeignKey("telegram_sessions.id"))
    status = Column(String, default='stopped') # Возможные значения: 'stopped', 'running', 'error', 'auth_required'
    last_started_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True) # Changed to timezone-aware
    pid = Column(Integer, nullable=True) # Добавлено поле pid
    last_error = Column(Text, nullable=True) # Добавлено поле для хранения последней ошибки

class WorkerError(Base):
    __tablename__ = "worker_errors"
    id = Column(Integer, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())  # Changed to timezone-aware
    error_type = Column(String)
    error_message = Column(Text)

class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    model = Column(String)
    system_content = Column(Text)
    user_content = Column(Text)
    max_tokens = Column(Integer)
    temperature = Column(Float)
    top_p = Column(Float)
    price_per_post = Column(Float, default=0.0)  # Цена за пост
    provider = Column(Integer, default=0)  # Провайдер модели (0 - по умолчанию)
    model_visible_name = Column(String, nullable=True)
    api_price = Column(Float, nullable=True)
    visible = Column(Integer, nullable=True)

    channel_pairs = relationship("ChannelPair", back_populates="model")

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    channel_pair_id = Column(Integer, ForeignKey("channel_pairs.id"))
    original_message_id = Column(BigInteger, nullable=True) 
    source_channel_id = Column(String, nullable=True) 
    target_channel_id = Column(String, nullable=True) 
    message_id = Column(BigInteger, nullable=True) 
    media_type = Column(String, nullable=True) # <--- ДОБАВЛЕНО ЭТО ПОЛЕ
    scheduled_at = Column(DateTime(timezone=True), nullable=True) # Changed to timezone-aware
    status = Column(String, default='pending') # e.g., 'pending', 'sent', 'failed'
    content = Column(Text, nullable=True)
    media_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # Changed to timezone-aware
    balance_after = Column(Float, nullable=True)  # New field for balance after deduction

    user = relationship("User")
    channel_pair = relationship("ChannelPair")

class ChannelPair(Base):
    __tablename__ = "channel_pairs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_channel = Column(String)  # Changed from BigInteger to String
    target_channel = Column(String)  # Changed from BigInteger to String
    text_to_delete = Column(Text, nullable=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=True)
    system_content = Column(Text, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    top_p = Column(Float, nullable=True)
    hour_min = Column(Integer, nullable=True)
    hour_max = Column(Integer, nullable=True)
    caption_text = Column(Text, nullable=True)  # Текст подписи
    caption_url = Column(String, nullable=True)  # URL для кликабельной ссылки

    model = relationship("Model", back_populates="channel_pairs")


class WorkerQueue(Base):
    __tablename__ = "worker_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, processing, starting, completed, failed
    priority = Column(Integer, default=0)  # Higher number = higher priority
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="queue_entries")

class ChannelProcessingState(Base):
    __tablename__ = "channel_processing_state"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_pair_id = Column(Integer, ForeignKey("channel_pairs.id"), nullable=False)
    last_processed_message_id = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
    channel_pair = relationship("ChannelPair")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'channel_pair_id'),
    )


class UserBotLogState(Base):
    __tablename__ = "user_bot_log_state"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_status_message_id = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="bot_log_state")


# Add relationship to User model
User.queue_entries = relationship("WorkerQueue", back_populates="user")


class Payment(Base):
    """
    Модель для хранения информации о платежах пользователей.
    Поддерживает различные валюты (Telegram Stars, криптовалюты и т.д.)
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Тип валюты: 'stars', 'crypto', 'card', etc.
    currency_type = Column(String(50), nullable=False, default='stars')
    
    # Сумма в валюте платежа (например, количество звёзд)
    amount = Column(Float, nullable=False)
    
    # Количество полученных батареек (курс может отличаться от 1:1)
    batteries_received = Column(Float, nullable=False)
    
    # Статус платежа: 'pending', 'completed', 'failed', 'refunded'
    status = Column(String(20), nullable=False, default='pending')
    
    # Telegram Invoice ID (для звёзд)
    telegram_invoice_id = Column(String(100), nullable=True)
    
    # Telegram PreCheckoutQuery ID
    telegram_pre_checkout_id = Column(String(100), nullable=True, unique=True)
    
    # Внешний ID транзакции (для интеграции с платёжными системами)
    external_transaction_id = Column(String(100), nullable=True)
    
    # Описание ошибки (если платеж не удался)
    error_message = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связь с пользователем
    user = relationship("User", backref="payments")
