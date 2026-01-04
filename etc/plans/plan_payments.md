# План реализации платежей через Telegram Stars

## Обзор задачи

Необходимо реализовать приём платежей в звёздах Telegram в разделе "Профиль" → "Баланс" → "Купить батарейки".

**Требования:**
- Курс фиксированный: 1 звезда = 1 батарейка
- Создать таблицу Payments в БД с учётом будущих валют
- Все сообщения и кнопки в системе локализации
- Приветственное сообщение: `✅ Способы оплаты - Telegram Stars.`
- Первая кнопка: `1🔋 - 1⭐️`

---

## Шаг 1: Создание модели Payments в БД

### Файл: `models.py`

Добавьте новую модель `Payment` в конец файла [`models.py`](models.py):

```python
# GRACE:START:models.py:Payment_model
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
# GRACE:END:models.py:Payment_model
```

---

## Шаг 2: Создание миграции Alembic

### Файл: `alembic/versions/XXXX_add_payments_table.py`

Создайте новую миграцию в директории [`alembic/versions/`](alembic/versions/):

```python
# GRACE:START:alembic/versions:add_payments_table
"""add payments table

Revision ID: XXXXXXXXXX
Revises: 
Create Date: 2025-12-29 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'XXXXXXXX'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Создаём таблицу payments
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('currency_type', sa.String(length=50), nullable=False, server_default='stars'),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('batteries_received', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('telegram_invoice_id', sa.String(length=100), nullable=True),
        sa.Column('telegram_pre_checkout_id', sa.String(length=100), nullable=True),
        sa.Column('external_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_pre_checkout_id')
    )
    
    # Создаём индексы для оптимизации запросов
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])


def downgrade():
    op.drop_index('ix_payments_created_at', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_user_id', table_name='payments')
    op.drop_table('payments')
# GRACE:END:alembic/versions:add_payments_table
```

---

## Шаг 3: Добавление локализации

### Файл: `locales/ru.json`

Добавьте новые ключи в секции `buttons` и `messages`:

```json
// GRACE:START:locales/ru.json:payments_localization
{
  "buttons": {
    // ... существующие кнопки ...
    "buy_1_battery": "1🔋 - 1⭐️",
    "buy_5_batteries": "5🔋 - 5⭐️",
    "buy_10_batteries": "10🔋 - 10⭐️",
    "buy_25_batteries": "25🔋 - 25⭐️",
    "buy_50_batteries": "50🔋 - 50⭐️",
    "buy_100_batteries": "100🔋 - 100⭐️"
  },
  "messages": {
    // ... существующие сообщения ...
    "payment_methods": "✅ Способы оплаты - Telegram Stars.",
    "buy_batteries_title": "💳 <b>Купить батарейки</b>",
    "buy_batteries_description": "Выберите количество батареек для покупки:\n\n💡 <i>1 звезда = 1 батарейка</i>",
    "payment_pending": "⏳ <b>Ожидание оплаты...</b>\n\nПлатёж создан. Пожалуйста, завершите оплату в Telegram.",
    "payment_success": "✅ <b>Оплата успешна!</b>\n\nПолучено: <code>{batteries:.1f}</code>🔋\nНовый баланс: <code>{balance:.1f}</code>🔋",
    "payment_failed": "❌ <b>Оплата не удалась</b>\n\nПричина: {reason}\n\nПопробуйте ещё раз или обратитесь в поддержку.",
    "payment_cancelled": "⚠️ <b>Оплата отменена</b>\n\nВы отменили платёж. Если возникли проблемы, попробуйте ещё раз.",
    "payment_processing": "⏳ Обработка платежа..."
  }
}
// GRACE:END:locales/ru.json:payments_localization
```

### Файл: `locales/en.json`

Добавьте те же ключи на английском:

