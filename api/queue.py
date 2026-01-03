from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models import User, Worker
from auth import get_current_user
from queue_manager import WorkerQueueManager
from worker_registry import worker_registry

# Get queue manager instance
from queue_manager import get_queue_manager
import auth
import db
from db import get_db_session
import logging

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/add", summary="Добавить пользователя в очередь воркеров")
async def add_to_queue(
    priority: int = 0,
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Добавить текущего пользователя в очередь на запуск воркера"""
    
    # Проверяем, не запущен ли уже воркер через worker_registry
    if worker_registry.is_worker_running(current_user.id):
        raise HTTPException(status_code=400, detail="Worker is already running")
    
    # Добавляем в очередь
    queue_manager = get_queue_manager()
    queue_entry = await queue_manager.add_to_queue(current_user.id, priority)
    
    # Получаем позицию в очереди
    position = await queue_manager.get_queue_position(current_user.id)
    
    return {
        "status": "added_to_queue",
        "queue_id": queue_entry.id,
        "position": position,
        "priority": priority
    }

@router.delete("/remove", summary="Удалить пользователя из очереди")
async def remove_from_queue(
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Удалить текущего пользователя из очереди"""
    
    queue_manager = get_queue_manager()
    await queue_manager.remove_from_queue(current_user.id)
    
    return {"status": "removed_from_queue"}

@router.get("/status", summary="Получить статус пользователя в очереди")
async def get_queue_status(
    current_user: User = Depends(auth.get_current_user)
):
    """Получить статус текущего пользователя в очереди"""
    
    # Получаем информацию из WorkerQueueManager
    queue_manager = get_queue_manager()
    queue_info = await queue_manager.get_queue_info()
    
    # Проверяем статус пользователя
    user_id = current_user.id
    if user_id not in queue_info["worker_statuses"]:
        return {
            "in_queue": False,
            "status": None,
            "position": None
        }
    
    status = queue_info["worker_statuses"][user_id]
    
    # Получаем позицию в очереди (только для pending)
    position = None
    if status == "pending":
        position = await queue_manager.get_queue_position(user_id)
    
    return {
        "in_queue": True,
        "status": status,
        "position": position,
        "priority": 0,  # Priority не хранится в статусах, используем значение по умолчанию
        "created_at": None,  # Время создания не доступно в in-memory очереди
        "started_at": None   # Время запуска не доступно в in-memory очереди
    }

@router.get("/info")
async def get_queue_info():
    """Get general queue information with active workers, starting workers and queue"""
    try:
        # Get queue information from WorkerQueueManager
        queue_manager = get_queue_manager()
        queue_info = await queue_manager.get_queue_info()
        
        # Extract data from queue_info
        active_workers = queue_info["active_workers"]
        starting_workers = queue_info["starting"]
        processing_workers = queue_info["processing"]
        pending_queue = queue_info["queue"]
        worker_statuses = queue_info["worker_statuses"]
        
        # Get database session for VIP levels and newcomer status
        session = await get_db_session()
        try:
            # Get VIP levels and newcomer status for all users
            all_user_ids = list(set(active_workers + starting_workers + processing_workers + pending_queue))
            worker_vips = {}
            worker_newcomers = {}
            worker_priorities = {}
            
            if all_user_ids:
                from user_priority import get_user_priority
                user_query = select(User.id, User.VIP_level, User.is_newcomer, User.created_at).where(User.id.in_(all_user_ids))
                user_result = await session.execute(user_query)
                
                for user_id, vip_level, is_newcomer, created_at in user_result.fetchall():
                    worker_vips[user_id] = vip_level or 0
                    
                    # Получаем актуальный приоритет и статус новичка
                    try:
                        priority, priority_reason, is_actual_newcomer = await get_user_priority(session, user_id)
                        worker_newcomers[user_id] = is_actual_newcomer
                        worker_priorities[user_id] = {
                            "priority": priority,
                            "reason": priority_reason,
                            "is_newcomer": is_actual_newcomer
                        }
                    except Exception as e:
                        logger.error(f"Error getting priority for user {user_id}: {e}")
                        worker_newcomers[user_id] = False
                        worker_priorities[user_id] = {
                            "priority": 0,
                            "reason": "error",
                            "is_newcomer": False
                        }
            
            return {
                "active_workers": active_workers,
                "queue": pending_queue,
                "worker_vips": worker_vips,
                "worker_statuses": worker_statuses,
                "worker_newcomers": worker_newcomers,
                "worker_priorities": worker_priorities
            }
        finally:
            await session.close()
    except Exception as e:
        logger.error(f"Error getting queue info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue information")

@router.get("/service-status")
async def get_service_status():
    """Get service status information for the header"""
    try:
        # Get queue information from WorkerQueueManager (только in-memory)
        from queue_manager import get_queue_manager
        queue_manager = get_queue_manager()
        queue_info = await queue_manager.get_queue_info()
        
        # Extract data from queue_info
        active_workers = queue_info["active_workers"]
        starting_workers = queue_info["starting"]
        processing_workers = queue_info["processing"]
        pending_queue = queue_info["queue"]
        
        # Get database session for user info
        session = await get_db_session()
        try:
            # Get VIP levels, usernames and newcomer status for all users
            all_user_ids = list(set(active_workers + starting_workers + processing_workers + pending_queue))
            worker_vips = {}
            usernames = {}
            worker_newcomers = {}
            
            if all_user_ids:
                # Use a simpler query that doesn't modify user objects
                user_query = select(User.id, User.telegram_user_name, User.VIP_level, User.is_newcomer, User.created_at).where(User.id.in_(all_user_ids))
                user_result = await session.execute(user_query)
                
                for user_id, username, vip_level, is_newcomer, created_at in user_result.fetchall():
                    usernames[user_id] = username or f"User{user_id}"
                    worker_vips[user_id] = vip_level or 0
                    
                    # Check newcomer status without modifying the user object
                    # A newcomer is someone with is_newcomer=True and created less than 24 hours ago
                    if is_newcomer and created_at:
                        time_since_creation = datetime.utcnow() - created_at
                        if time_since_creation <= timedelta(hours=24):
                            worker_newcomers[user_id] = True
                        else:
                            worker_newcomers[user_id] = False
                    else:
                        worker_newcomers[user_id] = False
            
            return {
                "service_state": "online",
                "active_workers": active_workers,
                "starting_workers": starting_workers,  # Только агенты в статусе "starting"
                "processing_workers": processing_workers,  # Агенты в статусе "processing" 
                "queue": pending_queue,
                "worker_vips": worker_vips,
                "usernames": usernames,
                "worker_newcomers": worker_newcomers
            }
        finally:
            await session.close()
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "service_state": "offline",
            "active_workers": [],
            "starting_workers": [],
            "processing_workers": [],
            "queue": [],
            "worker_vips": {},
            "usernames": {},
            "worker_newcomers": {}
        }



