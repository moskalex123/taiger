# План кодирования оптимизации запуска воркера

## Обзор

На основе анализа пути запуска воркера (plans/worker_startup_optimization_analysis.md) составлен детальный план кодирования для младшей кодер-модели. План включает 7 оптимизаций, разделенных на этапы по сложности и приоритету.

**Цель:** Сократить время до начала обработки новых постов с 20-80+ секунд до 6-10 секунд (улучшение 70-85%).

**Общий подход:**
- Начинать с простых оптимизаций (этап 1)
- Постепенно переходить к более сложным (этапы 2-3)
- Каждая оптимизация включает: описание проблемы, текущий код, предлагаемый код, шаги реализации

## Статус оптимизаций

| # | Оптимизация | Сложность | Статус | Экономия времени |
|---|-------------|-----------|--------|------------------|
| 1 | Замена фиксированных задержек | Низкая | ✅ Выполнена | 10-12s |
| 2 | Параллельная инициализация компонентов | Средняя | ⏳ Ожидает | 1-3s |
| 3 | Фоновая загрузка аватара | Низкая | ✅ Выполнена | 1-2s |
| 4 | Оптимизация пакетной обработки | Низкая | ⏳ Ожидает | 0.5-1s на канал |
| 5 | Кэширование прогрева клиента | Низкая | ✅ Выполнена | 0.5-1s на канал |
| 6 | Оптимизация проверки каналов | Низкая | ✅ Выполнена | 0.5-1s на канал |
| 7 | Асинхронная регистрация в API | Низкая | ✅ Выполнена | 0.1-1s |

---

## Этап 1: Быстрые победы (выполнено)

### Оптимизация 1: Замена фиксированных задержек на активную проверку готовности

**Файл:** `tg_worker.py` (строки 48-63)

**Проблема:** Фиксированные задержки 10+4=14 секунд не учитывают реальную готовность клиента.

**Текущий код:**
```python
# tg_worker.py:48-63
logging.info("⏳ Waiting for Telegram client to be fully ready...")
await asyncio.sleep(10)  # ⚠️ ФИКСИРОВАННАЯ ЗАДЕРЖКА

if not worker_instance.is_connected():
    logging.error("❌ Client lost connection during initialization")
    raise ConnectionError("Client not ready for processing")

logging.info("🔍 Additional client readiness check...")
await asyncio.sleep(4)  # ⚠️ ФИКСИРОВАННАЯ ЗАДЕРЖКА
```

**Предлагаемый код:**
```python
# tg_worker.py:48-63
logging.info("⏳ Waiting for Telegram client to be fully ready...")

# Активная проверка готовности с таймаутом
max_wait_time = 15  # Максимальное время ожидания (было 14)
check_interval = 0.5  # Проверять каждые 0.5 секунды
elapsed_time = 0

while elapsed_time < max_wait_time:
    if worker_instance.is_connected():
        # Дополнительная проверка: попробуем получить информацию о пользователе
        try:
            await worker_instance.client.get_me()
            logging.info("✅ Client is fully ready for channel processing")
            break
        except Exception as e:
            logging.warning(f"Client connected but not ready yet: {e}")
    
    await asyncio.sleep(check_interval)
    elapsed_time += check_interval
else:
    # Таймаут достигнут
    logging.error("❌ Client not ready after timeout")
    raise ConnectionError("Client not ready for processing")
```

**Шаги реализации:**
1. Открыть файл `tg_worker.py`
2. Найти строки 48-63
3. Заменить блок с фиксированными задержками на активную проверку
4. Протестировать запуск воркера - время должно сократиться с 14 секунд до 1-3 секунд

### Оптимизация 7: Асинхронная регистрация в API сервере

**Файл:** `worker.py` (строки 456-473)

**Проблема:** Синхронная регистрация в API сервере блокирует запуск.

**Текущий код:**
```python
# worker.py:456-473
try:
    import aiohttp
    session = await self._get_http_session()
    async with session.post(
        f"{get_api_base_url()}/api/internal/register-worker",
        json={...},
        timeout=aiohttp.ClientTimeout(total=5)
    ) as response:
        # ... обработка ответа ...
```

