from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timezone
from typing import Optional

import db
import auth
from models import User, TelegramSession, Worker, ScheduledPost, WorkerError
import asyncio
import worker_manager
import os
from s3_session_manager import S3SessionManager
from queue_manager import get_queue_manager
from worker_lock import get_worker_start_lock
from worker_registry import worker_registry

print("!!! EXECUTING SIMPLIFIED WORKERS.PY - IN-MEMORY ONLY !!!")

router = APIRouter()

@router.post("/start", summary="Запустить воркера для текущего пользователя")
async def start_worker_endpoint( 
    priority: int = 0,
    db_session: AsyncSession = Depends(db.get_db), 
    current_user_payload = Depends(auth.get_current_user)  # Remove type annotation
):
    user_id = current_user_payload.id  # This should now be an integer
    print(f"[START] Запрос на запуск воркера от user_id: {user_id}, приоритет: {priority}")
    
    try:
        # Get user data using raw SQL to avoid ORM cache issues
        result = await db_session.execute(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user_row = result.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for Telegram session using raw SQL
        session_result = await db_session.execute(
            text("SELECT * FROM telegram_sessions WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        tg_session_row = session_result.fetchone()

        if not tg_session_row or not tg_session_row.session_path:
            raise HTTPException(status_code=404, detail="Telegram session not found")
        
        # Check if worker is already running through worker_registry (in-memory)
        if worker_registry.is_worker_running(user_id):
            worker_info = worker_registry.get_worker_info(user_id)
            if worker_info and 'pid' in worker_info:
                print(f"INFO: Воркер для {user_id} уже запущен (PID: {worker_info['pid']})")
                return JSONResponse(content={"status": "already_running", "pid": worker_info['pid']})

        # Получаем актуальный приоритет пользователя
        from user_priority import get_user_priority
        try:
            actual_priority, priority_reason, is_newcomer = await get_user_priority(db_session, user_id)
            final_priority = max(priority, actual_priority)
            
            if is_newcomer:
                print(f"[START] 🌟 Пользователь {user_id} - НОВИЧОК! Приоритет: {final_priority}")
            else:
                print(f"[START] Приоритет пользователя {user_id}: {final_priority} ({priority_reason})")
        except Exception as e:
            print(f"[START] Ошибка при получении приоритета: {e}")
            final_priority = priority
            is_newcomer = False
        
        # Добавляем в очередь
        queue_manager = get_queue_manager()
        queue_entry = await queue_manager.add_to_queue(user_id, final_priority)
        position = await queue_manager.get_queue_position(user_id)
        
        print(f"[START] Воркер добавлен в очередь: user_id={user_id}, позиция: {position}")
        return JSONResponse(content={
            "status": "added_to_queue",
            "queue_id": queue_entry.id,
            "position": position,
            "priority": priority
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: [START] Exception occurred for user_id {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while starting worker")

@router.post("/stop", summary="Остановить воркера для текущего пользователя")
async def stop_worker_endpoint(
    db_session: AsyncSession = Depends(db.get_db),
    current_user_payload = Depends(auth.get_current_user)  # Remove type annotation
):
    user_id = current_user_payload.id
    print(f"[STOP] Остановка воркера для user_id: {user_id}")
    
    try:
        # Проверка воркера через worker_registry (in-memory)
        if not worker_registry.is_worker_running(user_id):
            print(f"INFO: Воркер для {user_id} не найден в registry")
            return JSONResponse(content={"status": "not_found"})

        # Получение информации о воркере
        worker_info = worker_registry.get_worker_info(user_id)
        if not worker_info or 'pid' not in worker_info:
            raise HTTPException(status_code=500, detail="Worker info not found")
        # Остановка процесса через централизованный менеджер
        success = await worker_manager.stop_worker(user_id)
        
        if success:
            print(f"INFO: Воркер остановлен")
            return JSONResponse(content={"status": "stopped"})
        else:
            print(f"ERROR: Не удалось остановить воркер для {user_id}")
            raise HTTPException(status_code=500, detail="Failed to stop worker")
            
    except Exception as e:
        print(f"ERROR: Исключение при остановке воркера для user_id {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error while stopping worker: {str(e)}")

@router.get("/status", summary="Получить статус воркера")
async def get_worker_status_endpoint(
    db_session: AsyncSession = Depends(db.get_db),
    current_user = Depends(auth.get_current_user)  # Remove type annotation
):
    """Проверка статуса воркера через WorkerRegistry (in-memory)"""
    user_id = current_user.id
    
    try:
        # Get user data using raw SQL to avoid ORM cache issues
        result = await db_session.execute(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user_row = result.fetchone()
        if not user_row:
            return JSONResponse(content={"status": "error", "pid": None, "last_started": None})

        # 1. Сначала проверяем критичные статусы в БД (auth_required, error)
        worker_stmt = select(Worker).where(Worker.user_id == user_id)
        worker_result = await db_session.execute(worker_stmt)
        worker_db = worker_result.scalar_one_or_none()
        
        if worker_db and worker_db.status in ['auth_required', 'error']:
            return JSONResponse(content={
                "status": worker_db.status,
                "pid": None,
                "error_message": getattr(worker_db, 'last_error', None),
                "last_started": worker_db.last_started_at.isoformat() if hasattr(worker_db.last_started_at, 'isoformat') and worker_db.last_started_at is not None else None
            })
        
        # 2. Проверяем активные воркеры через WorkerRegistry (in-memory)
        if worker_registry.is_worker_running(user_id):
            worker_info = worker_registry.get_worker_info(user_id)
            if worker_info:
                # Рассчитываем оставшееся время активности
                vip_level = worker_info.get('vip_level', 0)
                # Получаем таймауты из .env файла
                vip_timeouts = {
                    0: int(os.getenv("VIP_0_TIMEOUT", "5")),
                    1: int(os.getenv("VIP_1_TIMEOUT", "10")),
                    2: int(os.getenv("VIP_2_TIMEOUT", "20")),
                    3: int(os.getenv("VIP_3_TIMEOUT", "30"))
                }
                timeout_minutes = vip_timeouts.get(vip_level, 5)
                
                started_at = worker_info.get('started_at')
                if started_at:
                    elapsed_seconds = (datetime.now() - started_at).total_seconds()
                    remaining_seconds = max(0, (timeout_minutes * 60) - elapsed_seconds)
                else:
                    remaining_seconds = 0
                
                started_at_value = worker_info.get('started_at')
                started_at_str = None
                if started_at_value and hasattr(started_at_value, 'isoformat'):
                    started_at_str = started_at_value.isoformat()
                elif started_at_value:
                    started_at_str = str(started_at_value)
                
                return JSONResponse(content={
                    "status": "active",
                    "pid": worker_info.get('pid'),
                    "started_at": started_at_str,
                    "last_activity": worker_info.get('last_activity'),
                    "vip_level": worker_info.get('vip_level', 0),
                    "remaining_seconds": int(remaining_seconds)
                })
        
        # 3. Проверяем, находится ли воркер в очереди на запуск
        from queue_manager import get_queue_manager
        queue_manager = get_queue_manager()
        # Проверяем, есть ли пользователь в очереди (pending, starting или processing)
        for entry in queue_manager._queue:
            if entry.user_id == user_id:
                if entry.status == "starting":
                    return JSONResponse(content={
                        "status": "starting",
                        "queue_position": await queue_manager.get_queue_position(user_id),
                        "message": "Worker is starting"
                    })
                elif entry.status == "processing":
                    return JSONResponse(content={
                        "status": "processing",
                        "queue_position": await queue_manager.get_queue_position(user_id),
                        "message": "Worker is being processed"
                    })
                else:  # pending
                    position = await queue_manager.get_queue_position(user_id)
                    return JSONResponse(content={
                        "status": "pending",
                        "queue_position": position,
                        "message": f"Worker is in queue at position {position}"
                    })
        
        # 4. Воркер не запущен и не в очереди
        return JSONResponse(content={
            "status": "stopped",
            "pid": None,
            "started_at": None,
            "last_started": worker_db.last_started_at.isoformat() if worker_db and hasattr(worker_db.last_started_at, 'isoformat') and worker_db.last_started_at is not None else None
        })
        
    except Exception as e:
        print(f"ERROR: [API_STATUS_ENDPOINT] Exception occurred: {str(e)}")
        return JSONResponse(content={"status": "error", "pid": None, "last_started": None})

@router.post("/heartbeat", summary="Обновить время последней активности воркера")
async def worker_heartbeat_endpoint(
    db_session: AsyncSession = Depends(db.get_db),
    current_user = Depends(auth.get_current_user)  # Remove type annotation
):
    """Эндпоинт для обновления времени последней активности воркера"""
    user_id = current_user.id
    print(f"[HEARTBEAT] Получен heartbeat от user_id: {user_id}")
    
    # Проверить воркер через worker_registry (in-memory)
    if not worker_registry.is_worker_running(user_id):
        print(f"[HEARTBEAT] Воркер для user_id {user_id} не найден в registry")
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Обновить время последней активности в registry
    worker_registry.update_last_activity(user_id)
    
    print(f"[HEARTBEAT] Обновлено время активности для user_id: {user_id}")
    return JSONResponse(content={"status": "success", "last_activity_at": datetime.now(timezone.utc).isoformat()})

@router.get("/logs/scheduled_posts", summary="Получить логи успешных отложенных постов")
async def get_scheduled_posts(
    db_session: AsyncSession = Depends(db.get_db),
    current_user = Depends(auth.get_current_user)  # Remove type annotation
):
    user_id = current_user.id
    stmt = select(ScheduledPost).where(ScheduledPost.user_id == user_id).order_by(ScheduledPost.created_at.desc()).limit(50)
    result = await db_session.execute(stmt)
    posts = result.scalars().all()
    return [{
        'id': post.id,
        'content': post.content or '',
        'balance_after': post.balance_after,
        'scheduled_at': post.scheduled_at.isoformat() if hasattr(post.scheduled_at, 'isoformat') and post.scheduled_at is not None else None,
        'created_at': post.created_at.isoformat() if hasattr(post.created_at, 'isoformat') and post.created_at is not None else None
    } for post in posts]

@router.get("/logs/errors", summary="Получить логи ошибок воркера")
async def get_worker_errors(
    db_session: AsyncSession = Depends(db.get_db),
    current_user = Depends(auth.get_current_user)  # Remove type annotation
):
    user_id = current_user.id
    worker_stmt = select(Worker).where(Worker.user_id == user_id)
    worker_result = await db_session.execute(worker_stmt)
    worker = worker_result.scalar_one_or_none()
    if not worker:
        return []
    stmt = select(WorkerError).where(WorkerError.worker_id == worker.id).order_by(WorkerError.timestamp.desc()).limit(50)
    result = await db_session.execute(stmt)
    errors = result.scalars().all()
    return [{
        'id': error.id,
        'timestamp': error.timestamp.isoformat() if hasattr(error.timestamp, 'isoformat') and error.timestamp is not None else None,
        'error_type': error.error_type,
        'error_message': error.error_message
    } for error in errors]