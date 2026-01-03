import os
import sys
import time
import psutil
import subprocess
import signal
import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update as sql_update
from sqlalchemy.orm import selectinload

from db import async_session
from models import Worker, User, TelegramSession
from telegram_worker.unified_messenger import MessageRole

# Version 5 - Microservice Architecture Manager
print("!!! EXECUTING LATEST VERSION OF WORKER_MANAGER.PY - v5 !!!")

def get_inactivity_timeout(vip_level: int) -> int:
    """Get inactivity timeout based on VIP level from .env settings."""
    # Получаем настройки из .env файла
    vip_0_timeout = int(os.getenv("VIP_0_TIMEOUT", "2")) * 60  # Конвертируем минуты в секунды
    vip_1_timeout = int(os.getenv("VIP_1_TIMEOUT", "10")) * 60
    vip_2_timeout = int(os.getenv("VIP_2_TIMEOUT", "20")) * 60
    vip_3_timeout = int(os.getenv("VIP_3_TIMEOUT", "30")) * 60
    
    if vip_level >= 3:
        return vip_3_timeout
    elif vip_level == 2:
        return vip_2_timeout
    elif vip_level == 1:
        return vip_1_timeout
    else:
        return vip_0_timeout

class ProcessManager:
    """Manages auth and worker processes for users."""
    
    def __init__(self):
        self.auth_processes: Dict[int, subprocess.Popen] = {}
        self.worker_processes: Dict[int, subprocess.Popen] = {}
        self.logger = logging.getLogger(__name__)
    
    def get_auth_port(self, user_id: int) -> int:
        """Get auth service port for user."""
        return 9000 + user_id
    
    def get_worker_port(self, user_id: int) -> int:
        """Get worker service port for user."""
        # Используем порты начиная с 8100 чтобы избежать конфликтов
        return 8100 + user_id
    
    async def start_auth_service(self, user_id: int) -> bool:
        """Start authorization service for user."""
        if user_id in self.auth_processes:
            if self.is_process_running(self.auth_processes[user_id]):
                self.logger.info(f"Auth service already running for user {user_id}")
                return True
            else:
                del self.auth_processes[user_id]
        
        try:
            port = self.get_auth_port(user_id)
            cmd = [
                sys.executable, "tg_auth.py",
                "--user_id", str(user_id),
                "--port", str(port)
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.auth_processes[user_id] = process
            self.logger.info(f"Started auth service for user {user_id} on port {port}")
            
            # Wait a bit to check if process started successfully
            await asyncio.sleep(2)
            if not self.is_process_running(process):
                self.logger.error(f"Auth service failed to start for user {user_id}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start auth service for user {user_id}: {e}")
            return False
    
    async def start_worker_service(self, user_id: int, listen_posts: bool = True) -> bool:
        """Start worker service for user."""
        if user_id in self.worker_processes:
            if self.is_process_running(self.worker_processes[user_id]):
                self.logger.info(f"Worker service already running for user {user_id}")
                return True
            else:
                del self.worker_processes[user_id]
        
        try:
            port = self.get_worker_port(user_id)
            cmd = [
                sys.executable, "tg_worker.py",
                "--user_id", str(user_id),
                "--port", str(port)
            ]

            if not listen_posts:
                cmd.append("--skip-listening")
            
            # Создаем лог-файлы для вывода
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            stdout_log = open(f"{log_dir}/worker_{user_id}_stdout.log", "w", encoding="utf-8", errors="replace")
            stderr_log = open(f"{log_dir}/worker_{user_id}_stderr.log", "w", encoding="utf-8", errors="replace")
            
            process = subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                stdout=stdout_log,  # Записываем в файл вместо PIPE
                stderr=stderr_log,  # Записываем в файл вместо PIPE
                text=True,
                env=os.environ.copy()  # Передаем переменные окружения
            )
            
            self.worker_processes[user_id] = process
            # Сохраняем ссылки на лог-файлы для последующего закрытия
            process._stdout_log = stdout_log
            process._stderr_log = stderr_log
            self.logger.info(f"Started worker service for user {user_id} on port {port}")
            
            # Wait for process to start and register in WorkerRegistry
            self.logger.info(f"Waiting for worker {user_id} to initialize...")
            
            # Check process is running
            await asyncio.sleep(0.5)  # Уменьшили с 2 до 0.5 секунд
            if not self.is_process_running(process):
                self.logger.error(f"Worker service failed to start for user {user_id}")
                stdout_log.close()
                stderr_log.close()
                return False
            
            # НЕ регистрируем воркер принудительно - пусть он сам себя зарегистрирует!
            # Это важно, потому что регистрация должна происходить только после
            # успешной инициализации Telegram соединения
            
            # Ждем, пока воркер сам себя зарегистрирует
            self.logger.info(f"Waiting for worker {user_id} to self-register...")
            
            # Проверяем регистрацию в течение 60 секунд с более частыми проверками
            from worker_registry import worker_registry
            for attempt in range(300):  # 300 попыток по 0.2 секунды = ~60 секунд
                await asyncio.sleep(0.2)  # Проверяем каждые 200мс для быстрого отклика
                if worker_registry.is_worker_running(user_id):
                    self.logger.info(f"Worker {user_id} successfully self-registered after {attempt * 0.2:.1f}s")
                    break
                # Fallback: accept as started if worker HTTP health is OK
                try:
                    if await self.check_service_health(user_id, "worker"):
                        self.logger.info(f"Worker {user_id} HTTP health OK after {attempt * 0.2:.1f}s; proceeding without registry")
                        break
                except Exception:
                    pass
                if not self.is_process_running(process):
                    self.logger.error(f"Worker process {process.pid} died during initialization")
                    stdout_log.close()
                    stderr_log.close()
                    return False
            else:
                self.logger.error(f"Worker {user_id} failed to self-register within 60 seconds")
                # Не убиваем процесс - возможно, он просто медленно инициализируется
                # Но сообщаем об ошибке
                stdout_log.close()
                stderr_log.close()
                return False
            
            self.logger.info(f"Worker {user_id} started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start worker service for user {user_id}: {e}")
            return False
    
    def stop_auth_service(self, user_id: int) -> bool:
        """Stop authorization service for user."""
        if user_id not in self.auth_processes:
            return True
        
        process = self.auth_processes[user_id]
        try:
            if self.is_process_running(process):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            
            del self.auth_processes[user_id]
            self.logger.info(f"Stopped auth service for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop auth service for user {user_id}: {e}")
            return False
    
    def stop_worker_service(self, user_id: int) -> bool:
        """Stop worker service for user."""
        from worker_registry import worker_registry
        
        process = None
        pid_to_kill = None
        
        # Check if we have the process in our local tracking
        if user_id in self.worker_processes:
            process = self.worker_processes[user_id]
            pid_to_kill = process.pid if process else None
        
        # If not in local tracking, check worker_registry for the PID
        if pid_to_kill is None:
            worker_info = worker_registry.get_worker_info(user_id)
            if worker_info and 'pid' in worker_info:
                pid_to_kill = worker_info['pid']
                self.logger.info(f"Found worker PID {pid_to_kill} for user {user_id} from registry")
        
        # If still no PID found, worker is not running
        if pid_to_kill is None:
            self.logger.info(f"No worker found for user {user_id} to stop")
            worker_registry.remove_worker(user_id)  # Cleanup registry just in case
            return True
        
        try:
            # If we have a subprocess.Popen object, use it
            if process and self.is_process_running(process):
                self.logger.info(f"Terminating worker process {pid_to_kill} for user {user_id} via Popen")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Worker {pid_to_kill} did not terminate gracefully, killing")
                    process.kill()
                    process.wait()
                
                # Close log files
                if hasattr(process, '_stdout_log'):
                    process._stdout_log.close()
                if hasattr(process, '_stderr_log'):
                    process._stderr_log.close()
            else:
                # Kill by PID using psutil
                self.logger.info(f"Terminating worker process {pid_to_kill} for user {user_id} via psutil")
                try:
                    proc = psutil.Process(pid_to_kill)
                    if proc.is_running():
                        proc.terminate()
                        try:
                            proc.wait(timeout=10)
                        except psutil.TimeoutExpired:
                            self.logger.warning(f"Worker {pid_to_kill} did not terminate gracefully, killing")
                            proc.kill()
                            proc.wait()
                        self.logger.info(f"Worker process {pid_to_kill} terminated successfully")
                except psutil.NoSuchProcess:
                    self.logger.info(f"Worker process {pid_to_kill} already terminated")
                except psutil.AccessDenied:
                    self.logger.error(f"Access denied when trying to terminate PID {pid_to_kill}")
                    return False
            
            # Clean up local tracking
            if user_id in self.worker_processes:
                del self.worker_processes[user_id]
            
            # Remove worker from WorkerRegistry
            worker_registry.remove_worker(user_id)
            self.logger.info(f"Stopped worker service for user {user_id} and removed from WorkerRegistry")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop worker service for user {user_id}: {e}")
            # Still try to remove from registry
            worker_registry.remove_worker(user_id)
            return False
    
    def is_process_running(self, process: subprocess.Popen) -> bool:
        """Check if process is still running."""
        return process.poll() is None
    
    async def check_service_health(self, user_id: int, service_type: str) -> bool:
        """Check if service is healthy via HTTP health check."""
        if service_type == "auth":
            port = self.get_auth_port(user_id)
        elif service_type == "worker":
            port = self.get_worker_port(user_id)
        else:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{port}/_health", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def send_code_request(self, user_id: int, phone_number: str) -> Dict[str, Any]:
        """Send code request to auth service."""
        port = self.get_auth_port(user_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/send_code",
                    json={"phone_number": phone_number},
                    timeout=30
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to send code request: {e}")
            return {"success": False, "error": str(e)}
    
    async def sign_in_request(self, user_id: int, phone_number: str, 
                             phone_code: str, password: Optional[str] = None) -> Dict[str, Any]:
        """Send sign in request to auth service."""
        port = self.get_auth_port(user_id)
        try:
            data = {
                "phone_number": phone_number,
                "phone_code": phone_code
            }
            if password:
                data["password"] = password
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/sign_in",
                    json=data,
                    timeout=30
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to send sign in request: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_worker_status(self, user_id: int) -> Dict[str, Any]:
        """Get worker status from worker service."""
        port = self.get_worker_port(user_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{port}/status",
                    timeout=10
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to get worker status: {e}")
            return {"error": str(e)}
    
    async def reload_worker_rules(self, user_id: int) -> Dict[str, Any]:
        """Reload worker rules."""
        port = self.get_worker_port(user_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/reload_rules",
                    timeout=10
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to reload worker rules: {e}")
            return {"error": str(e)}
    
    async def pause_worker(self, user_id: int) -> Dict[str, Any]:
        """Pause worker processing."""
        port = self.get_worker_port(user_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/pause",
                    timeout=10
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to pause worker: {e}")
            return {"error": str(e)}
    
    async def resume_worker(self, user_id: int) -> Dict[str, Any]:
        """Resume worker processing."""
        port = self.get_worker_port(user_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/resume",
                    timeout=10
                ) as response:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to resume worker: {e}")
            return {"error": str(e)}
    
    def cleanup_dead_processes(self):
        """Clean up dead processes from tracking."""
        # Clean up auth processes
        dead_auth = []
        for user_id, process in self.auth_processes.items():
            if not self.is_process_running(process):
                dead_auth.append(user_id)
        
        for user_id in dead_auth:
            del self.auth_processes[user_id]
            self.logger.info(f"Cleaned up dead auth process for user {user_id}")
        
        # Clean up worker processes
        dead_workers = []
        for user_id, process in self.worker_processes.items():
            if not self.is_process_running(process):
                dead_workers.append(user_id)
        
        for user_id in dead_workers:
            del self.worker_processes[user_id]
            self.logger.info(f"Cleaned up dead worker process for user {user_id}")
    
    def get_running_services(self) -> Dict[str, List[int]]:
        """Get list of running services."""
        self.cleanup_dead_processes()
        return {
            "auth_services": list(self.auth_processes.keys()),
            "worker_services": list(self.worker_processes.keys())
        }

# Global process manager instance
process_manager = ProcessManager()

async def get_user_lang(user_id: int) -> str:
    """Get user's language preference from database."""
    try:
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user and user.language_code:
                return user.language_code
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to get language for user {user_id}: {e}")
    return 'en'  # Default to English if not found or error

async def notify_worker_stopping(user_id: int, key: str = "worker_stopping_manual") -> None:
    """Send a bot notification that the worker is about to stop."""
    try:
        from telegram_worker.unified_messenger import get_unified_messenger, MessageRole
        from telegram_worker.utils import get_localized_message

        # Get user's language preference
        lang = await get_user_lang(user_id)

        messenger = get_unified_messenger(user_id)
        await messenger.send(key, MessageRole.USER_STATUS)
    except Exception as exc:
        logging.getLogger(__name__).error(
            "Failed to notify user %s about worker stop: %s", user_id, exc
        )

# Wrapper functions for Telegram bot compatibility
async def start_worker(user_id: int) -> bool:
    """Start worker for user (wrapper for bot integration)"""
    return await process_manager.start_worker_service(user_id)

async def stop_worker(user_id: int) -> bool:
    """Stop worker for user (wrapper for bot integration)"""
    try:
        await notify_worker_stopping(user_id)
    except Exception:
        pass

    # Also remove from queue if present
    try:
        from queue_manager import get_queue_manager
        queue_manager = get_queue_manager()
        await queue_manager.remove_from_queue(user_id)
        logging.getLogger(__name__).info(f"Removed user {user_id} from queue (if present)")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to remove user {user_id} from queue: {e}")

    # Stop the worker service
    stop_result = process_manager.stop_worker_service(user_id)

    # Send final status message after successful stop
    if stop_result:
        try:
            from telegram_worker.unified_messenger import get_unified_messenger, MessageRole

            messenger = get_unified_messenger(user_id)
            await messenger.send("worker_stopped_final", MessageRole.USER_STATUS)
        except Exception as exc:
            logging.getLogger(__name__).error(
                "Failed to send final stop notification to user %s: %s", user_id, exc
            )

    return stop_result

# Legacy functions for backward compatibility
def is_valid_worker(pid: int, user_id: int) -> bool:
    """Legacy function - check if worker process is valid."""
    try:
        if not pid or pid < 1:
            return False
        
        process = psutil.Process(pid)
        if not process.is_running():
            return False
        
        cmdline = process.cmdline()
        if not cmdline or len(cmdline) < 2:
            return False
        
        # Check if it's a Python process running tg_worker.py
        cmdline_str = " ".join(cmdline)
        if "python" not in cmdline[0].lower() and "tg_worker.py" not in cmdline_str:
            return False
        
        # Check for user_id in command line arguments
        # The command line is: ["python", "tg_worker.py", "--user_id", "123", "--port", "8123"]
        try:
            user_id_index = cmdline.index("--user_id")
            if user_id_index + 1 < len(cmdline) and cmdline[user_id_index + 1] == str(user_id):
                return True
        except ValueError:
            pass
        
        return False
        
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    except Exception:
        return False

def start_worker_process(user_id: int, session_path: str) -> Optional[subprocess.Popen]:
    """Legacy function - start worker process."""
    try:
        # Import S3SessionManager here to avoid circular imports
        from s3_session_manager import S3SessionManager
        
        # Try to download session from S3 if it doesn't exist locally
        if not os.path.exists(session_path):
            s3_manager = S3SessionManager()
            if not s3_manager.download_session(user_id, session_path):
                logging.error(f"Session file not found locally or in S3: {session_path}")
                return None
        
        # Double-check that session file exists after potential download
        if not os.path.exists(session_path):
            logging.error(f"Session file still not found after download attempt: {session_path}")
            return None
        
        cmd = [
            sys.executable, "tg_worker.py",
            "--user_id", str(user_id),
            "--port", str(8000 + user_id)
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
        
    except Exception as e:
        logging.error(f"Failed to start worker process: {e}")
        return None

def stop_worker_process(pid: int) -> bool:
    """Legacy function - stop worker process."""
    try:
        if not pid or pid < 1:
            return False
        
        process = psutil.Process(pid)
        if not process.is_running():
            return True
        
        # Try graceful termination first
        process.terminate()
        
        # Wait for process to terminate
        try:
            process.wait(timeout=3)  # Reduced timeout from 10 to 3 seconds
        except psutil.TimeoutExpired:
            # Force kill if graceful termination failed
            process.kill()
            process.wait()
        
        return True
        
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return True  # Process already gone
    except Exception as e:
        logging.error(f"Failed to stop worker process {pid}: {e}")
        return False
