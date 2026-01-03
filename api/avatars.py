from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse
from s3_avatar_manager import S3AvatarManager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/avatars/{user_id}")
async def get_avatar(user_id: int):
    """Get user avatar from S3 or return default."""
    try:
        s3_avatar_manager = S3AvatarManager()
        
        if s3_avatar_manager.s3_enabled:
            # Try to get avatar URL from S3
            avatar_url = s3_avatar_manager.get_avatar_url(user_id, expires_in=3600)
            if avatar_url:
                # Redirect to S3 presigned URL
                return RedirectResponse(url=avatar_url)
        
        # Fallback to default avatar
        return RedirectResponse(url="/avatars/default.png")
        
    except Exception as e:
        logger.error(f"Error getting avatar for user {user_id}: {e}")
        return RedirectResponse(url="/avatars/default.png")

@router.get("/avatars/{user_id}/exists")
async def check_avatar_exists(user_id: int):
    """Check if user has a custom avatar."""
    try:
        s3_avatar_manager = S3AvatarManager()
        exists = s3_avatar_manager.avatar_exists(user_id)
        
        return {
            "user_id": user_id,
            "has_avatar": exists,
            "s3_enabled": s3_avatar_manager.s3_enabled
        }
        
    except Exception as e:
        logger.error(f"Error checking avatar existence for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "has_avatar": False,
            "s3_enabled": False,
            "error": str(e)
        }