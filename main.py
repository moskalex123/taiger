#!/usr/bin/env python3
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file with explicit path
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Try to load from current working directory
    load_dotenv()

import shutil
import uuid
from datetime import datetime, timedelta, timezone
from redis_client import get_redis_client, close_redis_client, redis_ping

# --- Установка политики цикла событий для Windows ---
# Это должно быть сделано до первого вызова asyncio.get_event_loop()
# или создания экземпляра FastAPI/Uvicorn, который может инициализировать цикл.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- Конец установки политики цикла событий ---

from fastapi import FastAPI, Depends, HTTPException, Response, Request, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os

# Добавляем каталог, содержащий этот файл (main.py), в начало sys.path
# Это гарантирует, что Python сможет найти модули как модули.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импорт новых модулей вместо устаревшего telegram_worker
from tg_auth import TelegramAuth
from tg_worker import TelegramWorker

from typing import Optional, List, Dict
from models import TelegramSession, User, Worker # Добавлены User, Worker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession # Добавлено
from db import get_db # Добавлено
from auth import create_jwt_token, get_current_user # Добавлено
from datetime import datetime # Добавлено
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PasswordHashInvalid # Добавлено
from fastapi.middleware.cors import CORSMiddleware  # Add this import
import uuid  # Добавить в начало файла

# Configure logging
import logging

class QueueInfoFilter(logging.Filter):
    def filter(self, record):
        # Фильтруем избыточные HTTP запросы для уменьшения шума в консоли
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            # Отключаем логи для часто повторяющихся endpoint'ов
            filtered_endpoints = [
                '/api/queue/info',
                '/api/queue/service-status', 
                '/api/workers/status',
                '/api/workers/logs/scheduled_posts',
                '/api/workers/logs/errors',
                '/api/logs/realtime',
                '/api/users/me',
                '/api/channel_pairs'
            ]
            
            for endpoint in filtered_endpoints:
                if endpoint in message and 'GET' in message and '200' in message:
                    return False
        return True

# Применяем фильтр к логгеру uvicorn.access
logging.getLogger("uvicorn.access").addFilter(QueueInfoFilter())

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import uvicorn

import auth
import models
import db
from db import get_db
from db import engine
from api import users_router, sessions_router, channel_pairs_router, workers_router
from api.avatars import router as avatars_router
from api.queue import router as queue_router
from api.websocket import router as websocket_router
from api.telegram import router as telegram_router
from api.system_prompt import router as system_prompt_router  # Add this line
from queue_manager import get_queue_manager
import worker_manager
from models import Worker, User
from sqlalchemy import select, and_
from worker_registry import worker_registry

# --- Asynchronous Table Creation ---
async def create_tables(): # Corrected: ensure this is async def
    async with engine.begin() as conn: # Corrected: use async with
        await conn.run_sync(models.Base.metadata.create_all)

# The following block was causing the TypeError and is removed as table creation is handled by startup_event
# with engine.begin() as conn:
#     conn.run_sync(models.Base.metadata.create_all)

async def main_async_setup():
    await create_tables()
    # Any other async setup can go here

# Run the async setup before starting the app
# This is a common pattern, but for uvicorn, startup events are better.
# However, for simplicity in this step, let's try this first.
# If issues persist, we'll move to startup events.

# logging.basicConfig should be called as early as possible.
# Let's ensure it's before any other significant operations.
print("INFO: Basic print-based logging configured.")

print("INFO: Print level for api.workers set to effectively DEBUG (all prints will show).")
print("INFO: Print level for uvicorn.access set to effectively WARNING (less verbose prints).")
print("INFO: Print level for uvicorn.error set to effectively INFO.")

# It's better to run async setup within an async context or a startup event.
# For now, let's try to run it before app instantiation. This might need adjustment.
# asyncio.run(main_async_setup()) # This will block if run directly here in a sync context.

app = FastAPI()

