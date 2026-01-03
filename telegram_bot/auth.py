import hmac
import hashlib
import json
import time
from urllib.parse import unquote, parse_qsl
from typing import Dict, Optional
from fastapi import HTTPException
import os

class TMAAuthenticator:
    def __init__(self):
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        
        self.bot_token: str = bot_token
    
    def validate_telegram_data(self, init_data: str) -> Dict:
        """Validate Telegram WebApp initialization data using bot token"""
        try:
            # Parse the init_data string
            parsed_data = dict(parse_qsl(unquote(init_data)))
            print(f"Parsed TMA data: {parsed_data}")
            
            # Extract hash and create data string for validation
            received_hash = parsed_data.pop('hash', '')
            auth_date = parsed_data.get('auth_date', '')
            
            # Check if auth_date is recent (within 1 day for development)
            current_time = int(time.time())
            auth_timestamp = int(auth_date)
            time_diff = abs(current_time - auth_timestamp)
            print(f"Current timestamp: {current_time}, Auth timestamp: {auth_timestamp}, Difference: {time_diff} seconds")
            
            if time_diff > 604800:  # 7 days for development
                print(f"Authentication data too old: {time_diff} seconds")
                raise HTTPException(status_code=401, detail=f"Authentication data too old: {time_diff} seconds")
            
            # Create data check string
            data_check_arr = []
            for key, value in sorted(parsed_data.items()):
                data_check_arr.append(f"{key}={value}")
            data_check_string = '\n'.join(data_check_arr)
            
            # Create secret key from bot token
            secret_key = hmac.new(
                "WebAppData".encode(),
                self.bot_token.encode(),
                hashlib.sha256
            ).digest()
            
            # Calculate expected hash
            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Verify hash
            if not hmac.compare_digest(calculated_hash, received_hash):
                raise HTTPException(status_code=401, detail="Invalid authentication data")
                
            return parsed_data
            
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication validation failed: {str(e)}")
    
    def extract_user_info(self, validated_data: Dict) -> Dict:
        """Extract user information from validated Telegram data"""
        user_data = json.loads(validated_data.get('user', '{}'))
        
        return {
            "telegram_id": user_data.get('id'),
            "username": user_data.get('username'),
            "first_name": user_data.get('first_name'),
            "last_name": user_data.get('last_name'),
            "language_code": user_data.get('language_code', 'en'),
            "allows_write_to_pm": user_data.get('allows_write_to_pm', False)
        }