**Предлагаемый код:**
```python
# worker.py:456-473
# Запускаем регистрацию в фоновом режиме
asyncio.create_task(self._register_worker_in_api())

# В новом методе:
async def _register_worker_in_api(self):
    """Register worker in API server - non-critical"""
    try:
        import aiohttp
        import os as os_module
        session = await self._get_http_session()
        async with session.post(
            f"{get_api_base_url()}/api/internal/register-worker",
            json={
                "user_id": self.user_id,
                "pid": os_module.getpid(),
                "vip_level": self.vip_level
            },
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            if response.status == 200:
                self.logger.info(f"Worker {self.user_id} registered in API server")
            else:
                self.logger.warning(f"Failed to register in API server: HTTP {response.status}")
    except Exception as e:
        self.logger.error(f"Failed to register worker in API server: {e}")
```

**Шаги реализации:**
1. Открыть файл `worker.py`
2. Найти метод `_update_worker_status` (строки 419-474)
3. Заменить синхронную регистрацию на фоновую задачу
4. Добавить новый метод `_register_worker_in_api`
5. Протестировать - воркер должен запускаться без ожидания регистрации

### Оптимизация 5: Кэширование прогрева клиента

**Файлы:** `worker.py` (строки 1010-1026), `hybrid_processor.py` (строка 71)

**Проблема:** Прогрев клиента выполняется многократно для каждого канала.

**Текущий код:**
```python
# worker.py:1010-1026
async def _warm_up_client(self, limit: int = 10):
    """Прогревает клиент — грузит несколько диалогов."""
    if self._client_warmed_up:
        self.logger.debug("🔄 Клиент уже прогрет, пропускаем")
        return
    
    # ... загрузка диалогов ...
    self._client_warmed_up = True

# hybrid_processor.py:71
await self.worker._warm_up_client(limit=5)
```

**Предлагаемый код:**
```python
# worker.py:1010-1026
async def _warm_up_client(self, limit: int = 10):
    """Прогревает клиент — грузит несколько диалогов."""
    if self._client_warmed_up:
        self.logger.debug("🔄 Клиент уже прогрет, пропускаем")
        return True
    
    # ... загрузка диалогов ...
    self._client_warmed_up = True
    return True

# В hybrid_processor.py:71
# Убираем лишние прогревы - клиент уже прогрет после подключения
# await self.worker._warm_up_client(limit=5)  # Убрать или закомментировать
```

**Шаги реализации:**
1. Открыть `worker.py`, добавить `return True` в `_warm_up_client`
2. Открыть `hybrid_processor.py`, найти строку 71
3. Закомментировать или удалить вызов `_warm_up_client`
4. Протестировать пакетную обработку - прогрев должен выполняться только один раз

### Оптимизация 6: Оптимизация проверки доступности каналов

**Файл:** `hybrid_processor.py` (строки 63-125)

**Проблема:** Множественные медленные проверки для каждого канала.

**Текущий код:**
```python
# hybrid_processor.py:63-125
async def verify_channel_specific_readiness(self, channel_id: str) -> bool:
    # ... множество проверок ...
    # 1. Поиск в диалогах
    # 2. get_chat для username
    # 3. resolve для числового ID
    # 4. Поиск по названию
```

**Предлагаемый код:**
```python
# hybrid_processor.py:63-125
async def verify_channel_specific_readiness(self, channel_id: str) -> bool:
    """Проверка готовности для работы с каналом - оптимизированная"""
    try:
        if not self.worker.is_connected():
            return False
        
        # Быстрая проверка: если это username, сразу пробуем get_chat
        if channel_id.startswith('@'):
            try:
                chat = await self.worker.client.get_chat(channel_id)
                chat_id = getattr(chat, 'id', None)
                if chat_id is not None:
                    await self.worker.messenger.send(
                        "channel_accessible_direct", 
                        MessageRole.INTERNAL_LOG, 
                        level="success", 
                        channel_id=channel_id, 
                        chat_id=chat_id
                    )
                    return True
            except Exception as e:
                # Если не удалось, пробуем resolve
                pass
        
        # Для числовых ID используем resolve
        try:
            resolved_id = await self.worker._resolve_channel_identifier(channel_id)
            if resolved_id:
                # Пробуем получить chat чтобы убедиться что доступен
                chat = await self.worker.client.get_chat(resolved_id)
                await self.worker.messenger.send(
                    "channel_accessible_resolved", 
                    MessageRole.INTERNAL_LOG, 
                    level="success", 
                    channel_id=channel_id, 
                    resolved_id=resolved_id
                )
                return True
        except Exception as e:
            await self.worker.messenger.send(
                "channel_access_failed", 
                MessageRole.WEBSOCKET_LOG, 
                level="error", 
                channel=channel_id, 
                error=str(e)
            )
        
        return False
            
    except Exception as e:
        await self.worker.messenger.send(
            "channel_verification_error", 
            MessageRole.WEBSOCKET_LOG, 
            level="error", 
            channel=channel_id, 
            error=str(e)
        )
        return False
```

