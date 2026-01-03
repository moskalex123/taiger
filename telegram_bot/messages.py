from typing import List, Dict
from datetime import datetime
from .i18n import I18n

class MessageTemplates:
    @staticmethod
    def welcome_new_user(balance: float, lang: str = 'en') -> str:
        return I18n.get(lang, "messages.welcome_new", balance=balance)
    
    @staticmethod
    def welcome_existing_user(balance: float, worker_status: str, last_logs: List[Dict], lang: str = 'en') -> str:
        status_emoji = {
            "running": "✅", "active": "✅",
            "stopped": "⏹️", "starting": "⏳",
            "pending": "⏳", "error": "❌"
        }.get(worker_status, "❓")

        recent_activity = ""
        if last_logs:
            recent_activity = "\n\n📋 <b>Recent Activity:</b>\n"
            for log in last_logs[-3:]:  # Last 3 logs
                time_str = log.get('timestamp', 'N/A')[:5] if log.get('timestamp') else 'N/A'
                # Escape braces in log message to prevent format string errors
                log_message = log.get('message', '').replace('{', '{{').replace('}', '}}')[:40]
                recent_activity += f"• <code>{time_str}</code> - {log_message}...\n"

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: balance={balance}, status_emoji={status_emoji}, worker_status={worker_status}, recent_activity={repr(recent_activity)}")
        result = I18n.get(lang, "messages.welcome_back", balance=balance, status_emoji=status_emoji, worker_status=worker_status, recent_activity=recent_activity)
        logger.info(f"DEBUG: result={repr(result)}")
        return result
    
    @staticmethod
    def worker_status(status: str, queue_position: int = None, runtime: str = None) -> str:
        status_emoji = {
            "running": "✅", "active": "✅",
            "stopped": "⏹️", "starting": "⏳",
            "pending": "⏳", "error": "❌"
        }.get(status, "❓")
        
        message = f"{status_emoji} <b>Worker Status:</b> <code>{status}</code>\n"
        
        if queue_position:
            message += f"📍 Queue Position: <code>{queue_position}</code>\n"
        if runtime:
            message += f"⏱️ Runtime: <code>{runtime}</code>\n"
            
        return message
    
    @staticmethod
    def balance_info(balance: float, lang: str = 'en') -> str:
        if balance > 1.0:
            emoji = "💰"
        elif balance > 0.1:
            emoji = "⚠️"
        else:
            emoji = "🔴"

        return I18n.get(lang, "messages.balance_info", emoji=emoji, balance=balance)

    @staticmethod
    def balance_message(user) -> str:
        bal = float(getattr(user, 'balance', 0.0))
        return MessageTemplates.balance_info(bal)

    @staticmethod
    def worker_message(user, status: str, info: dict) -> str:
        queue_position = info.get('queue_position') if isinstance(info, dict) else None
        runtime = None
        if isinstance(info, dict) and 'runtime' in info:
            runtime = info['runtime']
        return MessageTemplates.worker_status(status, queue_position, runtime)
    
    @staticmethod
    def logs_display(logs: List[Dict]) -> str:
        if not logs:
            return "📋 <b>Recent Logs:</b>\n\n<i>No recent activity</i>"
        
        message = "📋 <b>Recent Logs:</b>\n\n"
        for log in logs[-10:]:  # Last 10 logs
            timestamp = log.get('timestamp', 'N/A')
            if timestamp != 'N/A':
                time_str = timestamp[:16] if len(timestamp) > 16 else timestamp
            else:
                time_str = 'N/A'
            message += f"• <code>{time_str}</code>\n  {log.get('message', 'No message')}\n\n"
        
        return message
    
    @staticmethod
    def help_message(lang: str = 'en') -> str:
        # For now, returning a static message since we don't have this in the locale files
        # We can add it to the locale files later if needed
        return """
🤖 <b>Taiger7 Bot Commands:</b>

/start - Main dashboard and balance
/balance - Quick balance check
/worker - Worker control panel
/logs - View recent activity logs
/help - Show this help message

📱 <b>Mini App:</b>
Use the "Open App" button to access the full interface for:
• Channel configuration
• Processing rules setup
• Detailed analytics
• Account management

💡 <b>Quick Actions:</b>
• Worker controls via inline buttons
• Real-time status updates
• Balance monitoring
"""
    
    @staticmethod
    def worker_started(queue_position: int = None) -> str:
        if queue_position:
            return f"✅ Worker start request sent!\n📍 Queue position: <code>{queue_position}</code>"
        return "✅ Worker started successfully!"
    
    @staticmethod
    def worker_stopped() -> str:
        return "⏹️ Worker stopped successfully!"
    
    @staticmethod
    def worker_error(error: str) -> str:
        return f"❌ Worker error: <code>{error}</code>"
