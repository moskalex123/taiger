import threading
import time
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
import psutil
import logging

logger = logging.getLogger(__name__)

class WorkerRegistry:
    """In-memory registry для отслеживания активных воркеров на текущем сервере"""
    
    def __init__(self):
        self._workers: Dict[int, Dict] = {}  # {user_id: {'pid': int, 'started_at': datetime}}
        self._lock = threading.Lock()
        
    def add_worker(self, user_id: int, pid: int, vip_level: int = 0, auto_scheduled: bool = False) -> None:
        """Добавить воркера в registry"""
        with self._lock:
            # FIX: Check if worker is already registered
            if user_id in self._workers:
                logger.warning(f"[WORKER_REGISTRY] Worker {user_id} already registered, updating existing entry")
                # Update existing entry instead of overwriting
                existing_info = self._workers[user_id]
                existing_info['pid'] = pid
                existing_info['last_activity'] = time.time()
                existing_info['last_heartbeat'] = time.time()
                existing_info['vip_level'] = vip_level
                existing_info['auto_scheduled'] = auto_scheduled
            else:
                self._workers[user_id] = {
                    'pid': pid,
                    'started_at': datetime.now(),
                    'last_activity': time.time(),
                    'last_heartbeat': time.time(),
                    'vip_level': vip_level,
                    'auto_scheduled': auto_scheduled,
                    'is_processing': False,
                    'processing_started_at': None,
                    'current_message_id': None
                }
                logger.info(f"[WORKER_REGISTRY] Добавлен воркер для user_id {user_id} с PID {pid}, VIP {vip_level}")

            # DIAGNOSTIC: Verify the worker was actually added
            if user_id in self._workers:
                logger.debug(f"[WORKER_REGISTRY] Successfully added/updated worker {user_id}")
            else:
                logger.error(f"[WORKER_REGISTRY] CRITICAL: Failed to add worker {user_id} to registry")
    
    def remove_worker(self, user_id: int) -> bool:
        """Удалить воркера из registry. Возвращает True если воркер был найден и удален"""
        with self._lock:
            if user_id in self._workers:
                worker_info = self._workers.pop(user_id)
                logger.info(f"[WORKER_REGISTRY] Удален воркер для user_id {user_id} с PID {worker_info['pid']}")
                return True
            return False
    
    def get_worker_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о воркере"""
        with self._lock:
            return self._workers.get(user_id)
    
    def is_worker_running(self, user_id: int) -> bool:
        """Проверить, запущен ли воркер для пользователя"""
        with self._lock:
            if user_id not in self._workers:
                logger.info(f"[WORKER_REGISTRY] Worker {user_id} not found in registry")
                return False

            worker_info = self._workers[user_id]
            pid = worker_info['pid']

            # Проверяем, существует ли процесс
            try:
                if psutil.pid_exists(pid):
                    logger.debug(f"[WORKER_REGISTRY] Worker {user_id} with PID {pid} is running")
                    return True
                else:
                    # Процесс не существует, удаляем из registry
                    logger.warning(f"[WORKER_REGISTRY] Процесс {pid} для user_id {user_id} не существует, удаляем из registry")
                    del self._workers[user_id]
                    return False
            except Exception as e:
                logger.error(f"[WORKER_REGISTRY] Ошибка при проверке PID {pid}: {e}")
                return False
    
    def get_running_count(self) -> int:
        """Получить количество активных воркеров"""
        with self._lock:
            # Очищаем мертвые процессы и считаем живые
            dead_workers = []
            for user_id, worker_info in self._workers.items():
                pid = worker_info['pid']
                try:
                    if not psutil.pid_exists(pid):
                        dead_workers.append(user_id)
                except Exception as e:
                    logger.error(f"[WORKER_REGISTRY] Ошибка при проверке PID {pid}: {e}")
                    dead_workers.append(user_id)
            
            # Удаляем мертвые процессы
            for user_id in dead_workers:
                logger.warning(f"[WORKER_REGISTRY] Удаляем мертвый процесс для user_id {user_id}")
                del self._workers[user_id]
            
            count = len(self._workers)
            logger.debug(f"[WORKER_REGISTRY] Активных воркеров: {count}")
            return count
    
    def get_all_workers(self) -> Dict[int, Dict]:
        """Получить информацию о всех активных воркерах"""
        with self._lock:
            return self._workers.copy()
    
    def cleanup_dead_workers(self) -> int:
        """Очистить мертвые процессы. Возвращает количество удаленных записей"""
        with self._lock:
            dead_workers = []
            for user_id, worker_info in self._workers.items():
                pid = worker_info['pid']
                try:
                    if not psutil.pid_exists(pid):
                        dead_workers.append(user_id)
                except Exception:
                    dead_workers.append(user_id)
            
            for user_id in dead_workers:
                del self._workers[user_id]
            
            if dead_workers:
                logger.info(f"[WORKER_REGISTRY] Очищено {len(dead_workers)} мертвых процессов: {dead_workers}")
            
            return len(dead_workers)
    
    def update_last_activity(self, user_id: int) -> bool:
        """Обновить время последней активности воркера"""
        with self._lock:
            if user_id in self._workers:
                self._workers[user_id]['last_activity'] = time.time()
                logger.debug(f"[WORKER_REGISTRY] Обновлено время активности для user_id {user_id}")
                return True
            return False

    def update_last_heartbeat(self, user_id: int) -> bool:
        """Обновить время последнего heartbeat воркера"""
        with self._lock:
            if user_id in self._workers:
                self._workers[user_id]['last_heartbeat'] = time.time()
                logger.debug(f"[WORKER_REGISTRY] Обновлен heartbeat для user_id {user_id}")
                return True
            return False

    def start_processing(self, user_id: int, message_id: int) -> bool:
        """Отметить начало обработки поста"""
        with self._lock:
            if user_id in self._workers:
                self._workers[user_id]['is_processing'] = True
                self._workers[user_id]['processing_started_at'] = time.time()
                self._workers[user_id]['current_message_id'] = message_id
                self._workers[user_id]['last_activity'] = time.time()
                logger.info(f"[WORKER_REGISTRY] Worker {user_id} started processing message {message_id}")
                return True
            return False

    def finish_processing(self, user_id: int) -> bool:
        """Отметить завершение обработки поста"""
        with self._lock:
            if user_id in self._workers:
                message_id = self._workers[user_id].get('current_message_id')
                self._workers[user_id]['is_processing'] = False
                self._workers[user_id]['processing_started_at'] = None
                self._workers[user_id]['current_message_id'] = None
                self._workers[user_id]['last_activity'] = time.time()
                logger.info(f"[WORKER_REGISTRY] Worker {user_id} finished processing message {message_id}")
                return True
            return False

    def is_processing(self, user_id: int) -> bool:
        """Проверить, обрабатывает ли воркер пост в данный момент"""
        with self._lock:
            if user_id in self._workers:
                return self._workers[user_id].get('is_processing', False)
            return False

    def get_processing_duration(self, user_id: int) -> Optional[float]:
        """Получить время обработки текущего поста в секундах"""
        with self._lock:
            if user_id in self._workers:
                started_at = self._workers[user_id].get('processing_started_at')
                if started_at:
                    return time.time() - started_at
            return None

# Глобальный экземпляр registry
worker_registry = WorkerRegistry()