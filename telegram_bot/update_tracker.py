import time
import logging
from typing import Set

logger = logging.getLogger(__name__)

class UpdateTracker:
    """Tracks processed updates to prevent reprocessing after restarts"""
    
    def __init__(self):
        self._processed_updates: Set[int] = set()
        self._last_cleanup_time = time.time()
    
    def is_processed(self, update_id: int) -> bool:
        """Check if an update has already been processed"""
        self._cleanup_old_updates()
        return update_id in self._processed_updates
    
    def mark_processed(self, update_id: int):
        """Mark an update as processed"""
        self._processed_updates.add(update_id)
    
    def _cleanup_old_updates(self):
        """Clean up old processed updates to prevent memory leaks"""
        current_time = time.time()
        if current_time - self._last_cleanup_time > 300:  # Clean up every 5 minutes
            # Keep only updates from the last 10 minutes
            cutoff_time = int(current_time - 600)
            self._processed_updates = {update_id for update_id in self._processed_updates if update_id > cutoff_time}
            self._last_cleanup_time = current_time
            logger.debug(f"Cleaned up processed updates, now tracking {len(self._processed_updates)} updates")
    
    def clear_all(self):
        """Clear all tracked updates - useful on startup"""
        count = len(self._processed_updates)
        self._processed_updates.clear()
        logger.info(f"Cleared {count} tracked updates")

# Global instance
update_tracker = UpdateTracker()