**Шаги реализации:**
1. Открыть `hybrid_processor.py`
2. Найти метод `verify_channel_specific_readiness`
3. Заменить логику на оптимизированную версию
4. Убрать поиск в диалогах и лишние проверки
5. Протестировать проверку каналов - должна работать быстрее

### Оптимизация 3: Фоновая загрузка аватара

**Файл:** `worker.py` (строки 664-666)

**Проблема:** Загрузка аватара блокирует запуск воркера.

**Текущий код:**
```python
# worker.py:664-666
await self._update_user_avatar()
```

**Предлагаемый код:**
```python
# worker.py:664-666
# Запускаем загрузку аватара в фоновом режиме
asyncio.create_task(self._update_user_avatar_background())

# Добавить новый метод:
async def _update_user_avatar_background(self):
    """Update user avatar in background - non-critical"""
    try:
        await self._update_user_avatar()
    except Exception as e:
        self.logger.warning(f"⚠️ Background avatar update failed (non-critical): {e}")
```

**Шаги реализации:**
1. Открыть `worker.py`
2. Найти вызов `_update_user_avatar()` в методе `connect`
3. Заменить на фоновую задачу
4. Добавить метод `_update_user_avatar_background`
5. Протестировать - воркер должен запускаться без ожидания аватара

---

## Этап 2: Средняя сложность (ожидает реализации)

### Оптимизация 4: Оптимизация пакетной обработки

**Файл:** `hybrid_processor.py` (строки 181-210, 215-244)

**Проблема:** Последовательная обработка каналов с повторяющимися прогревами.

**Текущий код:**
```python
# hybrid_processor.py:181-210
for i, channel_pair in enumerate(channel_pairs):
    self.current_rule = i + 1
    
    try:
        # ... логирование ...
        
        posts_count = await self.process_channel_batch(channel_pair, process_old_messages=process_old_messages)
        total_posts += posts_count
        
        # ... обработка ошибок ...

# hybrid_processor.py:215-244
async def process_channel_batch(self, channel_pair: ChannelPair, process_old_messages: bool = False) -> int:
    # ... 
    # Прогрев клиента для каждого канала
    await self.worker._warm_up_client(limit=5)  # ⚠️ УБРАТЬ
    # ...
```

