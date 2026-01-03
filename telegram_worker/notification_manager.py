"""
Менеджер уведомлений для админа и системы
"""
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from db import async_session
from models import User, Worker
from telegram_worker.utils import get_api_base_url


# Admin notification settings
PAYMENT_CONTACT = os.getenv('PAYMENT_CONTACT', '@magellanvs')


class NotificationManager:
    """Управление уведомлениями"""
    
    def __init__(self, user_id: int, logger, get_http_session_callback, send_websocket_log_callback=None):
        self.user_id = user_id
        self.logger = logger
        self._get_http_session = get_http_session_callback
        self._send_websocket_log = send_websocket_log_callback
    
    async def notify_admin_critical_error(self, error_type: str, error_message: str, user_info: dict = None):
        """Send critical error notification to admin."""
        try:
            # Get user information
            if not user_info:
                async with async_session() as db_session:
                    user = await db_session.get(User, self.user_id)
                    if user:
                        current_balance = user.balance if user.balance else 0.0
                        user_info = {
                            'id': user.id,
                            'username': getattr(user, 'username', 'Unknown'),
                            'balance': float(current_balance),
                            'vip_level': getattr(user, 'VIP_level', 0)
                        }
                    else:
                        user_info = {'id': self.user_id, 'username': 'Unknown', 'balance': 0.0, 'vip_level': 0}

            # Format notification message
            notification_text = f"""🚨 КРИТИЧЕСКАЯ ОШИБКА TELEGRAM

👤 Пользователь: {user_info.get('username', 'Unknown')} (ID: {user_info['id']})
💰 Баланс: ${user_info.get('balance', 0):.2f}
⭐ VIP: {user_info.get('vip_level', 0)}

🔴 Тип ошибки: {error_type}
📝 Описание: {error_message}

⏰ Время: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

#критическая_ошибка #telegram #пользователь_{self.user_id}"""

            # Send notification to admin via HTTP API
            session = await self._get_http_session()
            api_url = f"{get_api_base_url()}/api/internal/notify-admin"
            
            payload = {
                "recipient": PAYMENT_CONTACT,
                "message": notification_text,
                "user_id": self.user_id,
                "error_type": error_type
            }
            
            async with session.post(api_url, json=payload, timeout=10) as response:
                if response.status == 200:
                    self.logger.info(f"Admin notification sent successfully for error: {error_type}")
                else:
                    self.logger.error(f"Failed to send admin notification: HTTP {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Failed to notify admin about critical error: {e}")
            # Don't raise exception to avoid breaking the main flow
    
    async def send_auth_required_signal(self, error_type: str, message: str):
        """Send signal to parent process that auth is required."""
        self.logger.critical(f"AUTH_REQUIRED: user_id={self.user_id}, error={error_type}, message={message}")
        
        # Send notification via WebSocket to dashboard
        try:
            if self._send_websocket_log:
                if error_type == "AuthKeyUnregistered":
                    await self._send_websocket_log('auth_required', 
                        'Сессия истекла, требуется повторная авторизация', 
                        'error')
                else:
                    await self._send_websocket_log('auth_error', 
                        f"Ошибка авторизации: {message}", 
                        'error')
        except Exception as e:
            self.logger.error(f"Failed to send auth required notification: {e}")
        
        # Also update database with auth required status
        async with async_session() as session:
            try:
                from sqlalchemy import update as sql_update
                await session.execute(
                    sql_update(Worker)
                    .where(Worker.user_id == self.user_id)
                    .values(
                        status='auth_required' if error_type == "AuthKeyUnregistered" else 'error',
                        last_error=f"{error_type}: {message}",
                        pid=None  # Clear PID since worker is no longer running
                    )
                )
                await session.commit()
            except Exception as e:
                self.logger.error(f"Failed to update worker status in database: {e}")
        
        # Remove worker from registry if it exists
        try:
            # Import here to avoid circular imports
            import requests
            import json
            
            # Call main backend to remove worker from registry
            payload = {"user_id": self.user_id, "error_type": error_type}
            requests.post(f"{get_api_base_url()}/api/internal/worker-auth-error", 
                         json=payload, timeout=2)
        except Exception as e:
            self.logger.error(f"Failed to notify main backend about auth error: {e}")