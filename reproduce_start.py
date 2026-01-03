import asyncio
import os
import sys
import logging
from unittest.mock import AsyncMock, MagicMock

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock telegram objects before importing handlers
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()
sys.modules['telegram.constants'] = MagicMock()

# Now import handlers - we need to be careful with imports that might fail
# We will manually import what we need or mock the environment

from db import async_session
from models import User
from sqlalchemy import select

# We need to mock the functions called by start_command if we can't import handlers directly
# due to missing dependencies or complex setup.
# Let's try to import handlers. If it fails, we'll copy the logic of start_command.

try:
    from telegram_bot.handlers import start_command, get_or_create_user, get_user_worker_status, get_user_recent_logs
    print("Successfully imported handlers")
except ImportError as e:
    print(f"Failed to import handlers: {e}")
    print("Will define start_command locally for testing logic")
    
    # We will need to redefine start_command and its dependencies if import fails
    # But for now, let's try to run with what we have.
    pass

async def test_start_command_logic():
    print("Testing start_command logic for user 16...")
    
    # Setup mock update and context
    telegram_id = 499963076
    user_id = 16
    
    # Mock User object from telegram
    tg_user = MagicMock()
    tg_user.id = telegram_id
    tg_user.username = "moskalexx"
    tg_user.first_name = "ꂵꂦꌚꀗꁲ꒒ꈼꇒ"
    tg_user.last_name = None
    tg_user.language_code = "en"
    
    # Mock Chat object
    tg_chat = MagicMock()
    tg_chat.id = telegram_id
    
    # Mock Update
    update = MagicMock()
    update.effective_user = tg_user
    update.effective_chat = tg_chat
    update.message.reply_text = AsyncMock()
    
    # Mock Context
    context = MagicMock()
    
    try:
        # Call the actual start_command
        print("Executing start_command...")
        await start_command(update, context)
        print("start_command executed successfully")
        
        # Check if reply_text was called
        if update.message.reply_text.called:
            print("Reply sent:")
            print(update.message.reply_text.call_args)
        else:
            print("No reply sent!")

    except Exception as e:
        print(f"Error executing start_command: {e}")
        import traceback
        traceback.print_exc()
            
    except Exception as e:
        print(f"Exception during logic test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_start_command_logic())
