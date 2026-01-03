"""
Обработчик медиафайлов для Telegram Worker
"""
import asyncio
import os
import tempfile
from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pyrogram import Client
from pyrogram.types import Message, Photo, Video, Document
from pyrogram.errors import FloodWait
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import ChannelPair
from db import async_session
from .utils import get_api_base_url, split_long_message, format_signature, smart_truncate_message

class MediaHandler:
    """Обработчик медиа контента и альбомов"""
    
    def __init__(self, user_id: int, client: Client, logger, 
                 process_text_callback, determine_schedule_time_callback,
                 resolve_channel_callback, deduct_balance_callback,
                 notify_admin_critical_error_callback,
                 process_with_hyperbolic_callback=None):
        self.user_id = user_id
        self.client = client
        self.logger = logger
        
        # Callbacks to main worker methods
        self._process_text_content_for_album = process_text_callback
        self._determine_schedule_time = determine_schedule_time_callback
        self._resolve_channel_identifier = resolve_channel_callback
        self._deduct_balance_async = deduct_balance_callback
        
        # AI processing callback
        self._process_with_hyperbolic_callback = process_with_hyperbolic_callback
        
        self.user_logger = logger  # Logger specific to user
        
        # Media group handling
        self._media_groups: Dict[str, Dict[str, Any]] = {}
        self._media_group_timers: Dict[str, asyncio.Task] = {}
        self.worker = None
        self._notify_admin_critical_error = notify_admin_critical_error_callback
    
    async def handle_media_group(self, message: Message, rule) -> bool:
        """Handle media group (album) messages."""
        media_group_id = message.media_group_id
        
        if not media_group_id:
            return False
            
        self.logger.info(f"📸 Processing media group message {message.id} (group: {media_group_id})")
        
        # Initialize media group if not exists
        if media_group_id not in self._media_groups:
            self._media_groups[media_group_id] = {
                'messages': [],
                'rule': rule,
                'chat_id': message.chat.id,
                'created_at': datetime.now(),
            }
        else:
            group = self._media_groups[media_group_id]
            group['rule'] = rule
        
        # Add message to group and ensure newest is processed only once
        group = self._media_groups[media_group_id]
        group['messages'] = [msg for msg in group['messages'] if msg.id != message.id]
        group['messages'].append(message)

        # Cancel existing timer if any
        if media_group_id in self._media_group_timers:
            self._media_group_timers[media_group_id].cancel()

        # Set timer to process group after 2 seconds (to collect all messages)
        self._media_group_timers[media_group_id] = asyncio.create_task(
            self._process_media_group_delayed(media_group_id)
        )
        
        return True
    
    async def _process_media_group_delayed(self, media_group_id: str):
        """Process media group after delay to ensure all messages are collected."""
        await asyncio.sleep(2)  # Wait 2 seconds to collect all messages
        
        if media_group_id not in self._media_groups:
            return
            
        group_data = self._media_groups[media_group_id]
        messages = group_data['messages']
        rule = group_data['rule']
        
        self.logger.info(f"📸 Processing complete media group {media_group_id} with {len(messages)} messages")
        
        try:
            await self._process_media_group(messages, rule)
        except Exception as e:
            self.logger.error(f"Failed to process media group {media_group_id}: {e}", exc_info=True)
        finally:
            # Clean up
            if media_group_id in self._media_groups:
                del self._media_groups[media_group_id]
            if media_group_id in self._media_group_timers:
                del self._media_group_timers[media_group_id]
    
    async def _process_media_group(self, messages: List[Message], rule):
        """Process a complete media group (album)."""
        if not messages:
            return
            
        # Sort messages by ID to maintain order
        messages.sort(key=lambda m: m.id)
        first_message = messages[0]
        
        self.logger.info(f"📸 Processing album with {len(messages)} items")
        
        # Check balance first
        async with async_session() as db_session:  # type: ignore
            user = await db_session.get(User, self.user_id)
            current_balance = user.balance if user else 0
            if not user or current_balance < 0:
                self.logger.error(f"Insufficient balance for album processing")
                return
        
        # Extract text from the first message with caption or any message with text
        album_text = ""
        for msg in messages:
            if msg.caption:
                album_text = msg.caption
                break
            elif msg.text:
                album_text = msg.text
                break
        
        # If no text found, create a default message
        if not album_text.strip():
            album_text = "📸 Альбом фотографий"
        
        # Process text content
        try:
            processed_text, has_ai_error = await self._process_text_content_for_album(rule, album_text)
            if processed_text == "UNSUPPORTED_FORMAT":
                self.logger.warning(f"Album text processing returned UNSUPPORTED_FORMAT")
                return
        except Exception as e:
            self.logger.error(f"Failed to process album text: {e}")
            return

        # Prepare signature
        signature = format_signature(rule.caption_text, rule.caption_url)
        
        # Get target channel
        target_channel_id = await self._resolve_channel_identifier(rule.target_channel)
        if not target_channel_id:
            self.logger.error(f"Could not resolve target channel: {rule.target_channel}")
            return
        
        # Calculate schedule time
        try:
            scheduled_time = await self._determine_schedule_time(rule, target_channel_id)
        except Exception as e:
            self.logger.error(f"Failed to calculate schedule time for album: {e}")
            return
        
        # Send album
        try:
            sent_messages = await self.send_album(messages, rule, processed_text, target_channel_id, scheduled_time, signature=signature)
            
            # Deduct balance after successful send
            if sent_messages:
                async with async_session() as db_session:  # type: ignore
                    await self._deduct_balance_async(db_session, self.user_id, rule.model_id)

        except Exception as e:
            self.logger.error(f"Failed to send album: {e}", exc_info=True)

    async def send_album(self, messages: List[Message], rule: ChannelPair,
                        processed_text: str, target_channel_id: int, schedule_time: datetime, signature: Optional[str] = None) -> Optional[List[Message]]:
        """Send album with processed text to target channel."""
        if not messages or not self.client:
            return None

        try:
            self.logger.info(f"📤 Sending album with {len(messages)} items to {target_channel_id}")
            
            # Split long text into parts
            text_parts = split_long_message(processed_text, 1000, self.logger)  # Use 1000 for safety

            # Add signature to the last text part if present
            if signature and text_parts:
                last_part = text_parts[-1]

                # Check limit for album captions (1024)
                if len(last_part) + len(signature) + 2 > 1024:
                    available_space = 1024 - len(signature) - 5
                    last_part = last_part[:available_space] + "..."

                text_parts[-1] = f"{last_part}\n\n{signature}"

            primary_caption = text_parts[0] if text_parts else ""
            
            # Prepare media group
            media_group = []
            for i, msg in enumerate(messages):
                if msg.photo:
                    media_group.append(msg.photo)
                elif msg.video:
                    media_group.append(msg.video)
                elif msg.document:
                    media_group.append(msg.document)

            if not media_group:
                self.logger.warning("Empty media group")
                return None

            # Send album with primary caption
            sent_messages = await self.client.send_media_group(
                chat_id=target_channel_id,
                media=media_group[:10],  # Telegram limit is 10 items per album
                caption=primary_caption,
                schedule_date=schedule_time
            )
            
            # If there are additional text parts, send them as separate messages
            if len(text_parts) > 1:
                additional_time = schedule_time + timedelta(seconds=1)
                for i, part in enumerate(text_parts[1:], 1):
                    try:
                        await self.client.send_message(
                            chat_id=target_channel_id,
                            text=part,
                            schedule_date=additional_time
                        )
                        additional_time += timedelta(seconds=1)  # Stagger subsequent messages
                    except Exception as e:
                        self.logger.error(f"Failed to send additional album text part {i+1}: {e}")

            if sent_messages:
                self.logger.info(f"✅ Album sent successfully with {len(sent_messages)} messages")
                
                # Removed database storage of album info since AlbumPost and AlbumMedia don't exist

            return sent_messages

        except FloodWait as e:
            wait_seconds = int(getattr(e, "value", getattr(e, "x", 1)))
            self.logger.warning(f"FloodWait while sending album: {wait_seconds}s")
            
            if self.worker._notify_admin_critical_error:
                await self.worker._notify_admin_critical_error(
                    "FloodWait",
                    f"Telegram flood limit exceeded while sending album. Waiting {wait_seconds} seconds."
                )

            await asyncio.sleep(wait_seconds)
            return await self.send_album(messages, rule, processed_text, target_channel_id, schedule_time)

        except Exception as e:
            self.logger.error(f"Failed to send album: {e}", exc_info=True)
            return None
    
    async def process_text_content_for_album(self, rule, text: str) -> tuple[str, bool]:
        """Process text content for album with fallback handling."""
        if not text or not text.strip():
            # For albums without text, create a default message
            text = "📸 Альбом фотографий"
        
        # Clean up text
        text = text.strip()
        
        # Apply text deletions
        if rule.text_to_delete:
            original_length = len(text)
            for pattern in [p.strip() for p in rule.text_to_delete.split(',') if p.strip()]:
                text = text.replace(pattern, "")
            text = text.strip()  # Remove extra whitespace after deletions
            self.logger.info(f"After deletions: {original_length} -> {len(text)} chars")
        
        # If text is empty after deletions, use default
        if not text.strip():
            text = "📸 Альбом фотографий"
        
        # Apply AI processing if configured
        if rule.model_id and rule.model:
            # Сохраняем значения модели для избежания синхронного доступа
            model_system_content = rule.model.system_content
            model_name = rule.model.model
            model_temperature = rule.model.temperature or 0.1
            model_top_p = rule.model.top_p or 0.9
            model_max_tokens = rule.model.max_tokens or 500
            
            system_prompt = rule.system_content if rule.system_content is not None else model_system_content
            temperature = rule.temperature if rule.temperature is not None else model_temperature
            top_p = rule.top_p if rule.top_p is not None else model_top_p
            max_tokens = rule.max_tokens if rule.max_tokens is not None else model_max_tokens
            
                # Call the AI processing callback
            if hasattr(self, '_process_with_hyperbolic_callback') and self._process_with_hyperbolic_callback is not None:
                processed_text = await self._process_with_hyperbolic_callback(
                    system_content=system_prompt,
                    user_content=text,
                    model_name=model_name,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens
                )
                
                if processed_text:
                    return processed_text, False
                else:
                    self.logger.warning("AI processing failed for album, using original text")
                    return text, True
            else:
                self.logger.info("AI processing callback not available for albums")
                return text, False
        else:
            # No AI processing, return original text
            return text, False