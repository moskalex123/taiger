from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer # Не используется для cookie
from fastapi.responses import JSONResponse # Added
import jwt
import os # Добавлено
from datetime import datetime, timedelta, timezone # Добавлено
from sqlalchemy import select, text # Added import
from sqlalchemy.ext.asyncio import AsyncSession # Added import
import asyncio
from typing import Dict, Optional, Union

from tg_auth import TelegramAuth
from tg_worker import TelegramWorker
from db import get_db # Added import
from models import User as DBUser, TelegramSession, Worker # Added import
from balance_utils import get_start_balance
from pyrogram.errors import PhoneNumberUnoccupied, UserDeactivated, PhoneCodeInvalid, SessionPasswordNeeded, PasswordHashInvalid, PhoneCodeExpired # Added Pyrogram errors
from s3_session_manager import S3SessionManager

# SECRET_KEY = "your_secret_key" # Заменено на переменную окружения
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_please_change_me") # Добавьте свою переменную окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 90 # 90 дней для удобства пользователей
CODE_EXPIRY_MINUTES = 5 # Время жизни кода в минутах

# UserData class to replace DBUser when using raw SQL
class UserData:
    def __init__(self, row):
        self.id = row.id
        self.telegram_id = row.telegram_id
        self.telegram_user_name = row.telegram_user_name
        self.phone_number = row.phone_number
        self.balance = row.balance
        self.send_report_to = row.send_report_to
        self.VIP_level = getattr(row, 'VIP_level', 0)
        self.username = row.username
        self.first_name = row.first_name
        self.last_name = row.last_name
        self.is_superuser = row.is_superuser
        self.avatar_url = row.avatar_url
        self.created_at = row.created_at
        self.is_active = row.is_active
        self.is_newcomer = row.is_newcomer
        self.language_code = getattr(row, 'language_code', 'en')

async def get_user_id_by_phone(phone_number: str) -> Optional[int]:
    """Найти ID пользователя по номеру телефона в базе данных"""
    from db import async_session
    print(f"🔍 Searching for user with phone: {phone_number}")
    async with async_session() as db_session:  # type: ignore
        try:
            result = await db_session.execute(
                select(DBUser.id).where(DBUser.phone_number == phone_number)
            )
            user_id = result.scalar_one_or_none()
            if user_id:
                print(f"✅ Found existing user with ID: {user_id} for phone: {phone_number}")
            else:
                print(f"❌ No user found for phone: {phone_number}")
            return user_id
        except Exception as e:
            print(f"❌ Error finding user by phone {phone_number}: {e}")
            return None

# Create an APIRouter instance
router = APIRouter()

# Кэш активных TelegramAuth экземпляров для предотвращения потери сессии
active_workers: Dict[str, TelegramAuth] = {}
worker_cleanup_tasks: Dict[str, asyncio.Task] = {}

async def cleanup_worker(phone_number: str, delay_minutes: int = 10):
    """Очистка worker'а через заданное время"""
    await asyncio.sleep(delay_minutes * 60)
    if phone_number in active_workers:
        worker = active_workers[phone_number]
        try:
            # Use the new disconnect method if available
            if hasattr(worker, 'disconnect_client'):
                success = await worker.disconnect_client()
                if not success:
                    print(f"Warning: Failed to disconnect worker for {phone_number}")
            elif hasattr(worker.client, 'is_connected') and worker.client.is_connected:
                await worker.client.disconnect()
        except Exception as e:
            print(f"Error disconnecting worker for {phone_number}: {e}")
        finally:
            active_workers.pop(phone_number, None)
            worker_cleanup_tasks.pop(phone_number, None)
            print(f"Worker for {phone_number} cleaned up")