async def check_inactive_workers():
    """Фоновая задача для проверки и останова неактивных воркеров"""
    # Получаем экземпляр менеджера очереди
    queue_manager = get_queue_manager()
    # check_and_stop_inactive_workers уже имеет свой цикл
    await queue_manager.check_and_stop_inactive_workers()

async def run_queue_processor():
    """Фоновая задача для периодической обработки очереди воркеров."""
    queue_manager = get_queue_manager()
    # process_queue теперь сам управляет своим циклом и не требует внешнего вызова
    await queue_manager.process_queue()

async def run_vip3_injection():
    """Фоновая задача автоинъекции пользователей VIP3 в очередь"""
    queue_manager = get_queue_manager()
    await queue_manager.auto_inject_vip3_users()

def cleanup_orphaned_worker_processes():
    """Принудительная очистка всех зависших процессов tg_worker.py"""
    try:
        import psutil
        killed_count = 0
        
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) > 1:
                    cmdline_str = " ".join(cmdline)
                    if "tg_worker.py" in cmdline_str and "python" in cmdline[0].lower():
                        print(f"INFO: Killing orphaned worker process PID {proc.info['pid']}: {cmdline_str}")
                        proc.kill()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if killed_count > 0:
            print(f"INFO: Killed {killed_count} orphaned worker processes")
        else:
            print("INFO: No orphaned worker processes found")
            
    except Exception as e:
        print(f"ERROR: Failed to cleanup orphaned processes: {e}")

