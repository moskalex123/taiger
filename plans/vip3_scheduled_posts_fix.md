# VIP3 Scheduled Posts Count Fix

## Problem Analysis

### Current Issue
The worker sends an incorrect report about remaining scheduled posts for VIP=3 users:

**Report shows:**
- Illusion of deception: 8 posts
- Living Ocean: 7 posts
- International Geographic: 5 posts
- Wildlife: 1 post

**Manual verification shows:**
- Wildlife: 0 posts (correct)
- Living Ocean: 5 posts (should be 5, not 7)
- Illusion of deception: 8 posts (correct)
- International Geographic: 3 posts (should be 3, not 5)

### Root Cause
The [`_get_scheduled_posts_count`](telegram_worker/hybrid_processor.py:686) method in [`telegram_worker/hybrid_processor.py`](telegram_worker/hybrid_processor.py:686-722) queries the database for scheduled posts, which is **not the source of truth**. The database may contain:
- Posts that were already sent but not updated in DB
- Posts with incorrect status
- Posts that failed to schedule properly

The correct source of truth is **Telegram itself**, as it manages the actual scheduled messages.

## Solution

Use Telegram's `GetScheduledHistory` API to retrieve the actual count of scheduled messages directly from Telegram for each target channel.

## Implementation Plan

### Step 1: Modify `_get_scheduled_posts_count` method

**File:** `telegram_worker/hybrid_processor.py`

**Current implementation (lines 686-722):**
```python
async def _get_scheduled_posts_count(self, channel_pair_id: int) -> int:
    """Получить количество запланированных постов для правила"""
    try:
        from datetime import datetime, timezone
    
        async with async_session() as session:
            # Получаем все pending посты для отладки
            debug_result = await session.execute(
                select(ScheduledPost).where(
                    ScheduledPost.channel_pair_id == channel_pair_id,
                    ScheduledPost.status == 'pending'
                )
            )
            all_pending = debug_result.scalars().all()
    
            # Логируем для отладки
            self.worker.logger.info(f"🔍 [VIP3_REPORT] Found {len(all_pending)} pending posts for channel_pair {channel_pair_id}")
            for post in all_pending:
                scheduled_time = post.scheduled_at.isoformat() if post.scheduled_at else "None"
                self.worker.logger.info(f"🔍 [VIP3_REPORT] Post ID {post.id}: scheduled_at={scheduled_time}, status={post.status}")
    
            # Считаем только посты, которые запланированы на будущее (исключаем None)
            now = datetime.now(timezone.utc)
            future_posts = [p for p in all_pending if p.scheduled_at is not None and p.scheduled_at > now]
    
            self.worker.logger.info(f"🔍 [VIP3_REPORT] Future posts: {len(future_posts)}")
            for post in future_posts:
                scheduled_time = post.scheduled_at.isoformat() if post.scheduled_at else "None"
                self.worker.logger.info(f"🔍 [VIP3_REPORT] Future post ID {post.id}: scheduled_at={scheduled_time}")
    
            count = len(future_posts)
            self.worker.logger.info(f"🔍 [VIP3_REPORT] Future/unscheduled posts count: {count}")
    
            return count
    except Exception as e:
        self.worker.logger.error(f"❌ [VIP3_REPORT] Error getting scheduled posts count: {e}")
        return 0
```

