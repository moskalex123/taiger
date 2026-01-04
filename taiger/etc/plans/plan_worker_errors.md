# Plan for Fixing Worker Errors (User ID 2)

## 1. Fix UnboundLocalError in MessageProcessor
The `messenger` instance must be available in `process_rule`.

```python
# telegram_worker/message_processor.py

async def process_rule(self, rule: ChannelPair, message: Message, client: Client) -> bool:
    # ADD THIS:
    from .unified_messenger import get_unified_messenger
    messenger = get_unified_messenger(self.user_id)
    
    # ... existing code ...
    await messenger.send("processing_text", MessageRole.USER_STATUS)
```

## 2. Implement Missing API Endpoints
Add the missing internal logging endpoints to `main.py` to stop 404 errors.

```python
# main.py

@app.post("/api/internal/bot-log")
async def bot_log(request: Request):
    data = await request.json()
    # Logic to store or broadcast log
    return {"status": "success"}

@app.post("/api/internal/bot-status")
async def bot_status(request: Request):
    # ...
    return {"status": "success", "message_id": 123}

@app.post("/api/internal/bot-report")
async def bot_report(request: Request):
    # ...
    return {"status": "success"}
```

## 3. Optimize Telegram Client Warm-up
Reduce `GetDialogs` calls to avoid FloodWait. Cache resolved channel IDs.

```python
# telegram_worker/worker.py (Conceptual)

# Instead of:
# await client.get_dialogs(limit=5) # Every time

# Use a flag or cache:
if not self._client_warmed_up:
    await client.get_dialogs(limit=20)
    self._client_warmed_up = True
```

## 4. Graceful Error Handling (Grace Markup)
Implement better try-except blocks in `UnifiedMessenger` to prevent fallback spam.

```python
# telegram_worker/unified_messenger.py

async def _send_internal_log(self, message: str, level: str, **kwargs):
    try:
        # ... attempt API call ...
    except Exception as e:
        # Graceful fallback to local logger only once
        self.logger.error(f"Log API unavailable: {e}")
```
