from datetime import datetime
from typing import Dict, List, Optional

from balance_utils import get_start_balance

def format_balance(balance: float) -> str:
    """Format balance with appropriate precision"""
    if balance >= 1:
        return f"{balance:.2f}"
    else:
        return f"{balance:.3f}"

def get_worker_status_emoji(status: str) -> str:
    """Get emoji for worker status"""
    status_emojis = {
        "running": "✅",
        "active": "✅", 
        "stopped": "⏹️",
        "starting": "⏳",
        "pending": "⏳",
        "error": "❌",
        "unknown": "❓"
    }
    return status_emojis.get(status.lower(), "❓")

def get_balance_emoji(balance: float) -> str:
    """Get emoji based on balance level"""
    if balance > 1.0:
        return "💰"
    elif balance > 0.1:
        return "⚠️"
    else:
        return "🔴"

def truncate_message(message: str, max_length: int = 40) -> str:
    """Truncate message with ellipsis"""
    if len(message) <= max_length:
        return message
    return message[:max_length] + "..."

def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display"""
    try:
        # Try to parse the timestamp and format it
        if timestamp:
            # Assuming timestamp is in ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        return "N/A"
    except:
        # If parsing fails, return first 5 characters
        return timestamp[:5] if timestamp else "N/A"

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_runtime(seconds: int) -> str:
    """Format runtime in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def validate_telegram_id(telegram_id: str) -> bool:
    """Validate Telegram user ID format"""
    try:
        tid = int(telegram_id)
        return tid > 0
    except (ValueError, TypeError):
        return False

def get_default_balance() -> float:
    """Get default starting balance for new users"""
    return get_start_balance()

def safe_get_user_data(user_info: Dict, key: str, default: str = "") -> str:
    """Safely get user data with fallback"""
    return user_info.get(key, default) or default

def format_user_display_name(user_info: Dict) -> str:
    """Format user display name from Telegram data"""
    first_name = safe_get_user_data(user_info, 'first_name')
    last_name = safe_get_user_data(user_info, 'last_name')
    username = safe_get_user_data(user_info, 'username')
    
    if first_name:
        if last_name:
            return f"{first_name} {last_name}"
        return first_name
    elif username:
        return f"@{username}"
    else:
        return "User"