```json
// GRACE:START:locales/en.json:payments_localization
{
  "buttons": {
    // ... existing buttons ...
    "buy_1_battery": "1🔋 - 1⭐️",
    "buy_5_batteries": "5🔋 - 5⭐️",
    "buy_10_batteries": "10🔋 - 10⭐️",
    "buy_25_batteries": "25🔋 - 25⭐️",
    "buy_50_batteries": "50🔋 - 50⭐️",
    "buy_100_batteries": "100🔋 - 100⭐️"
  },
  "messages": {
    // ... existing messages ...
    "payment_methods": "✅ Payment methods - Telegram Stars.",
    "buy_batteries_title": "💳 <b>Buy Batteries</b>",
    "buy_batteries_description": "Select the number of batteries to purchase:\n\n💡 <i>1 star = 1 battery</i>",
    "payment_pending": "⏳ <b>Waiting for payment...</b>\n\nPayment created. Please complete the payment in Telegram.",
    "payment_success": "✅ <b>Payment successful!</b>\n\nReceived: <code>{batteries:.1f}</code>🔋\nNew balance: <code>{balance:.1f}</code>🔋",
    "payment_failed": "❌ <b>Payment failed</b>\n\nReason: {reason}\n\nPlease try again or contact support.",
    "payment_cancelled": "⚠️ <b>Payment cancelled</b>\n\nYou cancelled the payment. If you encountered issues, please try again.",
    "payment_processing": "⏳ Processing payment..."
  }
}
// GRACE:END:locales/en.json:payments_localization
```

---

## Шаг 4: Добавление клавиатуры для покупки батареек

### Файл: `telegram_bot/keyboards.py`

Добавьте новый метод в класс `BotKeyboards`:

```python
# GRACE:START:telegram_bot/keyboards.py:buy_batteries_menu
@staticmethod
def buy_batteries_menu(lang: str = 'en') -> InlineKeyboardMarkup:
    """Buy batteries menu with different package options"""
    keyboard = [
        [
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_1_battery"), callback_data="buy_battery:1"),
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_5_batteries"), callback_data="buy_battery:5")
        ],
        [
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_10_batteries"), callback_data="buy_battery:10"),
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_25_batteries"), callback_data="buy_battery:25")
        ],
        [
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_50_batteries"), callback_data="buy_battery:50"),
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_100_batteries"), callback_data="buy_battery:100")
        ],
        [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="balance")]
    ]
    return InlineKeyboardMarkup(keyboard)
# GRACE:END:telegram_bot/keyboards.py:buy_batteries_menu
```

---

## Шаг 5: Обработка callback для buy_battery

### Файл: `telegram_bot/handlers.py`

Добавьте обработчики в функцию `callback_query_handler`:

```python
# GRACE:START:telegram_bot/handlers.py:buy_battery_handler
# В начале файла добавьте импорты
from models import Payment
from datetime import datetime, timezone
import secrets

# Внутри callback_query_handler добавьте новый блок elif:

elif data == "buy_battery":
    # Показать меню покупки батареек
    session = async_session()
    try:
        result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
        db_user = result.scalar_one_or_none()
    finally:
        await session.close()
    
    user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
    message = I18n.get(user_lang, "messages.payment_methods") + "\n\n" + I18n.get(user_lang, "messages.buy_batteries_description")
    keyboard = BotKeyboards.buy_batteries_menu(user_lang)

elif data.startswith("buy_battery:"):
    # Обработка выбора количества батареек
    try:
        _, batteries_str = data.split(":")
        batteries_count = int(batteries_str)
    except ValueError:
        await query.answer("❌ Invalid batteries count")
        return
    
    # Получаем пользователя
    session = async_session()
    try:
        result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
        db_user = result.scalar_one_or_none()
    finally:
        await session.close()
    
    if not db_user:
        await query.answer("❌ User not found")
        return
    
    user_lang = db_user.language_code if db_user.language_code in ['ru', 'en'] else 'en'
    
    # Создаём запись о платеже в БД
    session = async_session()
    try:
        # Генерируем уникальный pre_checkout_id
        pre_checkout_id = f"payment_{db_user.id}_{secrets.token_hex(8)}"
        
        payment = Payment(
            user_id=db_user.id,
            currency_type='stars',
            amount=float(batteries_count),  # 1 звезда = 1 батарейка
            batteries_received=float(batteries_count),
            status='pending',
            telegram_pre_checkout_id=pre_checkout_id,
            created_at=datetime.now(timezone.utc)
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
    finally:
        await session.close()
    
    # Отправляем invoice через Telegram Stars API
    try:
        # Создаём invoice для Telegram Stars
        invoice_title = f"{batteries_count} Batteries" if user_lang == 'en' else f"{batteries_count} Батареек"
        invoice_description = f"Buy {batteries_count} batteries for tAIger bot" if user_lang == 'en' else f"Купить {batteries_count} батареек для бота tAIger"
        
        # Отправляем invoice
        await query.message.reply_invoice(
            title=invoice_title,
            description=invoice_description,
            payload=pre_checkout_id,  # Используем как payload
            provider_token="",  # Пустой для Telegram Stars
            currency="XTR",  # XTR - код валюты Telegram Stars
            prices=[{"label": f"{batteries_count} batteries" if user_lang == 'en' else f"{batteries_count} батареек", "amount": batteries_count}],
            max_tip_amount=0,
            start_parameter="buy-batteries",
            reply_markup=BotKeyboards.back_to_main(user_lang)
        )
        
        # Отправляем сообщение о создании платежа
        await query.message.reply_text(
            I18n.get(user_lang, "messages.payment_pending"),
            reply_markup=BotKeyboards.back_to_main(user_lang),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        await query.answer(f"❌ Error: {str(e)}")
# GRACE:END:telegram_bot/handlers.py:buy_battery_handler
```

