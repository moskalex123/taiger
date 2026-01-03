import boto3
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
from PIL import Image
import io

# Load environment variables
load_dotenv()

class S3AvatarManager:
    """Manages user avatar files in S3 storage."""
    
    def __init__(self):
        # Get Yandex Cloud credentials from environment variables
        self.yc_access_key = os.getenv('YC_ACCESS_KEY_ID')
        self.yc_secret_key = os.getenv('YC_SECRET_ACCESS_KEY')
        self.yc_region = os.getenv('YC_REGION', 'ru-central1')
        self.yc_endpoint_url = os.getenv('YC_ENDPOINT_URL', 'https://storage.yandexcloud.net')
        self.bucket_name = os.getenv('AVATAR_BUCKET_NAME')
        
        # Check if Yandex Cloud is configured
        self.s3_enabled = all([self.yc_access_key, self.yc_secret_key, self.bucket_name])
        
        if self.s3_enabled:
            # Initialize S3 client for Yandex Object Storage
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.yc_access_key,
                aws_secret_access_key=self.yc_secret_key,
                region_name=self.yc_region,
                endpoint_url=self.yc_endpoint_url
            )
        else:
            self.s3_client = None
        
        self.logger = logging.getLogger(__name__)
    
    def _get_avatar_key(self, user_id: int) -> str:
        """Generate S3 key for user avatar."""
        return f"avatars/{user_id}.jpg"
    
    def avatar_exists(self, user_id: int) -> bool:
        """Check if avatar exists in S3 or locally."""
        jpg_path = f"frontend/dist/avatars/{user_id}.jpg"
        png_path = f"frontend/dist/avatars/{user_id}.png"

        # Prefer already cached local files regardless of S3 configuration
        for path in (jpg_path, png_path):
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True

        if not self.s3_enabled:
            return False
            
        try:
            avatar_key = self._get_avatar_key(user_id)
            self.s3_client.head_object(Bucket=self.bucket_name, Key=avatar_key)
            
            # Ensure local cache is populated for web serving
            if not os.path.exists(jpg_path) or os.path.getsize(jpg_path) == 0:
                self.download_avatar(user_id, jpg_path)
            
            # Re-check local cache after potential download
            for path in (jpg_path, png_path):
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    return True

            return False
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Avatar missing in S3, fall back to any local copy (even zero-sized cache cleaned above)
                for path in (jpg_path, png_path):
                    if os.path.exists(path) and os.path.getsize(path) > 0:
                        return True
                return False
            else:
                self.logger.error(f"Error checking avatar existence: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error checking avatar: {e}")
            return False
    
    def _compress_image(self, input_path: str, quality: int = 85, max_size: tuple = (512, 512)) -> bytes:
        """Compress image to reduce file size while maintaining reasonable quality."""
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if image is too large
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save to bytes with compression
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=quality, optimize=True)
                return output.getvalue()
        except Exception as e:
            self.logger.error(f"Failed to compress image: {e}")
            # Fallback: return original file content
            with open(input_path, 'rb') as f:
                return f.read()
    
    def upload_avatar(self, user_id: int, local_avatar_path: str) -> bool:
        """Upload avatar file to S3 with compression or keep locally."""
        if not self.s3_enabled:
            # When S3 is not configured, avatar is already local - just return True
            if os.path.exists(local_avatar_path):
                self.logger.info(f"Avatar kept locally: {local_avatar_path}")
                return True
            return False
            
        try:
            if not os.path.exists(local_avatar_path):
                self.logger.error(f"Local avatar file not found: {local_avatar_path}")
                return False
            
            avatar_key = self._get_avatar_key(user_id)
            
            # Compress image before uploading
            compressed_data = self._compress_image(local_avatar_path)
            
            # Upload compressed image
            self.s3_client.upload_fileobj(
                io.BytesIO(compressed_data),
                self.bucket_name,
                avatar_key,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
            
            self.logger.info(f"Compressed avatar uploaded to S3: {avatar_key} (size: {len(compressed_data)} bytes)")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"Avatar file not found: {local_avatar_path}")
            return False
        except NoCredentialsError:
            self.logger.error("S3 credentials not available")
            return False
        except Exception as e:
            self.logger.error(f"Failed to upload avatar: {e}")
            return False
    
    def download_avatar(self, user_id: int, local_avatar_path: str) -> bool:
        """Download avatar file from S3 or check locally."""
        if not self.s3_enabled:
            # When S3 is not configured, check if avatar exists locally
            avatar_path = f"frontend/dist/avatars/{user_id}.png"
            if os.path.exists(avatar_path):
                self.logger.info(f"Avatar found locally: {avatar_path}")
                return True
            return False
            
        try:
            avatar_key = self._get_avatar_key(user_id)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_avatar_path), exist_ok=True)
            
            with open(local_avatar_path, 'wb') as avatar_file:
                self.s3_client.download_fileobj(
                    self.bucket_name,
                    avatar_key,
                    avatar_file
                )
            
            self.logger.info(f"Avatar downloaded from S3: {avatar_key}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.logger.error(f"Avatar not found in S3: {avatar_key}")
            else:
                self.logger.error(f"Failed to download avatar: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading avatar: {e}")
            return False
    
    def delete_avatar(self, user_id: int) -> bool:
        """Delete avatar file from S3."""
        if not self.s3_enabled:
            return True
            
        try:
            avatar_key = self._get_avatar_key(user_id)
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=avatar_key
            )
            
            self.logger.info(f"Avatar deleted from S3: {avatar_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete avatar: {e}")
            return False
    
    def get_avatar_url(self, user_id: int, expires_in: int = 3600) -> Optional[str]:
        """Generate URL for avatar access."""
        # Check if avatar exists first
        if not self.avatar_exists(user_id):
            return None
            
        # For TMA compatibility, use local avatar path instead of presigned S3 URL
        # This avoids CORS issues with presigned URLs
        # First check for JPG (S3 format), then PNG (legacy format)
        jpg_path = f"frontend/dist/avatars/{user_id}.jpg"
        png_path = f"frontend/dist/avatars/{user_id}.png"
        
        # Check if JPG exists and is not empty
        if os.path.exists(jpg_path) and os.path.getsize(jpg_path) > 0:
            return f"/avatars/{user_id}.jpg"
        # Check if PNG exists (fallback)
        elif os.path.exists(png_path) and os.path.getsize(png_path) > 0:
            return f"/avatars/{user_id}.png"
        else:
            return None
    
    def update_user_avatar(self, user_id: int, avatar_data: bytes) -> bool:
        """Update user avatar with provided data."""
        # Check if avatar data is empty
        if not avatar_data or len(avatar_data) == 0:
            self.logger.warning(f"Avatar data is empty for user {user_id}, skipping upload")
            return False
            
        if not self.s3_enabled:
            # Save locally when S3 is not configured
            try:
                avatar_dir = "frontend/dist/avatars"
                os.makedirs(avatar_dir, exist_ok=True)
                avatar_path = os.path.join(avatar_dir, f"{user_id}.png")
                
                with open(avatar_path, 'wb') as f:
                    f.write(avatar_data)
                
                self.logger.info(f"Avatar updated locally: {avatar_path}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to save avatar locally: {e}")
                return False
        
        try:
            avatar_key = self._get_avatar_key(user_id)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=avatar_key,
                Body=avatar_data,
                ContentType='image/jpeg'
            )
            
            self.logger.info(f"Avatar updated in S3: {avatar_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update avatar in S3: {e}")
            return False

    def list_avatars(self) -> list:
        """List all avatar files in S3."""
        if not self.s3_enabled:
            return []
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="avatars/"
            )
            
            avatars = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.jpg'):
                        # Extract user_id from key
                        filename = os.path.basename(key)
                        user_id = filename.replace('.jpg', '')
                        avatars.append({
                            'user_id': user_id,
                            'key': key,
                            'last_modified': obj['LastModified'],
                            'size': obj['Size']
                        })
            
            return avatars
            
        except Exception as e:
            self.logger.error(f"Failed to list avatars: {e}")
            return []