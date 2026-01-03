print("ЗАГРУЖЕНА 3 ВЕРСИЯ API/SESSIONS.PY")
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_db
from models import TelegramSession, User
from pydantic import BaseModel
from datetime import datetime, timedelta
import os

from pathlib import Path



from auth import create_jwt_token

SESSION_BASE_DIR = "session_data"

router = APIRouter()

class PhoneCheckRequest(BaseModel):
    phone: str

@router.post("/check")
async def check_phone_session(request_data: PhoneCheckRequest, response: Response, db: AsyncSession = Depends(get_db)):
    phone = request_data.phone
    print(f"Attempting to check and validate session for phone: {phone}")
    
    user_stmt = select(User).where(User.phone_number == phone)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        print(f"WARNING: User not found for phone number: {phone}")
        return {"session_valid": False, "message": "User not found for this phone number."}

    session_stmt = select(TelegramSession).where(TelegramSession.user_id == user.id)
    session_result = await db.execute(session_stmt)
    tg_session = session_result.scalar_one_or_none()

    if not tg_session:
        print(f"WARNING: Telegram session data not found for user ID: {user.id} (phone: {phone})")
        return {"session_valid": False, "message": "Telegram session data not found for this user."}

    if not tg_session.session_path or not os.path.exists(tg_session.session_path):
        print(f"WARNING: Session file missing or path not set for user ID: {user.id} (path: {tg_session.session_path})")
        return {"session_valid": False, "message": "Session file missing or path not set."}
        
    print(f"Session file exists and DB record present for user ID: {user.id}. Proceeding to issue JWT.")

    tg_session.session_last_used = datetime.utcnow()
    await db.commit()
    await db.refresh(tg_session)

    token = create_jwt_token({"sub": user.id})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax",
        secure=False, 
        domain="localhost",
        path="/"  # Ensure cookie is available for all paths
    )

    print(f"Successfully set JWT cookie for user ID: {user.id} with path=/")
    return {
        "session_valid": True,
        "message": "Session check successful, authentication token issued.",
        "user_id": user.id,
        "username": user.telegram_user_name,
    }