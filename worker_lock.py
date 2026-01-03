import asyncio

# Глобальная блокировка для запуска воркеров
# Используется во всех модулях для предотвращения race condition
_global_worker_start_lock = asyncio.Lock()

def get_worker_start_lock():
    """Получить глобальную блокировку для запуска воркеров"""
    return _global_worker_start_lock