#!/usr/bin/env python3
"""
Test script to verify the status/report race condition fix.
This script simulates concurrent status and report operations to ensure
permanent reports are not overwritten by subsequent status updates.
"""

import asyncio
import logging
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_worker.unified_messenger import get_unified_messenger

# Setup logging to see grace markers
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

async def test_race_condition():
    """Test the race condition fix."""
    print("🧪 Testing status/report race condition fix...")

    # Create a messenger instance (using a test user ID)
    test_user_id = 999999  # Use a test user ID that won't interfere with real users
    messenger = get_unified_messenger(test_user_id)

    print("1. Sending initial status message...")
    await messenger.send_status("🔄 Initial processing...")

    print("2. Sending a report (should promote the status to permanent)...")
    await messenger.send_report("✅ Task completed successfully!", "success")

    print("3. Immediately sending another status (should NOT overwrite the report)...")
    await messenger.send_status("🔄 Next task starting...")

    print("4. Sending another report...")
    await messenger.send_report("✅ Second task completed!", "success")

    print("5. Final status update...")
    await messenger.send_status("🔄 All tasks done")

    print("✅ Test completed. Check logs for 'grace:' markers to verify the fix.")

if __name__ == "__main__":
    asyncio.run(test_race_condition())