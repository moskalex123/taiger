#!/usr/bin/env python3
"""
Test script to verify balance functionality is working correctly.
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

async def test_balance_callback():
    """Test that balance button callback works correctly"""
    print("🧪 Testing balance button callback functionality...")

    # Create mock update and context
    mock_query = MagicMock()
    mock_query.data = "balance"
    mock_query.message = MagicMock()
    mock_query.message.reply_text = AsyncMock()
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 12345

    mock_update = MagicMock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_user

    mock_context = MagicMock()

    # Mock database user
    mock_db_user = MagicMock()
    mock_db_user.id = 12345
    mock_db_user.balance = 5.5
    mock_db_user.VIP_level = 2
    mock_db_user.free_batteries_total = 3.0

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
        try:
            await callback_query_handler(mock_update, mock_context)

            # Verify that edit_message_text was called
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args

            # Check that balance menu keyboard was used
            assert call_args[1]['reply_markup'] is not None
            keyboard = call_args[1]['reply_markup']

            # Verify it's the balance menu keyboard
            expected_keyboard = BotKeyboards.balance_menu()
            assert str(keyboard) == str(expected_keyboard)

            # Check message content
            message_text = call_args[0][0]
            assert "Ваш баланс: <b>5.5🔋</b>" in message_text
            assert "VIP уровень: <b>2</b>" in message_text
            assert "Всего заработано: <b>3.0🔋</b>" in message_text

            print("✅ Balance button callback test PASSED")
            return True

        except Exception as e:
            print(f"❌ Balance button callback test FAILED: {e}")
            return False

async def test_earn_battery_callback():
    """Test that earn battery button callback works correctly"""
    print("🧪 Testing earn battery button callback functionality...")

    # Create mock update and context
    mock_query = MagicMock()
    mock_query.data = "earn_battery"
    mock_query.message = MagicMock()
    mock_query.message.reply_text = AsyncMock()
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 12345

    mock_update = MagicMock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_user

    mock_context = MagicMock()

    # Mock database user
    mock_db_user = MagicMock()
    mock_db_user.id = 12345
    mock_db_user.free_batteries_total = 2.5
    mock_db_user.time_of_last_earned_battery = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago

    with patch('telegram_bot.handlers_clean.async_session') as mock_async_session, \
         patch('telegram_bot.handlers_clean.os.getenv') as mock_getenv:

        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'REST_HOURS_BETWEEN_EARNED_BATTERY': '8'
        }.get(key, default)

        # Create async mock session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.close = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_db_user
        mock_session.execute.return_value = mock_result

        # Test the callback handler
        try:
            await callback_query_handler(mock_update, mock_context)

            # Verify that edit_message_text was called
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args

            # Check that earn battery menu keyboard was used
            assert call_args[1]['reply_markup'] is not None
            keyboard = call_args[1]['reply_markup']

            # Verify it's the earn battery menu keyboard
            expected_keyboard = BotKeyboards.earn_battery_menu()
            assert str(keyboard) == str(expected_keyboard)

            # Check message content
            message_text = call_args[0][0]
            assert "Всего заработано: <b>2.5🔋</b>" in message_text
            assert "Следующая батарейка будет доступна:" in message_text

            print("✅ Earn battery button callback test PASSED")
            return True

        except Exception as e:
            print(f"❌ Earn battery button callback test FAILED: {e}")
            return False

async def test_claim_battery_success():
    """Test that claim battery works when user is eligible"""
    print("🧪 Testing claim battery success functionality...")

    # Create mock update and context
    mock_query = MagicMock()
    mock_query.data = "claim_battery"
    mock_query.message = MagicMock()
    mock_query.message.reply_text = AsyncMock()
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 12345

    mock_update = MagicMock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_user

    mock_context = MagicMock()

    # Mock database user
    mock_db_user = MagicMock()
    mock_db_user.id = 12345
    mock_db_user.balance = 3.0
    mock_db_user.free_batteries_total = 1.5
    mock_db_user.time_of_last_earned_battery = None  # Never claimed before

    with patch('telegram_bot.handlers_clean.async_session') as mock_async_session, \
         patch('telegram_bot.handlers_clean.os.getenv') as mock_getenv, \
         patch('telegram_bot.handlers_clean.datetime') as mock_datetime:

        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'EARNED_BATTERY': '0.5',
            'REST_HOURS_BETWEEN_EARNED_BATTERY': '8'
        }.get(key, default)

        # Mock current time
        mock_now = datetime.utcnow()
        mock_datetime.utcnow.return_value = mock_now

        # Create async mock session
        mock_session = MagicMock()
        mock_session.get = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_async_session.return_value = mock_session

        # Mock user to update
        mock_user_to_update = MagicMock()
        mock_user_to_update.balance = 3.0
        mock_user_to_update.free_batteries_total = 1.5
        mock_user_to_update.time_of_last_earned_battery = None
        mock_session.get.return_value = mock_user_to_update

        # Test the callback handler
        try:
            await callback_query_handler(mock_update, mock_context)

            # Verify that edit_message_text was called
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args

            # Check that balance menu keyboard was used (should return to balance menu after claim)
            assert call_args[1]['reply_markup'] is not None
            keyboard = call_args[1]['reply_markup']

            # Verify it's the balance menu keyboard
            expected_keyboard = BotKeyboards.balance_menu()
            assert str(keyboard) == str(expected_keyboard)

            # Check message content
            message_text = call_args[0][0]
            assert "Успех! Вы получили <b>0.5🔋</b>" in message_text
            assert "Ваш новый баланс: <b>3.5🔋</b>" in message_text
            assert "Всего заработано: <b>2.0🔋</b>" in message_text
            assert "Следующая батарейка:" in message_text

            # Verify database was updated
            assert mock_user_to_update.balance == 3.5
            assert mock_user_to_update.free_batteries_total == 2.0
            assert mock_user_to_update.time_of_last_earned_battery == mock_now

            print("✅ Claim battery success test PASSED")
            return True

        except Exception as e:
            print(f"❌ Claim battery success test FAILED: {e}")
            return False

async def test_claim_battery_too_early():
    """Test that claim battery fails when user tries too early"""
    print("🧪 Testing claim battery too early functionality...")

    # Create mock update and context
    mock_query = MagicMock()
    mock_query.data = "claim_battery"
    mock_query.message = MagicMock()
    mock_query.message.reply_text = AsyncMock()
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 12345

    mock_update = MagicMock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_user

    mock_context = MagicMock()

    # Mock database user
    mock_db_user = MagicMock()
    mock_db_user.id = 12345
    mock_db_user.time_of_last_earned_battery = datetime.utcnow() - timedelta(hours=2)  # Only 2 hours ago

    with patch('telegram_bot.handlers_clean.async_session') as mock_async_session, \
         patch('telegram_bot.handlers_clean.os.getenv') as mock_getenv, \
         patch('telegram_bot.handlers_clean.datetime') as mock_datetime:

        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'REST_HOURS_BETWEEN_EARNED_BATTERY': '8'
        }.get(key, default)

        # Mock current time
        mock_now = datetime.utcnow()
        mock_datetime.utcnow.return_value = mock_now

        # Create async mock session
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.close = AsyncMock()
        mock_async_session.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_db_user
        mock_session.execute.return_value = mock_result

        # Test the callback handler
        try:
            await callback_query_handler(mock_update, mock_context)

            # Verify that edit_message_text was called
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args

            # Check that earn battery menu keyboard was used (should stay on earn menu)
            assert call_args[1]['reply_markup'] is not None
            keyboard = call_args[1]['reply_markup']

            # Verify it's the earn battery menu keyboard
            expected_keyboard = BotKeyboards.earn_battery_menu()
            assert str(keyboard) == str(expected_keyboard)

            # Check message content
            message_text = call_args[0][0]
            assert "Ещё слишком рано!" in message_text
            assert "Следующая батарейка будет доступна:" in message_text

            print("✅ Claim battery too early test PASSED")
            return True

        except Exception as e:
            print(f"❌ Claim battery too early test FAILED: {e}")
            return False

async def test_buy_battery_callback():
    """Test that buy battery button shows placeholder message"""
    print("🧪 Testing buy battery button callback functionality...")

    # Create mock update and context
    mock_query = MagicMock()
    mock_query.data = "buy_battery"
    mock_query.message = MagicMock()
    mock_query.message.reply_text = AsyncMock()
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 12345

    mock_update = MagicMock()
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_user

    mock_context = MagicMock()

    # Mock database user
    mock_db_user = MagicMock()
    mock_db_user.id = 12345

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
        try:
            await callback_query_handler(mock_update, mock_context)

            # Verify that edit_message_text was called
            mock_query.edit_message_text.assert_called_once()
            call_args = mock_query.edit_message_text.call_args

            # Check that balance menu keyboard was used
            assert call_args[1]['reply_markup'] is not None
            keyboard = call_args[1]['reply_markup']

            # Verify it's the balance menu keyboard
            expected_keyboard = BotKeyboards.balance_menu()
            assert str(keyboard) == str(expected_keyboard)

            # Check message content
            message_text = call_args[0][0]
            assert "Покупка батареек будет доступна в будущем" in message_text

            print("✅ Buy battery button callback test PASSED")
            return True

        except Exception as e:
            print(f"❌ Buy battery button callback test FAILED: {e}")
            return False

async def run_all_tests():
    """Run all balance functionality tests"""
    print("🚀 Running comprehensive balance functionality tests...\n")

    tests = [
        test_balance_callback,
        test_earn_battery_callback,
        test_claim_battery_success,
        test_claim_battery_too_early,
        test_buy_battery_callback
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()

    passed = sum(results)
    total = len(results)

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests PASSED! Balance functionality is working correctly.")
        return True
    else:
        print("❌ Some tests FAILED. Balance functionality needs fixes.")
        return False

if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)