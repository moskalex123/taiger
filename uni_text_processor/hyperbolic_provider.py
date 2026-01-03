"""
Hyperbolic AI Provider Implementation
"""
import os
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Optional, Dict, Any
from .provider_interface import AIProviderInterface


class HyperbolicProvider(AIProviderInterface):
    """Hyperbolic API provider implementation"""
    
    def __init__(self, logger=None):
        super().__init__(logger)
        self.api_url = "https://api.hyperbolic.xyz/v1/chat/completions"
        self.api_key = os.getenv("HYPERBOLIC_API_KEY")
    
    def get_required_parameters(self) -> Dict[str, bool]:
        """
        Hyperbolic requires temperature and top_p parameters.
        
        Returns:
            Dictionary with required parameters
        """
        return {
            "temperature": True,
            "top_p": True,
            "max_tokens": False  # Optional but recommended
        }
    
    def validate_config(self) -> bool:
        """
        Validate Hyperbolic configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.api_key:
            self.log_error("HYPERBOLIC_API_KEY environment variable is required")
            return False
        return True
    
    async def process_text(self, system_content: str, user_content: str,
                          model_name: str, temperature: float,
                          top_p: float, max_tokens: int,
                          http_session: Optional[aiohttp.ClientSession] = None) -> Optional[str]:
        """
        Process text with Hyperbolic API.
        
        Args:
            system_content: System prompt/instructions
            user_content: User input text to process
            model_name: Name of the model to use
            temperature: Temperature parameter for the model
            top_p: Top-p parameter for the model
            max_tokens: Maximum tokens to generate
            http_session: Optional HTTP session to reuse (recommended)
            
        Returns:
            Processed text or error message
        """
        if not self.validate_config():
            return "Configuration Error: Hyperbolic API key not found"
        
        self.log_info(f"Processing with Hyperbolic API. Model: {model_name}")
        self.log_info(f"Request parameters: temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature,
            "top_p": top_p
        }
        
        # Add max_tokens only if provided
        if max_tokens > 0:
            payload["max_tokens"] = max_tokens
        
        request_start_time = datetime.now()
        self.log_info(f"Sending request to Hyperbolic API at {request_start_time}")
        
        try:
            # Use provided session or create a new one
            if http_session is not None:
                session = http_session
                should_close_session = False
            else:
                timeout = aiohttp.ClientTimeout(total=300)
                session = aiohttp.ClientSession(timeout=timeout)
                should_close_session = True
            
            try:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    request_duration = (datetime.now() - request_start_time).total_seconds()
                    self.log_info(f"API response received after {request_duration:.2f} seconds")
                    
                    if response.status != 200:
                        response_data = await response.text()
                        self.log_error(f"API error {response.status}: {response_data}")
                        return f"API Error {response.status}: {response_data}"
                    
                    response_data = await response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        message = response_data["choices"][0]["message"]
                        
                        # Extract the actual content
                        processed_text = ""
                        if "content" in message and message["content"] is not None:
                            processed_text = message["content"]
                        
                        # For reasoning models, extract only the actual response content
                        # Some models return thinking process in the content field
                        # We want to extract the final response, not the thinking process
                        processed_text = self._extract_actual_response(processed_text)
                        
                        self.log_info(f"API processed successfully: {len(processed_text)} chars output")
                        self.log_info(f"Processing completed in {request_duration:.2f} seconds")
                        return processed_text
                    else:
                        self.log_warning(f"Invalid API response structure: {response_data}")
                        return f"Invalid API response structure: {json.dumps(response_data, ensure_ascii=False)}"
            finally:
                # Close session only if we created it
                if should_close_session:
                    if not session.closed:
                        await session.close()
                        
        except asyncio.TimeoutError as e:
            request_duration = (datetime.now() - request_start_time).total_seconds()
            self.log_error(f"API request timeout after {request_duration:.2f} seconds: {e}")
            # Close session if we created it
            if http_session is None and 'session' in locals() and session and not session.closed:
                await session.close()
            return f"TimeoutError: Request took {request_duration:.2f}s (limit: 300s)"
        except aiohttp.ClientError as e:
            request_duration = (datetime.now() - request_start_time).total_seconds()
            self.log_error(f"API client error after {request_duration:.2f} seconds: {e}")
            # Close session if we created it
            if http_session is None and 'session' in locals() and session and not session.closed:
                await session.close()
            return f"ClientError [{type(e).__name__}]: {str(e)[:100]}"
        except Exception as e:
            request_duration = (datetime.now() - request_start_time).total_seconds()
            self.log_error(f"API request failed after {request_duration:.2f} seconds: {e}")
            # Close session if we created it
            if http_session is None and 'session' in locals() and session and not session.closed:
                await session.close()
            return f"{type(e).__name__}: {str(e)[:150]}"
    
    def _extract_actual_response(self, content: str) -> str:
        """
        Extract the actual response from content that may include reasoning/thinking process.
        
        Args:
            content: Raw content from the API response
            
        Returns:
            Extracted actual response content
        """
        if not content:
            return content
            
        # For reasoning models that include thinking process in the content,
        # we want to extract only the actual response part
        content = content.strip()
        
        # If content starts with the notebook emoji (reasoning marker), 
        # try to extract the actual formatted response
        if content.startswith('\ud83d\udcda'):
            lines = content.split('\n')
            
            # Look for lines that contain formatted response indicators
            # such as lines with emojis, markdown formatting, or clear response structure
            actual_response_lines = []
            found_response = False
            
            for line in lines:
                # Skip empty lines and lines that look like thinking process
                if not line.strip():
                    continue
                    
                # If we find a line that looks like a formatted response, 
                # start collecting response lines
                if (line.startswith(('**', '##', '#', '🎉', '🔥', '📢', '📣', '💥', '✨', '✅', '🔥')) or 
                    'скидка' in line.lower() or 
                    'Завтра' in line or
                    ('**' in line and ('%' in line or 'скидка' in line.lower()))):
                    found_response = True
                
                if found_response:
                    actual_response_lines.append(line)
            
            # If we found response lines, return them
            if actual_response_lines:
                return '\n'.join(actual_response_lines).strip()
            
            # Fallback: if we couldn't identify response lines, 
            # return the last substantial line as it's often the actual response
            substantial_lines = [line for line in lines if len(line.strip()) > 10]
            if substantial_lines:
                return substantial_lines[-1].strip()
        
        # Just return the content as is, since most models return the actual response directly
        return content