async def get_or_create_worker(phone_number: str, user_id: Optional[int] = None) -> TelegramAuth:
    """Получить существующий или создать новый worker"""
    # Always disconnect and remove existing worker to prevent "Client is already connected" errors
    if phone_number in active_workers:
        worker = active_workers[phone_number]
        try:
            # Use the new disconnect method if available
            if hasattr(worker, 'disconnect_client'):
                success = await worker.disconnect_client()
                if not success:
                    print(f"Warning: Failed to disconnect worker for {phone_number}")
            elif hasattr(worker.client, 'is_connected') and worker.client.is_connected:
                await worker.client.disconnect()
        except Exception as e:
            print(f"Warning: Error disconnecting existing client for {phone_number}: {e}")
        finally:
            # Remove the old worker from cache regardless of disconnect success
            active_workers.pop(phone_number, None)
            # Also cancel any cleanup tasks
            if phone_number in worker_cleanup_tasks:
                worker_cleanup_tasks[phone_number].cancel()
                worker_cleanup_tasks.pop(phone_number, None)
    
    session_file_path = f"sessions/{phone_number}.session"
    os.makedirs(os.path.dirname(session_file_path), exist_ok=True)
    
    # Если user_id не передан, попробуем найти его в базе данных
    if user_id is None:
        user_id = await get_user_id_by_phone(phone_number)
        if user_id is None:
            # Если пользователь не найден, используем хеш номера телефона для нового пользователя
            user_id = abs(hash(phone_number)) % 1000000
    
    # Pass phone_number to TelegramAuth for new users
    worker = TelegramAuth(user_id=user_id, phone_number=phone_number)
    
    active_workers[phone_number] = worker
    return worker

def schedule_worker_cleanup(phone_number: str):
    """Запланировать очистку worker'а"""
    # Отменить предыдущую задачу очистки, если она существует
    if phone_number in worker_cleanup_tasks:
        worker_cleanup_tasks[phone_number].cancel()
    
    # Создать новую задачу очистки
    task = asyncio.create_task(cleanup_worker(phone_number))
    worker_cleanup_tasks[phone_number] = task

def is_code_expired(code_sent_time: datetime) -> bool:
    """Проверить, истек ли код"""
    if not code_sent_time:
        return True
    
    # Убеждаемся, что code_sent_time в UTC
    if code_sent_time.tzinfo is None:
        # Если timezone не указан, считаем что это UTC
        code_sent_time = code_sent_time.replace(tzinfo=timezone.utc)
    
    # Используем datetime.now(timezone.utc) вместо datetime.utcnow()
    current_time = datetime.now(timezone.utc)
    time_diff = current_time - code_sent_time
    
    print(f"Code expiry check: current_time={current_time}, code_sent_time={code_sent_time}, diff={time_diff.total_seconds()}s, limit={CODE_EXPIRY_MINUTES * 60}s")
    
    return time_diff.total_seconds() > (CODE_EXPIRY_MINUTES * 60)

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    # First try to get token from Authorization header (for TMA)
    authorization: Optional[str] = request.headers.get("Authorization")
    token = None
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    else:
        # Fallback to cookie-based authentication
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated - No token provided. Please login again.")
    
    payload = decode_jwt_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token - Token could not be decoded. Token: {token[:50]}{'...' if len(token) > 50 else ''}")
    user_id = payload.get("sub") # Assuming user_id is stored in 'sub' claim
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token payload - Missing 'sub' field in token. Payload: {payload}")
    
    # Query by id using raw SQL to avoid ORM cache issues
    result = await db.execute(
        text("SELECT * FROM users WHERE id = :user_id"),
        {"user_id": int(user_id)}
    )
    user_row = result.fetchone()

    if user_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"User not found - No user with ID {user_id} exists in the database. Please contact support.")
    
    return UserData(user_row)