---

## Шаг 6: Обработка PreCheckoutQuery

### Файл: `telegram_bot/handlers.py`

Добавьте новый обработчик для PreCheckoutQuery:

```python
# GRACE:START:telegram_bot/handlers.py:pre_checkout_handler
async def pre_checkout_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query from Telegram Stars payment"""
    try:
        query = update.pre_checkout_query
        if not query:
            return
        
        payload = query.invoice_payload
        
        # Проверяем, существует ли платеж в БД
        session = async_session()
        try:
            result = await session.execute(
                select(Payment).where(Payment.telegram_pre_checkout_id == payload)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                await query.answer(ok=False, error_message="Payment not found")
                return
            
            # Проверяем статус платежа
            if payment.status != 'pending':
                await query.answer(ok=False, error_message="Payment already processed")
                return
            
            # Подтверждаем pre-checkout
            await query.answer(ok=True)
            
        finally:
            await session.close()
            
    except Exception as e:
        logger.error(f"Error in pre-checkout handler: {e}")
        await query.answer(ok=False, error_message="Payment verification failed")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment from Telegram Stars"""
    try:
        message = update.message
        if not message or not message.successful_payment:
            return
        
        successful_payment = message.successful_payment
        payload = successful_payment.invoice_payload
        
        # Находим платеж в БД
        session = async_session()
        try:
            result = await session.execute(
                select(Payment).where(Payment.telegram_pre_checkout_id == payload)
            )
            payment = result.scalar_one_or_none()
            
            if not payment:
                logger.error(f"Payment not found for payload: {payload}")
                return
            
            # Проверяем, не был ли уже обработан
            if payment.status == 'completed':
                logger.info(f"Payment {payment.id} already completed")
                return
            
            # Получаем пользователя
            user_result = await session.execute(
                select(User).where(User.id == payment.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found for payment: {payment.id}")
                return
            
            # Обновляем баланс пользователя
            user.balance = (user.balance or 0.0) + payment.batteries_received
            
            # Обновляем статус платежа
            payment.status = 'completed'
            payment.telegram_invoice_id = successful_payment.telegram_payment_charge_id
            payment.completed_at = datetime.now(timezone.utc)
            
            await session.commit()
            await session.refresh(user)
            
            # Отправляем подтверждение пользователю
            user_lang = user.language_code if user.language_code in ['ru', 'en'] else 'en'
            success_message = I18n.get(
                user_lang, 
                "messages.payment_success",
                batteries=payment.batteries_received,
                balance=user.balance
            )
            
            await message.reply_text(
                success_message,
                reply_markup=BotKeyboards.balance_menu(user_lang),
                parse_mode="HTML"
            )
            
            logger.info(f"Payment {payment.id} completed successfully. User {user.id} received {payment.batteries_received} batteries")
            
        finally:
            await session.close()
            
    except Exception as e:
        logger.error(f"Error in successful payment handler: {e}", exc_info=True)
# GRACE:END:telegram_bot/handlers.py:pre_checkout_handler
```

---

## Шаг 7: Регистрация новых обработчиков

### Файл: `telegram_bot/handlers.py`

Добавьте регистрацию новых обработчиков в функцию `setup_handlers`:

```python
# GRACE:START:telegram_bot/handlers.py:setup_payment_handlers
def setup_handlers(application: Application):
    """Set up all command and callback handlers"""
    print("DEBUG: Setting up handlers")
    
    # ... существующие обработчики ...
    
    # Добавьте новые обработчики для платежей
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_query_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    print("DEBUG: All handlers set up")
    logger.info("Bot handlers set up successfully")
# GRACE:END:telegram_bot/handlers.py:setup_payment_handlers
```

