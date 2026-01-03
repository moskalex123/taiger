from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession # Добавлено
from sqlalchemy import select # Добавлено
from db import get_db # Добавлено
from auth import get_current_user # Добавлено
from models import User # Добавлено
from s3_avatar_manager import S3AvatarManager
from s3_session_manager import S3SessionManager
from pyrogram import Client
import os
import tempfile

router = APIRouter()

async def load_user_avatar_from_telegram(user_id: int):
    """Load user avatar from Telegram and save to S3"""
    try:
        # Get Telegram API credentials
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            print(f"[AVATAR] Telegram API credentials not configured")
            return
        
        # Get session from S3
        session_manager = S3SessionManager()
        session_data = await session_manager.get_session(user_id)
        
        if not session_data:
            print(f"[AVATAR] No session found for user {user_id}")
            return
        
        # Create temporary session file
        temp_session_path = f"temp_avatar_session_{user_id}.session"
        
        try:
            # Write session data to temporary file
            with open(temp_session_path, 'wb') as f:
                f.write(session_data)
            
            # Initialize Pyrogram client
            client = Client(
                temp_session_path.replace('.session', ''),
                api_id=int(api_id),
                api_hash=api_hash,
                workdir="."
            )
            
            await client.start()
            
            # Get user's own profile
            me = await client.get_me()
            
            if me.photo:
                # Download profile photo
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    photo_path = await client.download_media(me.photo.big_file_id, file_name=temp_file.name)
                    
                    if photo_path:
                        # Upload to S3
                        s3_avatar_manager = S3AvatarManager()
                        if s3_avatar_manager.s3_enabled:
                            success = s3_avatar_manager.upload_avatar(user_id, photo_path)
                            if success:
                                print(f"[AVATAR] Successfully uploaded avatar for user {user_id}")
                            else:
                                print(f"[AVATAR] Failed to upload avatar to S3 for user {user_id}")
                        
                        # Clean up downloaded file
                        try:
                            os.unlink(photo_path)
                        except:
                            pass
            else:
                print(f"[AVATAR] User {user_id} has no profile photo")
            
            await client.stop()
            
        finally:
            # Clean up temporary session file
            try:
                if os.path.exists(temp_session_path):
                    os.remove(temp_session_path)
            except Exception as e:
                print(f"[AVATAR] Warning: Could not clean up temporary file {temp_session_path}: {e}")
                
    except Exception as e:
        print(f"[AVATAR] Error loading avatar for user {user_id}: {e}")
        import traceback
        traceback.print_exc()

@router.get("/me")
async def get_me(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get the actual User model from database
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user has custom avatar in S3
    s3_avatar_manager = S3AvatarManager()
    avatar_url = s3_avatar_manager.get_avatar_url(user.id)

    if not avatar_url and s3_avatar_manager.s3_enabled:
        # Try to load avatar from Telegram if not in S3 yet
        try:
            await load_user_avatar_from_telegram(user.id)
            avatar_url = s3_avatar_manager.get_avatar_url(user.id)
        except Exception as e:
            print(f"Failed to load avatar from Telegram for user {user.id}: {e}")

    if not avatar_url:
        avatar_url = "/avatars/default.png"

    # Определяем отображаемое имя пользователя с fallback логикой
    display_name = None
    if user.username:
        display_name = user.username
    elif user.first_name or user.last_name:
        name_parts = []
        if user.first_name:
            name_parts.append(user.first_name)
        if user.last_name:
            name_parts.append(user.last_name)
        display_name = " ".join(name_parts)
    elif user.telegram_user_name:
        display_name = user.telegram_user_name
    else:
        display_name = f"User {user.id}"

    return {
        "id": user.id,
        "username": display_name,
        "balance": user.balance,
        "avatar_url": avatar_url,
        "VIP_level": user.VIP_level
    }

@router.get("/me/language")
async def get_user_language(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get the actual User model from database
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"language_code": user.language_code or 'en'}

@router.post("/me/language")
async def update_user_language(
    request: dict,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    language_code = request.get("language_code")
    if language_code not in ['ru', 'en']:
        raise HTTPException(status_code=400, detail="Invalid language code")

    # Get the actual User model from database
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.language_code = language_code
    await db.commit()
    return {"language_code": user.language_code}