**Предлагаемый код:**
```python
# hybrid_processor.py:181-210
# Предварительный прогрев клиента (один раз для всех каналов)
self.logger.info("🔄 Pre-warming client for all channels...")
await self.worker._warm_up_client(limit=10)
self.logger.info("✅ Client pre-warmed")

for i, channel_pair in enumerate(channel_pairs):
    self.current_rule = i + 1
    
    try:
        # ... логирование ...
        
        # process_channel_batch больше не вызывает _warm_up_client для каждого канала
        posts_count = await self.process_channel_batch(channel_pair, process_old_messages=process_old_messages)
        total_posts += posts_count
        
        # ... обработка ошибок ...

# hybrid_processor.py:215-244
async def process_channel_batch(self, channel_pair: ChannelPair, process_old_messages: bool = False) -> int:
    """Обработка накопленных постов для одного правила"""
    try:
        if not self.worker.is_connected():
            await self.worker.messenger.send("client_not_connected", MessageRole.INTERNAL_LOG, level="error", rule_id=channel_pair.id)
            await self.worker.user_logger.send_report(self.worker._get_localized_message("client_disconnected", rule_id=channel_pair.id), "error")
            return 0

        # Extract values to avoid type issues
        channel_pair_id = int(str(channel_pair.id))
        source_channel = str(channel_pair.source_channel)

        # DIAGNOSTIC: Log batch processing start
        self.worker.logger.info(f"📊 [BATCH_DIAGNOSTIC] Starting batch processing for rule {channel_pair_id}: {source_channel} → {channel_pair.target_channel}")

        # Send status about which channel is being processed
        await self.worker.messenger.send("processing_channel_status", MessageRole.USER_STATUS,
                                       channel=source_channel)

        # Проверяем доступность канала (упрощенная проверка без лишних прогревов)
        try:
            # Убираем прогрев клиента - он уже прогрет на этапе process_accumulated_posts
            # await self.worker._warm_up_client(limit=5)  # ⚠️ УБРАНО
            
            if not await self.verify_channel_specific_readiness(source_channel):
                await self.worker.messenger.send("channel_not_ready", MessageRole.INTERNAL_LOG, level="warning", channel=source_channel)
                return 0
        except Exception as e:
            await self.worker.messenger.send("channel_access_error", MessageRole.INTERNAL_LOG, level="error", channel=source_channel, error=str(e))
            await self.worker.user_logger.send_report(get_localized_message("channel_access_denied", channel=source_channel, error=str(e)), "error")
            return 0
        
        # ... остальной код без изменений ...
```

**Шаги реализации:**
1. Открыть `hybrid_processor.py`
2. Найти метод `process_accumulated_posts`
3. Добавить предварительный прогрев перед циклом
4. В `process_channel_batch` убрать вызов `_warm_up_client`
5. Протестировать пакетную обработку - прогрев только один раз

---

## Этап 3: Архитектурные изменения (ожидает реализации)

### Оптимизация 2: Параллельная инициализация компонентов

**Файл:** `worker.py` (строки 66-199)

**Проблема:** Последовательная инициализация компонентов блокирует скачивание сессии.

**Текущий код:**
```python
# worker.py:66-199 (в __init__)
# Все компоненты инициализируются последовательно
self.messenger = get_unified_messenger(user_id)
self.s3_manager = S3SessionManager()
self.s3_avatar_manager = S3AvatarManager()
self.ai_processor = AIProcessor(...)
self.balance_manager = BalanceManager(...)
# ... и т.д.

# БЛОКИРУЮЩАЯ операция - скачивание сессии
if self.s3_manager.session_exists(user_id):
    self.s3_manager.download_session(user_id, self.session_path)
```