Не забудьте добавить импорт в начале файла:

```python
from telegram.ext import PreCheckoutQueryHandler
```

---

## Шаг 8: Обновление balance_menu

### Файл: `telegram_bot/keyboards.py`

Обновите метод `balance_menu` для добавления кнопки "Купить батарейки":

```python
# GRACE:START:telegram_bot/keyboards.py:balance_menu_updated
@staticmethod
def balance_menu(lang: str = 'en') -> InlineKeyboardMarkup:
    """Balance and account menu"""
    keyboard = [
        [
            InlineKeyboardButton(I18n.get(lang, "buttons.earn_battery"), callback_data="earn_battery"),
            InlineKeyboardButton(I18n.get(lang, "buttons.buy_battery"), callback_data="buy_battery")
        ],
        [InlineKeyboardButton(I18n.get(lang, "buttons.back"), callback_data="profile")]
    ]
    return InlineKeyboardMarkup(keyboard)
# GRACE:END:telegram_bot/keyboards.py:balance_menu_updated
```

---

## Шаг 9: Обновление callback_query_handler для balance

### Файл: `telegram_bot/handlers.py`

Обновите обработчик для `balance` callback:

```python
# GRACE:START:telegram_bot/handlers.py:balance_callback_updated
elif data == "balance":
    db_user = None
    session = async_session()
    try:
        result = await session.execute(select(User).where(User.telegram_id == int(telegram_id)))
        db_user = result.scalar_one_or_none()
    finally:
        await session.close()

    balance = float(db_user.balance) if db_user and db_user.balance is not None else get_default_balance()
    user_lang = db_user.language_code if db_user and db_user.language_code in ['ru', 'en'] else 'en'
    
    # Обновлённое сообщение с информацией о способах оплаты
    message = I18n.get(user_lang, "messages.payment_methods") + "\n\n" + I18n.get(user_lang, "messages.balance_info", emoji="💰", balance=balance)
    keyboard = BotKeyboards.balance_menu(user_lang)
# GRACE:END:telegram_bot/handlers.py:balance_callback_updated
```

---

## Порядок выполнения

1. **Создать миграцию Alembic** для таблицы `payments`
2. **Добавить модель Payment** в [`models.py`](models.py)
3. **Добавить локализацию** в [`locales/ru.json`](locales/ru.json) и [`locales/en.json`](locales/en.json)
4. **Добавить клавиатуру** `buy_batteries_menu` в [`telegram_bot/keyboards.py`](telegram_bot/keyboards.py)
5. **Добавить обработчики** в [`telegram_bot/handlers.py`](telegram_bot/handlers.py):
   - `buy_battery` callback
   - `buy_battery:N` callback (где N - количество)
   - `pre_checkout_query_handler`
   - `successful_payment_handler`
6. **Зарегистрировать новые обработчики** в функции `setup_handlers`
7. **Протестировать** создание invoice и обработку платежей

---

## Важные замечания

### Безопасность
- Всегда проверяйте существование платежа в БД перед подтверждением
- Используйте уникальные `pre_checkout_id` для предотвращения повторной обработки
- Проверяйте статус платежа перед начислением баланса

### Telegram Stars API
- Валюта для звёзд: `XTR`
- `provider_token` должен быть пустым для Telegram Stars
- `payload` используется для связи invoice с записью в БД

### Расширяемость
- Таблица `payments` поддерживает разные валюты через поле `currency_type`
- В будущем можно добавить криптовалюты, карты и т.д.
- Курс конвертации хранится в полях `amount` и `batteries_received`

### Логирование
- Логируйте все этапы обработки платежа
- Записывайте причины неудачных платежей в поле `error_message`

---

## Тестирование

После реализации проверьте:

1. **Создание invoice** - корректно ли создаётся invoice для 1 звезды
2. **PreCheckout** - корректно ли подтверждается pre-checkout
3. **Успешный платёж** - начисляется ли баланс пользователю
4. **Отмена платежа** - корректно ли обрабатывается отмена
5. **Локализация** - корректно ли отображаются сообщения на RU и EN
6. **Повторная обработка** - предотвращается ли повторное начисление за один платёж

---

## Дополнительные улучшения (будущее)

- Добавить историю платежей в профиль пользователя
- Добавить промокоды для скидок
- Добавить подписки с автоматическим списанием
- Добавить аналитику платежей для админа
