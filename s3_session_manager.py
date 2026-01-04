import os
import boto3
import logging
from typing import Optional
from botocore.exceptions import ClientError, NoCredentialsError

class S3SessionManager:
    """Manages Telegram session files in S3 storage."""
    
    def __init__(self):
        # Get Yandex Cloud credentials from environment variables
        self.yc_access_key = os.getenv('YC_ACCESS_KEY_ID')
        self.yc_secret_key = os.getenv('YC_SECRET_ACCESS_KEY')
        self.yc_region = os.getenv('YC_REGION', 'ru-central1')
        self.yc_endpoint_url = os.getenv('YC_ENDPOINT_URL', 'https://storage.yandexcloud.net')
        self.bucket_name = os.getenv('BUCKET_NAME')
        
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
    
    def _get_session_key(self, user_id: int) -> str:
        """Generate S3 key for user session."""
        return f"sessions/{user_id}.session"
    
    def session_exists(self, user_id: int) -> bool:
        """Check if session exists in S3 or locally."""
        if not self.s3_enabled:
            # Fallback to local file check
            import os
            session_path = f"sessions/{user_id}.session"
            return os.path.exists(session_path)
            
        try:
            session_key = self._get_session_key(user_id)
            self.s3_client.head_object(Bucket=self.bucket_name, Key=session_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                self.logger.error(f"Error checking session existence: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error checking session: {e}")
            return False
    
    def upload_session(self, user_id: int, local_session_path: str) -> bool:
        """Upload session file to S3 or keep locally."""
        if not self.s3_enabled:
            # When S3 is not configured, session is already local - just return True
            if os.path.exists(local_session_path):
                self.logger.debug(f"Session kept locally: {local_session_path}")
                return True
            return False
            
        try:
            if not os.path.exists(local_session_path):
                self.logger.error(f"Local session file not found: {local_session_path}")
                return False
            
            session_key = self._get_session_key(user_id)
            
            with open(local_session_path, 'rb') as session_file:
                self.s3_client.upload_fileobj(
                    session_file,
                    self.bucket_name,
                    session_key
                )
            
            self.logger.debug(f"Session uploaded to S3: {session_key}")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"Session file not found: {local_session_path}")
            return False
        except NoCredentialsError:
            self.logger.error("S3 credentials not available")
            return False
        except Exception as e:
            self.logger.error(f"Failed to upload session: {e}")
            return False
    
    def download_session(self, user_id: int, local_session_path: str) -> bool:
        """Download session file from S3 or check locally."""
        if not self.s3_enabled:
            # When S3 is not configured, check if session exists locally
            if os.path.exists(local_session_path):
                self.logger.debug(f"Session found locally: {local_session_path}")
                return True
            return False
            
        try:
            session_key = self._get_session_key(user_id)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_session_path), exist_ok=True)
            
            with open(local_session_path, 'wb') as session_file:
                self.s3_client.download_fileobj(
                    self.bucket_name,
                    session_key,
                    session_file
                )
            
            self.logger.debug(f"Session downloaded from S3: {session_key}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.logger.error(f"Session not found in S3: {session_key}")
            else:
                self.logger.error(f"Failed to download session: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading session: {e}")
            return False
    
    def delete_session(self, user_id: int) -> bool:
        """Delete session file from S3."""
        try:
            session_key = self._get_session_key(user_id)
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=session_key
            )
            
            self.logger.debug(f"Session deleted from S3: {session_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete session: {e}")
            return False
    
    async def get_session(self, user_id: int) -> Optional[bytes]:
        """Get session data from S3 or local storage."""
        if not self.s3_enabled:
            # Fallback to local file
            session_path = f"sessions/{user_id}.session"
            try:
                if os.path.exists(session_path):
                    with open(session_path, 'rb') as f:
                        return f.read()
                return None
            except Exception as e:
                self.logger.error(f"Error reading local session: {e}")
                return None
        
        try:
            session_key = self._get_session_key(user_id)
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=session_key
            )
            
            session_data = response['Body'].read()
            self.logger.debug(f"Session retrieved from S3: {session_key}")
            return session_data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                self.logger.error(f"Session not found in S3: {session_key}")
            else:
                self.logger.error(f"Failed to get session from S3: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting session: {e}")
            return None

    def list_sessions(self) -> list:
        """List all session files in S3."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="sessions/"
            )
            
            sessions = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.session'):
                        # Extract user_id from key
                        filename = os.path.basename(key)
                        user_id = filename.replace('.session', '')
                        sessions.append({
                            'user_id': user_id,
                            'key': key,
                            'last_modified': obj['LastModified'],
                            'size': obj['Size']
                        })
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return []