**Предлагаемый код:**
```python
# worker.py:66-199 (переписываем __init__)
def __init__(self, user_id: int):
    self.api_id = os.getenv("TELEGRAM_API_ID")
    self.api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not self.api_id or not self.api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are required")
    
    self.user_id = user_id
    self.logger = self._setup_logging(user_id)
    
    # Инициализация messenger (нужна для логов)
    self.messenger = get_unified_messenger(user_id)
    self.messenger.logger = self.logger
    
    # Инициализация S3 менеджеров
    self.s3_manager = S3SessionManager()
    self.s3_avatar_manager = S3AvatarManager()
    
    # Проверяем существование сессии
    self.logger.info("☁️ Checking for existing session in S3...")
    session_exists = self.s3_manager.session_exists(user_id)
    
    if not session_exists:
        error_msg = f"No session found in S3 for user {user_id}"
        self.logger.error(error_msg)
        raise ValueError(f"No session found for user {user_id}. Authorization required.")
    
    # Подготовка пути к сессии
    import os as os_module
    process_id = os_module.getpid()
    self.session_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
    self.session_path = os.path.join(self.session_dir, f"{user_id}_{process_id}.session")
    os.makedirs(self.session_dir, exist_ok=True)
    
    self.logger.info(f"📁 Session directory: {self.session_dir}")
    self.logger.info(f"📄 Session file: {os.path.basename(self.session_path)}")
    
    # Параллельная инициализация компонентов и скачивание сессии
    self.logger.info("🔄 Starting parallel initialization...")
    import asyncio
    
    # Создаем event loop если его нет (для инициализации)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def init_all():
        """Параллельная инициализация всех компонентов"""
        
        # Задача 1: Скачивание сессии из S3
        async def download_session():
            self.logger.info("📥 Downloading session from S3...")
            await asyncio.to_thread(
                self.s3_manager.download_session,
                user_id,
                self.session_path
            )
            self.logger.info("✅ Session downloaded successfully from S3")
        
        # Задача 2: Инициализация компонентов (не зависят от сессии)
        async def init_components():
            self.logger.info("🧠 Initializing processing components...")
            self.ai_processor = AIProcessor(self.logger, self._log_worker_status)
            self.balance_manager = BalanceManager(self.logger)
            self.notification_manager = NotificationManager(
                user_id, self.logger, self._get_http_session, self._send_websocket_log
            )
            self.scheduler = MessageScheduler(
                None,
                self.logger,
                self._notify_admin_critical_error,
                self._log_worker_status,
                self.handle_flood_wait
            )
            self.media_handler = MediaHandler(
                user_id, None, self.logger,
                self._process_text_content_for_album,
                self._get_last_pending_scheduled_time,
                self._resolve_channel_identifier,
                self._deduct_balance_async,
                self._notify_admin_critical_error,
                self._process_with_hyperbolic_async
            )
            self.message_processor = MessageProcessor(
                user_id, self.logger,
                self.media_handler, self.ai_processor, self.balance_manager,
                self.scheduler, self.notification_manager,
                self._resolve_channel_identifier, self._log_worker_status,
                self._update_worker_activity, self._get_message_via_raw_api,
                self._log_scheduled_post, self._log_insufficient_funds_post,
                self._log_worker_error, self._send_websocket_log,
                self._update_stats
            )
            self.hybrid_processor = HybridProcessor(self)
            self.logger.info("✅ All processing components initialized successfully")
        
        # Запускаем обе задачи параллельно
        await asyncio.gather(
            download_session(),
            init_components()
        )
    
    # Выполняем параллельную инициализацию
    loop.run_until_complete(init_all())
    
    # Создаем Pyrogram клиент (после скачивания сессии)
    self.logger.info("🔧 Creating Telegram client...")
    self.client = Client(
        name=os.path.splitext(os.path.basename(self.session_path))[0],
        api_id=self.api_id,
        api_hash=self.api_hash,
        workdir=self.session_dir
    )
    
    # Обновляем processors с client
    self.scheduler.client = self.client
    self.media_handler.client = self.client
    
    self.logger.info("🎯 TelegramWorker initialization completed successfully")
```

**Шаги реализации:**
1. Открыть `worker.py`
2. Переписать метод `__init__` для поддержки параллельной инициализации
3. Разделить инициализацию на две параллельные задачи
4. Создать клиента только после скачивания сессии
5. Тщательно протестировать - все компоненты должны работать корректно

---

## Тестирование и мониторинг

### Метрики для отслеживания

Добавьте измерение времени запуска:

```python
# В начале main() в tg_worker.py
startup_start = time.time()

# В конце main(), перед idle()
startup_time = time.time() - startup_start
self.logger.info(f"📊 Worker startup time: {startup_time:.2f}s")
```

### Конфигурация через .env

```env
# Worker startup optimization
CLIENT_READY_CHECK_INTERVAL=0.5
CLIENT_READY_MAX_WAIT=15
UPDATE_AVATAR_BACKGROUND=true
PRE_WARM_CLIENT_FOR_BATCH=true
```

### Graceful degradation

```python
try:
    # Оптимизированный путь
    await optimized_approach()
except Exception as e:
    self.logger.warning(f"Optimization failed, using fallback: {e}")
    await fallback_approach()
```

---

## Порядок выполнения

1. **Этап 1 (выполнено):** Быстрые победы - уже реализованы
2. **Этап 2:** Оптимизация пакетной обработки
3. **Этап 3:** Параллельная инициализация компонентов

**Ожидаемый результат после всех оптимизаций:**
- Время до начала обработки новых постов: 6-10 секунд
- Улучшение: 70-85%

