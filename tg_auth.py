import os
import sys
import asyncio
import argparse
import logging
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeInvalid, PhoneCodeExpired, PhoneNumberInvalid,
    SessionPasswordNeeded, PasswordHashInvalid, FloodWait,
    ChannelInvalid, ChannelsTooMuch, PeerFlood
)

from pythonjsonlogger import jsonlogger
from dotenv import load_dotenv

from sqlalchemy import select, update as sql_update
from sqlalchemy.orm import selectinload

from db import async_session
from models import User, TelegramSession
from s3_session_manager import S3SessionManager
from s3_avatar_manager import S3AvatarManager

load_dotenv()

# FastAPI app
app = FastAPI(title="Telegram Auth Service")

# Request/Response models
class SendCodeRequest(BaseModel):
    user_id: int

class SendCodeResponse(BaseModel):
    status: str
    message: str
    phone_number: Optional[str] = None

class SignInRequest(BaseModel):
    user_id: int
    code: str
    password: Optional[str] = None

class SignInResponse(BaseModel):
    status: str
    message: str
    session_saved: bool = False

class AuthStatusResponse(BaseModel):
    user_id: int
    status: str
    phone_number: Optional[str] = None
    session_exists: bool = False
    last_auth: Optional[datetime] = None

class TelegramAuth:
    """Handles Telegram authentication process."""
    
    def __init__(self, user_id: int, phone_number: Optional[str] = None):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are required")
        
        self.user_id = user_id
        self.logger = self._setup_logging(user_id)
        self.phone_number = phone_number  # Can be set directly for new users
        self.phone_code_hash = None
        self.code_sent_time = None
        
        # S3 managers
        self.s3_manager = S3SessionManager()
        self.s3_avatar_manager = S3AvatarManager()
        
        # Session setup
        self.session_dir = os.path.join(tempfile.gettempdir(), "telegram_auth_sessions")
        self.session_path = os.path.join(self.session_dir, f"{user_id}.session")
        os.makedirs(self.session_dir, exist_ok=True)
        
        self.client = Client(
            name=os.path.splitext(os.path.basename(self.session_path))[0],
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=self.session_dir
        )
    
    def _setup_logging(self, user_id: int):
        """Sets up structured JSON logging for the auth service."""
        auth_logger = logging.getLogger(f"auth_{user_id}")
        auth_logger.setLevel(logging.INFO)
        
        if auth_logger.handlers:
            auth_logger.handlers.clear()
        
        log_handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(user_id)s'
        )
        log_handler.setFormatter(formatter)
        auth_logger.addHandler(log_handler)
        
        adapter = logging.LoggerAdapter(auth_logger, {'user_id': user_id})
        adapter.info("Auth service logging initialized")
        return adapter

    def _client_state(self) -> dict:
        """Small helper to log current client/session state without leaking secrets."""
        try:
            is_connected = bool(getattr(self.client, "is_connected", False))
        except Exception:
            is_connected = None

        try:
            session_exists = os.path.exists(self.session_path)
            session_size = os.path.getsize(self.session_path) if session_exists else None
        except Exception:
            session_exists = None
            session_size = None

        return {
            "user_id": self.user_id,
            "phone_number_set": bool(self.phone_number),
            "phone_code_hash_set": bool(self.phone_code_hash),
            "code_sent_time_set": bool(self.code_sent_time),
            "client_is_connected": is_connected,
            "session_path": self.session_path,
            "session_exists": session_exists,
            "session_size": session_size,
        }
    
    async def _load_user_phone(self) -> Optional[str]:
        """Load user phone number from database."""
        async with async_session() as db_session:
            try:
                user = await db_session.get(User, self.user_id)
                if user and user.phone_number:
                    self.logger.info(f"Loaded phone number for user {self.user_id}")
                    return user.phone_number
                else:
                    self.logger.error(f"No phone number found for user {self.user_id}")
                    return None
            except Exception as e:
                self.logger.error(f"Failed to load user phone: {e}")
                return None
    
    async def send_code(self) -> dict:
        """Send authentication code to user's phone."""
        try:
            # Load phone number from database if not already provided
            if not self.phone_number:
                self.phone_number = await self._load_user_phone()
                if not self.phone_number:
                    return {
                        "status": "error",
                        "message": "Phone number not found in database"
                    }
            
            self.logger.info(f"Sending code to {self.phone_number}")
            
            # Always ensure client is disconnected before attempting to connect
            try:
                if hasattr(self.client, 'is_connected') and self.client.is_connected:
                    self.logger.info("Client already connected, disconnecting first")
                    await self.client.disconnect()
                    # Small delay to ensure clean disconnection
                    await asyncio.sleep(0.1)
            except Exception as disconnect_error:
                self.logger.warning(f"Error during disconnect attempt: {disconnect_error}")
                # Continue anyway, we'll try to connect fresh
            
            # Ensure we have a fresh connection
            try:
                await self.client.connect()
            except Exception as connect_error:
                self.logger.warning(f"Initial connect failed, trying stop then connect: {connect_error}")
                try:
                    await self.client.stop()
                    await asyncio.sleep(0.1)
                    await self.client.connect()
                except Exception as retry_error:
                    self.logger.error(f"Retry connect also failed: {retry_error}")
                    return {
                        "status": "error",
                        "message": f"Failed to connect to Telegram: {str(retry_error)}"
                    }
            
            sent_code = await self.client.send_code(self.phone_number)
            self.phone_code_hash = sent_code.phone_code_hash
            self.code_sent_time = datetime.now(timezone.utc)
            
            self.logger.info("Authentication code sent successfully")
            return {
                "status": "success",
                "message": "Authentication code sent",
                "phone_number": self.phone_number,
                "phone_code_hash": self.phone_code_hash,
                "code_sent_time": self.code_sent_time
            }
            
        except PhoneNumberInvalid:
            self.logger.error("Invalid phone number")
            return {
                "status": "error",
                "message": "Invalid phone number. Please check the number and try again."
            }
        except FloodWait as e:
            self.logger.warning(f"FloodWait: {e.value}s")
            return {
                "status": "error",
                "message": f"Too many requests. Wait {e.value} seconds before trying again."
            }
        except Exception as e:
            self.logger.error(f"Failed to send code: {e}")
            error_msg = str(e)
            # Provide more specific error messages
            if "ApiIdInvalid" in error_msg:
                return {
                    "status": "error",
                    "message": "Invalid Telegram API credentials. Please contact support."
                }
            elif "PhoneMigrate" in error_msg:
                return {
                    "status": "error",
                    "message": "Phone number belongs to a different data center. Please contact support."
                }
            elif "NetworkError" in error_msg:
                return {
                    "status": "error",
                    "message": "Network connection error. Please check your internet connection and try again."
                }
            elif "Client is already connected" in error_msg:
                # Try one more time with a completely fresh client
                try:
                    self.logger.info("Client already connected error, creating fresh client")
                    await self.client.stop()
                    await asyncio.sleep(0.2)
                    # Create a completely new client instance
                    self.client = Client(
                        name=os.path.splitext(os.path.basename(self.session_path))[0],
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        workdir=self.session_dir
                    )
                    await self.client.connect()
                    sent_code = await self.client.send_code(self.phone_number)
                    self.phone_code_hash = sent_code.phone_code_hash
                    self.code_sent_time = datetime.now(timezone.utc)
                    
                    self.logger.info("Authentication code sent successfully with fresh client")
                    return {
                        "status": "success",
                        "message": "Authentication code sent",
                        "phone_number": self.phone_number,
                        "phone_code_hash": self.phone_code_hash,
                        "code_sent_time": self.code_sent_time
                    }
                except Exception as retry_error:
                    self.logger.error(f"Retry with fresh client also failed: {retry_error}")
                    return {
                        "status": "error",
                        "message": f"Failed to send code: {str(retry_error)}. Please try again later."
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to send code: {error_msg}. Please try again later."
                }
    
    async def sign_in(self, code: str, password: Optional[str] = None) -> dict:
        """Sign in with the provided code and optional 2FA password."""
        try:
            if not self.phone_number or not self.phone_code_hash:
                return {
                    "status": "error",
                    "message": "Send code first"
                }

            self.logger.info("Attempting to sign in")
            self.logger.info(f"sign_in state(before connect/sign_in): {self._client_state()}")
            
            # Check if client is connected, if not connect it
            if not self.client.is_connected:
                self.logger.info("Client not connected, connecting first")
                await self.client.connect()
            else:
                self.logger.info("Client already connected, proceeding with sign in")
            
            # Try to sign in with code
            try:
                await self.client.sign_in(
                    phone_number=self.phone_number,
                    phone_code_hash=self.phone_code_hash,
                    phone_code=code
                )

                self.logger.info(f"sign_in succeeded, starting finalize. state: {self._client_state()}")

                # If successful, finalize auth
                try:
                    return await self._finalize_auth()
                except Exception as finalize_error:
                    finalize_error_msg = str(finalize_error)
                    if "Client is already terminated" in finalize_error_msg:
                        self.logger.warning("Client terminated during finalization, but sign in was successful")
                        # Try to finalize again with a fresh connection
                        try:
                            # Reconnect and try to get user info
                            if not self.client.is_connected:
                                await self.client.connect()
                            me = await self.client.get_me()
                            if me:
                                # Disconnect and try to save session
                                if self.client.is_connected:
                                    await self.client.stop()

                                # Try to save session to S3
                                session_saved = False
                                if os.path.exists(self.session_path):
                                    session_saved = self.s3_manager.upload_session(self.user_id, self.session_path)

                                # Update database
                                await self._update_session_in_db(me.id, me.username)

                                return {
                                    "status": "success",
                                    "message": "Authentication successful (recovered from client termination)",
                                    "session_saved": session_saved
                                }
                        except Exception as recovery_error:
                            self.logger.error(f"Recovery after client termination failed: {recovery_error}")
                            # Even if recovery fails, authentication was successful
                            return {
                                "status": "success",
                                "message": "Authentication successful (client termination during finalization)",
                                "session_saved": False
                            }
                    else:
                        # Re-raise other finalization errors
                        raise finalize_error
                
            except SessionPasswordNeeded:
                # 2FA is enabled
                if not password:
                    self.logger.info("2FA password required")
                    return {
                        "status": "password_required",
                        "message": "Two-factor authentication password required. Please provide your 2FA password."
                    }
                
                # Try with 2FA password
                try:
                    await self.client.check_password(password)
                    # If successful, finalize auth
                    try:
                        return await self._finalize_auth()
                    except Exception as finalize_error:
                        finalize_error_msg = str(finalize_error)
                        if "Client is already terminated" in finalize_error_msg:
                            self.logger.warning("Client terminated during finalization, but 2FA was successful")
                            # Try to finalize again with a fresh connection
                            try:
                                # Reconnect and try to get user info
                                if not self.client.is_connected:
                                    await self.client.connect()
                                me = await self.client.get_me()
                                if me:
                                    # Disconnect and try to save session
                                    if self.client.is_connected:
                                        await self.client.stop()

                                    # Try to save session to S3
                                    session_saved = False
                                    if os.path.exists(self.session_path):
                                        session_saved = self.s3_manager.upload_session(self.user_id, self.session_path)

                                    # Update database
                                    await self._update_session_in_db(me.id, me.username)

                                    return {
                                        "status": "success",
                                        "message": "Authentication successful (recovered from client termination)",
                                        "session_saved": session_saved
                                    }
                            except Exception as recovery_error:
                                self.logger.error(f"Recovery after client termination failed: {recovery_error}")
                                # Even if recovery fails, authentication was successful
                                return {
                                    "status": "success",
                                    "message": "Authentication successful (client termination during finalization)",
                                    "session_saved": False
                                }
                        else:
                            # Re-raise other finalization errors
                            raise finalize_error
                except PasswordHashInvalid:
                    self.logger.error("Invalid 2FA password")
                    return {
                        "status": "error",
                        "message": "Invalid two-factor authentication password. Please check your password and try again."
                    }
                
        except PhoneCodeInvalid:
            self.logger.error("Invalid phone code")
            return {
                "status": "error",
                "message": "Invalid authentication code. Please check the code and try again."
            }
        except PhoneCodeExpired:
            self.logger.error("Phone code expired")
            return {
                "status": "error",
                "message": "Authentication code expired. Please request a new code."
            }
        except PasswordHashInvalid:
            self.logger.error("Invalid 2FA password")
            return {
                "status": "error",
                "message": "Invalid two-factor authentication password. Please check your password and try again."
            }
        except Exception as e:
            self.logger.error(f"Sign in failed: {e}")
            error_msg = str(e)
            # Provide more specific error messages
            if "AuthKeyUnregistered" in error_msg:
                return {
                    "status": "error",
                    "message": "Session expired or revoked. Please re-authenticate your Telegram account."
                }
            elif "SessionRevoked" in error_msg:
                return {
                    "status": "error",
                    "message": "Session has been revoked. Please re-authenticate your Telegram account."
                }
            elif "UserDeactivated" in error_msg:
                return {
                    "status": "error",
                    "message": "Telegram account has been deactivated. Please check your account status."
                }
            elif "PhoneNumberUnoccupied" in error_msg:
                return {
                    "status": "error",
                    "message": "Phone number is not registered with Telegram. Please check the number."
                }
            elif "FloodWait" in error_msg:
                import re
                wait_time_match = re.search(r"(\d+)", error_msg)
                wait_time = wait_time_match.group(1) if wait_time_match else "a few"
                return {
                    "status": "error",
                    "message": f"Too many requests. Please wait {wait_time} seconds before trying again."
                }
            elif "NetworkError" in error_msg:
                return {
                    "status": "error",
                    "message": "Network connection error. Please check your internet connection and try again."
                }
            elif "Client is already connected" in error_msg:
                # Try one more time with a fresh connection
                try:
                    self.logger.info("Client already connected error during sign in, reconnecting")
                    await self.client.stop()
                    await asyncio.sleep(0.2)
                    await self.client.connect()
                    
                    # Retry sign in
                    await self.client.sign_in(
                        phone_number=self.phone_number,
                        phone_code_hash=self.phone_code_hash,
                        phone_code=code
                    )

                    # If successful, finalize auth
                    try:
                        return await self._finalize_auth()
                    except Exception as finalize_error:
                        finalize_error_msg = str(finalize_error)
                        if "Client is already terminated" in finalize_error_msg:
                            self.logger.warning("Client terminated during finalization after reconnect")
                            return {
                                "status": "success",
                                "message": "Authentication successful (client termination during finalization)",
                                "session_saved": False
                            }
                        else:
                            raise finalize_error
                except SessionPasswordNeeded:
                    # 2FA is enabled
                    if not password:
                        self.logger.info("2FA password required after reconnect")
                        return {
                            "status": "password_required",
                            "message": "Two-factor authentication password required. Please provide your 2FA password."
                        }
                    
                    # Try with 2FA password
                    try:
                        await self.client.check_password(password)
                        try:
                            return await self._finalize_auth()
                        except Exception as finalize_error:
                            finalize_error_msg = str(finalize_error)
                            if "Client is already terminated" in finalize_error_msg:
                                self.logger.warning("Client terminated during finalization after 2FA reconnect")
                                return {
                                    "status": "success",
                                    "message": "Authentication successful (client termination during finalization)",
                                    "session_saved": False
                                }
                            else:
                                raise finalize_error
                    except PasswordHashInvalid:
                        self.logger.error("Invalid 2FA password after reconnect")
                        return {
                            "status": "error",
                            "message": "Invalid two-factor authentication password. Please check your password and try again."
                        }
                except Exception as retry_error:
                    self.logger.error(f"Retry sign in also failed: {retry_error}")
                    return {
                        "status": "error",
                        "message": f"Sign in failed: {str(retry_error)}. Please try again."
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Sign in failed: {error_msg}. Please try again."
                }
    
    async def _finalize_auth(self) -> dict:
        """Finalize authentication by saving session and updating database."""
        try:
            self.logger.info(f"finalize_auth enter. state: {self._client_state()}")
            # Get user info
            self.logger.debug(f"finalize_auth step=get_me (before). state: {self._client_state()}")
            me = await self.client.get_me()
            if not me:
                raise Exception("Failed to get user info")

            self.logger.debug(f"finalize_auth step=get_me (after) telegram_id={getattr(me, 'id', None)} username={getattr(me, 'username', None)}")
            
            self.logger.info(f"Successfully authenticated as {me.username} (ID: {me.id})")
            
            # Download and save user avatar
            self.logger.debug(f"finalize_auth step=avatar_download (before). state: {self._client_state()}")
            avatar_saved = await self._download_and_save_avatar(me)
            self.logger.debug(f"finalize_auth step=avatar_download (after) avatar_saved={avatar_saved}. state: {self._client_state()}")
            
            # Disconnect to save session
            if self.client.is_connected:
                self.logger.debug(f"finalize_auth step=client_stop (before). state: {self._client_state()}")
                try:
                    await self.client.stop()
                except Exception as stop_error:
                    # Pyrogram may raise ConnectionError("Client is already terminated") here.
                    # This happens after successful auth/IO; treat as non-fatal and continue finalization.
                    if "Client is already terminated" in str(stop_error):
                        self.logger.warning(
                            f"finalize_auth client already terminated during stop(); continuing. error={stop_error}"
                        )
                    else:
                        raise
                self.logger.debug(f"finalize_auth step=client_stop (after). state: {self._client_state()}")
            
            # Upload session to S3
            session_saved = False
            if os.path.exists(self.session_path):
                self.logger.debug(f"finalize_auth step=s3_upload (before). state: {self._client_state()}")
                session_saved = self.s3_manager.upload_session(self.user_id, self.session_path)
                if session_saved:
                    self.logger.info("Session uploaded to S3")
                else:
                    self.logger.error("Failed to upload session to S3")
                self.logger.debug(f"finalize_auth step=s3_upload (after) session_saved={session_saved}. state: {self._client_state()}")
            else:
                self.logger.warning(f"finalize_auth session_path missing, cannot upload. state: {self._client_state()}")
            
            # Update database
            self.logger.debug(f"finalize_auth step=db_update (before). state: {self._client_state()}")
            await self._update_session_in_db(me.id, me.username)
            self.logger.debug(f"finalize_auth step=db_update (after). state: {self._client_state()}")
            
            return {
                "status": "success",
                "message": "Authentication successful",
                "session_saved": session_saved,
                "avatar_saved": avatar_saved
            }

        except Exception as e:
            # Make sure to disconnect even if there's an error
            try:
                if self.client.is_connected:
                    await self.client.stop()
            except:
                pass
            # Keep full traceback in logs to pinpoint the exact failing step.
            self.logger.exception(f"Failed to finalize auth: {e}. state: {self._client_state()}")
            return {
                "status": "error",
                "message": f"Failed to finalize authentication: {str(e)}"
            }
    
    async def _download_and_save_avatar(self, me) -> bool:
        """Download and save user avatar to S3."""
        try:
            # Check if user has profile photos
            photos = []
            async for photo in self.client.get_chat_photos("me", limit=1):
                photos.append(photo)
            
            if not photos:
                self.logger.info("No profile photos found")
                return False
            
            # Download the first (current) profile photo
            avatar_dir = os.path.join(tempfile.gettempdir(), "telegram_avatars")
            os.makedirs(avatar_dir, exist_ok=True)
            
            avatar_path = os.path.join(avatar_dir, f"{self.user_id}.jpg")
            
            # Download photo
            await self.client.download_media(photos[0], file_name=avatar_path)
            
            if os.path.exists(avatar_path):
                # Upload to S3
                avatar_saved = self.s3_avatar_manager.upload_avatar(self.user_id, avatar_path)
                
                # Clean up local file
                try:
                    os.remove(avatar_path)
                except:
                    pass
                
                if avatar_saved:
                    self.logger.info("Avatar uploaded to S3")
                    return True
                else:
                    self.logger.error("Failed to upload avatar to S3")
                    return False
            else:
                self.logger.error("Failed to download avatar")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to download and save avatar: {e}")
            return False
    
    async def _update_session_in_db(self, telegram_id: int, username: Optional[str]):
        """Update session information in database."""
        async with async_session() as db_session:
            try:
                # Update or create telegram session record
                session_name = os.path.basename(self.session_path)
                
                stmt = select(TelegramSession).where(
                    TelegramSession.user_id == self.user_id
                )
                result = await db_session.execute(stmt)
                existing_session = result.scalar_one_or_none()
                
                if existing_session:
                    existing_session.session_path = session_name
                    existing_session.telegram_id = telegram_id
                    existing_session.username = username
                    existing_session.session_last_used = datetime.now(timezone.utc)
                    existing_session.is_active = True
                else:
                    new_session = TelegramSession(
                        user_id=self.user_id,
                        session_path=session_name,
                        telegram_id=telegram_id,
                        username=username,
                        session_last_used=datetime.now(timezone.utc),
                        is_active=True
                    )
                    db_session.add(new_session)
                
                await db_session.commit()
                self.logger.info("Session updated in database")
                
            except Exception as e:
                self.logger.error(f"Failed to update session in DB: {e}")
                await db_session.rollback()
    
    async def get_me(self):
        """Get current user information."""
        try:
            if not self.client.is_connected:
                await self.client.start()
            
            me = await self.client.get_me()
            return me
            
        except Exception as e:
            self.logger.error(f"Failed to get user info: {e}")
            raise e
    
    async def save_session_to_s3(self) -> bool:
        """Save current session to S3."""
        try:
            if not os.path.exists(self.session_path):
                self.logger.error(f"Session file not found: {self.session_path}")
                return False
            
            # Upload session to S3
            session_saved = self.s3_manager.upload_session(self.user_id, self.session_path)
            if session_saved:
                self.logger.info(f"Session successfully uploaded to S3 for user {self.user_id}")
                return True
            else:
                self.logger.error(f"Failed to upload session to S3 for user {self.user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving session to S3: {e}")
            return False

    def _validate_channel_params(self, title: str, description: Optional[str] = None) -> Optional[str]:
        """Валидация параметров канала перед созданием."""
        if not title or len(title.strip()) < 1:
            return "Название канала не может быть пустым"
        
        if len(title) > 255:
            return "Название канала слишком длинное (максимум 255 символов)"
        
        # Проверяем на недопустимые символы
        forbidden_chars = ['@', '#', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in title for char in forbidden_chars):
            return f"Название канала не может содержать символы: {', '.join(forbidden_chars)}"
        
        if description and len(description) > 255:
            return "Описание канала слишком длинное (максимум 255 символов)"
        
        return None

    async def create_channel_with_error_handling(self, title: str, description: Optional[str] = None, is_megagroup: bool = False) -> dict:
        """Создать канал с расширенной обработкой ошибок."""
        try:
            # Валидация входных данных
            validation_error = self._validate_channel_params(title, description)
            if validation_error:
                return {
                    "status": "error",
                    "channel_id": None,
                    "channel_username": None,
                    "invite_link": None,
                    "title": None,
                    "message": validation_error
                }
            
            # Вызываем основной метод создания
            return await self.create_channel(title, description, is_megagroup)
            
        except Exception as e:
            # Основной метод уже обрабатывает все ошибки, просто передаем результат
            return await self.create_channel(title, description, is_megagroup)

    async def create_channel(self, title: str, description: Optional[str] = None, is_megagroup: bool = False) -> dict:
        """Создать новый канал или супергруппу в Telegram."""
        try:
            self.logger.info(f"Creating {'supergroup' if is_megagroup else 'channel'}: {title}")
            
            # Проверяем, что клиент подключен
            if not self.client.is_connected:
                # Загружаем сессию из S3 если нужно
                if self.s3_manager.session_exists(self.user_id):
                    self.s3_manager.download_session(self.user_id, self.session_path)
                    await self.client.start()
                else:
                    raise Exception("No active session found. Please authenticate first.")
            
            # Создаем канал или супергруппу
            if is_megagroup:
                self.logger.info(f"Creating supergroup: {title}")
                result = await self.client.create_supergroup(
                    title=title,
                    description=description or ""
                )
            else:
                self.logger.info(f"Creating channel: {title}")
                result = await self.client.create_channel(
                    title=title,
                    description=description or ""
                )
            
            # Получаем информацию о созданном канале
            chat = await self.client.get_chat(result.id)
            
            self.logger.info(f"Successfully created {'supergroup' if is_megagroup else 'channel'}: {chat.title} (ID: {chat.id})")
            
            return {
                "status": "success",
                "channel_id": chat.id,
                "channel_username": chat.username,
                "invite_link": chat.invite_link,
                "title": chat.title,
                "message": f"{'Супергруппа' if is_megagroup else 'Канал'} '{chat.title}' успешно создан"
            }
            
        except FloodWait as e:
            self.logger.warning(f"FloodWait error: {e.value}s")
            return {
                "status": "error",
                "channel_id": None,
                "channel_username": None,
                "invite_link": None,
                "title": None,
                "message": f"Превышен лимит запросов. Попробуйте снова через {e.value} секунд"
            }
        except ChannelsTooMuch:
            self.logger.error("Daily channel creation limit reached")
            return {
                "status": "error",
                "channel_id": None,
                "channel_username": None,
                "invite_link": None,
                "title": None,
                "message": "Достигнут дневной лимит создания каналов. Попробуйте завтра"
            }
        except ChannelInvalid:
            self.logger.error("Invalid channel parameters")
            return {
                "status": "error",
                "channel_id": None,
                "channel_username": None,
                "invite_link": None,
                "title": None,
                "message": "Неверные параметры канала"
            }
        except PeerFlood:
            self.logger.error("Peer flood error")
            return {
                "status": "error",
                "channel_id": None,
                "channel_username": None,
                "invite_link": None,
                "title": None,
                "message": "Слишком много операций. Подождите некоторое время"
            }
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to create {'supergroup' if is_megagroup else 'channel'}: {error_msg}")
            
            # Дополнительная обработка специфичных ошибок по тексту
            if "CHANNELS_TOO_MUCH" in error_msg:
                return {
                    "status": "error",
                    "channel_id": None,
                    "channel_username": None,
                    "invite_link": None,
                    "title": None,
                    "message": "Достигнут дневной лимит создания каналов"
                }
            elif "CHANNEL_INVALID" in error_msg:
                return {
                    "status": "error",
                    "channel_id": None,
                    "channel_username": None,
                    "invite_link": None,
                    "title": None,
                    "message": "Неверные параметры канала"
                }
            elif "SESSION_PASSWORD_NEEDED" in error_msg:
                return {
                    "status": "error",
                    "channel_id": None,
                    "channel_username": None,
                    "invite_link": None,
                    "title": None,
                    "message": "Требуется повторная авторизация"
                }
            else:
                return {
                    "status": "error",
                    "channel_id": None,
                    "channel_username": None,
                    "invite_link": None,
                    "title": None,
                    "message": f"Не удалось создать {'супергруппу' if is_megagroup else 'канал'}: {error_msg}"
                }

    async def disconnect_client(self):
        """Safely disconnect the Telegram client."""
        try:
            if hasattr(self.client, 'is_connected') and self.client.is_connected:
                await self.client.disconnect()
                self.logger.info("Client disconnected successfully")
                return True
            else:
                self.logger.info("Client was not connected")
                return True
        except Exception as e:
            self.logger.error(f"Error disconnecting client: {e}")
            # Try to force disconnect with stop method
            try:
                if hasattr(self.client, 'stop'):
                    await self.client.stop()
                    self.logger.info("Client stopped successfully")
                    return True
            except Exception as stop_error:
                self.logger.error(f"Error stopping client: {stop_error}")
            return False

    async def cleanup(self):
        """Clean up resources."""
        try:
            await self.disconnect_client()
            
            # Clean up local session file
            if os.path.exists(self.session_path):
                os.remove(self.session_path)
                self.logger.info("Local session file cleaned up")
                
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

