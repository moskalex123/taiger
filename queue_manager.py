import asyncio
import time
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, TelegramSession
import worker_manager
import logging
import os
from dotenv import load_dotenv
from worker_registry import worker_registry
from worker_lock import get_worker_start_lock
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from db import async_session

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class QueueEntry:
    user_id: int
    priority: int
    status: str = "pending"  # pending, processing, starting
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    source: str = "default"
    id: str = field(default_factory=lambda: f"{datetime.utcnow().timestamp()}_{hash(datetime.utcnow())}")

class WorkerQueueManager:
    def __init__(self):
        self._processing_lock = asyncio.Lock()
        # In-memory queue - no database connection needed
        self._queue: List[QueueEntry] = []
        self.max_concurrent_workers = int(os.getenv("MAX_CONCURRENT_WORKERS", "3"))
        self.vip3_injection_interval = max(int(os.getenv("VIP3_INJECTION_INTERVAL_SECONDS", "300")), 1)
        print(f"[QUEUE_MANAGER] Инициализирован с max_concurrent_workers = {self.max_concurrent_workers}")
        print(f"[QUEUE_MANAGER] Интервал автоинъекции VIP3 = {self.vip3_injection_interval}с")

    async def add_to_queue(self, user_id: int, priority: int = 0, *, source: str = "default"):
        """Добавить пользователя в очередь на запуск воркера"""
        async with self._processing_lock:
            # Проверяем, нет ли уже записи для этого пользователя
            existing = next((entry for entry in self._queue if entry.user_id == user_id), None)
            if existing:
                print(f"[QUEUE] Пользователь {user_id} уже в очереди со статусом {existing.status}")
                return existing
            
            # Получаем актуальный приоритет пользователя из БД
            from user_priority import get_user_priority
            try:
                actual_priority, priority_reason, is_newcomer = await get_user_priority(async_session(), user_id)
                # Используем максимальный приоритет из переданного и вычисленного
                final_priority = max(priority, actual_priority)
                
                print(f"[QUEUE] Приоритет пользователя {user_id}: переданный={priority}, вычисленный={actual_priority} ({priority_reason}), финальный={final_priority}")
                if is_newcomer:
                    print(f"[QUEUE] 🌟 Пользователь {user_id} - НОВИЧОК! Получает максимальный приоритет")
            except Exception as e:
                print(f"[QUEUE] Ошибка при получении приоритета для пользователя {user_id}: {e}")
                final_priority = priority
                is_newcomer = False
            
            # Добавляем новую запись
            entry = QueueEntry(user_id=user_id, priority=final_priority, source=source)
            self._queue.append(entry)
            print(f"[QUEUE] Добавлен пользователь {user_id} в очередь (приоритет: {final_priority})")
            
            # Немедленно пытаемся обработать очередь для быстрого запуска
            asyncio.create_task(self._try_immediate_start(entry))
            
            return entry

    async def remove_from_queue(self, user_id: int):
        """Удалить пользователя из очереди"""
        async with self._processing_lock:
            self._queue = [entry for entry in self._queue if entry.user_id != user_id]
            print(f"[QUEUE] Пользователь {user_id} удален из очереди")

    async def _try_immediate_start(self, entry: QueueEntry):
        """Попытка немедленного запуска воркера без ожидания основного цикла"""
        try:
            await asyncio.sleep(0.1)  # Небольшая задержка для завершения текущих операций
            
            async with self._processing_lock:
                # Проверяем, можем ли мы запустить воркера сейчас
                active_workers = list(worker_registry.get_all_workers().keys())
                active_count = len(active_workers)
                starting_count = len([e for e in self._queue if e.status == "starting"])
                processing_count = len([e for e in self._queue if e.status == "processing"])
                total_busy = active_count + starting_count + processing_count
                
                if total_busy >= self.max_concurrent_workers:
                    print(f"[IMMEDIATE_START] Лимит воркеров достигнут ({total_busy}/{self.max_concurrent_workers}), ждем основной цикл")
                    return
                
                # Проверяем, что запись все еще pending
                if entry.status != "pending":
                    print(f"[IMMEDIATE_START] Запись для пользователя {entry.user_id} уже обрабатывается")
                    return
                
                # Определяем, нужно ли слушать новые посты
                listen_posts = entry.source != "vip3_auto"

                # Переводим в статус "starting"
                entry.status = "starting"
                entry.started_at = datetime.utcnow()
                
                print(f"[IMMEDIATE_START] Немедленный запуск воркера для пользователя {entry.user_id} (listen_posts={listen_posts})")
                
                # Запускаем воркера
                asyncio.create_task(self._start_worker_for_user_wrapper(entry, listen_posts=listen_posts))
                
        except Exception as e:
            print(f"[IMMEDIATE_START] Ошибка при немедленном запуске для пользователя {entry.user_id}: {e}")

    async def get_queue_position(self, user_id: int) -> Optional[int]:
        """Получить позицию пользователя в очереди"""
        async with self._processing_lock:
            # Получаем только pending записи, отсортированные по приоритету и времени
            pending_entries = [entry for entry in self._queue if entry.status == "pending"]
            pending_entries.sort(key=lambda x: (-x.priority, x.created_at))
            
            # Ищем позицию пользователя
            for i, entry in enumerate(pending_entries):
                if entry.user_id == user_id:
                    return i + 1  # Позиция начинается с 1
            
            return None  # Пользователь не найден в очереди pending

    async def get_queue_info(self):
        """Получить информацию о текущей очереди"""
        async with self._processing_lock:
            queue_list = [entry.user_id for entry in self._queue if entry.status == "pending"]
            processing_list = [entry.user_id for entry in self._queue if entry.status == "processing"]
            starting_list = [entry.user_id for entry in self._queue if entry.status == "starting"]
            
            # Получаем список активных воркеров
            active_workers = list(worker_registry.get_all_workers().keys())
            
            # Получаем статусы воркеров
            worker_statuses = {}
            for entry in self._queue:
                if entry.status == "starting":
                    worker_statuses[entry.user_id] = "starting"
                elif entry.status == "processing":
                    worker_statuses[entry.user_id] = "processing"
                else:
                    worker_statuses[entry.user_id] = "pending"
            
            # Добавляем статусы активных воркеров
            for user_id in active_workers:
                worker_statuses[user_id] = "running"
            
            return {
                "queue": queue_list,
                "active_workers": active_workers,
                "processing": processing_list,
                "starting": starting_list,
                "worker_statuses": worker_statuses,
                "worker_vips": {}  # Placeholder for VIP levels
            }

    async def process_queue(self):
        """Основной цикл обработки очереди"""
        print("[PROCESS_QUEUE] Запущен цикл обработки очереди")
        
        while True:
            try:
                await asyncio.sleep(0.5)  # Проверяем каждые 0.5 секунды для быстрого отклика
                
                async with self._processing_lock:
                    # Подсчитываем активных воркеров
                    active_workers = list(worker_registry.get_all_workers().keys())
                    active_count = len(active_workers)
                    
                    # Подсчитываем воркеров в процессе запуска
                    starting_count = len([entry for entry in self._queue if entry.status == "starting"])
                    processing_count = len([entry for entry in self._queue if entry.status == "processing"])
                    pending_count = len([entry for entry in self._queue if entry.status == "pending"])
                    
                    total_busy = active_count + starting_count + processing_count
                    
                    if total_busy >= self.max_concurrent_workers:
                        if pending_count > 0:
                            print(f"[PROCESS_QUEUE] Достигнут лимит воркеров ({total_busy}/{self.max_concurrent_workers}), ожидание...")
                        continue
                    
                    # Показываем текущее состояние очереди
                    if pending_count > 0 or starting_count > 0 or processing_count > 0:
                        print(f"[PROCESS_QUEUE] В очереди: {pending_count} pending, {starting_count} starting, {processing_count} processing")
                    
                    # Получаем следующую запись из очереди (pending или starting)
                    # Сортируем по приоритету (убывание) и времени создания (возрастание)
                    candidates = [entry for entry in self._queue 
                                if entry.status in ["pending", "starting"]]
                    
                    if not candidates:
                        # Очередь пуста, пауза перед следующей проверкой
                        continue
                    
                    # Сортируем кандидатов по приоритету и времени
                    candidates.sort(key=lambda x: (-x.priority, x.created_at))
                    next_entry = candidates[0]
                    
                    # Если запись уже в статусе "starting", пропускаем
                    if next_entry.status == "starting":
                        continue
                    
                    # Переводим в статус "starting"
                    next_entry.status = "starting"
                    next_entry.started_at = datetime.utcnow()
                    
                    print(f"[PROCESS_QUEUE] Начинаем запуск воркера для пользователя {next_entry.user_id}")
                    
                    # Запускаем воркера в отдельной задаче
                    listen_posts = next_entry.source != "vip3_auto"
                    asyncio.create_task(self._start_worker_for_user_wrapper(next_entry, listen_posts=listen_posts))
                    
            except Exception as e:
                print(f"[PROCESS_QUEUE] Ошибка в цикле обработки очереди: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(2)  # Уменьшили паузу при ошибке с 5 до 2 секунд
        
        print("[PROCESS_QUEUE] Цикл обработки очереди завершен.")

    async def auto_inject_vip3_users(self):
        """Периодическая инъекция пользователей VIP уровня 3 в очередь"""
        print("[VIP3_INJECTION] Запущена автоинъекция пользователей VIP3")

        while True:
            try:
                await self._inject_vip3_batch()
            except Exception as e:
                print(f"[VIP3_INJECTION] Ошибка при автоинъекции: {e}")
                import traceback
                traceback.print_exc()

            await asyncio.sleep(self.vip3_injection_interval)

    async def _inject_vip3_batch(self):
        """Добавить всех пользователей с VIP_level = 3 в очередь"""
        async with async_session() as db_session:
            result = await db_session.execute(select(User.id).where(User.VIP_level == 3))
            vip_user_ids = result.scalars().all()

        if not vip_user_ids:
            return

        for user_id in vip_user_ids:
            if worker_registry.is_worker_running(user_id):
                continue

            # add_to_queue сам обрабатывает дублирование записей
            await self.add_to_queue(user_id, source="vip3_auto")

    async def _start_worker_for_user_wrapper(self, queue_entry: QueueEntry, *, listen_posts: bool = True):
        """Обертка для запуска воркера с обработкой ошибок"""
        try:
            from db import async_session
            async with async_session() as db_session:
                await self._start_worker_for_user(db_session, queue_entry, listen_posts=listen_posts)
        except Exception as e:
            print(f"[START_WORKER_WRAPPER] Ошибка при запуске воркера для пользователя {queue_entry.user_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Удаляем запись из очереди при ошибке
            async with self._processing_lock:
                self._queue = [entry for entry in self._queue if entry.user_id != queue_entry.user_id]

    async def _start_worker_for_user(self, db_session: AsyncSession, queue_entry: QueueEntry, listen_posts: bool):
        """Запустить воркера для конкретного пользователя"""
        print(f"[START_WORKER] ===== НАЧАЛО ЗАПУСКА ВОРКЕРА ДЛЯ USER_ID: {queue_entry.user_id} (приоритет: {queue_entry.priority}) =====")
        
        user_id = queue_entry.user_id
        
        try:
            # Получаем блокировку для запуска воркера
            async with get_worker_start_lock():
                print(f"[START_WORKER] Получена блокировка для пользователя {user_id}")
                
                # Проверяем, не запущен ли уже воркер для этого пользователя
                if worker_registry.is_worker_running(user_id):
                    print(f"[START_WORKER] Воркер для пользователя {user_id} уже активен, пропускаем")
                    async with self._processing_lock:
                        self._queue = [entry for entry in self._queue if entry.user_id != user_id]
                    return
                
                # Переводим в статус "processing"
                async with self._processing_lock:
                    for entry in self._queue:
                        if entry.user_id == user_id:
                            entry.status = "processing"
                            break
                
                print(f"[START_WORKER] Запускаем воркера для пользователя {user_id}")
                
                # Запускаем воркера через worker_manager
                success = await worker_manager.process_manager.start_worker_service(user_id, listen_posts=listen_posts)
                
                if success:
                    print(f"[START_WORKER] ✓ Воркер для пользователя {user_id} успешно запущен")
                    # Удаляем из очереди после успешного запуска
                    async with self._processing_lock:
                        self._queue = [entry for entry in self._queue if entry.user_id != user_id]
                else:
                    print(f"[START_WORKER] ✗ Не удалось запустить воркера для пользователя {user_id}")
                    # Удаляем из очереди при неудаче
                    async with self._processing_lock:
                        self._queue = [entry for entry in self._queue if entry.user_id != user_id]
                
        except Exception as e:
            print(f"[START_WORKER] Ошибка при запуске воркера для пользователя {user_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Удаляем из очереди при ошибке
            async with self._processing_lock:
                self._queue = [entry for entry in self._queue if entry.user_id != user_id]
        
        print(f"[START_WORKER] ===== КОНЕЦ ЗАПУСКА ВОРКЕРА ДЛЯ USER_ID: {user_id} =====")

    async def check_and_stop_inactive_workers(self):
        """Проверка и остановка неактивных воркеров"""
        print("[INACTIVE_CHECK] Запущена проверка неактивных воркеров")
        
        while True:
            try:
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
                
                print("[INACTIVE_CHECK] Проверяем неактивных воркеров...")
                
                # Получаем список всех зарегистрированных воркеров из in-memory реестра
                active_workers = list(worker_registry.get_all_workers().keys())
                
                if not active_workers:
                    continue
                
                print(f"[INACTIVE_CHECK] Найдено {len(active_workers)} активных воркеров: {active_workers}")
                
                # Проверяем каждого воркера
                for user_id in active_workers.copy():  # Копируем список для безопасной итерации
                    try:
                        # Получаем PID воркера из in-memory реестра
                        worker_info = worker_registry.get_worker_info(user_id)
                        if not worker_info:
                            print(f"[INACTIVE_CHECK] Воркер {user_id} не найден в реестре, пропускаем")
                            continue
                        
                        pid = worker_info.get('pid')
                        if not pid:
                            print(f"[INACTIVE_CHECK] Воркер {user_id} не имеет PID, удаляем из реестра")
                            worker_registry.remove_worker(user_id)
                            continue
                        
                        # Проверяем, что процесс все еще существует и валиден
                        if not worker_manager.is_valid_worker(pid, user_id):
                            print(f"[INACTIVE_CHECK] Воркер {user_id} (PID: {pid}) не валиден, удаляем из реестра")
                            worker_registry.remove_worker(user_id)
                            
                            # Если в очереди есть ожидающие воркеры, запускаем обработку
                            async with self._processing_lock:
                                pending_count = len([entry for entry in self._queue if entry.status == "pending"])
                                if pending_count > 0:
                                    print(f"[INACTIVE_CHECK] В очереди {pending_count} ожидающих воркеров, запускаем обработку")
                            continue
                        
                        # Получаем VIP уровень пользователя из БД
                        async with async_session() as db_session:
                            try:
                                user = await db_session.get(User, user_id)
                                vip_level = user.VIP_level if user else 0
                            except Exception as db_error:
                                print(f"[INACTIVE_CHECK] Ошибка получения VIP уровня для {user_id}: {db_error}")
                                vip_level = 0  # Используем VIP 0 по умолчанию при ошибке
                        
                        # Получаем timeout для данного VIP уровня
                        timeout_seconds = worker_manager.get_inactivity_timeout(vip_level)

                        # Проверяем общее время работы агента
                        started_at = worker_info.get('started_at')
                        if started_at:
                            if isinstance(started_at, datetime):
                                started_dt = started_at
                            else:
                                try:
                                    started_dt = datetime.fromisoformat(str(started_at))
                                except Exception:
                                    started_dt = None
                            if started_dt:
                                elapsed_runtime = (datetime.utcnow() - started_dt).total_seconds()
                                if elapsed_runtime >= timeout_seconds:
                                    print(f"[INACTIVE_CHECK] Воркер {user_id} превысил максимальное время работы {elapsed_runtime:.0f}с (лимит: {timeout_seconds}с для VIP {vip_level}), останавливаем")
                                    success = await worker_manager.stop_worker(user_id)
                                    if success:
                                        print(f"[INACTIVE_CHECK] Воркер {user_id} остановлен по общему таймеру")
                                    else:
                                        print(f"[INACTIVE_CHECK] Не удалось остановить воркер {user_id} по общему таймеру")
                                    continue

                        # Максимальное время обработки одного поста (из .env или 5 минут по умолчанию)
                        max_processing_time = int(os.getenv("MAX_PROCESSING_TIME_SECONDS", "300"))
                        
                        # Проверяем, обрабатывает ли воркер пост в данный момент
                        if worker_registry.is_processing(user_id):
                            processing_duration = worker_registry.get_processing_duration(user_id)
                            if processing_duration is not None:
                                if processing_duration < max_processing_time:
                                    print(f"[INACTIVE_CHECK] Воркер {user_id} обрабатывает пост ({processing_duration:.0f}с), пропускаем таймаут")
                                    continue
                                else:
                                    print(f"[INACTIVE_CHECK] Воркер {user_id} обрабатывает пост слишком долго ({processing_duration:.0f}с >= {max_processing_time}с), останавливаем")
                                    success = await worker_manager.stop_worker(user_id)
                                    if success:
                                        print(f"[INACTIVE_CHECK] Воркер {user_id} остановлен - превышено время обработки")
                                    else:
                                        print(f"[INACTIVE_CHECK] Не удалось остановить воркер {user_id}")
                                    continue
                        
                        # Проверяем время неактивности с учетом VIP уровня
                        last_activity = worker_info.get('last_activity', time.time())
                        current_time = time.time()
                        inactive_duration = current_time - last_activity
                        
                        if inactive_duration > timeout_seconds:
                            print(f"[INACTIVE_CHECK] Воркер {user_id} неактивен {inactive_duration:.0f}с (лимит: {timeout_seconds}с для VIP {vip_level}), останавливаем")
                            
                            # Останавливаем воркер
                            success = await worker_manager.stop_worker(user_id)
                            if success:
                                print(f"[INACTIVE_CHECK] Воркер {user_id} остановлен по таймауту")
                            else:
                                print(f"[INACTIVE_CHECK] Не удалось остановить воркер {user_id}")
                        else:
                            remaining_time = timeout_seconds - inactive_duration
                            print(f"[INACTIVE_CHECK] Воркер {user_id} активен, осталось {remaining_time:.0f}с до таймаута")
                        
                    except Exception as worker_error:
                        print(f"[INACTIVE_CHECK] Ошибка при проверке воркера {user_id}: {worker_error}")
                        # При ошибке проверки удаляем воркера из реестра
                        worker_registry.remove_worker(user_id)
                    
            except Exception as e:
                print(f"[INACTIVE_CHECK] Error checking inactive workers: {e}")
                import traceback
                traceback.print_exc()
    


# Глобальный экземпляр менеджера очереди (ленивая инициализация)
_queue_manager_instance = None

def get_queue_manager():
    """Получить глобальный экземпляр менеджера очереди с ленивой инициализацией"""
    global _queue_manager_instance
    if _queue_manager_instance is None:
        # Убеждаемся, что переменные окружения загружены
        load_dotenv()
        _queue_manager_instance = WorkerQueueManager()
        print(f"[QUEUE_MANAGER] Создан экземпляр с max_concurrent_workers = {_queue_manager_instance.max_concurrent_workers}")
    return _queue_manager_instance

# Для обратной совместимости
queue_manager = get_queue_manager()