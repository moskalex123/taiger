#!/usr/bin/env python3
"""
Simple test script to verify balance functionality is working correctly.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append('/opt/taiger')

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot.handlers import callback_query_handler
from telegram_bot.keyboards import BotKeyboards
from models import User

async def test_balance_functionality_simple():
    """Simple test to verify balance functionality works"""
    print("🧪 Testing balance functionality with simple approach...")

    # Test 1: Balance button callback
    print("  1. Testing balance button callback...")
    try:
        # Create a simple mock query
        mock_query = MagicMock()
        mock_query.data = "balance"
        mock_query.answer = AsyncMock()

        # Mock the edit_message_text to capture the call
        mock_query.edit_message_text = AsyncMock()

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_user = MagicMock()
        mock_user.id = 12345
        mock_update.effective_user = mock_user

        mock_context = MagicMock()

        # Mock database user
        mock_db_user = MagicMock()
        mock_db_user.id = 12345
        mock_db_user.balance = 7.5
        mock_db_user.VIP_level = 3
        mock_db_user.free_batteries_total = 4.5

        with patch('telegram_bot.handlers_clean.async_session') as mock_async_session:
            # Create async mock session
            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_session.close = AsyncMock()
            mock_async_session.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_db_user
            mock_session.execute.return_value = mock_result

            # Test the callback handler
            await callback_query_handler(mock_update, mock_context)

            # Verify that edit_message_text was called
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args

            # Check message content
            message_text = call_args[0][0]
            assert "Ваш баланс: <b>7.5🔋</b>" in message_text
            assert "VIP уровень: <b>3</b>" in message_text
            assert "Всего заработано: <b>4.5🔋</b>" in message_text

            print("     ✅ Balance button callback works correctly")

        # Test 2: Earn battery button callback
        print("  2. Testing earn battery button callback...")
        mock_query.data = "earn_battery"
        mock_query.edit_message_text = AsyncMock()

        mock_db_user.time_of_last_earned_battery = None  # Never claimed before

        with patch('telegram_bot.handlers_clean.async_session') as mock_async_session, \
             patch('telegram_bot.handlers_clean.os.getenv') as mock_getenv:

            mock_getenv.side_effect = lambda key, default=None: {
                'REST_HOURS_BETWEEN_EARNED_BATTERY': '8'
            }.get(key, default)

            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_session.close = AsyncMock()
            mock_async_session.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_db_user
            mock_session.execute.return_value = mock_result

            await callback_query_handler(mock_update, mock_context)

            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args
            message_text = call_args[0][0]

            assert "Всего заработано: <b>4.5🔋</b>" in message_text
            assert "Вы можете получить батарейку прямо сейчас!" in message_text

            print("     ✅ Earn battery button callback works correctly")

        # Test 3: Buy battery button callback
        print("  3. Testing buy battery button callback...")
        mock_query.data = "buy_battery"
        mock_query.edit_message_text = AsyncMock()

        with patch('telegram_bot.handlers_clean.async_session') as mock_async_session:
            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_session.close = AsyncMock()
            mock_async_session.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_db_user
            mock_session.execute.return_value = mock_result

            await callback_query_handler(mock_update, mock_context)

            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args
            message_text = call_args[0][0]

            assert "Покупка батареек будет доступна в будущем" in message_text

            print("     ✅ Buy battery button callback works correctly")

        # Test 4: Claim battery too early
        print("  4. Testing claim battery too early...")
        mock_query.data = "claim_battery"
        mock_query.edit_message_text = AsyncMock()

        mock_db_user.time_of_last_earned_battery = datetime.utcnow() - timedelta(hours=2)  # Only 2 hours ago

        with patch('telegram_bot.handlers_clean.async_session') as mock_async_session, \
             patch('telegram_bot.handlers_clean.os.getenv') as mock_getenv, \
             patch('telegram_bot.handlers_clean.datetime') as mock_datetime:

            mock_getenv.side_effect = lambda key, default=None: {
                'REST_HOURS_BETWEEN_EARNED_BATTERY': '8'
            }.get(key, default)

            mock_now = datetime.utcnow()
            mock_datetime.utcnow.return_value = mock_now

            mock_session = MagicMock()
            mock_session.execute = AsyncMock()
            mock_session.close = AsyncMock()
            mock_async_session.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_db_user
            mock_session.execute.return_value = mock_result

            await callback_query_handler(mock_update, mock_context)

            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args
            message_text = call_args[0][0]

            assert "Ещё слишком рано!" in message_text
            assert "Следующая батарейка будет доступна:" in message_text

            print("     ✅ Claim battery too early works correctly")

        print("✅ All balance functionality tests PASSED!")
        return True

    except Exception as e:
        print(f"❌ Balance functionality test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the simple test
    success = asyncio.run(test_balance_functionality_simple())
    sys.exit(0 if success else 1)