# Global auth instance
auth_instance: Optional[TelegramAuth] = None

# API Endpoints
@app.post("/send_code", response_model=SendCodeResponse)
async def send_code(request: SendCodeRequest):
    """Send authentication code to user's phone."""
    global auth_instance
    
    try:
        auth_instance = TelegramAuth(request.user_id)
        result = await auth_instance.send_code()
        
        return SendCodeResponse(
            status=result["status"],
            message=result["message"],
            phone_number=result.get("phone_number")
        )
        
    except Exception as e:
        logging.error(f"Send code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sign_in", response_model=SignInResponse)
async def sign_in(request: SignInRequest):
    """Sign in with authentication code and optional 2FA password."""
    global auth_instance
    
    if not auth_instance or auth_instance.user_id != request.user_id:
        raise HTTPException(status_code=400, detail="Send code first")
    
    try:
        result = await auth_instance.sign_in(request.code, request.password)
        
        return SignInResponse(
            status=result["status"],
            message=result["message"],
            session_saved=result.get("session_saved", False)
        )
        
    except Exception as e:
        logging.error(f"Sign in error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{user_id}", response_model=AuthStatusResponse)
async def get_auth_status(user_id: int):
    """Get authentication status for user."""
    try:
        async with async_session() as db_session:
            # Get user info
            user = await db_session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check session
            stmt = select(TelegramSession).where(
                TelegramSession.user_id == user_id
            )
            result = await db_session.execute(stmt)
            session = result.scalar_one_or_none()
            
            # Check S3 session
            s3_manager = S3SessionManager()
            session_exists = s3_manager.session_exists(user_id)
            
            return AuthStatusResponse(
                user_id=user_id,
                status="authenticated" if session_exists else "not_authenticated",
                phone_number=user.phone_number,
                session_exists=session_exists,
                last_auth=session.session_last_used if session else None
            )
            
    except Exception as e:
        logging.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/_health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "telegram_auth"}

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on service shutdown."""
    global auth_instance
    if auth_instance:
        await auth_instance.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Auth Service")
    parser.add_argument("--port", type=int, default=9000, help="Port for auth service")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run FastAPI
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")