async def cleanup_worker_statuses():
    """Очистка worker_registry при старте приложения"""
    try:
        # Сначала убиваем все зависшие процессы воркеров
        cleanup_orphaned_worker_processes()
        
        # Очищаем in-memory registry при старте
        worker_registry.cleanup_dead_workers()
        print("INFO: Worker registry очищен при старте приложения")
        
        # Note: Skipping database cleanup for now to avoid complexity
        # The database session handling in startup events is complex and not critical for backdoor functionality
                
    except Exception as e:
        print(f"ERROR: Ошибка при очистке worker registry: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("startup")
async def startup_event():
    try:
        # Enhanced database connection logic to handle optional authentication
        try:
            await create_tables()
            print("INFO: Database tables checked/created.")
        except Exception as db_error:
            print(f"WARNING: Database connection failed: {db_error}")
            print("INFO: This is a known Docker networking authentication issue on Windows.")
            print("INFO: Server will continue running without database functionality.")
            # Don't raise the error - continue with limited functionality
        
        # Test Redis connection
        redis_connected = await redis_ping()
        if redis_connected:
            print("INFO: Redis connection successful.")
        else:
            print("WARNING: Redis connection failed. Some features may not work properly.")
        
        # Note: Skipping database cleanup for now to avoid complexity
        # The database session handling in startup events is complex and not critical for backdoor functionality
        
        # Initialize Telegram bot with additional cleanup
        try:
            from telegram_bot.bot import telegram_bot
            from telegram_bot.update_tracker import update_tracker
            
            # Clear update tracker to prevent reprocessing
            update_tracker.clear_all()
            
            # Инициализируем Telegram бота
            try:
                await telegram_bot.remove_webhook()
                # Add a small delay to ensure webhook is removed and pending updates are dropped
                await asyncio.sleep(2)
                await telegram_bot.initialize(start_polling=True)
                print("INFO: Telegram bot initialized successfully with polling")
            except Exception as bot_error:
                print(f"WARNING: Telegram bot initialization failed: {bot_error}")
                # Don't raise - continue with other tasks even if Telegram fails
            
            # Запускаем фоновую задачу проверки неактивных воркеров
            asyncio.create_task(check_inactive_workers())
            print("INFO: Фоновая задача проверки неактивных воркеров запущена")

            # Запускаем фоновую задачу обработки очереди
            asyncio.create_task(run_queue_processor())
            print("INFO: Фоновая задача обработки очереди запущена")

            # Запускаем фоновую задачу автоинъекции VIP3 пользователей
            asyncio.create_task(run_vip3_injection())
            print("INFO: Фоновая задача автоинъекции VIP3 запущена")
            
            # Запускаем фоновую задачу очистки статусов новичков
            try:
                from newcomer_cleanup_task import get_newcomer_cleanup_task
                cleanup_task = get_newcomer_cleanup_task(interval_minutes=60)  # Проверяем каждый час
                asyncio.create_task(cleanup_task.start())
                print("INFO: Фоновая задача очистки статусов новичков запущена")
            except Exception as newcomer_error:
                print(f"WARNING: Newcomer cleanup task failed: {newcomer_error}")
                
        except Exception as e:
            print(f"ERROR: Telegram bot initialization failed: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - let the server start without Telegram functionality
            print("INFO: Server starting without Telegram functionality.")

    except Exception as e:
        print(f"ERROR: Startup failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't raise - let the server start with limited functionality
        print("INFO: Server starting with limited functionality due to database issues.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    try:
        await close_redis_client()
        print("INFO: Redis client closed.")
    except Exception as e:
        print(f"WARNING: Error during shutdown: {e}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"CRITICAL ERROR: Unhandled exception: {exc}")
    import traceback
    traceback.print_exc()
    return {"error": "Internal server error", "detail": str(exc)}

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://tactically-healing-parrotfish.cloudpub.ru",  # Для TMA
        "http://localhost:5174",  # Дополнительный порт для разработки
        "http://taiger.pro",  # Для production TMA
        "https://taiger.pro",  # Для production TMA (HTTPS)
        "https://www.taiger.pro"  # Для www subdomain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])
app.include_router(channel_pairs_router, prefix="/api/channel_pairs", tags=["channel_pairs"])
app.include_router(workers_router, prefix="/api/workers", tags=["workers"])
app.include_router(queue_router, prefix="/api/queue", tags=["queue"])
app.include_router(avatars_router, prefix="/api", tags=["avatars"])
app.include_router(websocket_router, prefix="/api", tags=["websocket"])
app.include_router(telegram_router, prefix="/api", tags=["telegram"])
app.include_router(system_prompt_router, prefix="/api/system-prompt", tags=["system-prompt"])  # Add this line

# Mount static files for avatars (this should be after API routes)
app.mount("/avatars", StaticFiles(directory="frontend/dist/avatars"), name="avatars")

# Internal endpoints for worker communication
@app.post("/api/internal/register-worker")
async def register_worker(request: Request):
    """Internal endpoint for worker registration"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        pid = data.get("pid")
        vip_level = data.get("vip_level", 0)
        
        if user_id and pid:
            # Register worker in API server's registry
            worker_registry.add_worker(user_id, pid, vip_level)
            print(f"[INTERNAL] ✅ WORKER REGISTERED: user_id={user_id}, PID={pid}, VIP={vip_level}")
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Missing user_id or pid"}
    except Exception as e:
        print(f"[INTERNAL] Error registering worker: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/worker-heartbeat")
async def worker_heartbeat(request: Request):
    """Internal endpoint for worker heartbeat"""
    try:
        data = await request.json()
        user_id = data.get("user_id")

        if user_id:
            # DIAGNOSTIC: Check registry state before heartbeat
            worker_info = worker_registry.get_worker_info(user_id)
            print(f"[INTERNAL] 🔍 HEARTBEAT CHECK: user_id={user_id}, current_info={worker_info}")

            # Update activity in API server's registry
            if worker_registry.is_worker_running(user_id):
                worker_registry.update_last_heartbeat(user_id)
                print(f"[INTERNAL] 💓 HEARTBEAT: user_id={user_id}")
                return {"status": "success"}
            else:
                print(f"[INTERNAL] ❌ HEARTBEAT FAILED: user_id={user_id} not found")
                return {"status": "not_found"}
        else:
            return {"status": "error", "message": "Missing user_id"}
    except Exception as e:
        print(f"[INTERNAL] Error processing heartbeat: {e}")
@app.post("/api/internal/worker-start-processing")
async def worker_start_processing(request: Request):
    """Internal endpoint for worker to signal start of message processing"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        message_id = data.get("message_id")

        if user_id and message_id:
            # Update processing state in API server's registry
            if worker_registry.start_processing(user_id, message_id):
                print(f"[INTERNAL] 🔄 WORKER STARTED PROCESSING: user_id={user_id}, message_id={message_id}")
                return {"status": "success"}
            else:
                print(f"[INTERNAL] ❌ FAILED TO START PROCESSING: user_id={user_id}, message_id={message_id}")
                return {"status": "error", "message": "Worker not found"}
        else:
            return {"status": "error", "message": "Missing user_id or message_id"}
    except Exception as e:
        print(f"[INTERNAL] Error starting processing: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/worker-finish-processing")
async def worker_finish_processing(request: Request):
    """Internal endpoint for worker to signal end of message processing"""
    try:
        data = await request.json()
        user_id = data.get("user_id")

        if user_id:
            # Update processing state in API server's registry
            if worker_registry.finish_processing(user_id):
                print(f"[INTERNAL] ✅ WORKER FINISHED PROCESSING: user_id={user_id}")
                return {"status": "success"}
            else:
                print(f"[INTERNAL] ❌ FAILED TO FINISH PROCESSING: user_id={user_id}")
                return {"status": "error", "message": "Worker not found"}
        else:
            return {"status": "error", "message": "Missing user_id"}
    except Exception as e:
        print(f"[INTERNAL] Error finishing processing: {e}")
        return {"status": "error", "message": str(e)}
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/bot-log")
async def bot_log(request: Request):
    """Internal endpoint for bot logging"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        telegram_id = data.get("telegram_id")
        message = data.get("message")
        log_type = data.get("log_type", "info")
        level = data.get("level", "info")

        if user_id and message:
            # Log the message
            print(f"[BOT_LOG] User {user_id}: {message}")
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Missing user_id or message"}
    except Exception as e:
        print(f"[INTERNAL] Error in bot-log: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/bot-status")
async def bot_status(request: Request):
    """Internal endpoint for bot status updates"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        telegram_id = data.get("telegram_id")
        message = data.get("message")
        last_status_message_id = data.get("last_status_message_id")

        if user_id and message:
            # For now, just log and return success
            # In a real implementation, this would send a message via Telegram Bot API
            print(f"[BOT_STATUS] User {user_id}: {message}")
            return {"status": "success", "message_id": None}
        else:
            return {"status": "error", "message": "Missing user_id or message"}
    except Exception as e:
        print(f"[INTERNAL] Error in bot-status: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/bot-report")
async def bot_report(request: Request):
    """Internal endpoint for bot reports"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        telegram_id = data.get("telegram_id")
        message = data.get("message")
        report_type = data.get("report_type", "info")
        last_status_message_id = data.get("last_status_message_id")

        if user_id and message:
            # For now, just log and return success
            # In a real implementation, this would send a message via Telegram Bot API
            print(f"[BOT_REPORT] User {user_id} ({report_type}): {message}")
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Missing user_id or message"}
    except Exception as e:
        print(f"[INTERNAL] Error in bot-report: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/worker-auth-error")
async def handle_worker_auth_error(request: Request):
    """Internal endpoint to handle worker authentication errors"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        error_type = data.get("error_type")
        
        if user_id:
            # Remove worker from registry
            worker_registry.remove_worker(user_id)
            print(f"[INTERNAL] Removed worker {user_id} from registry due to {error_type}")
        
        return {"status": "success"}
    except Exception as e:
        print(f"[INTERNAL] Error handling worker auth error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/internal/notify-admin")
async def notify_admin(request: Request):
    """Internal endpoint to send critical error notifications to admin"""
    try:
        data = await request.json()
        recipient = data.get("recipient")  # Admin contact (e.g., @magellanvs)
        message = data.get("message")
        user_id = data.get("user_id")
        error_type = data.get("error_type")
        
        # Log the critical error notification
        print(f"[ADMIN NOTIFICATION] Critical error for user {user_id}: {error_type}")
        print(f"[ADMIN NOTIFICATION] Message: {message}")
        print(f"[ADMIN NOTIFICATION] Should notify: {recipient}")
        
        # TODO: Implement actual notification mechanism (Telegram bot, email, etc.)
        # For now, just log the notification
        # In the future, this could send a message via Telegram Bot API or email
        
        return {"status": "success", "message": "Admin notification logged"}
    except Exception as e:
        print(f"[INTERNAL] Error sending admin notification: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
def read_root():
    return {"message": "Welcome to the API"}

@app.get("/health")
async def health_check(db_session: AsyncSession = Depends(get_db)):
    """Health check endpoint with database and Redis status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "healthy",
            "redis": "healthy"
        }
    }
    
    # Check database connection
    try:
        # Simple query to test connection
        result = await db_session.execute(select(1))
        if result.scalar() == 1:
            health_status["services"]["database"] = "healthy"
        else:
            health_status["services"]["database"] = "unhealthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis connection
    try:
        redis_connected = await redis_ping()
        if redis_connected:
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

# Add redirect for /api/health to support frontend checks
@app.get("/api/health")
async def api_health_check(db_session: AsyncSession = Depends(get_db)):
    """API health check endpoint - redirects to main health check"""
    return await health_check(db_session)

# Temporary backdoor for user ID 2 - for debugging without authentication
@app.get("/api/debug/backdoor/{user_id}")
async def debug_backdoor(user_id: int, db_session: AsyncSession = Depends(get_db)):
    """Temporary backdoor for debugging without authentication"""
    if user_id != 2:
        raise HTTPException(status_code=403, detail="Backdoor only available for user ID 2")
    
    try:
        # Get user from database
        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Return user data directly without JWT token
        # Fix: Handle telegram_id properly
        telegram_id_str = None
        if user.telegram_id is not None:
            telegram_id_str = str(user.telegram_id)
        
        return {
            "message": "Backdoor access granted",
            "user_id": user.id,
            "username": user.username,
            "telegram_id": telegram_id_str,
            "is_superuser": user.is_superuser or False,
            "dashboard_url": "/dashboard"  # Direct URL to dashboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Ultra simple backdoor - direct access to dashboard for user 2
@app.get("/backdoor/2/dashboard")
async def simple_backdoor_dashboard():
    """Ultra simple backdoor - direct access to dashboard for user 2"""
    # This endpoint bypasses all authentication and directly serves a response
    # that indicates the user is logged in as user ID 2
    return {
        "status": "authenticated",
        "user_id": 2,
        "username": "magellanvs",
        "message": "Direct dashboard access granted",
        "instructions": "Frontend should recognize this special authentication state"
    }

# Real temporary backdoor - creates a special session that bypasses all authentication
@app.get("/api/backdoor/login/user/2")
async def backdoor_login_user_2(response: Response, db_session: AsyncSession = Depends(get_db)):
    """Real temporary backdoor that creates a special session for user ID 2 without JWT"""
    try:
        # Get user from database
        result = await db_session.execute(select(User).where(User.id == 2))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create a special backdoor token/session identifier
        # This is a simple approach - in a real implementation, you might want something more secure
        backdoor_token = f"backdoor_session_user_2_{uuid.uuid4()}"
        
        # Store this token in Redis with user info for the frontend to recognize
        redis_client = await get_redis_client()
        # Fix: Handle telegram_id properly
        telegram_id_str = None
        if user.telegram_id is not None:
            telegram_id_str = str(user.telegram_id)
            
        user_data = {
            "user_id": user.id,
            "username": user.username,
            "telegram_id": telegram_id_str,
            "is_superuser": user.is_superuser or False,
            "backdoor": True  # Special flag to indicate this is a backdoor session
        }
        
        # Store in Redis for 1 hour (3600 seconds)
        await redis_client.setex(f"backdoor_session:{backdoor_token}", 3600, str(user_data))
        
        # Return the token to the frontend
        return {
            "backdoor_token": backdoor_token,
            "user": user_data,
            "message": "Backdoor access granted - use this token to access the dashboard without authentication"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Endpoint for frontend to verify backdoor token
@app.get("/api/backdoor/verify/{token}")
async def verify_backdoor_token(token: str):
    """Verify a backdoor token and return user info if valid"""
    try:
        redis_client = await get_redis_client()
        user_data_str = await redis_client.get(f"backdoor_session:{token}")
        
        if not user_data_str:
            raise HTTPException(status_code=401, detail="Invalid or expired backdoor token")
        
        # In a real implementation, you might want to parse this properly
        # For now, we'll just return a success response
        return {
            "valid": True,
            "message": "Backdoor token is valid",
            "token": token
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Ultra simple backdoor - direct access to dashboard for user 2 with automatic redirect
@app.get("/api/backdoor/login/user/2/redirect")
async def backdoor_login_redirect(db_session: AsyncSession = Depends(get_db)):
    """Ultra simple backdoor that automatically logs in user 2 and redirects to dashboard"""
    try:
        # Get user from database
        result = await db_session.execute(select(User).where(User.id == 2))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create a special backdoor token
        backdoor_token = f"backdoor_session_user_2_{uuid.uuid4()}"
        
        # Store this token in Redis with user info
        redis_client = await get_redis_client()
        # Fix: Handle telegram_id properly
        telegram_id_str = None
        if user.telegram_id is not None:
            telegram_id_str = str(user.telegram_id)
            
        user_data = {
            "user_id": user.id,
            "username": user.username,
            "telegram_id": telegram_id_str,
            "is_superuser": user.is_superuser or False,
            "backdoor": True
        }
        
        # Store in Redis for 1 hour
        await redis_client.setex(f"backdoor_session:{backdoor_token}", 3600, str(user_data))
        
        # Return a response that can be used by frontend to automatically authenticate
        return {
            "backdoor_token": backdoor_token,
            "user": user_data,
            "redirect_url": "/dashboard",
            "message": "Backdoor access granted - automatically redirecting to dashboard"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Comprehensive TMA Debug Backdoor - for testing TMA environment and observing live agent logs
@app.get("/api/debug/tma/backdoor/worker/2")
async def tma_debug_backdoor_worker_2(db_session: AsyncSession = Depends(get_db)):
    """Comprehensive backdoor for TMA debugging - starts worker #2 and observes live logs"""
    try:
        # Get user from database
        result = await db_session.execute(select(User).where(User.id == 2))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create a special debug session token
        debug_token = f"tma_debug_session_user_2_{uuid.uuid4()}"
        
        # Store this token in Redis with user info
        redis_client = await get_redis_client()
        # Fix: Handle telegram_id properly
        telegram_id_str = None
        if user.telegram_id is not None:
            telegram_id_str = str(user.telegram_id)
            
        user_data = {
            "user_id": user.id,
            "username": user.username,
            "telegram_id": telegram_id_str,
            "is_superuser": user.is_superuser or False,
            "tma_debug": True,
            "debug_token": debug_token
        }
        
        # Store in Redis for 1 hour (3600 seconds)
        await redis_client.setex(f"tma_debug_session:{debug_token}", 3600, str(user_data))
        
        # Return debug information
        return {
            "debug_token": debug_token,
            "user": user_data,
            "message": "TMA Debug session created - use this token to access TMA debugging features",
            "instructions": {
                "step1": "Connect to WebSocket using wss://taiger.pro/api/ws/2",
                "step2": "Use the debug token in your TMA simulation",
                "step3": "Worker #2 will be started automatically",
                "step4": "Live logs will be streamed via WebSocket"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# TMA Debug Backdoor - Start Worker #2 and Stream Live Logs
@app.post("/api/debug/tma/start-worker/2")
async def tma_debug_start_worker_2(db_session: AsyncSession = Depends(get_db)):
    """Start worker #2 for TMA debugging and stream live logs"""
    try:
        # Import global process manager
        from worker_manager import process_manager
        
        # Start worker #2
        worker_started = await process_manager.start_worker_service(2)
        
        if not worker_started:
            raise HTTPException(status_code=500, detail="Failed to start worker #2")
        
        # Get worker process info
        worker_processes = process_manager.worker_processes
        worker_process = worker_processes.get(2) if 2 in worker_processes else None
        
        return {
            "status": "success",
            "message": "Worker #2 started successfully for TMA debugging",
            "worker_info": {
                "user_id": 2,
                "process_id": worker_process.pid if worker_process else None,
                "started": True
            },
            "websocket_info": {
                "url": "wss://taiger.pro/api/ws/2",
                "instructions": "Connect to this WebSocket to observe live logs from worker #2"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting worker #2: {str(e)}")

# TMA Debug Backdoor - Stop Worker #2
@app.post("/api/debug/tma/stop-worker/2")
async def tma_debug_stop_worker_2():
    """Stop worker #2 for TMA debugging"""
    try:
        # Import global process manager
        from worker_manager import process_manager
        
        # Stop worker #2
        worker_stopped = process_manager.stop_worker_service(2)
        
        return {
            "status": "success",
            "message": "Worker #2 stopped successfully",
            "worker_stopped": worker_stopped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping worker #2: {str(e)}")

# TMA Debug Backdoor - Get Worker #2 Status
@app.get("/api/debug/tma/worker/2/status")
async def tma_debug_worker_2_status():
    """Get status of worker #2 for TMA debugging"""
    try:
        # Import worker registry
        from worker_registry import worker_registry
        
        # Check if worker #2 is running
        is_running = False
        worker_info = None
        
        try:
            is_running = worker_registry.is_worker_running(2)
            worker_info = worker_registry.get_worker_info(2)
        except Exception as registry_error:
            print(f"Error accessing worker registry: {registry_error}")
            # Continue with default values
        
        return {
            "status": "success",
            "worker_id": 2,
            "is_running": is_running,
            "worker_info": worker_info,
            "websocket_info": {
                "url": "wss://taiger.pro/api/ws/2",
                "instructions": "Connect to this WebSocket to observe live logs from worker #2"
            }
        }
    except Exception as e:
        print(f"Error in worker status endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting worker #2 status: {str(e)}")

# TMA Debug Backdoor - Simulate TMA Environment
@app.post("/api/debug/tma/simulate")
async def tma_debug_simulate_environment(request: Request, db_session: AsyncSession = Depends(get_db)):
    """Simulate TMA environment for debugging"""
    try:
        # Get request data
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        
        # Get user from database
        result = await db_session.execute(select(User).where(User.id == 2))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create TMA simulation session
        simulation_token = f"tma_simulation_{uuid.uuid4()}"
        
        # Store simulation data in Redis
        redis_client = await get_redis_client()
        simulation_data = {
            "user_id": user.id,
            "username": user.username,
            "simulation_token": simulation_token,
            "created_at": datetime.now().isoformat(),
            "websocket_url": f"wss://taiger.pro/api/ws/2",
            "api_base_url": f"https://taiger.pro",
            "telegram_webapp_url": os.getenv("TELEGRAM_WEBAPP_URL", "https://taiger.pro")
        }
        
        # Store in Redis for 1 hour
        await redis_client.setex(f"tma_simulation:{simulation_token}", 3600, str(simulation_data))
        
        return {
            "status": "success",
            "message": "TMA environment simulation created",
            "simulation_token": simulation_token,
            "simulation_data": simulation_data,
            "next_steps": {
                "connect_websocket": f"Connect to WebSocket: wss://taiger.pro/api/ws/2",
                "start_worker": "POST to /api/debug/tma/start-worker/2 to start worker #2",
                "observe_logs": "Live logs will be streamed via WebSocket connection"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating TMA environment: {str(e)}")

if __name__ == "__main__":
    import sys
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1] == "--port" and len(sys.argv) > 2:
        port = int(sys.argv[2])
    elif "PORT" in os.environ:
        port = int(os.environ["PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning", access_log=False)
