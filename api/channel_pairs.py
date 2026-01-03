from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select # Added import
from sqlalchemy.ext.asyncio import AsyncSession # Changed from Session
from sqlalchemy.orm import joinedload 

from auth import get_current_user # Changed from get_current_active_user
from db import get_db # This now returns AsyncSession
from models import ChannelPair as DBChannelPair, Model as DBModel, User as DBUser
from pydantic import BaseModel, validator, Field
import asyncio
import os
from pyrogram import Client
from pyrogram.types import Chat
from s3_session_manager import S3SessionManager

router = APIRouter()

# Admin status validation function removed - no longer needed as 
# target_channel list now contains only admin channels

# Pydantic schemas
class ModelResponse(BaseModel):
    id: int
    model: str
    model_visible_name: Optional[str] = None
    api_price: Optional[float] = None
    visible: Optional[int] = None
    system_content: Optional[str] = None
    user_content: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    price_per_post: Optional[float] = None

    class Config:
        from_attributes = True

class ModelBase(BaseModel): # This can be kept if used elsewhere, or removed if only ModelResponse is needed for /models/
    id: int
    model: str

    class Config:
        from_attributes = True

class ChannelPairBase(BaseModel):
    source_channel: str  # Changed from int to str
    target_channel: str  # Changed from int to str
    text_to_delete: Optional[str] = None
    model_id: Optional[int] = None
    system_content: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    hour_min: Optional[int] = None
    hour_max: Optional[int] = None
    caption_text: Optional[str] = None
    caption_url: Optional[str] = None

class ChannelPairCreate(ChannelPairBase):
    pass

class ChannelPairUpdate(ChannelPairBase):
    pass

class ChannelPairResponse(ChannelPairBase):
    id: int
    user_id: int
    model_name: Optional[str] = None # Для отображения имени модели

    class Config:
        from_attributes = True # Changed from orm_mode

class ChannelInfo(BaseModel):
    id: int
    title: str
    username: Optional[str] = None
    photo_url: Optional[str] = None
    type: str
    is_admin: bool = False

class ChannelsResponse(BaseModel):
    subscribed_channels: List[ChannelInfo]
    admin_channels: List[ChannelInfo]
    session_valid: bool = True
    user_info: Optional[dict] = None
    session_status: str = "active"  # active, expired, revoked, invalid

class CreateChannelRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Название канала")
    description: Optional[str] = Field(None, max_length=255, description="Описание канала")
    is_megagroup: bool = Field(False, description="False = канал, True = супергруппа")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Название канала не может быть пустым')
        
        # Проверяем на недопустимые символы
        forbidden_chars = ['@', '#', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in v for char in forbidden_chars):
            raise ValueError(f'Название канала не может содержать символы: {", ".join(forbidden_chars)}')
        
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Мой новый канал",
                "description": "Описание канала",
                "is_megagroup": False
            }
        }

class ChannelCreationResponse(BaseModel):
    status: str
    channel_id: Optional[int] = None
    channel_username: Optional[str] = None
    invite_link: Optional[str] = None
    title: Optional[str] = None
    message: str

from sqlalchemy import desc
...
@router.get("/models", response_model=List[ModelResponse]) # MODIFIED: Removed trailing slash
async def get_models(db: AsyncSession = Depends(get_db), current_user: DBUser = Depends(get_current_user)):
    stmt = select(DBModel).where(DBModel.model.isnot(None)).order_by(desc(DBModel.api_price).nulls_last())
    result = await db.execute(stmt)
    models = result.scalars().all()
    return models