@router.post("/auto-login")
async def auto_login(request: Request, db: AsyncSession = Depends(get_db)):
    """Автоматический вход через cookies"""
    try:
        # Auto-login logs disabled to reduce console clutter
        token = request.cookies.get("access_token")
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"status": "no_token", "message": "No authentication token found"}
            )
        
        # Декодируем токен
        payload = decode_jwt_token(token)
        if payload is None:
            # Удаляем недействительный cookie
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"status": "invalid_token", "message": "Invalid authentication token"}
            )
            response.delete_cookie("access_token")
            return response
        
        user_id = payload.get("sub")
        if user_id is None:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"status": "invalid_payload", "message": "Invalid token payload"}
            )
            response.delete_cookie("access_token")
            return response
        
        # Проверяем пользователя в базе данных
        result = await db.execute(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": int(user_id)}
        )
        user_row = result.fetchone()
        
        if user_row is None:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "status": "user_not_found", 
                    "message": f"User not found - No user with ID {user_id} exists in the database. Please contact support.",
                    "user_id_attempted": user_id
                }
            )
            response.delete_cookie("access_token")
            return response
        
        # Успешная автоматическая авторизация
        return JSONResponse(
            content={
                "status": "success",
                "message": "Auto-login successful",
                "user_id": user_row.id,
                "phone_number": user_row.phone_number
            }
        )
        
    except Exception as e:
        print(f"Error in /auto-login: {e}")
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "Internal server error"}
        )
        response.delete_cookie("access_token")
        return response




@router.post("/login")
async def login_for_access_token(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        # Сначала проверяем наличие валидного токена в куках
        token = request.cookies.get("access_token")
        if token:
            payload = decode_jwt_token(token)
            if payload:
                user_id_from_token = payload.get("sub")
                if user_id_from_token:
                    # Проверяем пользователя в базе данных по id из токена
                    result = await db.execute(select(DBUser).where(DBUser.id == int(user_id_from_token)))
                    user = result.scalar_one_or_none()
                    if user:
                        # Пользователь найден и токен валиден, перенаправляем на дашборд
                        return JSONResponse(
                            status_code=status.HTTP_200_OK,
                            content={
                                "status": "redirect_to_dashboard",
                                "message": "User authenticated via cookie. Redirecting to dashboard.",
                                "user_id": user.id,
                                "phone_number": user.phone_number
                            }
                        )
        
        # Если токена нет или он невалиден, проверяем наличие JSON данных
        try:
            data = await request.json()
        except Exception:
            # Если нет JSON данных и нет валидного токена, требуем номер телефона
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number required or valid session cookie")
        
        phone_number = data.get("phone")
        if not phone_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number required")

        # Actual user lookup
        result = await db.execute(select(DBUser).where(DBUser.phone_number == phone_number))
        user = result.scalar_one_or_none()

        if user:
            # User exists, but require Telegram authentication for security
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "telegram_auth_required",
                    "message": "Please complete Telegram authentication to access your account.",
                    "phone_number": phone_number
                }
            )
        else:
            # User does not exist, signal for Telegram authentication
            return JSONResponse(
                status_code=status.HTTP_200_OK, # Using 200 OK with a specific payload
                content={
                    "status": "new_user_telegram_auth_required",
                    "message": "User not found. Please complete Telegram authentication to register.",
                    "phone_number": phone_number
                }
            )

    except Exception as e:
        print(f"Error in /login: {e}") # Consider using proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Internal server error during login: {str(e)} - Please contact support with this error message for assistance."
        )

@router.post("/check")
async def check_session(request: Request, current_user: DBUser = Depends(get_current_user)):
    # If get_current_user succeeds, a valid session exists for the user.
    # The user details are in current_user.
    return {"message": "Session is active", "user_id": current_user.id, "phone": current_user.phone_number}

@router.post("/logout")
async def logout(request: Request):
    """Logout user by clearing cookies"""
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("access_token", path="/")
    return response