**New implementation:**
```python
async def _get_scheduled_posts_count(self, channel_pair_id: int) -> int:
    """Получить количество запланированных постов для правила из Telegram"""
    try:
        # Get channel pair to find target channel
        async with async_session() as session:
            result = await session.execute(
                select(ChannelPair).where(ChannelPair.id == channel_pair_id)
            )
            channel_pair = result.scalar_one_or_none()
            
            if not channel_pair:
                self.worker.logger.warning(f"🔍 [VIP3_REPORT] Channel pair {channel_pair_id} not found")
                return 0
        
        # Resolve target channel ID
        target_channel = str(channel_pair.target_channel)
        resolved_channel_id = await self.worker._resolve_channel_identifier(target_channel)
        
        if not resolved_channel_id:
            self.worker.logger.warning(f"🔍 [VIP3_REPORT] Could not resolve channel {target_channel}")
            return 0
        
        # Get scheduled messages directly from Telegram
        try:
            from pyrogram.raw.functions.messages.get_scheduled_history import GetScheduledHistory
            from pyrogram.raw.types.input_peer_channel import InputPeerChannel
            
            # Get chat to extract access_hash
            chat = await self.worker.client.get_chat(resolved_channel_id)
            
            # Create InputPeerChannel with access_hash
            input_peer = InputPeerChannel(
                channel_id=resolved_channel_id,
                access_hash=chat.access_hash
            )
            
            # Call GetScheduledHistory
            result = await self.worker.client.invoke(
                GetScheduledHistory(
                    peer=input_peer,
                    limit=100  # Get up to 100 scheduled messages
                )
            )
            
            # Count scheduled messages
            count = len(result.messages)
            
            self.worker.logger.info(
                f"🔍 [VIP3_REPORT] Channel {target_channel} (ID: {resolved_channel_id}): "
                f"{count} scheduled messages from Telegram"
            )
            
            return count
            
        except Exception as e:
            self.worker.logger.error(
                f"❌ [VIP3_REPORT] Error getting scheduled history from Telegram for {target_channel}: {e}"
            )
            return 0
            
    except Exception as e:
        self.worker.logger.error(f"❌ [VIP3_REPORT] Error in _get_scheduled_posts_count: {e}")
        return 0
```

### Step 2: Update imports (if needed)

**File:** `telegram_worker/hybrid_processor.py`

**Add at the top of the file (around line 24):**
```python
from pyrogram.raw.functions.messages.get_scheduled_history import GetScheduledHistory
from pyrogram.raw.types.input_peer_channel import InputPeerChannel
```

Note: These imports may already be available via the worker instance, but it's cleaner to import them directly.

### Step 3: Update method signature

The method signature remains the same:
```python
async def _get_scheduled_posts_count(self, channel_pair_id: int) -> int:
```

### Step 4: Test the implementation

After implementing the changes, verify:
1. The report shows correct counts matching manual verification
2. No errors occur when accessing scheduled messages
3. The method handles edge cases (no scheduled messages, inaccessible channels)

## Benefits

1. **Accuracy**: Gets the actual count from Telegram, the source of truth
2. **Reliability**: Not affected by database inconsistencies
3. **Simplicity**: Direct API call, no complex filtering logic
4. **Performance**: Single API call per channel instead of database queries

## Edge Cases to Handle

1. **Channel not accessible**: Return 0 and log warning
2. **No scheduled messages**: Return 0 (normal case)
3. **Channel resolution failure**: Return 0 and log error
4. **API rate limits**: The method should handle FloodWait errors gracefully

## Code Grace Markup for Junior Developer

```grace
# File: telegram_worker/hybrid_processor.py
# Method: _get_scheduled_posts_count (lines 686-722)

# TASK: Replace database-based counting with Telegram API call
# REASON: Database is not source of truth for scheduled posts
# IMPACT: Fixes incorrect VIP3 scheduled posts report

# STEPS:
# 1. Import GetScheduledHistory and InputPeerChannel from pyrogram.raw
# 2. Get channel_pair from database to find target_channel
# 3. Resolve target_channel to numeric ID using _resolve_channel_identifier
# 4. Get chat info to extract access_hash
# 5. Create InputPeerChannel with channel_id and access_hash
# 6. Invoke GetScheduledHistory with the peer
# 7. Return len(result.messages) as the count
# 8. Handle exceptions gracefully with logging

# NOTE: Remove all database queries for ScheduledPost
# NOTE: Keep the same method signature
# NOTE: Maintain existing logging format with [VIP3_REPORT] prefix
```

## Verification Checklist

- [ ] Implementation completed
- [ ] Test with channels that have scheduled posts
- [ ] Test with channels that have no scheduled posts
- [ ] Test with inaccessible channels
- [ ] Verify report matches manual verification
- [ ] Check logs for errors
- [ ] Ensure no database queries for ScheduledPost remain in this method
