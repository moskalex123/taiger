"""
Планировщик сообщений для Telegram
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.messages.get_scheduled_history import GetScheduledHistory
from pyrogram.raw.types.input_peer_channel import InputPeerChannel
from pyrogram.client import Client
from pyrogram.raw.base.input_peer import InputPeer

# Import the split function
from .utils import split_long_message


class MessageScheduler:
    """Планировщик отложенных сообщений"""
    
    def __init__(self, client: Optional[Client], logger, notify_admin_callback=None, log_worker_status_callback=None, handle_flood_wait_callback=None):
        self.client = client
        self.logger = logger
        self._notify_admin_critical_error = notify_admin_callback
        self._log_worker_status = log_worker_status_callback
        self._handle_flood_wait = handle_flood_wait_callback
        self.last_error_message: Optional[str] = None
        
        # Remove caching attributes since we now always fetch from Telegram
    
    async def get_last_pending_scheduled_time(self, target_channel_id: int) -> Optional[datetime]:
        """Gets the datetime of the last scheduled message in the target channel."""
        last_scheduled_datetime = None
        try:
            if self.client is None:
                self.logger.error("Client is not initialized")
                return None
                
            peer = await self.client.resolve_peer(target_channel_id)
            
            if not isinstance(peer, InputPeerChannel):
                self.logger.warning(f"Target {target_channel_id} is not a channel")
                return None
            
            # Use the resolved peer directly instead of wrapping it in InputPeer()
            scheduled_history = await self.client.invoke(
                GetScheduledHistory(peer=peer, hash=0)  # type: ignore
            )
            
            if scheduled_history.messages:
                latest_message = max(scheduled_history.messages, key=lambda m: m.date)
                last_scheduled_datetime = datetime.fromtimestamp(latest_message.date, tz=timezone.utc)
                self.logger.info(f"Last scheduled message in {target_channel_id} is at {last_scheduled_datetime}")
            else:
                self.logger.info(f"No scheduled messages found in {target_channel_id}")
                
        except FloodWait as e:
            wait_seconds = int(getattr(e, "value", getattr(e, "x", 1)))
            self.logger.warning(f"FloodWait while fetching scheduled messages for {target_channel_id}: {wait_seconds}s")

            if self._notify_admin_critical_error:
                await self._notify_admin_critical_error(
                    "FloodWait",
                    f"Telegram flood limit exceeded while getting scheduled messages. Waiting {wait_seconds} seconds."
                )

            if self._handle_flood_wait:
                await self._handle_flood_wait(wait_seconds, f"fetching scheduled messages for {target_channel_id}")
            else:
                await asyncio.sleep(wait_seconds)

            return await self.get_last_pending_scheduled_time(target_channel_id)
        except Exception as e:
            self.logger.error(f"Error getting scheduled messages: {e}")
            
        return last_scheduled_datetime
    
    async def determine_schedule_time(self, rule, target_channel_id: int) -> datetime:
        """Calculate scheduled time for post."""
        now_utc = datetime.now(timezone.utc)
        
        # ALWAYS fetch the latest scheduled time from Telegram's scheduled posts feed
        # This is the key requirement - we must never use cached values
        last_scheduled = await self.get_last_pending_scheduled_time(target_channel_id)
        
        # Log the fetched value for debugging
        self.logger.info(f"Fetched last scheduled time from Telegram: {last_scheduled}")
        
        # Use the fetched time as base if it exists, otherwise use current time
        if last_scheduled is not None:
            base_time = last_scheduled
        else:
            base_time = now_utc
        
        delay = random.randint(7 * 3600, 9 * 3600)  # 7-9 hours
        scheduled_time = base_time + timedelta(seconds=delay)
        
        # Ensure the scheduled time is not in the past
        if scheduled_time < now_utc:
            scheduled_time = now_utc + timedelta(seconds=delay)
        
        self.logger.info(f"Final scheduling decision: base_time={base_time}, delay={delay}, scheduled_time={scheduled_time}")
        
        return scheduled_time
    
    async def schedule_message(self, text: str, target_channel_id: int,
                              schedule_time: datetime, original_message: Optional[Message] = None,
                              update_worker_status_callback=None,
                              disconnect_callback=None, balance_deducted: Optional[float] = None,
                              retry_count: int = 0, signature: Optional[str] = None) -> Optional[Message]:
        """Schedule message (text or media) to target channel."""
        if retry_count > 5:
            raise RuntimeError("Exceeded flood wait retries while scheduling message")

        if self.client is None:
            self.logger.error("Client is not initialized")
            return None

        try:
            # Determine message type
            if original_message and (original_message.photo or original_message.video or original_message.document):
                media_type = "photo" if original_message.photo else "video" if original_message.video else "document"
                self.logger.info(f"📅 Scheduling {media_type} message to channel {target_channel_id} at {schedule_time}")
                self.logger.info(f"📝 Caption length: {len(text)} chars")
                
                # For media messages, we split the caption if it's too long
                from uni_text_processor.text_formatting import markdown_to_telegram_html
                formatted_text = markdown_to_telegram_html(text)
                caption_parts = split_long_message(formatted_text, 1000, self.logger)  # Use 1000 for safety

                # Add signature to the last caption part if present
                if signature and caption_parts:
                    last_part = caption_parts[-1]

                    # Check limit for media captions (1024)
                    if len(last_part) + len(signature) + 2 > 1024:
                        available_space = 1024 - len(signature) - 5
                        last_part = last_part[:available_space] + "..."

                    caption_parts[-1] = f"{last_part}\n\n{signature}"

                primary_caption = caption_parts[0] if caption_parts else ""
                
                # Schedule media message with primary caption part
                if original_message.photo:
                    scheduled_msg = await self.client.send_photo(
                        chat_id=target_channel_id,
                        photo=original_message.photo.file_id,
                        caption=primary_caption,
                        parse_mode=ParseMode.HTML,
                        schedule_date=schedule_time
                    )
                elif original_message.video:
                    scheduled_msg = await self.client.send_video(
                        chat_id=target_channel_id,
                        video=original_message.video.file_id,
                        caption=primary_caption,
                        parse_mode=ParseMode.HTML,
                        schedule_date=schedule_time
                    )
                elif original_message.document:
                    scheduled_msg = await self.client.send_document(
                        chat_id=target_channel_id,
                        document=original_message.document.file_id,
                        caption=primary_caption,
                        parse_mode=ParseMode.HTML,
                        schedule_date=schedule_time
                    )
                else:
                    # Fallback to text
                    scheduled_msg = await self.client.send_message(
                        chat_id=target_channel_id,
                        text=_fmt(text) if 'primary_caption' in locals() and primary_caption else _fmt(text),
                        parse_mode=ParseMode.HTML,
                        schedule_date=schedule_time
                    )
                
                # If there are additional caption parts, send them as separate messages
                if len(caption_parts) > 1:
                    additional_time = schedule_time + timedelta(seconds=1)
                    for i, part in enumerate(caption_parts[1:], 1):
                        try:
                            await self.client.send_message(
                                chat_id=target_channel_id,
                                text=part,
                                parse_mode=ParseMode.HTML,
                                schedule_date=additional_time
                            )
                            additional_time += timedelta(seconds=1)  # Stagger subsequent messages
                        except Exception as e:
                            self.logger.error(f"Failed to send additional caption part {i+1}: {e}")
            else:
                # For text messages, we split the text into multiple messages
                # Apply HTML formatting to text messages like we do for media captions
                from uni_text_processor.text_formatting import markdown_to_telegram_html
                formatted_text = markdown_to_telegram_html(text)
                text_parts = split_long_message(formatted_text, 1000, self.logger)  # Use 1000 for safety

                # Add signature to the last text part if present
                if signature and text_parts:
                    last_part = text_parts[-1]

                    # Check limit for text messages (4096)
                    if len(last_part) + len(signature) + 2 > 4000:
                        available_space = 4000 - len(signature) - 5
                        last_part = last_part[:available_space] + "..."

                    text_parts[-1] = f"{last_part}\n\n{signature}"

                scheduled_msg = None
                current_time = schedule_time

                # Schedule the first part
                if text_parts:
                    first_part = text_parts[0]
                    if len(text_parts) > 1:
                        # Add part indicator for multi-part messages
                        first_part = f"(1/{len(text_parts)})\n\n{first_part}"

                    scheduled_msg = await self.client.send_message(
                        chat_id=target_channel_id,
                        text=first_part,
                        parse_mode=ParseMode.HTML,
                        schedule_date=current_time
                    )
                    current_time += timedelta(seconds=1)  # Stagger subsequent messages

                # Schedule additional parts
                for i, part in enumerate(text_parts[1:], 2):  # Start from part 2
                    try:
                        part_text = f"({i}/{len(text_parts)})\n\n{part}"
                        await self.client.send_message(
                            chat_id=target_channel_id,
                            text=part_text,
                            parse_mode=ParseMode.HTML,
                            schedule_date=current_time
                        )
                        current_time += timedelta(seconds=1)  # Stagger subsequent messages
                    except Exception as e:
                        self.logger.error(f"Failed to send text part {i}: {e}")
            
            # Детальное логирование ответа от Telegram
            if scheduled_msg:
                self.logger.info(f"✅ Telegram response: Message scheduled successfully")
                self.logger.info(f"📊 Scheduled message ID: {scheduled_msg.id}")
                self.logger.info(f"📅 Scheduled date: {scheduled_msg.date}")
                self.logger.info(f"🎯 Target chat ID: {scheduled_msg.chat.id}")
                self.logger.info(f"📝 Message type: {scheduled_msg.media}")
                self.logger.info(f"🔗 Message link: https://t.me/c/{str(scheduled_msg.chat.id)[4:]}/{scheduled_msg.id}")
                # Логирование перенесено в message_processor для избежания дублирования
                # и правильного отображения информации о списанном балансе
                pass
            else:
                self.logger.warning("⚠️ Telegram returned None for scheduled message")
                if self._log_worker_status:
                    await self._log_worker_status("telegram_schedule_warning", 
                        "log_telegram_schedule_warning", "warning")
            
            return scheduled_msg
        except FloodWait as e:
            wait_seconds = int(getattr(e, "value", getattr(e, "x", 1)))
            self.logger.warning(
                f"FloodWait while scheduling message to {target_channel_id}: {wait_seconds}s"
            )
            self.last_error_message = f"FloodWait: retry after {wait_seconds}s"

            if self._notify_admin_critical_error:
                await self._notify_admin_critical_error(
                    "Telegram FloodWait",
                    f"Flood wait triggered while scheduling message to {target_channel_id}. Waiting {wait_seconds} seconds."
                )

            if self._handle_flood_wait:
                await self._handle_flood_wait(wait_seconds, f"scheduling message to {target_channel_id}")
            else:
                await asyncio.sleep(wait_seconds)

            return await self.schedule_message(
                text,
                target_channel_id,
                schedule_time,
                original_message,
                update_worker_status_callback,
                disconnect_callback,
                balance_deducted,
                retry_count=retry_count + 1
            )

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"🚨 Failed to schedule message: {error_msg}", exc_info=True)
            self.last_error_message = error_msg
            # Schedule failed
            self.logger.error(f"🔍 Schedule parameters: channel={target_channel_id}, time={schedule_time}, text_len={len(text)}")
            # Log detailed scheduling error to dashboard
            if self._log_worker_status:
                await self._log_worker_status("telegram_schedule_error", 
                    "log_telegram_schedule_error", "error", error=error_msg)
            
            # Check for specific Telegram scheduling errors
            if "flood" in error_msg.lower():
                if self._log_worker_status:
                    await self._log_worker_status("telegram_schedule_flood", 
                        "log_telegram_schedule_flood", "error")
                # Notify admin about scheduling flood error
                if self._notify_admin_critical_error:
                    await self._notify_admin_critical_error(
                        "Telegram Schedule Flood", 
                        f"Telegram flood limit exceeded during message scheduling: {error_msg}"
                    )
                
                # Stop worker due to critical flood error
                self.logger.critical(f"Stopping worker due to Telegram Schedule Flood: {error_msg}")
                if update_worker_status_callback:
                    await update_worker_status_callback('stopped', f"Telegram Schedule Flood: {error_msg}")
                if disconnect_callback:
                    await disconnect_callback()
                import os
                os._exit(1)  # Force exit the worker process
            elif "forbidden" in error_msg.lower():
                if self._log_worker_status:
                    await self._log_worker_status("telegram_schedule_forbidden", 
                        "log_telegram_schedule_forbidden", "error")
                # Notify admin about forbidden access
                if self._notify_admin_critical_error:
                    await self._notify_admin_critical_error(
                        "Telegram Access Forbidden", 
                        f"Bot lacks permissions to schedule messages: {error_msg}"
                    )
            elif "chat not found" in error_msg.lower():
                if self._log_worker_status:
                    await self._log_worker_status("telegram_schedule_not_found", 
                        "log_telegram_schedule_not_found", "error")
            elif "schedule" in error_msg.lower():
                if self._log_worker_status:
                    await self._log_worker_status("telegram_schedule_time_error", 
                        "log_telegram_schedule_time_error", "error", error=error_msg)
            
            return None
    
    async def schedule_text_message(self, text: str, target_channel_id: int,
                                  schedule_time: datetime, update_worker_status_callback=None,
                                  disconnect_callback=None) -> Optional[Message]:
        """Schedule text message to target channel (backward compatibility)."""
        return await self.schedule_message(text, target_channel_id, schedule_time, None, 
                                         update_worker_status_callback, disconnect_callback)
