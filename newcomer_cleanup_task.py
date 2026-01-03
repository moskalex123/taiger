#!/usr/bin/env python3
"""
Фоновая задача для автоматического обновления статуса новичков
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import text, select
from db import async_session
from models import User

logger = logging.getLogger(__name__)

class NewcomerCleanupTask:
    """Задача для очистки устаревших статусов новичков"""
    
    def __init__(self, interval_minutes: int = 60):
        """
        Args:
            interval_minutes: Интервал проверки в минутах (по умолчанию 60 минут)
        """
        self.interval_minutes = interval_minutes
        self.is_running = False
    
    async def cleanup_expired_newcomers(self) -> int:
        """
        Обновить статус новичков, у которых прошло более 24 часов с момента регистрации
        
        Returns:
            int: Количество обновленных пользователей
        """
        try:
            async with async_session() as session:
                # Находим пользователей, которые больше не являются новичками
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                query = text("""
                    UPDATE users 
                    SET is_newcomer = FALSE 
                    WHERE is_newcomer = TRUE 
                    AND created_at < :cutoff_time
                    RETURNING id, telegram_user_name, created_at
                """)
                
                result = await session.execute(query, {"cutoff_time": cutoff_time})
                updated_users = result.fetchall()
                
                await session.commit()
                
                # Логируем обновленных пользователей
                for user_id, username, created_at in updated_users:
                    time_since_creation = datetime.utcnow() - created_at
                    logger.info(f"Пользователь {user_id} ({username}) больше не новичок (прошло {time_since_creation})")
                
                if updated_users:
                    logger.info(f"Обновлен статус новичка для {len(updated_users)} пользователей")
                
                return len(updated_users)
                
        except Exception as e:
            logger.error(f"Ошибка при очистке статусов новичков: {e}")
            return 0
    
    async def get_newcomer_stats(self) -> dict:
        """
        Получить статистику по новичкам
        
        Returns:
            dict: Статистика новичков
        """
        try:
            async with async_session() as session:
                query = text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE is_newcomer = TRUE) as active_newcomers,
                        COUNT(*) FILTER (WHERE is_newcomer = TRUE AND created_at > NOW() - INTERVAL '1 hour') as new_in_hour,
                        COUNT(*) FILTER (WHERE is_newcomer = TRUE AND created_at > NOW() - INTERVAL '6 hours') as new_in_6_hours,
                        COUNT(*) FILTER (WHERE is_newcomer = TRUE AND created_at > NOW() - INTERVAL '12 hours') as new_in_12_hours,
                        COUNT(*) FILTER (WHERE is_newcomer = FALSE AND created_at > NOW() - INTERVAL '24 hours') as graduated_today
                    FROM users
                """)
                
                result = await session.execute(query)
                stats = result.fetchone()
                
                return {
                    "active_newcomers": stats.active_newcomers or 0,
                    "new_in_hour": stats.new_in_hour or 0,
                    "new_in_6_hours": stats.new_in_6_hours or 0,
                    "new_in_12_hours": stats.new_in_12_hours or 0,
                    "graduated_today": stats.graduated_today or 0
                }
                
        except Exception as e:
            logger.error(f"Ошибка при получении статистики новичков: {e}")
            return {}
    
    async def run_cleanup_cycle(self):
        """Выполнить один цикл очистки"""
        logger.info("🧹 Запуск цикла очистки статусов новичков")
        
        # Получаем статистику до очистки
        stats_before = await self.get_newcomer_stats()
        logger.info(f"📊 Статистика до очистки: {stats_before}")
        
        # Выполняем очистку
        updated_count = await self.cleanup_expired_newcomers()
        
        # Получаем статистику после очистки
        stats_after = await self.get_newcomer_stats()
        logger.info(f"📊 Статистика после очистки: {stats_after}")
        
        if updated_count > 0:
            logger.info(f"✅ Цикл очистки завершен: обновлено {updated_count} пользователей")
        else:
            logger.debug("✅ Цикл очистки завершен: обновлений не требовалось")
    
    async def start(self):
        """Запустить фоновую задачу"""
        if self.is_running:
            logger.warning("Задача очистки новичков уже запущена")
            return
        
        self.is_running = True
        logger.info(f"🚀 Запуск задачи очистки новичков (интервал: {self.interval_minutes} минут)")
        
        try:
            while self.is_running:
                await self.run_cleanup_cycle()
                
                # Ждем до следующего цикла
                await asyncio.sleep(self.interval_minutes * 60)
                
        except asyncio.CancelledError:
            logger.info("🛑 Задача очистки новичков была отменена")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка в задаче очистки новичков: {e}")
        finally:
            self.is_running = False
            logger.info("🏁 Задача очистки новичков завершена")
    
    def stop(self):
        """Остановить фоновую задачу"""
        logger.info("🛑 Запрос на остановку задачи очистки новичков")
        self.is_running = False

# Глобальный экземпляр задачи
_cleanup_task_instance = None

def get_newcomer_cleanup_task(interval_minutes: int = 60) -> NewcomerCleanupTask:
    """Получить глобальный экземпляр задачи очистки"""
    global _cleanup_task_instance
    if _cleanup_task_instance is None:
        _cleanup_task_instance = NewcomerCleanupTask(interval_minutes)
    return _cleanup_task_instance

async def main():
    """Запуск задачи как отдельного процесса"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    task = get_newcomer_cleanup_task(interval_minutes=30)  # Проверяем каждые 30 минут
    
    try:
        await task.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
        task.stop()

if __name__ == "__main__":
    asyncio.run(main())