@router.post("/request_telegram_code")
async def request_telegram_code(request: Request, db: AsyncSession = Depends(get_db)):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            data = await request.json()
            phone_number = data.get("phone")
            if not phone_number:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number required")

            # Попробуем найти пользователя в базе данных по номеру телефона
            print(f"🔍 Searching for user with phone: {phone_number}")
            user_query = select(DBUser).where(DBUser.phone_number == phone_number)
            user_result = await db.execute(user_query)
            existing_user = user_result.scalar_one_or_none()
            
            # Получаем или создаем worker для данного номера телефона
            user_id = existing_user.id if existing_user else None
            print(f"🔍 Found existing_user: {existing_user}")
            print(f"🔍 Using user_id: {user_id} for phone: {phone_number}")
            
            if existing_user:
                print(f"✅ Found existing user with ID: {existing_user.id}, phone: {existing_user.phone_number}")
            else:
                print(f"❌ No user found for phone: {phone_number}, will create new")
            # IMPORTANT: don't pass user_id=0 for new users.
            # Let get_or_create_worker() generate a stable id for this phone number.
            worker = await get_or_create_worker(phone_number, int(user_id) if user_id is not None else None)  # type: ignore

            # Отправляем код подтверждения через Telegram и получаем phone_code_hash
            result = await worker.send_code()
            phone_code_hash = result.get('phone_code_hash') if isinstance(result, dict) else None
            code_sent_time = worker.code_sent_time
            
            # Проверяем результат отправки кода
            if isinstance(result, dict) and result.get('status') == 'error':
                error_message = result.get('message', 'Unknown error')
                print(f"Error sending Telegram code: {error_message}")
                
                # Special handling for "Client is already connected" error
                if "Client is already connected" in error_message and retry_count < max_retries - 1:
                    retry_count += 1
                    print(f"Retrying due to 'Client is already connected' error (attempt {retry_count}/{max_retries})")
                    # Force remove worker from cache and create a fresh one
                    active_workers.pop(phone_number, None)
                    await asyncio.sleep(0.5)  # Small delay before retry
                    continue  # Retry the loop
                elif "Client is already connected" in error_message:
                    # Final attempt failed
                    active_workers.pop(phone_number, None)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Failed to send Telegram code: Client is already connected. Please try again later."
                    )
                
                # Удаляем worker из кэша при ошибке
                active_workers.pop(phone_number, None)
                
                # Проверяем тип ошибки и возвращаем соответствующее сообщение
                if "Invalid phone number" in error_message:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid phone number. Please check the number and try again."
                    )
                elif "Too many requests" in error_message:
                    # Извлекаем время ожидания из сообщения
                    import re
                    wait_time_match = re.search(r"Wait (\d+) seconds", error_message)
                    wait_time = wait_time_match.group(1) if wait_time_match else "a few"
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many requests. Please wait {wait_time} seconds before trying again."
                    )
                elif "FloodWait" in error_message:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests to Telegram. Please wait before trying again."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to send Telegram code: {error_message}"
                    )
            
            if not phone_code_hash or not code_sent_time:
                print(f"Error: Failed to get phone_code_hash from Telegram for phone {phone_number}. Worker returned: {phone_code_hash}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get phone_code_hash from Telegram. Please try again later."
                )
            
            print(f"Successfully received phone_code_hash: {phone_code_hash} for phone {phone_number}")
            
            # Планируем очистку worker'а через 10 минут, если код не будет использован
            schedule_worker_cleanup(phone_number)

            return JSONResponse(
                content={
                    "message": "Telegram code sent successfully",
                    "phone_number": phone_number,
                    "phone_code_hash": phone_code_hash,
                    "code_sent_time": code_sent_time.isoformat(),
                    "expires_in_minutes": CODE_EXPIRY_MINUTES
                }
            )
        except HTTPException:
            # Re-raise HTTP exceptions without modification
            raise
        except Exception as e:
            print(f"Error in request_telegram_code: {e}")
            # Удаляем worker из кэша при неожиданной ошибке
            if 'phone_number' in locals():
                active_workers.pop(phone_number, None)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error during Telegram code request: {str(e)}"
            )
    
    # If we get here, all retries failed
    if 'phone_number' in locals():
        active_workers.pop(phone_number, None)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Failed to send Telegram code after multiple attempts. Please try again later."
    )