**Важно:** Тестируйте каждую оптимизацию отдельно перед переходом к следующей.</content>
</xai:function_call">## Заключение

План кодирования составлен на основе детального анализа пути запуска воркера. Большая часть оптимизаций (этап 1) уже реализована, что должно дать значительное улучшение производительности.

**Ключевые принципы для младшей кодер-модели:**
- Всегда проверяйте существующий код перед внесением изменений
- Тестируйте каждую оптимизацию отдельно
- Используйте логирование для отслеживания прогресса
- В случае проблем откатывайтесь к предыдущей версии

**Следующие шаги:**
1. Реализовать оптимизацию 4 (пакетная обработка)
2. Реализовать оптимизацию 2 (параллельная инициализация)
3. Добавить метрики и мониторинг
4. Протестировать в продакшене</content>
</xai:function_call">### Оптимизация 4: Оптимизация пакетной обработки

**Файл:** `hybrid_processor.py` (строки 181-210, 215-244)

**Проблема:** Последовательная обработка каналов с повторяющимися прогревами.

**Текущий код:**
```python
# hybrid_processor.py:181-210
for i, channel_pair in enumerate(channel_pairs):
    self.current_rule = i + 1
    
    try:
        # ... логирование ...
        
        posts_count = await self.process_channel_batch(channel_pair, process_old_messages=process_old_messages)
        total_posts += posts_count
        
        # ... обработка ошибок ...

# hybrid_processor.py:215-244
async def process_channel_batch(self, channel_pair: ChannelPair, process_old_messages: bool = False) -> int:
    # ... 
    # Прогрев клиента для каждого канала
    await self.worker._warm_up_client(limit=5)  # ⚠️ УБРАТЬ
    # ...
```

**Предлагаемый код:**
```python
# hybrid_processor.py:181-210
# Предварительный прогрев клиента (один раз для всех каналов)
self.logger.info("🔄 Pre-warming client for all channels...")
await self.worker._warm_up_client(limit=10)
self.logger.info("✅ Client pre-warmed")

for i, channel_pair in enumerate(channel_pairs):
    self.current_rule = i + 1
    
    try:
        # ... логирование ...
        
        # process_channel_batch больше не вызывает _warm_up_client для каждого канала
        posts_count = await self.process_channel_batch(channel_pair, process_old_messages=process_old_messages)
        total_posts += posts_count
        
        # ... обработка ошибок ...

# hybrid_processor.py:215-244
async def process_channel_batch(self, channel_pair: ChannelPair, process_old_messages: bool = False) -> int:
    """Обработка накопленных постов для одного правила"""
    try:
        if not self.worker.is_connected():
            await self.worker.messenger.send("client_not_connected", MessageRole.INTERNAL_LOG, level="error", rule_id=channel_pair.id)
            await self.worker.user_logger.send_report(self.worker._get_localized_message("client_disconnected", rule_id=channel_pair.id), "error")
            return 0

        # Extract values to avoid type issues
        channel_pair_id = int(str(channel_pair.id))
        source_channel = str(channel_pair.source_channel)

        # DIAGNOSTIC: Log batch processing start
        self.worker.logger.info(f"📊 [BATCH_DIAGNOSTIC] Starting batch processing for rule {channel_pair_id}: {source_channel} → {channel_pair.target_channel}")

        # Send status about which channel is being processed
        await self.worker.messenger.send("processing_channel_status", MessageRole.USER_STATUS,
                                       channel=source_channel)

        # Проверяем доступность канала (упрощенная проверка без лишних прогревов)
        try:
            # Убираем прогрев клиента - он уже прогрет на этапе process_accumulated_posts
            # await self.worker._warm_up_client(limit=5)  # ⚠️ УБРАНО
            
            if not await self.verify_channel_specific_readiness(source_channel):
                await self.worker.messenger.send("channel_not_ready", MessageRole.INTERNAL_LOG, level="warning", channel=source_channel)
                return 0
        except Exception as e:
            await self.worker.messenger.send("channel_access_error", MessageRole.INTERNAL_LOG, level="error", channel=source_channel, error=str(e))
            await self.worker.user_logger.send_report(get_localized_message("channel_access_denied", channel=source_channel, error=str(e)), "error")
            return 0
        
        # ... остальной код без изменений ...
```

