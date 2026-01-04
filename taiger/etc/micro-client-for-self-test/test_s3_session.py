#!/usr/bin/env python3
"""
Test script to verify S3 session loading functionality
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import S3SessionManager
sys.path.append('..')
from s3_session_manager import S3SessionManager

def test_s3_session_loading():
    """Test S3 session loading functionality"""
    logger.info("🧪 Testing S3 Session Loading")
    
    try:
        # Initialize S3 session manager
        s3_manager = S3SessionManager()
        
        test_user_id = 7
        logger.info(f"📦 Checking session for user {test_user_id}")
        
        # Check if S3 is configured
        if s3_manager.s3_enabled:
            logger.info("☁️ S3 is configured and enabled")
            logger.info(f"📍 Bucket: {s3_manager.bucket_name}")
            logger.info(f"🌍 Region: {s3_manager.yc_region}")
            logger.info(f"🔗 Endpoint: {s3_manager.yc_endpoint_url}")
        else:
            logger.info("⚠️ S3 is not configured, will use local sessions")
        
        # Check if session exists
        session_exists = s3_manager.session_exists(test_user_id)
        logger.info(f"🔍 Session exists: {session_exists}")
        
        if session_exists:
            logger.info("✅ Session found in S3!")
            
            # Try to download session
            import tempfile
            session_path = os.path.join(tempfile.gettempdir(), "test_session.session")
            
            if s3_manager.download_session(test_user_id, session_path):
                logger.info(f"✅ Session downloaded successfully to: {session_path}")
                
                # Check file size
                if os.path.exists(session_path):
                    file_size = os.path.getsize(session_path)
                    logger.info(f"📊 Session file size: {file_size} bytes")
                    
                    if file_size > 0:
                        logger.info("✅ Session file appears to be valid")
                        return True
                    else:
                        logger.warning("⚠️ Session file is empty")
                        return False
                else:
                    logger.error("❌ Session file was not created")
                    return False
            else:
                logger.error("❌ Failed to download session")
                return False
        else:
            logger.warning(f"⚠️ No session found for user {test_user_id}")
            logger.info("💡 Make sure the session exists in S3 or local storage")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during S3 session test: {e}")
        return False

if __name__ == "__main__":
    success = test_s3_session_loading()
    if success:
        logger.info("🎉 S3 session loading test passed!")
        sys.exit(0)
    else:
        logger.info("❌ S3 session loading test failed!")
        sys.exit(1)