@router.post("/submit_code")
async def submit_telegram_code(request: Request, db: AsyncSession = Depends(get_db)):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            data = await request.json()
            phone_number = data.get("phone")
            code = data.get("code")
            phone_code_hash = data.get("phone_code_hash")
            password = data.get("password") # Для 2FA
            code_sent_time_str = data.get("code_sent_time")

            # Diagnostic logs (do not log code/password values)
            print(
                "[TG_AUTH][submit_code] incoming payload: "
                f"phone={phone_number} code_present={bool(code)} phone_code_hash_present={bool(phone_code_hash)} "
                f"password_present={bool(password)} code_sent_time_present={bool(code_sent_time_str)}"
            )

            if not phone_number or not code or not phone_code_hash or not code_sent_time_str:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number, code, phone_code_hash, and code_sent_time are required")

            # Проверяем время отправки кода
            try:
                code_sent_time = datetime.fromisoformat(code_sent_time_str)
                # Убеждаемся, что datetime имеет timezone info
                if code_sent_time.tzinfo is None:
                    code_sent_time = code_sent_time.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                print(f"Warning: code_sent_time_str '{code_sent_time_str}' is invalid")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code_sent_time format")
            
            # Проверяем, не истек ли код
            if is_code_expired(code_sent_time):
                # Удаляем worker из кэша, так как код истек
                active_workers.pop(phone_number, None)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Telegram code has expired. Please request a new code. Code expires after {CODE_EXPIRY_MINUTES} minutes."
                )

            # Получаем существующий worker или создаем новый
            worker = active_workers.get(phone_number)
            if not worker:
                print(f"Warning: No active worker found for {phone_number}, creating new one")
                worker = await get_or_create_worker(phone_number)
                worker.phone_code_hash = phone_code_hash
                worker.code_sent_time = code_sent_time

            # More diagnostics about worker/client state
            try:
                client_connected = bool(getattr(worker.client, "is_connected", False))
            except Exception:
                client_connected = None
            print(
                "[TG_AUTH][submit_code] worker state: "
                f"phone={phone_number} worker_user_id={getattr(worker, 'user_id', None)} "
                f"phone_number_set={bool(getattr(worker, 'phone_number', None))} "
                f"phone_code_hash_set={bool(getattr(worker, 'phone_code_hash', None))} "
                f"code_sent_time_set={bool(getattr(worker, 'code_sent_time', None))} "
                f"client_is_connected={client_connected}"
            )
            
            # Убеждаемся, что у worker'а есть необходимые данные
            if not worker.phone_code_hash:
                worker.phone_code_hash = phone_code_hash
            if not worker.code_sent_time:
                worker.code_sent_time = code_sent_time

            try:
                # Пытаемся войти с кодом и паролем (если есть)
                user = await worker.sign_in(code=code, password=password)

                # Diagnostic log of TelegramAuth result
                try:
                    print(
                        "[TG_AUTH][submit_code] worker.sign_in result: "
                        f"type={type(user)} status={user.get('status') if isinstance(user, dict) else None} "
                        f"message={user.get('message') if isinstance(user, dict) else None}"
                    )
                except Exception as log_error:
                    print(f"[TG_AUTH][submit_code] failed to log worker.sign_in result: {log_error}")
                
                # Проверяем результат входа
                if isinstance(user, dict) and user.get('status') == 'error':
                    error_message = user.get('message', 'Unknown error')
                    print(f"Error during Telegram sign in: {error_message}")
                    
                    # Special handling for "Client is already connected" error
                    if "Client is already connected" in error_message and retry_count < max_retries - 1:
                        retry_count += 1
                        print(f"Retrying due to 'Client is already connected' error (attempt {retry_count}/{max_retries})")
                        # Force remove worker from cache and create a fresh one
                        active_workers.pop(phone_number, None)
                        await asyncio.sleep(0.5)  # Small delay before retry
                        continue  # Retry the loop
                    elif "Client is already connected" in error_message:
                        # Final attempt failed
                        active_workers.pop(phone_number, None)
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Failed to sign in: Client is already connected. Please try again later."
                        )
                    
                    # Проверяем тип ошибки и возвращаем соответствующее сообщение
                    if "Invalid authentication code" in error_message:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Telegram code. Please check the code and try again."
                        )
                    elif "Authentication code expired" in error_message:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Telegram code has expired. Please request a new code."
                        )
                    elif "Two-factor authentication password required" in error_message:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Two-factor authentication password required. Please provide your 2FA password."
                        )
                    elif "Invalid two-factor authentication password" in error_message:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid two-factor authentication password. Please check your password and try again."
                        )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Telegram authentication failed: {error_message}. Please try again."
                        )
                
                # After successful login, get user info
                tg_user = await worker.get_me()
                if not tg_user:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to verify Telegram user after sign in.")

                # First check by telegram_id (primary identifier)
                tg_id_result = await db.execute(select(DBUser).where(DBUser.telegram_id == int(tg_user.id)))
                db_user = tg_id_result.scalar_one_or_none()
                
                if db_user:
                    # User found by telegram_id, update phone number if changed
                    if db_user.phone_number != phone_number:
                        print(f"Updating phone number for user {db_user.id}: {db_user.phone_number} -> {phone_number}")
                        db_user.phone_number = phone_number
                    
                    # Update other fields from Telegram
                    db_user.telegram_user_name = tg_user.username  # type: ignore
                    db_user.username = tg_user.username  # type: ignore
                    db_user.first_name = tg_user.first_name  # type: ignore
                    db_user.last_name = tg_user.last_name  # type: ignore
                    
                    await db.commit()
                    await db.refresh(db_user)
                    print(f"Existing user {db_user.id} logged in from new device with phone {phone_number}")
                else:
                    # Check by phone number (user may exist but without telegram_id)
                    phone_result = await db.execute(select(DBUser).where(DBUser.phone_number == phone_number))
                    db_user = phone_result.scalar_one_or_none()
                    
                    if db_user:
                        # User found by phone, update telegram_id
                        print(f"Linking existing user {db_user.id} with telegram_id {tg_user.id}")
                        db_user.telegram_id = int(tg_user.id)  # type: ignore
                        db_user.telegram_user_name = tg_user.username  # type: ignore
                        db_user.username = tg_user.username  # type: ignore
                        db_user.first_name = tg_user.first_name  # type: ignore
                        db_user.last_name = tg_user.last_name  # type: ignore
                        
                        await db.commit()
                        await db.refresh(db_user)
                        print(f"Linked existing user {db_user.id} with Telegram account")
                    else:
                        # Create new user
                        start_balance = get_start_balance()
                        db_user = DBUser(
                            phone_number=phone_number,
                            telegram_id=int(tg_user.id),
                            telegram_user_name=tg_user.username,
                            username=tg_user.username,
                            first_name=tg_user.first_name,
                            last_name=tg_user.last_name,
                            balance=start_balance,
                            # created_at should be handled by model or DB
                        )
                        db.add(db_user)
                        await db.commit()
                        await db.refresh(db_user)
                        print(f"New user created: {db_user.id} for phone {phone_number}")

                # Update user_id in worker after getting/creating user in DB
                worker.user_id = int(db_user.id)  # type: ignore
                
                # Save Telegram session to S3 for future use
                session_save_success = False
                try:
                    print(f"Attempting to save session for user {db_user.id}")
                    session_saved = await worker.save_session_to_s3()
                    if session_saved:
                        print(f"✅ Session successfully saved to S3 for user {db_user.id}")
                        session_save_success = True

                        # Also save session record in DB
                        session_stmt = select(TelegramSession).where(TelegramSession.user_id == db_user.id)
                        session_result = await db.execute(session_stmt)
                        existing_session = session_result.scalar_one_or_none()

                        if existing_session:
                            # Update existing record
                            existing_session.session_path = f"{db_user.id}.session"  # type: ignore
                            existing_session.session_last_used = datetime.now(timezone.utc)  # type: ignore
                        else:
                            # Create new record
                            new_session = TelegramSession(
                                user_id=db_user.id,
                                session_path=f"{db_user.id}.session",
                                session_last_used=datetime.now(timezone.utc)
                            )
                            db.add(new_session)

                        await db.commit()
                        print(f"✅ Session record updated in database for user {db_user.id}")

                        # Reset worker status to stopped after successful authentication
                        from sqlalchemy import update as sql_update

                        await db.execute(
                            sql_update(Worker)
                            .where(Worker.user_id == db_user.id)
                            .values(status='stopped', last_error=None, pid=None)
                        )
                        await db.commit()
                        print(f"✅ Worker status reset to stopped for user {db_user.id}")

                    else:
                        print(f"❌ Warning: Failed to save session to S3 for user {db_user.id}")
                except Exception as session_error:
                    print(f"Error saving session for user {db_user.id}: {session_error}")
                    # Check if this is a client termination error after successful auth
                    if "Client is already terminated" in str(session_error) and 'db_user' in locals():
                        print(f"⚠️ Client terminated during finalization, but user {db_user.id} was successfully authenticated")
                        session_save_success = True  # Consider it successful since auth worked
                    else:
                        print(f"❌ Session save failed with non-termination error: {session_error}")
                
                # Download user avatar after successful authentication (optional)
                try:
                    # Avatar download is handled in finalize_auth method
                    pass
                except Exception as avatar_error:
                    print(f"Warning: Failed to download avatar for user {db_user.id}: {avatar_error}")
                    # Don't fail authentication if avatar download fails
                
                # At this point, authentication was successful - user exists and session was established
                # Even if session save had issues, the core auth worked
                print(f"✅ Authentication successful for user {db_user.id}")

                # Create JWT token
                access_token_payload = {"sub": str(db_user.id)}
                token = create_jwt_token(access_token_payload)

                response_content = {
                    "message": "Login successful after Telegram verification.",
                    "access_token": token,
                    "token_type": "bearer",
                    "user_id": db_user.id
                }
                json_response = JSONResponse(content=response_content)
                json_response.set_cookie(
                    key="access_token",
                    value=token,
                    httponly=True,
                    samesite="lax",
                    secure=False, # True in production
                    max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    # Remove domain so cookies work on any domain
                    path="/"
                )
                return json_response

            except ConnectionError as e:
                print(f"Telegram connection error during code submission: {e}")
                # Remove worker from cache on connection error
                active_workers.pop(phone_number, None)
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Telegram service connection error: {str(e)}. Please check your internet connection and try again.")
            except jwt.PyJWTError as e:
                print(f"JWT Error during sign_in or get_me: {e}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Telegram authentication error: {str(e)}. Please try again.")
            except PhoneCodeInvalid as e_code_invalid:
                print(f"PhoneCodeInvalid during code submission: {e_code_invalid}")
                # Remove worker from cache on invalid code
                active_workers.pop(phone_number, None)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Telegram code. Please check the code and try again.")
            except PhoneCodeExpired as e_code_expired:
                print(f"PhoneCodeExpired during code submission: {e_code_expired}")
                # Remove worker from cache on expired code
                active_workers.pop(phone_number, None)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram code has expired. Please request a new code.")
            except SessionPasswordNeeded as e_session_pwd:
                print(f"SessionPasswordNeeded during code submission: {e_session_pwd}")
                # DON'T remove worker, as 2FA may be required
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Two-factor authentication password required. Please provide your 2FA password.")
            except PasswordHashInvalid as e_pwd_hash:
                print(f"PasswordHashInvalid during code submission: {e_pwd_hash}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid two-factor authentication password. Please check your password and try again.")
            except (PhoneNumberUnoccupied, UserDeactivated) as e_telegram_user_issue:
                error_detail = f"Telegram error: {str(e_telegram_user_issue)}"
                print(f"Telegram user issue during code submission: {e_telegram_user_issue}")
                # Remove worker from cache on user issues
                active_workers.pop(phone_number, None)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Telegram account issue: {str(e_telegram_user_issue)}. Please check your Telegram account status.")
            except Exception as e:
                error_detail = str(e)
                print(f"Generic error submitting Telegram code: {e}")

                # Special handling: if user was successfully created/updated but client terminated during finalization
                if "Client is already terminated" in error_detail and 'db_user' in locals() and db_user is not None:
                    print(f"⚠️ Client terminated during finalization, but authentication was successful for user {db_user.id}")
                    print("✅ Returning success despite client termination - authentication completed")

                    # Create JWT token for the successfully authenticated user
                    access_token_payload = {"sub": str(db_user.id)}
                    token = create_jwt_token(access_token_payload)

                    response_content = {
                        "message": "Login successful after Telegram verification.",
                        "access_token": token,
                        "token_type": "bearer",
                        "user_id": db_user.id
                    }
                    json_response = JSONResponse(content=response_content)
                    json_response.set_cookie(
                        key="access_token",
                        value=token,
                        httponly=True,
                        samesite="lax",
                        secure=False, # True in production
                        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                        path="/"
                    )
                    return json_response

                # For other errors, remove worker and raise exception
                active_workers.pop(phone_number, None)
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                raise HTTPException(status_code=status_code, detail=f"Unexpected error during Telegram authentication: {error_detail}. Please try again or contact support.")
            finally:
                # Cancel cleanup task since code was successfully used or error occurred
                if phone_number in worker_cleanup_tasks:
                    worker_cleanup_tasks[phone_number].cancel()
                    worker_cleanup_tasks.pop(phone_number, None)
                
                # Schedule worker cleanup shortly after successful authentication
                # or immediately remove on error (already handled above)
                if phone_number in active_workers:
                    schedule_worker_cleanup(phone_number)

        except HTTPException:
            # Re-raise HTTP exceptions without modification
            raise
        except Exception as e:
            print(f"Error in submit_telegram_code endpoint: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Internal server error during Telegram code submission: {str(e)} - Please contact support with this error message for assistance."
            )
    
    # If we get here, all retries failed
    if 'phone_number' in locals():
        active_workers.pop(phone_number, None)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Failed to submit Telegram code after multiple attempts. Please try again later."
    )

