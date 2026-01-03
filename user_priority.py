"""
Утилиты для работы с приоритетами пользователей
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
import logging

logger = logging.getLogger(__name__)

# Константы приоритетов
NEWCOMER_PRIORITY = 1000  # Максимальный приоритет для новичков
VIP_3_PRIORITY = 300      # VIP 3
VIP_2_PRIORITY = 200      # VIP 2  
VIP_1_PRIORITY = 100      # VIP 1
REGULAR_PRIORITY = 0      # Обычные пользователи

async def get_user_priority(db_session: AsyncSession, user_id: int) -> tuple[int, str, bool]:
    """
    Получить приоритет пользователя в очереди
    
    Returns:
        tuple: (priority, priority_reason, is_newcomer)
    """
    try:
        user = await db_session.get(User, user_id)
        if not user:
            return REGULAR_PRIORITY, "user_not_found", False
        
        # Проверяем статус новичка
        is_newcomer = await is_user_newcomer(user)
        
        if is_newcomer:
            return NEWCOMER_PRIORITY, "newcomer", True
        
        # Определяем приоритет по VIP уровню
        vip_level = user.VIP_level or 0
        
        if vip_level >= 3:
            return VIP_3_PRIORITY, f"vip_{vip_level}", False
        elif vip_level == 2:
            return VIP_2_PRIORITY, f"vip_{vip_level}", False
        elif vip_level == 1:
            return VIP_1_PRIORITY, f"vip_{vip_level}", False
        else:
            return REGULAR_PRIORITY, "regular", False
            
    except Exception as e:
        logger.error(f"Ошибка при получении приоритета пользователя {user_id}: {e}")
        return REGULAR_PRIORITY, "error", False

async def is_user_newcomer(user: User) -> bool:
    """
    Проверить, является ли пользователь новичком
    Новичок = создан менее 24 часов назад И флаг is_newcomer = True
    """
    if not user.is_newcomer:
        return False
    
    # Проверяем время создания аккаунта
    if user.created_at:
        time_since_creation = datetime.utcnow() - user.created_at
        if time_since_creation > timedelta(hours=24):
            # Пользователь больше не новичок, обновляем флаг
            user.is_newcomer = False
            return False
    
    return True

async def update_newcomer_status(db_session: AsyncSession, user_id: int) -> bool:
    """
    Обновить статус новичка для пользователя
    Возвращает True если статус был изменен
    """
    try:
        user = await db_session.get(User, user_id)
        if not user or not user.is_newcomer:
            return False
        
        # Проверяем, прошло ли 24 часа
        if user.created_at:
            time_since_creation = datetime.utcnow() - user.created_at
            if time_since_creation > timedelta(hours=24):
                user.is_newcomer = False
                await db_session.commit()
                logger.info(f"Пользователь {user_id} больше не новичок (прошло {time_since_creation})")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса новичка для пользователя {user_id}: {e}")
        return False

def get_priority_display_name(priority: int, reason: str, is_newcomer: bool) -> str:
    """
    Получить отображаемое название приоритета
    """
    if is_newcomer:
        return "🌟 Новичок"
    elif reason.startswith("vip_"):
        vip_level = reason.split("_")[1]
        return f"💎 VIP {vip_level}"
    elif reason == "regular":
        return "👤 Обычный"
    else:
        return "❓ Неизвестно"

def get_priority_color(priority: int, is_newcomer: bool) -> str:
    """
    Получить цвет для отображения приоритета
    """
    if is_newcomer:
        return "#FFD700"  # Ярко-желтый для новичков
    elif priority >= 300:
        return "#9C27B0"  # Фиолетовый для VIP 3
    elif priority >= 200:
        return "#E91E63"  # Розовый для VIP 2
    elif priority >= 100:
        return "#2196F3"  # Синий для VIP 1
    else:
        return "#757575"  # Серый для обычных пользователей