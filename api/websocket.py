from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Optional, Any, Union
import json
import asyncio
from datetime import datetime, timezone
import logging

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # НЕ ХРАНИМ ЛОГИ - ТОЛЬКО ЖИВАЯ ПЕРЕДАЧА!

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"[WEBSOCKET] User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"[WEBSOCKET] User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                    print(f"[WEBSOCKET] Sent message to user {user_id}: {message.get('message', 'no message')[:50]}...")
                except Exception as e:
                    print(f"[WEBSOCKET] Failed to send message to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn, user_id)
        else:
            print(f"[WEBSOCKET] No active connections for user {user_id}")

    async def send_log_message(self, user_id: int, log_type: str, message: Optional[str] = None, level: str = "info", message_key: Optional[str] = None, message_params: Optional[Dict[str, Any]] = None):
        """Send log message to user's dashboard - ТОЛЬКО ЖИВАЯ ПЕРЕДАЧА"""
        
        # НЕ ОТПРАВЛЯЕМ ПУСТЫЕ СООБЩЕНИЯ!
        final_message = message if message else message_key
        if not final_message or final_message.strip() == '':
            print(f"[WEBSOCKET] Skipping empty message for user {user_id}: '{final_message}'")
            return
        
        log_entry: Dict[str, Any] = {
            "type": "log",
            "log_type": log_type,  # "worker_status", "worker_error", "scheduled_post", etc.
            "level": level,        # "info", "error", "warning", "success"
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Support both old format (message) and new format (message_key + params)
        if message_key:
            log_entry["message_key"] = message_key
            if message_params is not None:
                log_entry["message_params"] = message_params
            else:
                log_entry["message_params"] = {}
        else:
            log_entry["message"] = message or ""
        
        print(f"[WEBSOCKET] Preparing to send log message to user {user_id}: {final_message[:50]}...")
        
        # Store log for HTTP fallback
        store_log_for_http_fallback(user_id, log_entry)
        
        # НЕ СОХРАНЯЕМ ЛОГИ - ТОЛЬКО ЖИВЫЕ ЧЕРЕЗ WEBSOCKET!
        await self.send_personal_message(log_entry, user_id)
    
    def get_recent_logs(self, user_id: int, limit: int = 20) -> List[dict]:
        """НЕТ СОХРАНЕННЫХ ЛОГОВ - ТОЛЬКО ЖИВЫЕ ЧЕРЕЗ WEBSOCKET"""
        return []  # Всегда возвращаем пустой список

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    print(f"[WEBSOCKET] Connection attempt for user {user_id}")
    try:
        await manager.connect(websocket, user_id)
        print(f"[WEBSOCKET] User {user_id} connected successfully")
        
        # Send initial connection message
        await manager.send_log_message(user_id, "system", "Dashboard connected to real-time logs", "info", None, None)
        
        # Keep connection alive
        while True:
            # Wait for any message from client (ping/pong)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back for ping/pong
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}))
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()}))
    except WebSocketDisconnect:
        print(f"[WEBSOCKET] User {user_id} disconnected (WebSocketDisconnect)")
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"[WEBSOCKET] Error in websocket for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

# Function to send logs from anywhere in the application
async def send_worker_log(user_id: int, log_type: str, message: str, level: str = "info"):
    """Send worker log to dashboard in real-time"""
    await manager.send_log_message(user_id, log_type, message, level, None, None)

# HTTP endpoint for workers to send logs
from pydantic import BaseModel

class LogMessage(BaseModel):
    user_id: int
    log_type: str
    message: Optional[str] = None  # For backward compatibility
    message_key: Optional[str] = None  # New localization key
    message_params: Optional[Dict[str, Any]] = None  # Parameters for localization
    level: str = "info"
    timestamp: str

@router.post("/internal/log")
async def receive_worker_log(log_message: LogMessage):
    """Receive log from worker process and forward to WebSocket - ТОЛЬКО ЖИВЫЕ ЛОГИ"""
    try:
        # Используем локализованное сообщение если оно есть, иначе message_key
        message_to_send = log_message.message if log_message.message else log_message.message_key
        
        # НЕ ПРИНИМАЕМ ПУСТЫЕ СООБЩЕНИЯ!
        if not message_to_send or message_to_send.strip() == '':
            print(f"[WEBSOCKET] Rejecting empty log message for user {log_message.user_id}")
            return {"status": "rejected", "reason": "empty_message"}
        
        print(f"[WEBSOCKET] Forwarding log message for user {log_message.user_id}: {message_to_send[:50]}...")
        
        await manager.send_log_message(
            log_message.user_id,
            log_message.log_type,
            log_message.message,
            log_message.level,
            log_message.message_key,
            log_message.message_params
        )
        return {"status": "ok"}
    except Exception as e:
        print(f"[WEBSOCKET] Error forwarding log: {e}")
        return {"status": "error", "message": str(e)}

# HTTP endpoint to get recent logs (fallback for when WebSocket is not available)
from auth import get_current_user

# In-memory storage for recent logs (temporary solution)
recent_logs_storage: Dict[int, List[dict]] = {}

# Function to store logs for HTTP fallback
def store_log_for_http_fallback(user_id: int, log_entry: Dict[str, Any]):
    """Store log entry for HTTP fallback mechanism"""
    if user_id not in recent_logs_storage:
        recent_logs_storage[user_id] = []
    
    recent_logs_storage[user_id].append(log_entry)
    
    # Keep only last 100 logs per user to prevent memory issues
    if len(recent_logs_storage[user_id]) > 100:
        recent_logs_storage[user_id] = recent_logs_storage[user_id][-100:]

@router.get("/logs/realtime")
async def get_realtime_logs(
    limit: int = 20,
    current_user = Depends(get_current_user)
):
    """Получить последние логи для пользователя (fallback для WebSocket)"""
    user_id = current_user.id
    if user_id in recent_logs_storage:
        # Return last N logs for the user
        logs = recent_logs_storage[user_id]
        return logs[-limit:] if len(logs) > limit else logs
    else:
        return []

# Export the manager for use in other modules
websocket_manager = manager