**Шаги реализации:**
1. Открыть `hybrid_processor.py`
2. Найти метод `process_accumulated_posts`
3. Добавить предварительный прогрев перед циклом
4. В `process_channel_batch` убрать вызов `_warm_up_client`
5. Протестировать пакетную обработку - прогрев только один раз

---

## Этап 3: Архитектурные изменения (ожидает реализации)

### Оптимизация 2: Параллельная инициализация компонентов

**Файл:** `worker.py` (строки 66-199)

**Проблема:** Последовательная инициализация компонентов блокирует скачивание сессии.

**Текущий код:**
```python
# worker.py:66-199 (в __init__)
# Все компоненты инициализируются последовательно
self.messenger = get_unified_messenger(user_id)
self.s3_manager = S3SessionManager()
self.s3_avatar_manager = S3AvatarManager()
self.ai_processor = AIProcessor(...)
self.balance_manager = BalanceManager(...)
# ... и т.д.

# БЛОКИРУЮЩАЯ операция - скачивание сессии
if self.s3_manager.session_exists(user_id):
    self.s3_manager.download_session(user_id, self.session_path)
```

**Предлагаемый код:**
```python
# worker.py:66-199 (переписываем __init__)
def __init__(self, user_id: int):
    self.api_id = os.getenv("TELEGRAM_API_ID")
    self.api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not self.api_id or not self.api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are required")
    
    self.user_id = user_id
    self.logger = self._setup_logging(user_id)
    
    # Инициализация messenger (нужна для логов)
    self.messenger = get_unified_messenger(user_id)
    self.messenger.logger = self.logger
    
    # Инициализация S3 менеджеров
    self.s3_manager = S3SessionManager()
    self.s3_avatar_manager = S3AvatarManager()
    
    # Проверяем существование сессии
    self.logger.info("☁️ Checking for existing session in S3...")
    session_exists = self.s3_manager.session_exists(user_id)
    
    if not session_exists:
        error_msg = f"No session found in S3 for user {user_id}"
        self.logger.error(error_msg)
        raise ValueError(f"No session found for user {user_id}. Authorization required.")
    
    # Подготовка пути к сессии
    import os as os_module
    process_id = os_module.getpid()
    self.session_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
    self.session_path = os.path.join(self.session_dir, f"{user_id}_{process_id}.session")
    os.makedirs(self.session_dir, exist_ok=True)
    
    self.logger.info(f"📁 Session directory: {self.session_dir}")
    self.logger.info(f"📄 Session file: {os.path.basename(self.session_path)}")
    
    # Параллельная инициализация компонентов и скачивание сессии
    self.logger.info("🔄 Starting parallel initialization...")
    import asyncio
    
    # Создаем event loop если его нет (для инициализации)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def init_all():
        """Параллельная инициализация всех компонентов"""
        
        # Задача 1: Скачивание сессии из S3
        async def download_session():
            self.logger.info("📥 Downloading session from S3...")
            await asyncio.to_thread(
                self.s3_manager.download_session,
                user_id,
                self.session_path
            )
            self.logger.info("✅ Session downloaded successfully from S3")
        
        # Задача 2: Инициализация компонентов (не зависят от сессии)
        async def init_components():
            self.logger.info("🧠 Initializing processing components...")
            self.ai_processor = AIProcessor(self.logger, self._log_worker_status)
            self.balance_manager = BalanceManager(self.logger)
            self.notification_manager = NotificationManager(
                user_id, self.logger, self._get_http_session, self._send_websocket_log
            )
            self.scheduler = MessageScheduler(
                None,
                self.logger,
                self._notify_admin_critical_error,
                self._log_worker_status,
                self.handle_flood_wait
            )
            self.media_handler = MediaHandler(
                user_id, None, self.logger,
                self._process_text_content_for_album,
                self._get_last_pending_scheduled_time,
                self._resolve_channel_identifier,
                self._deduct_balance_async,
                self._notify_admin_critical_error,
                self._process_with_hyperbolic_async
            )
            self.message_processor = MessageProcessor(
                user_id, self.logger,
                self.media_handler, self.ai_processor, self.balance_manager,
                self.scheduler, self.notification_manager,
                self._resolve_channel_identifier, self._log_worker_status,
                self._update_worker_activity, self._get_message_via_raw_api,
                self._log_scheduled_post, self._log_insufficient_funds_post,
                self._log_worker_error, self._send_websocket_log,
                self._update_stats
            )
            self.hybrid_processor = HybridProcessor(self)
            self.logger.info("✅ All processing components initialized successfully")
        
        # Запускаем обе задачи параллельно
        await asyncio.gather(
            download_session(),
            init_components()
        )
    
    # Выполняем параллельную инициализацию
    loop.run_until_complete(init_all())
    
    # Создаем Pyrogram клиент (после скачивания сессии)
    self.logger.info("🔧 Creating Telegram client...")
    self.client = Client(
        name=os.path.splitext(os.path.basename(self.session_path))[0],
        api_id=self.api_id,
        api_hash=self.api_hash,
        workdir=self.session_dir
    )
    
    # Обновляем processors с client
    self.scheduler.client = self.client
    self.media_handler.client = self.client
    
    self.logger.info("🎯 TelegramWorker initialization completed successfully")
```