@router.get("/list", summary="Получить список очереди (только для администраторов)")
async def get_queue_list(
    db_session: AsyncSession = Depends(db.get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Получить список всех записей в очереди (только для VIP пользователей)"""
    
    # Проверяем VIP статус
    if current_user.VIP_level < 1:
        raise HTTPException(status_code=403, detail="Access denied. VIP required.")
    
    # Получаем информацию из in-memory очереди
    queue_manager = get_queue_manager()
    queue_info = await queue_manager.get_queue_info()
    
    # Получаем все user_id из очереди
    all_user_ids = list(set(
        queue_info["queue"] + 
        queue_info["starting"] + 
        queue_info["processing"] + 
        queue_info["active_workers"]
    ))
    
    # Получаем информацию о пользователях из БД
    user_info = {}
    if all_user_ids:
        user_stmt = select(User.id, User.telegram_user_name).where(User.id.in_(all_user_ids))
        user_result = await db_session.execute(user_stmt)
        user_info = {row[0]: row[1] or f"User{row[0]}" for row in user_result.fetchall()}
    
    queue_list = []
    
    # Добавляем pending записи
    for user_id in queue_info["queue"]:
        queue_list.append({
            "id": f"pending_{user_id}",
            "user_id": user_id,
            "username": user_info.get(user_id, f"User{user_id}"),
            "status": "pending",
            "priority": 0,  # Priority не доступен в in-memory очереди
            "created_at": None,
            "started_at": None
        })
    
    # Добавляем starting записи
    for user_id in queue_info["starting"]:
        queue_list.append({
            "id": f"starting_{user_id}",
            "user_id": user_id,
            "username": user_info.get(user_id, f"User{user_id}"),
            "status": "starting",
            "priority": 0,
            "created_at": None,
            "started_at": None
        })
    
    # Добавляем processing записи
    for user_id in queue_info["processing"]:
        queue_list.append({
            "id": f"processing_{user_id}",
            "user_id": user_id,
            "username": user_info.get(user_id, f"User{user_id}"),
            "status": "processing",
            "priority": 0,
            "created_at": None,
            "started_at": None
        })
    
    return {
        "queue": queue_list,
        "total_count": len(queue_list)
    }