@router.post("", response_model=ChannelPairResponse) # MODIFIED: Removed /channel_pairs/ and trailing slash, path is now relative to prefix
async def create_channel_pair(
    channel_pair: ChannelPairCreate,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    # Admin status validation removed - target_channel list now contains only admin channels
    db_channel_pair = DBChannelPair(
        **channel_pair.dict(),
        user_id=current_user.id
    )
    db.add(db_channel_pair)
    await db.commit()
    await db.refresh(db_channel_pair)
    
    model_name = None
    if db_channel_pair.model_id:
        result = await db.execute(select(DBModel.model).where(DBModel.id == db_channel_pair.model_id))
        model_name = result.scalar_one_or_none()
            
    return ChannelPairResponse(**db_channel_pair.__dict__, model_name=model_name)

@router.get("/session-info")
async def get_session_info(
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get Telegram session info and user details without loading channels."""
    try:
        print(f"[SESSION_INFO] Checking session for user {current_user.id}")
        
        # Initialize Telegram client
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            return {"session_valid": False, "session_status": "api_not_configured"}
        
        # Get session from S3
        session_manager = S3SessionManager()
        session_data = await session_manager.get_session(current_user.id)
        
        if not session_data:
            return {"session_valid": False, "session_status": "no_session"}
        
        temp_session_path = f"temp_session_info_{current_user.id}.session"
        
        try:
            with open(temp_session_path, 'wb') as f:
                f.write(session_data)
            
            client = Client(
                temp_session_path.replace('.session', ''),
                api_id=int(api_id),
                api_hash=api_hash,
                workdir="."
            )
            
            await client.start()
            
            try:
                me = await client.get_me()
                
                # Get additional stats
                dialogs_count = 0
                channels_count = 0
                groups_count = 0
                
                async for dialog in client.get_dialogs(limit=100):  # Limit for performance
                    dialogs_count += 1
                    from pyrogram.enums import ChatType
                    if dialog.chat.type == ChatType.CHANNEL:
                        channels_count += 1
                    elif dialog.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                        groups_count += 1
                
                user_info = {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "phone_number": me.phone_number,
                    "is_premium": getattr(me, 'is_premium', False),
                    "is_verified": getattr(me, 'is_verified', False),
                    "stats": {
                        "total_dialogs": dialogs_count,
                        "channels": channels_count,
                        "groups": groups_count
                    }
                }
                
                await client.stop()
                
                return {
                    "session_valid": True,
                    "session_status": "active",
                    "user_info": user_info
                }
                
            except Exception as e:
                await client.stop()
                error_str = str(e).lower()
                if "unauthorized" in error_str or "auth" in error_str:
                    status = "expired"
                elif "revoked" in error_str:
                    status = "revoked"
                else:
                    status = "invalid"
                
                return {
                    "session_valid": False,
                    "session_status": status,
                    "error": str(e)
                }
                
        finally:
            try:
                if os.path.exists(temp_session_path):
                    os.remove(temp_session_path)
            except:
                pass
                
    except Exception as e:
        print(f"[SESSION_INFO] Error: {e}")
        return {
            "session_valid": False,
            "session_status": "error",
            "error": str(e)
        }


@router.get("/session-exists")
async def get_session_exists(
    current_user: DBUser = Depends(get_current_user)
):
    """Fast check: does the user's Telegram .session file exist in storage (S3/local)?"""
    try:
        session_manager = S3SessionManager()
        exists = session_manager.session_exists(current_user.id)
        return {"session_exists": bool(exists)}
    except Exception as e:
        print(f"[SESSION_EXISTS] Error for user {current_user.id}: {e}")
        return {"session_exists": False}

@router.get("/channels", response_model=ChannelsResponse)
async def get_user_channels(
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get user's subscribed channels and admin channels."""
    try:
        print(f"[CHANNELS] Getting channels for user {current_user.id} ({current_user.phone_number})")
        
        # Initialize Telegram client
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            print("[CHANNELS] ERROR: Telegram API credentials not configured")
            raise HTTPException(status_code=500, detail="Telegram API credentials not configured")
        
        print(f"[CHANNELS] Using API ID: {api_id}")
        
        # Get session from S3
        session_manager = S3SessionManager()
        print(f"[CHANNELS] Checking session for user {current_user.id}")
        session_data = await session_manager.get_session(current_user.id)
        
        if not session_data:
            print(f"[CHANNELS] ERROR: No session found for user {current_user.id}")
            raise HTTPException(status_code=422, detail="No Telegram session found. Please authenticate first.")
        
        print(f"[CHANNELS] Session found, length: {len(session_data)} bytes")
        
        # For Pyrogram, we need to save session data to a temporary file
        # since session_data is binary, not a session string
        temp_session_path = f"temp_session_{current_user.id}.session"
        
        try:
            # Write session data to temporary file
            with open(temp_session_path, 'wb') as f:
                f.write(session_data)
            print(f"[CHANNELS] Session written to temporary file: {temp_session_path}")
            
            # Initialize Pyrogram client with session file
            client = Client(
                temp_session_path.replace('.session', ''),  # name without .session extension
                api_id=int(api_id),
                api_hash=api_hash,
                workdir="."
            )
            
            print("[CHANNELS] Starting Pyrogram client...")
            await client.start()
            print("[CHANNELS] Pyrogram client started successfully")
            
            # Validate session and get user info
            session_valid = True
            user_info = None
            session_status = "active"
            
            try:
                # Get current user info to validate session
                me = await client.get_me()
                print(f"[CHANNELS] Session validated for user: @{me.username} ({me.first_name} {me.last_name})")
                
                user_info = {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "phone_number": me.phone_number,
                    "is_premium": getattr(me, 'is_premium', False),
                    "is_verified": getattr(me, 'is_verified', False)
                }
                
                # Update user info in database if needed
                if me.username and me.username != current_user.telegram_user_name:
                    current_user.telegram_user_name = me.username
                    db.add(current_user)
                    await db.commit()
                    print(f"[CHANNELS] Updated username in DB: {me.username}")
                
            except Exception as e:
                print(f"[CHANNELS] Session validation failed: {e}")
                session_valid = False
                session_status = "invalid"
                
                # Check specific error types
                error_str = str(e).lower()
                if "unauthorized" in error_str or "auth" in error_str:
                    session_status = "expired"
                elif "revoked" in error_str:
                    session_status = "revoked"
            
            subscribed_channels = []
            admin_channels = []
            
            # Only load channels if session is valid
            if session_valid:
                # Get all dialogs (chats)
                print("[CHANNELS] Getting dialogs...")
                dialog_count = 0
                async for dialog in client.get_dialogs():
                    dialog_count += 1
                    chat = dialog.chat
                    
                    # Only process channels and supergroups
                    from pyrogram.enums import ChatType
                    if chat.type in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
                        print(f"[CHANNELS] Processing {chat.type}: {chat.title} (ID: {chat.id})")
                        
                        # Get chat member info to check admin status (testing performance impact)
                        try:
                            member = await client.get_chat_member(chat.id, "me")
                            from pyrogram.enums import ChatMemberStatus
                            is_admin = member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
                            print(f"[CHANNELS] Admin status for {chat.title}: {is_admin} ({member.status})")
                        except Exception as e:
                            print(f"[CHANNELS] Could not get member status for {chat.title}: {e}")
                            is_admin = False
                        
                        # Photo download disabled for faster channel loading
                        photo_url = None
                        
                        channel_info = ChannelInfo(
                            id=chat.id,
                            title=chat.title or "",
                            username=chat.username,
                            photo_url=photo_url,
                            type=chat.type,
                            is_admin=is_admin  # Now checking real admin status
                        )
                        
                        subscribed_channels.append(channel_info)
                        if is_admin:
                            admin_channels.append(channel_info)
                
                print(f"[CHANNELS] Processed {dialog_count} dialogs, found {len(subscribed_channels)} channels, {len(admin_channels)} admin channels")
            else:
                print(f"[CHANNELS] Session invalid ({session_status}), skipping channel loading")
            
            await client.stop()
            print("[CHANNELS] Pyrogram client stopped")
            
            return ChannelsResponse(
                subscribed_channels=subscribed_channels,
                admin_channels=admin_channels,
                session_valid=session_valid,
                user_info=user_info,
                session_status=session_status
            )
            
        finally:
            # Clean up temporary session file
            try:
                if os.path.exists(temp_session_path):
                    os.remove(temp_session_path)
                    print(f"[CHANNELS] Cleaned up temporary session file: {temp_session_path}")
            except Exception as e:
                print(f"[CHANNELS] Warning: Could not clean up temporary file {temp_session_path}: {e}")
                
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"[CHANNELS] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")

@router.get("", response_model=List[ChannelPairResponse]) # MODIFIED: Removed /channel_pairs/ and trailing slash, path is now relative to prefix
async def get_channel_pairs(
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    # Используем joinedload для загрузки связанной модели Model
    # и получаем имя модели через model_relation.model
    stmt = (
        select(DBChannelPair)
        .options(joinedload(DBChannelPair.model).load_only(DBModel.model))  # Changed model_relation to model
        .where(DBChannelPair.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    db_channel_pairs = result.scalars().all()
    
    response_list = []
    for cp in db_channel_pairs:
        model_name = cp.model.model if cp.model else None # Changed model_relation to model
        response_list.append(ChannelPairResponse(**cp.__dict__, model_name=model_name))
        
    return response_list

@router.get("/{channel_pair_id}", response_model=ChannelPairResponse)
async def get_channel_pair(
    channel_pair_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    stmt = (
        select(DBChannelPair)
        .options(joinedload(DBChannelPair.model).load_only(DBModel.model)) # Changed model_relation to model
        .where(
            DBChannelPair.id == channel_pair_id,
            DBChannelPair.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_channel_pair = result.scalars().first()
    if db_channel_pair is None:
        raise HTTPException(status_code=404, detail="Channel pair not found")
    model_name = db_channel_pair.model_relation.model if db_channel_pair.model_relation else None
    return ChannelPairResponse(**db_channel_pair.__dict__, model_name=model_name)

@router.put("/{channel_pair_id}", response_model=ChannelPairResponse)
async def update_channel_pair(
    channel_pair_id: int,
    channel_pair: ChannelPairUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    stmt = (
        select(DBChannelPair)
        .where(
            DBChannelPair.id == channel_pair_id,
            DBChannelPair.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_channel_pair = result.scalars().first()
    if db_channel_pair is None:
        raise HTTPException(status_code=404, detail="Channel pair not found")
    
    # Admin status validation removed - target_channel list now contains only admin channels
    update_data = channel_pair.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_channel_pair, key, value)
    
    await db.commit()
    await db.refresh(db_channel_pair)
    
    model_name = None
    if db_channel_pair.model_id:
        result = await db.execute(select(DBModel.model).where(DBModel.id == db_channel_pair.model_id))
        model_name = result.scalar_one_or_none()
            
    return ChannelPairResponse(**db_channel_pair.__dict__, model_name=model_name)

@router.delete("/{channel_pair_id}", status_code=204)
async def delete_channel_pair(
    channel_pair_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    stmt = (
        select(DBChannelPair)
        .where(
            DBChannelPair.id == channel_pair_id,
            DBChannelPair.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_channel_pair = result.scalars().first()
    if db_channel_pair is None:
        raise HTTPException(status_code=404, detail="Channel pair not found")
    
    # Сначала удаляем связанные записи из channel_processing_state
    from models import ChannelProcessingState
    processing_states_stmt = select(ChannelProcessingState).where(
        ChannelProcessingState.channel_pair_id == channel_pair_id
    )
    processing_states_result = await db.execute(processing_states_stmt)
    processing_states = processing_states_result.scalars().all()
    
    for state in processing_states:
        await db.delete(state)
    
    # Также удаляем связанные scheduled_posts
    from models import ScheduledPost
    scheduled_posts_stmt = select(ScheduledPost).where(
        ScheduledPost.channel_pair_id == channel_pair_id
    )
    scheduled_posts_result = await db.execute(scheduled_posts_stmt)
    scheduled_posts = scheduled_posts_result.scalars().all()
    
    for post in scheduled_posts:
        await db.delete(post)
    
    # Теперь удаляем сам channel_pair
    await db.delete(db_channel_pair)
    await db.commit()
    
    return {"ok": True}

@router.post("/create-channel", response_model=ChannelCreationResponse)
async def create_telegram_channel(
    request: CreateChannelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Создать новый канал в Telegram"""
    try:
        print(f"[CREATE_CHANNEL] User {current_user.id} creating channel: {request.title}")
        
        # Проверяем, что у пользователя есть активная сессия
        session_manager = S3SessionManager()
        if not session_manager.session_exists(current_user.id):
            print(f"[CREATE_CHANNEL] No session found for user {current_user.id}")
            raise HTTPException(
                status_code=422, 
                detail="No Telegram session found. Please authenticate first."
            )
        
        print(f"[CREATE_CHANNEL] Session found for user {current_user.id}")
        
        # Импортируем TelegramAuth для создания канала
        from tg_auth import TelegramAuth
        
        # Создаем экземпляр TelegramAuth
        auth = TelegramAuth(user_id=current_user.id)
        
        # Создаем канал с расширенной обработкой ошибок
        result = await auth.create_channel_with_error_handling(
            title=request.title,
            description=request.description,
            is_megagroup=request.is_megagroup
        )
        
        print(f"[CREATE_CHANNEL] Result: {result['status']}")
        
        # Очищаем ресурсы
        await auth.cleanup()
        
        if result["status"] == "success":
            print(f"[CREATE_CHANNEL] Successfully created channel {result['channel_id']}")
            return ChannelCreationResponse(**result)
        else:
            print(f"[CREATE_CHANNEL] Failed to create channel: {result['message']}")
            # Возвращаем ошибку как успешный ответ с информацией об ошибке
            return ChannelCreationResponse(**result)
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[CREATE_CHANNEL] ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return ChannelCreationResponse(
            status="error",
            channel_id=None,
            channel_username=None,
            invite_link=None,
            title=None,
            message=f"Внутренняя ошибка сервера: {error_msg}"
        )

# Batch channel creation models
class BatchChannelRequest(BaseModel):
    channels: List[CreateChannelRequest]

class BatchChannelResponse(BaseModel):
    results: List[ChannelCreationResponse]
    success_count: int
    error_count: int

@router.post("/create-channels-batch", response_model=BatchChannelResponse)
async def create_telegram_channels_batch(
    request: BatchChannelRequest,
    current_user: DBUser = Depends(get_current_user)
):
    """Создать несколько каналов в Telegram в рамках одной сессии"""
    results = []
    success_count = 0
    error_count = 0
    
    if not request.channels:
        return BatchChannelResponse(
            results=[],
            success_count=0,
            error_count=0
        )
    
    try:
        print(f"[CREATE_CHANNELS_BATCH] User {current_user.id} creating {len(request.channels)} channels")
        
        # Проверяем, что у пользователя есть активная сессия
        session_manager = S3SessionManager()
        if not session_manager.session_exists(current_user.id):
            print(f"[CREATE_CHANNELS_BATCH] No session found for user {current_user.id}")
            # Возвращаем ошибку для всех каналов
            error_result = ChannelCreationResponse(
                status="error",
                channel_id=None,
                channel_username=None,
                invite_link=None,
                title=None,
                message="Сессия Telegram не найдена. Пожалуйста, войдите в систему заново."
            )
            return BatchChannelResponse(
                results=[error_result] * len(request.channels),
                success_count=0,
                error_count=len(request.channels)
            )
        
        print(f"[CREATE_CHANNELS_BATCH] Session found for user {current_user.id}")
        
        # Импортируем TelegramAuth для создания каналов
        from tg_auth import TelegramAuth
        
        # Создаем ОДИН экземпляр TelegramAuth для всех каналов
        auth = TelegramAuth(user_id=current_user.id)
        
        try:
            # Создаем каналы последовательно в рамках одной сессии
            for i, channel_request in enumerate(request.channels):
                print(f"[CREATE_CHANNELS_BATCH] Creating channel {i+1}/{len(request.channels)}: {channel_request.title}")
                
                # Небольшая задержка между созданием каналов (кроме первого)
                if i > 0:
                    await asyncio.sleep(0.5)
                
                result = await auth.create_channel_with_error_handling(
                    title=channel_request.title,
                    description=channel_request.description,
                    is_megagroup=channel_request.is_megagroup
                )
                
                channel_result = ChannelCreationResponse(**result)
                results.append(channel_result)
                
                if result["status"] == "success":
                    success_count += 1
                    print(f"[CREATE_CHANNELS_BATCH] Successfully created channel {i+1}: {result['channel_id']}")
                else:
                    error_count += 1
                    print(f"[CREATE_CHANNELS_BATCH] Failed to create channel {i+1}: {result['message']}")
        
        finally:
            # ВАЖНО: Очищаем ресурсы только один раз в конце
            await auth.cleanup()
            print(f"[CREATE_CHANNELS_BATCH] Session cleanup completed")
        
        print(f"[CREATE_CHANNELS_BATCH] Batch completed: {success_count} success, {error_count} errors")
        
        return BatchChannelResponse(
            results=results,
            success_count=success_count,
            error_count=error_count
        )
            
    except Exception as e:
        error_msg = str(e)
        print(f"[CREATE_CHANNELS_BATCH] ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Возвращаем ошибку для всех каналов
        error_result = ChannelCreationResponse(
            status="error",
            channel_id=None,
            channel_username=None,
            invite_link=None,
            title=None,
            message=f"Внутренняя ошибка сервера: {error_msg}"
        )
        
        return BatchChannelResponse(
            results=[error_result] * len(request.channels),
            success_count=0,
            error_count=len(request.channels)
        )
