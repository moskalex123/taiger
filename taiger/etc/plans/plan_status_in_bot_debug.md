# Debug Plan: Permanent Log Overwriting Issue

## 1. Problem Description
Permanent reports (e.g., successful scheduling) are occasionally being overwritten or deleted by subsequent status updates. This happens because the "status slot" (the ID of the last transient message) is not being cleared or synchronized correctly across concurrent worker tasks.

## 2. Hypotheses
- **H1 (Race Condition):** A status update is triggered immediately after a report is sent, but before the `last_status_message_id` is cleared in Redis/DB.
- **H2 (Stale Cache):** The `UnifiedMessenger` instance in one task has a cached `last_status_message_id` that was just promoted to a report by another task.
- **H3 (API Logic):** The `/api/internal/bot-status` endpoint deletes the `last_status_message_id` provided in the request without verifying if that message has already been "promoted" to a permanent report.

## 3. Debugging Steps

### Step 1: Enhanced Logging (Grace Markup)
Add detailed diagnostic logs to [`telegram_worker/unified_messenger.py`](telegram_worker/unified_messenger.py) and [`api/telegram.py`](api/telegram.py) to track the lifecycle of a message ID.

[`telegram_worker/unified_messenger.py`](telegram_worker/unified_messenger.py:284)
```python
# Add unique request ID to track flow across worker and API
import uuid
request_id = str(uuid.uuid4())
self.logger.info(f"grace: [REPORT_START] req={request_id} user={self.user_id} last_id={self.last_status_message_id}")
```

[`api/telegram.py`](api/telegram.py:778)
```python
# Log the incoming report request
logger.info(f"grace: [API_REPORT] user={request.user_id} target_id={request.last_status_message_id}")
```

### Step 2: Reproduction Script
Create a script that fires a report followed immediately by multiple status updates to trigger the race condition.

### Step 3: Logic Verification
Check if `_clear_status_slot()` is called *before* or *after* the API call. Currently, it's after, which leaves a gap.

## 4. Proposed Fix Strategy (Conceptual)

### A. Atomic "Promote and Clear"
The API should ensure that once a message is promoted to a report, any subsequent status requests for that specific `message_id` are ignored or treated as "new message" requests.

### B. Client-Side Guard
Update `UnifiedMessenger` to invalidate the local `last_status_message_id` *immediately* before making the API call to `bot-report`, and only restore/update it if the call fails.

[`telegram_worker/unified_messenger.py`](telegram_worker/unified_messenger.py:278)
```python
async def _send_user_report(self, message: str, report_type: str = "success"):
    async with self._status_lock:
        # grace: Capture ID and clear locally BEFORE network call
        target_id = self.last_status_message_id
        self.last_status_message_id = None 
        # ... perform API call with target_id ...
```

### C. API-Side Validation
Modify `send_bot_status` to verify if the `last_status_message_id` it's about to delete is still marked as a "status" message in a local cache or if it has been recently promoted.
