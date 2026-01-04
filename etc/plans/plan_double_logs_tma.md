# Plan: Fix Duplicate Logs and Localization in TMA

## Problem Analysis
1.  **Duplicate Logs**: The system uses both `UnifiedMessenger` (new) and `_log_worker_status`/`_send_websocket_log` (old) simultaneously. This results in the same event being logged twice to the TMA WebSocket.
2.  **Localization**: The "Worker ready" message is often stuck in Russian because the language preference is not consistently passed or loaded in the worker process, defaulting to 'ru'.

## Proposed Changes

### 1. Consolidate Logging in `tg_worker.py`
Remove redundant calls to `_log_worker_status` when `messenger.send` is already covering the event.

```python
# grace: [LOG_CONSOLIDATION] Remove redundant status logging
<<<<<<< SEARCH
:start_line:106
                logging.info(f"⏳ Worker entering idle state, waiting for messages...")
                await worker_instance._log_worker_status("worker_ready", worker_instance._get_localized_message("agent_ready_full"), "info")
=======
                logging.info(f"⏳ Worker entering idle state, waiting for messages...")
                # UnifiedMessenger will handle this in start_listening()
>>>>>>> REPLACE
```

### 2. Fix Duplication in `HybridProcessor`
Remove calls to `_log_worker_status` in `telegram_worker/hybrid_processor.py` as it already uses `messenger.send`.

```python
# grace: [LOG_CONSOLIDATION] Remove redundant status logging in HybridProcessor
<<<<<<< SEARCH
:start_line:66
            if not self.worker.is_connected():
                await self.worker._log_worker_status("client_not_connected", f"❌ Client not connected for channel {channel_id}", "error")
                return False
=======
            if not self.worker.is_connected():
                # messenger.send is used in start_hybrid_processing for general connection errors
                return False
>>>>>>> REPLACE
```

### 3. Improve `UnifiedMessenger` Localization
Ensure `language_code` is loaded once and used consistently.

```python
# grace: [LOCALIZATION_FIX] Ensure language is loaded and used
<<<<<<< SEARCH
:start_line:166
    async def send(self, key: str, role: MessageRole, level: str = "info", **kwargs):
        """
        Отправить сообщение в зависимости от роли.

        Args:
            key: Ключ локализованного сообщения
            role: Роль определяет аудиторию и поведение
            level: Уровень логирования (для INTERNAL_LOG)
            **kwargs: Параметры для локализации
        """
        try:
            # Получить локализованное сообщение
            user_lang = await self._get_user_language()
=======
    async def send(self, key: str, role: MessageRole, level: str = "info", **kwargs):
        """
        Отправить сообщение в зависимости от роли.
        """
        try:
            # grace: Use cached language or load it
            if not hasattr(self, '_user_lang') or self._user_lang is None:
                self._user_lang = await self._get_user_language()
            user_lang = self._user_lang
>>>>>>> REPLACE
```

### 4. Refactor `TelegramWorker` Status Methods
Redirect `_log_worker_status` to `UnifiedMessenger` to ensure all logs go through the same localization and deduplication logic.

```python
# grace: [LOG_UNIFICATION] Redirect old status methods to UnifiedMessenger
<<<<<<< SEARCH
:start_line:476
    async def _log_worker_status(self, status_type: str, message_key: str, level: str = "info", **params):
        """Send worker status update to dashboard via WebSocket."""
        # Send to WebSocket dashboard
        try:
            session = await self._get_http_session()
            payload = {
                "user_id": self.user_id,
                "log_type": status_type,
                "message_key": message_key,
                "message_params": params,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            async with session.post(
                f"{get_api_base_url()}/api/internal/log",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                if response.status != 200:
                    self.logger.debug(f"Failed to send WebSocket log: HTTP {response.status}")
        except Exception as e:
            self.logger.debug(f"Failed to send WebSocket log: {e}")
=======
    async def _log_worker_status(self, status_type: str, message_key: str, level: str = "info", **params):
        """Redirect to UnifiedMessenger to prevent duplication and fix localization."""
        role = MessageRole.INTERNAL_LOG
        if level == "success" or status_type == "worker_ready":
            role = MessageRole.USER_STATUS
        
        await self.messenger.send(message_key, role, level=level, **params)
>>>>>>> REPLACE
```

## Implementation Steps
1.  ✅ **Modify `telegram_worker/unified_messenger.py`**: Add language caching and WEBSOCKET_LOG role.
2.  ✅ **Modify `telegram_worker/worker.py`**: Redirect `_log_worker_status` and `_send_websocket_log` to `messenger.send` with WEBSOCKET_LOG role.
3.  ✅ **Modify `tg_worker.py`**: Remove redundant manual logging calls.
4.  ✅ **Modify `telegram_worker/hybrid_processor.py`**: Remove redundant `_log_worker_status` calls.
5.  ✅ **Verify**: Syntax check passed, WebSocket logging test successful.

## Additional Fix Applied
- **Added WEBSOCKET_LOG role** to distinguish between bot logs (`INTERNAL_LOG`) and WebSocket/TMA logs (`WEBSOCKET_LOG`)
- **Fixed endpoint routing**: WebSocket logs now correctly go to `/api/internal/log` instead of `/api/internal/bot-log`