# security = HTTPBearer() # Не используется для cookie
def create_jwt_token(data: dict):
    # Добавляем обязательное поле 'sub' для JWT стандарта
    if 'sub' not in data:
        raise ValueError("Payload must contain 'sub' field for subject")
    to_encode = data.copy()
    # --- Убедимся, что 'sub' является строкой ---
    to_encode['sub'] = str(to_encode['sub'])
    # --- Конец изменения ---
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str):
    try:
        # All token decoding logs disabled to reduce console clutter
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"WARNING: JWT EXPIRED: {e}. Token: {token[:30]}...")
        return None
    except jwt.InvalidSignatureError as e: # Более специфичная ошибка для неверной подписи
        print(f"WARNING: JWT INVALID SIGNATURE: {e}. Token: {token[:30]}...")
        return None
    except jwt.InvalidTokenError as e: # Общая ошибка невалидного токена (может включать разные проблемы)
        print(f"WARNING: JWT INVALID TOKEN (InvalidTokenError): {e}. Token: {token[:30]}...")
        return None
    except jwt.PyJWTError as e: # Общий обработчик для других ошибок PyJWT
        print(f"ERROR: JWT DECODING ERROR (PyJWTError): {e}. Token: {token[:30]}...")
        return None
    except Exception as e: # Обработка любых других неожиданных ошибок
        print(f"ERROR: UNEXPECTED ERROR during JWT decoding: {e}. Token: {token[:30]}...")
        return None

@router.get("/newcomer-status")
async def get_newcomer_status(current_user: DBUser = Depends(get_current_user)):
    """Проверить, является ли текущий пользователь новичком"""
    try:
        from user_priority import is_user_newcomer
        
        # Проверяем статус новичка
        is_newcomer = await is_user_newcomer(current_user)
        
        return {
            "is_newcomer": is_newcomer,
            "user_id": current_user.id,
            "created_at": current_user.created_at.isoformat() if hasattr(current_user.created_at, 'isoformat') and current_user.created_at is not None else None
        }
        
    except Exception as e:
        print(f"Error checking newcomer status: {e}")
        # В случае ошибки возвращаем False (не показываем модальное окно)
        return {
            "is_newcomer": False,
            "user_id": current_user.id,
            "error": str(e)
        }