**Шаги реализации:**
1. Открыть `worker.py`
2. Переписать метод `__init__` для поддержки параллельной инициализации
3. Разделить инициализацию на две параллельные задачи
4. Создать клиента только после скачивания сессии
5. Тщательно протестировать - все компоненты должны работать корректно

---

## Тестирование и мониторинг

### Метрики для отслеживания

Добавьте измерение времени запуска:

```python
# В начале main() в tg_worker.py
startup_start = time.time()

# В конце main(), перед idle()
startup_time = time.time() - startup_start
self.logger.info(f"📊 Worker startup time: {startup_time:.2f}s")
```

### Конфигурация через .env

```env
# Worker startup optimization
CLIENT_READY_CHECK_INTERVAL=0.5
CLIENT_READY_MAX_WAIT=15
UPDATE_AVATAR_BACKGROUND=true
PRE_WARM_CLIENT_FOR_BATCH=true
```

### Graceful degradation

```python
try:
    # Оптимизированный путь
    await optimized_approach()
except Exception as e:
    self.logger.warning(f"Optimization failed, using fallback: {e}")
    await fallback_approach()
```

---

## Порядок выполнения

1. **Этап 1 (выполнено):** Быстрые победы - уже реализованы
2. **Этап 2:** Оптимизация пакетной обработки
3. **Этап 3:** Параллельная инициализация компонентов

**Ожидаемый результат после всех оптимизаций:**
- Время до начала обработки новых постов: 6-10 секунд
- Улучшение: 70-85%

**Важно:** Тестируйте каждую оптимизацию отдельно перед переходом к следующей.

## Заключение

План кодирования составлен на основе детального анализа пути запуска воркера. Большая часть оптимизаций (этап 1) уже реализована, что должно дать значительное улучшение производительности.

**Ключевые принципы для младшей кодер-модели:**
- Всегда проверяйте существующий код перед внесением изменений
- Тестируйте каждую оптимизацию отдельно
- Используйте логирование для отслеживания прогресса
- В случае проблем откатывайтесь к предыдущей версии

**Следующие шаги:**
1. Реализовать оптимизацию 4 (пакетная обработка)
2. Реализовать оптимизацию 2 (параллельная инициализация)
3. Добавить метрики и мониторинг
4. Протестировать в продакшене</content>
</xai:function_call name="attempt_completion">
<parameter name="result">План кодирования оптимизации запуска воркера создан и записан в `/opt/taiger/plans/worker_startup_optimization_coding.md`. 

План включает:
- Подробное описание всех 7 оптимизаций с примерами кода
- Статус выполнения (5 оптимизаций уже выполнены)
- Пошаговые инструкции для реализации оставшихся оптимизаций
- Метрики для мониторинга и тестирования
- Graceful degradation подходы

План структурирован для младшей кодер-модели с четкими шагами и образцами кода для каждой оптимизации.
