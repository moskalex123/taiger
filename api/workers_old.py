from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional # Added for Optional type hint in handle_worker_error


import db # Import db module
import auth # Import auth module
from models import User, TelegramSession, Worker, ScheduledPost, WorkerError # Import models used in this file
import asyncio
import worker_manager  # Импорт менеджера воркеров с новой функцией is_valid_worker
import os # Добавим os для работы с путями
from s3_session_manager import S3SessionManager
from queue_manager import get_queue_manager
from worker_lock import get_worker_start_lock
from worker_registry import worker_registry

print("!!! EXECUTING OPTIMIZED WORKERS.PY - v15072024-01 !!!")

router = APIRouter()

@router.post("/start", summary="Запустить воркера для текущего пользователя")
async def start_worker_endpoint( 
    priority: int = 0,
    db_session: AsyncSession = Depends(db.get_db), 
    current_user_payload: User = Depends(auth.get_current_user)
):
    user_id = current_user_payload.id 
    print(f"[START] ===== НАЧАЛО ОБРАБОТКИ ЗАПРОСА НА ЗАПУСК ВОРКЕРА =====")
    print(f"[START] Запрос на запуск воркера от user_id: {user_id}, приоритет: {priority}")
    print(f"[START] Время запроса: {datetime.utcnow()}")
    
    try:
        # Получаем экземпляр менеджера очереди для отладки
        queue_manager = get_queue_manager()
        print(f"[START] DEBUG: queue_manager.max_concurrent_workers = {queue_manager.max_concurrent_workers}")
        print(f"[START] Шаг 1: Получен менеджер очереди")
        
        # Получение данных пользователя
        print(f"[START] Шаг 2: Получение данных пользователя {user_id}")
        user = await db_session.get(User, user_id)
        if not user:
            print(f"ERROR: Пользователь {user_id} не найден")
            raise HTTPException(status_code=404, detail="User not found")
        print(f"[START] Шаг 2: Пользователь найден - {user.phone_number}")

        # Проверка наличия сессии Telegram
        print(f"[START] Шаг 3: Проверка сессии Telegram для user_id {user_id}")
        session_stmt = select(TelegramSession).where(TelegramSession.user_id == user.id)
        session_result = await db_session.execute(session_stmt)
        tg_session = session_result.scalar_one_or_none()

        if not tg_session or not tg_session.session_path:
            print(f"ERROR: Сессия Telegram для {user_id} не найдена")
            raise HTTPException(status_code=404, detail="Telegram session not found")
        print(f"[START] Шаг 3: Сессия Telegram найдена - {tg_session.session_path}")
        
        # Очищаем критичные статусы в БД при запуске
        worker_stmt = select(Worker).where(Worker.user_id == user_id)
        worker_result = await db_session.execute(worker_stmt)
        worker_db = worker_result.scalar_one_or_none()
        
        if worker_db and worker_db.status in ['auth_required', 'error']:
            print(f"[START] Очищаем критичный статус {worker_db.status} для user_id {user_id}")
            worker_db.status = 'stopped'
            worker_db.last_error = None
            worker_db.pid = None
            await db_session.commit()
        
        # Поиск существующей записи воркера
        print(f"[START] Шаг 4: Поиск существующей записи воркера для user_id {user_id}")
        worker_stmt = select(Worker).where(Worker.user_id == user.id)
        worker_result = await db_session.execute(worker_stmt)
        worker_db_entry = worker_result.scalar_one_or_none()
        print(f"[START] Шаг 4: Запись воркера {'найдена' if worker_db_entry else 'не найдена'}")
        if worker_db_entry:
            print(f"[START] Шаг 4: Текущий статус воркера: {worker_db_entry.status}, PID: {worker_db_entry.pid}")

        # Проверка активного воркера через file_worker_registry
        from file_worker_registry import file_worker_registry
        if file_worker_registry.is_worker_running(user_id):
            worker_info = file_worker_registry.get_worker_info(user_id)
            print(f"INFO: Воркер для {user_id} уже запущен (PID: {worker_info['pid']})")
            return JSONResponse(content={"status": "already_running", "pid": worker_info['pid']})

        # Всегда добавляем в очередь, менеджер сам решит, когда запускать
        print(f"[START] Шаг 5: Добавляем запрос на запуск в очередь для user_id: {user_id}")
        queue_manager = get_queue_manager()
        print(f"[START] Шаг 5: Вызываем queue_manager.add_to_queue()")
        queue_entry = await queue_manager.add_to_queue(user_id, priority)
        print(f"[START] Шаг 5: Задача добавлена в очередь")
        position = await queue_manager.get_queue_position(user_id)
        print(f"[START] Шаг 5: Позиция в очереди: {position}")
        
        # Проверим, был ли воркер запущен немедленно
        print(f"[START] Шаг 6: Проверка немедленного запуска воркера")
        if worker_db_entry:
            await db_session.refresh(worker_db_entry, attribute_names=['status', 'pid'])
            print(f"[START] Шаг 6: Обновленный статус воркера: {worker_db_entry.status}, PID: {worker_db_entry.pid}")
            if worker_db_entry.status == 'running':
                print(f"[START] ===== ВОРКЕР ЗАПУЩЕН НЕМЕДЛЕННО ===== user_id: {user_id}, PID: {worker_db_entry.pid}")
                return JSONResponse(content={"status": "started", "pid": worker_db_entry.pid})
        else:
            print(f"[START] Шаг 6: worker_db_entry отсутствует, проверяем создание новой записи")

        print(f"[START] ===== ВОРКЕР ДОБАВЛЕН В ОЧЕРЕДЬ ===== user_id: {user_id}, позиция: {position}")
        return JSONResponse(content={
            "status": "added_to_queue",
            "queue_id": queue_entry.id,
            "position": position,
            "priority": priority
        })
        
    except HTTPException:
        # Перебрасываем HTTP исключения как есть
        raise
    except Exception as e:
        print(f"ERROR: [START] Exception occurred for user_id {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Возвращаем безопасный ответ в случае любой ошибки
        raise HTTPException(
            status_code=500, 
            detail="Internal server error while starting worker"
        )


@router.post("/start_direct", summary="Прямой запуск воркера (только для VIP)")
async def start_worker_direct_endpoint( 
    db_session: AsyncSession = Depends(db.get_db), 
    current_user_payload: User = Depends(auth.get_current_user)
):
    """Прямой запуск воркера без очереди (только для VIP пользователей)"""
    user_id = current_user_payload.id 
    
    try:
        # Проверяем VIP статус
        if current_user_payload.VIP_level < 1:
            raise HTTPException(status_code=403, detail="Direct start requires VIP status")
        
        print(f"[START_DIRECT] Прямой запуск воркера для VIP user_id: {user_id}")

        # Получение данных пользователя
        user = await db_session.get(User, user_id)
        if not user:
            print(f"ERROR: Пользователь {user_id} не найден")
            raise HTTPException(status_code=404, detail="User not found")

        # Проверка наличия сессии Telegram
        session_stmt = select(TelegramSession).where(TelegramSession.user_id == user.id)
        session_result = await db_session.execute(session_stmt)
        tg_session = session_result.scalar_one_or_none()

        if not tg_session or not tg_session.session_path:
            print(f"ERROR: Сессия Telegram для {user_id} не найдена")
            raise HTTPException(status_code=404, detail="Telegram session not found")
        
        # Поиск существующей записи воркера
        worker_stmt = select(Worker).where(Worker.user_id == user.id)
        worker_result = await db_session.execute(worker_stmt)
        worker_db_entry = worker_result.scalar_one_or_none()

        # Проверка активного воркера через file_worker_registry
        from file_worker_registry import file_worker_registry
        if file_worker_registry.is_worker_running(user_id):
            worker_info = file_worker_registry.get_worker_info(user_id)
            print(f"INFO: Воркер для {user_id} уже запущен (PID: {worker_info['pid']})")
            return JSONResponse(content={"status": "already_running", "pid": worker_info['pid']})

        # КРИТИЧЕСКАЯ СЕКЦИЯ: Даже VIP должны соблюдать лимит воркеров
        async with get_worker_start_lock():
            # Получаем экземпляр менеджера очереди
            queue_manager = get_queue_manager()
            
            # Проверяем количество активных воркеров
            active_workers = queue_manager.get_running_workers_count()
            max_workers = queue_manager.max_concurrent_workers
            
            print(f"INFO: [VIP] Проверка лимита воркеров для user_id {user_id}: активных {active_workers}/{max_workers}")
            
            # Если лимит превышен, отклоняем запрос даже для VIP
            if active_workers >= max_workers:
                print(f"WARNING: [VIP] Лимит воркеров достигнут ({active_workers}/{max_workers}), отклоняем запрос для VIP user_id: {user_id}")
                raise HTTPException(status_code=429, detail="Worker limit reached, even for VIP users")

            # Запуск нового воркера
            # Преобразуем относительный путь из БД в полный путь
            if os.path.isabs(tg_session.session_path):
                session_path = tg_session.session_path
            else:
                # Получаем корневую директорию проекта
                current_file_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_file_dir)
                session_path = os.path.join(project_root, tg_session.session_path)
            
            print(f"INFO: [VIP] Запуск процесса для {user_id}, сессия: {session_path}")
            process = worker_manager.start_worker_process(user_id, session_path)
            pid = process.pid if process else None
            
            # Проверка успешности запуска
            if not pid:
                print(f"ERROR: Не удалось получить PID для {user_id}")
                await handle_worker_error(db_session, user, tg_session, worker_db_entry)
                raise HTTPException(status_code=500, detail="Failed to start worker")

            # Даем процессу время на инициализацию
            await asyncio.sleep(1.5)
            
            # Валидация запущенного процесса
            if not worker_manager.is_valid_worker(pid, user_id): # Removed await
                print(f"ERROR: Запущенный процесс не прошел валидацию (PID: {pid}, user: {user_id})")
                worker_manager.stop_worker_process(pid)
                await handle_worker_error(db_session, user, tg_session, worker_db_entry)
                raise HTTPException(status_code=500, detail="Worker failed validation")

            # Добавление воркера в worker_registry
            worker_registry.add_worker(user_id, pid, user.VIP_level)
            print(f"INFO: [VIP] Воркер добавлен в registry: user_id={user_id}, pid={pid}")

            # Обновление БД (только для персистентных данных)
            current_time = datetime.utcnow()
            if worker_db_entry:
                worker_db_entry.status = "running"
                worker_db_entry.pid = pid
                worker_db_entry.last_started_at = current_time
                worker_db_entry.last_activity_at = current_time  # Устанавливаем время активности при запуске
                if worker_db_entry.session_id != tg_session.id:
                     worker_db_entry.session_id = tg_session.id
            else:
                worker_db_entry = Worker(
                    user_id=user.id,
                    session_id=tg_session.id,
                    status="running",
                    pid=pid,
                    last_started_at=current_time,
                    last_activity_at=current_time  # Устанавливаем время активности при запуске
                )
                db_session.add(worker_db_entry)
            
            try:
                await db_session.commit()
                await db_session.refresh(worker_db_entry)
                print(f"INFO: [VIP] Статус воркера в БД обновлен: user_id={user_id}, status={worker_db_entry.status}, pid={worker_db_entry.pid}")
            except Exception as db_error:
                print(f"ERROR: Ошибка БД при обновлении: {db_error}")
                worker_registry.remove_worker(user_id)
                worker_manager.stop_worker_process(pid)
                raise HTTPException(status_code=500, detail=f"DB update failed: {db_error}")

            # Дополнительная проверка статуса после коммита
            final_check_stmt = select(Worker).where(Worker.user_id == user_id)
            final_check_result = await db_session.execute(final_check_stmt)
            final_worker = final_check_result.scalar_one_or_none()
            print(f"INFO: [VIP] Финальная проверка статуса: user_id={user_id}, status={final_worker.status if final_worker else 'None'}, pid={final_worker.pid if final_worker else 'None'}")

            # Воркер успешно запущен
            return JSONResponse(content={"status": "started", "pid": pid})
            
    except HTTPException:
        # Перебрасываем HTTP исключения как есть
        raise
    except Exception as e:
        print(f"ERROR: [START_DIRECT] Exception occurred for user_id {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Возвращаем безопасный ответ в случае любой ошибки
        raise HTTPException(
            status_code=500, 
            detail="Internal server error while starting worker directly"
        )

async def handle_worker_error(
    db_session: AsyncSession, 
    user: User, 
    tg_session: TelegramSession,
    worker_db_entry: Optional[Worker]
):
    """Обработка ошибок запуска воркера и обновление БД"""
    if worker_db_entry:
        async with db_session.begin_nested():
            worker_db_entry.status = "error"
            worker_db_entry.pid = None
    else:
        async with db_session.begin():
            worker_db_entry = Worker(
                user_id=user.id,
                session_id=tg_session.id,
                status="error",
                pid=None
            )
            db_session.add(worker_db_entry)
            await db_session.commit()

@router.post("/stop", summary="Остановить воркера для текущего пользователя")
async def stop_worker_endpoint(
    db_session: AsyncSession = Depends(db.get_db),
    current_user_payload: User = Depends(auth.get_current_user)
):
    user_id = current_user_payload.id
    print(f"[STOP] Остановка воркера для user_id: {user_id}")
    
    try:
        # Проверка воркера через file_worker_registry
        from file_worker_registry import file_worker_registry
        if not file_worker_registry.is_worker_running(user_id):
            print(f"INFO: Воркер для {user_id} не найден в registry")
            return JSONResponse(content={"status": "not_found"})

        # Получение информации о воркере
        worker_info = file_worker_registry.get_worker_info(user_id)
        pid = worker_info['pid']
        
        # Остановка процесса
        success = worker_manager.stop_worker_process(pid)
        
        if success:
            # Удаление воркера из обоих registry
            worker_registry.remove_worker(user_id)
            file_worker_registry.remove_worker(user_id)
            
            # Обновление статуса в БД
            worker_stmt = select(Worker).where(Worker.user_id == user_id)
            worker_result = await db_session.execute(worker_stmt)
            worker_db_entry = worker_result.scalar_one_or_none()
            
            if worker_db_entry:
                worker_db_entry.status = "stopped"
                worker_db_entry.pid = None
                await db_session.commit()
            
            # Воркер остановлен, очередь автоматически обработает следующего
            print(f"INFO: Воркер остановлен")
            
            # Воркер остановлен
            return JSONResponse(content={"status": "stopped"})
        else:
            print(f"ERROR: Не удалось остановить воркер для {user_id}")
            raise HTTPException(status_code=500, detail="Failed to stop worker")
            
    except Exception as e:
        print(f"ERROR: Исключение при остановке воркера для user_id {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            # Попытаемся обновить статус в БД на error
            worker_stmt = select(Worker).where(Worker.user_id == user_id)
            worker_result = await db_session.execute(worker_stmt)
            worker_db_entry = worker_result.scalar_one_or_none()
            if worker_db_entry:
                worker_db_entry.status = "error"
                await db_session.commit()
        except Exception as db_error:
            print(f"ERROR: Не удалось обновить статус в БД: {str(db_error)}")
        
        raise HTTPException(status_code=500, detail=f"Internal server error while stopping worker: {str(e)}")

@router.get("/status", summary="Получить статус воркера")
async def get_worker_status_endpoint(
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Упрощенная проверка статуса воркера через WorkerRegistry"""
    user_id = current_user.id
    
    try:
        # Получаем пользователя из БД
        user = await db_session.get(User, user_id)
        if not user:
            return JSONResponse(content={"status": "error", "pid": None, "last_started": None})

        # 1. Сначала проверяем критичные статусы в БД (auth_required, error)
        worker_stmt = select(Worker).where(Worker.user_id == user_id)
        worker_result = await db_session.execute(worker_stmt)
        worker_db = worker_result.scalar_one_or_none()
        
        if worker_db and worker_db.status in ['auth_required', 'error']:
            # Убираем воркер из реестра, если он там есть
            worker_registry.remove_worker(user_id)
            
            return JSONResponse(content={
                "status": worker_db.status,
                "pid": None,
                "error_message": getattr(worker_db, 'last_error', None),
                "last_started": worker_db.last_started_at.isoformat() if worker_db.last_started_at else None
            })
        
        # 2. Проверяем активные воркеры через WorkerRegistry (in-memory)
        if worker_registry.is_worker_running(user_id):
            worker_info = worker_registry.get_worker_info(user_id)
            if worker_info:
                return JSONResponse(content={
                    "status": "active",
                    "pid": worker_info.get('pid'),
                    "started_at": worker_info.get('started_at').isoformat() if hasattr(worker_info.get('started_at'), 'isoformat') else worker_info.get('started_at'),
                    "last_activity": worker_info.get('last_activity'),
                    "vip_level": worker_info.get('vip_level', 0)
                })
        
        # 3. Воркер не запущен
        return JSONResponse(content={
            "status": "stopped",
            "pid": None,
            "started_at": None,
            "last_started": worker_db.last_started_at.isoformat() if worker_db and worker_db.last_started_at else None
        })
        
    except Exception as e:
        print(f"ERROR: [API_STATUS_ENDPOINT] Exception occurred: {str(e)}")
        print(f"ERROR: [API_STATUS_ENDPOINT] Exception type: {type(e).__name__}")
        import traceback
        print(f"ERROR: [API_STATUS_ENDPOINT] Traceback: {traceback.format_exc()}")
        return JSONResponse(content={"status": "error", "pid": None, "last_started": None})
    finally:
        if 'db_session' in locals():
            await db_session.close()
            # DB session close log disabled to reduce console clutter

@router.post("/heartbeat", summary="Обновить время последней активности воркера")
async def worker_heartbeat_endpoint(
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Эндпоинт для обновления времени последней активности воркера"""
    user_id = current_user.id
    print(f"[HEARTBEAT] Получен heartbeat от user_id: {user_id}")
    
    # Проверить воркер через file_worker_registry
    from file_worker_registry import file_worker_registry
    if not file_worker_registry.is_worker_running(user_id):
        print(f"[HEARTBEAT] Воркер для user_id {user_id} не найден в registry")
        raise HTTPException(status_code=404, detail="Worker not found")
    
    # Обновить время последней активности в обоих registry
    worker_registry.update_last_activity(user_id)
    file_worker_registry.update_last_activity(user_id)
    
    # Также обновить в БД для персистентности
    worker_stmt = select(Worker).where(Worker.user_id == user_id)
    worker_result = await db_session.execute(worker_stmt)
    worker_db_entry = worker_result.scalar_one_or_none()
    
    if worker_db_entry:
        worker_db_entry.last_activity_at = datetime.utcnow()
        await db_session.commit()
        last_activity_time = worker_db_entry.last_activity_at.isoformat()
    else:
        last_activity_time = datetime.utcnow().isoformat()
    
    print(f"[HEARTBEAT] Обновлено время активности для user_id: {user_id}")
    return JSONResponse(content={"status": "success", "last_activity_at": last_activity_time})


@router.get("/logs/scheduled_posts", summary="Получить логи успешных отложенных постов")
async def get_scheduled_posts(
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
):
    user_id = current_user.id
    stmt = select(ScheduledPost).where(ScheduledPost.user_id == user_id).order_by(ScheduledPost.created_at.desc()).limit(50)
    result = await db_session.execute(stmt)
    posts = result.scalars().all()
    return [{
        'id': post.id,
        'content': post.content or '',
        'balance_after': post.balance_after,
        'scheduled_at': post.scheduled_at.isoformat() if post.scheduled_at else None,
        'created_at': post.created_at.isoformat() if post.created_at else None
    } for post in posts]

@router.get("/logs/errors", summary="Получить логи ошибок воркера")
async def get_worker_errors(
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
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
        'timestamp': error.timestamp.isoformat() if error.timestamp else None,
        'error_type': error.error_type,
        'error_message': error.error_message
    } for error in errors]
