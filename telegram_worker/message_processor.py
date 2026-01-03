"""
Основной процессор сообщений
"""
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Any, Union, Callable
from pyrogram.client import Client
from pyrogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from models import (
    User,
    ChannelPair,
    ScheduledPost,
    WorkerError,
    Model,
    ChannelProcessingState,
)
from db import async_session
from telegram_worker.utils import get_localized_message, smart_truncate_message, format_signature
from telegram_worker.unified_messenger import MessageRole


class MessageProcessor:
    """Основной процессор входящих сообщений"""
    
    def __init__(self, user_id: int, logger, 
                 # Callbacks to other components
                 media_handler, ai_processor, balance_manager, 
                 scheduler, notification_manager,
                 # Callbacks to worker methods
                 resolve_channel_callback, log_worker_status_callback,
                 update_worker_activity_callback, get_message_via_raw_api_callback,
                 log_scheduled_post_callback, log_insufficient_funds_post_callback,
                 log_worker_error_callback, send_websocket_log_callback,
                 update_stats_callback):
        
        self.user_id = user_id
        self.logger = logger
        
        # Component references
        self.media_handler = media_handler
        self.ai_processor = ai_processor
        self.balance_manager = balance_manager
        self.scheduler = scheduler
        self.notification_manager = notification_manager
        
        # Worker method callbacks
        self._resolve_channel_identifier = resolve_channel_callback
        self._log_worker_status = log_worker_status_callback
        self._update_worker_activity = update_worker_activity_callback
        self._get_message_via_raw_api = get_message_via_raw_api_callback
        self._log_scheduled_post = log_scheduled_post_callback
        self._log_insufficient_funds_post = log_insufficient_funds_post_callback
        self._log_worker_error = log_worker_error_callback
        self._send_websocket_log = send_websocket_log_callback
        self._update_stats = update_stats_callback
        
        # AI processing callback
        self._process_with_hyperbolic_callback: Optional[Callable] = None
        
        # Initialize user logger for sending logs directly to user via Telegram bot
        from .user_logger import get_user_logger
        self.user_logger = get_user_logger(user_id)
    
    async def process_message(self, message: Message, channel_pair: ChannelPair, client: Client) -> bool:
        """Process a single message for hybrid processing"""
        try:
            # Processing message
            
            # Process the message using existing process_rule logic
            success = await self.process_rule(channel_pair, message, client)
            
            if success:
                # Update the last processed message ID in the database
                # This ensures the message won't be reprocessed in batch mode
                try:
                    from models import ChannelProcessingState
                    from sqlalchemy import select
                    
                    async with async_session() as session:  # type: ignore
                        result = await session.execute(
                            select(ChannelProcessingState).where(
                                ChannelProcessingState.user_id == self.user_id,
                                ChannelProcessingState.channel_pair_id == channel_pair.id
                            )
                        )
                        state = result.scalar_one_or_none()
                        
                        if state and message.id > state.last_processed_message_id:
                            state.last_processed_message_id = message.id
                            state.updated_at = datetime.now(timezone.utc)
                            await session.commit()
                except Exception as e:
                    self.logger.error(f"Failed to update processing state for message {message.id}: {e}")
                
                # Получаем текст поста для упрощенного сообщения
                post_text = ""
                if hasattr(message, 'text') and message.text:
                    post_text = message.text[:100] + ("..." if len(message.text) > 100 else "")
                elif hasattr(message, 'caption') and message.caption:
                    post_text = message.caption[:100] + ("..." if len(message.caption) > 100 else "")
                
                # Упрощенное сообщение об успешной обработке
                await self._send_websocket_log(
                    "post_processed_success", 
                    f"Пост {message.id} обработан: {post_text}",
                    "info"
                )
                
                # Message processed successfully
                return True
            else:
                # Упрощенное сообщение о неуспешной обработке
                await self._send_websocket_log(
                    "post_processing_failed", 
                    f"Пост {message.id} не обработан: правило не сработало",
                    "warning"
                )
                
                # Message processing failed - rule not triggered
                return False
                
        except Exception:
            return False
    
    async def on_new_message(self, client: Client, message: Message, channel_rules: List[ChannelPair], is_processing: bool):
        """Main handler for new messages."""
        try:
            # Log message reception with details
            channel_info = f"@{message.chat.username}" if message.chat.username else f"ID:{message.chat.id}"
            message_type = "text" if message.text else "media" if message.media else "other"
            
            self.logger.info(f"📨 New message received: {message.id} from {channel_info} (type: {message_type})")
            
            # Update activity
            await self._update_worker_activity()
            
            # Check if processing is enabled
            if not is_processing:
                self.logger.info("⏸️ Message processing is paused - skipping message")
                await messenger.send("paused_status", MessageRole.USER_STATUS)
                return
            
            # Log processing start
            self.logger.info(f"🔄 Starting message processing for {message.id}")
            # Get user language and send localized status
            from .unified_messenger import get_unified_messenger, MessageRole
            messenger = get_unified_messenger(self.user_id)
            await messenger.send("processing_message_status", MessageRole.USER_STATUS,
                               message_id=message.id, channel=channel_info)
            
            # Mark message as processed immediately to prevent reprocessing
            try:
                await self._add_processed_marker_to_message(message)
                self.logger.debug(f"✅ Added processed marker to message {message.id}")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to add processed marker to message {message.id}: {e}")
            
            # Log rules matching
            matching_rules = []
            for rule in channel_rules:
                # Debug logging to see what rules we have and what channel we're matching against
                self.logger.info(f"🔍 Checking rule: {rule.source_channel} vs message channel: {message.chat.id} (@{message.chat.username if hasattr(message.chat, 'username') else 'no_username'})")
                if (hasattr(rule, 'source_channel') and rule.source_channel and
                    (str(rule.source_channel) == str(message.chat.id) or
                     (hasattr(message.chat, 'username') and message.chat.username and
                      str(rule.source_channel) == f"@{message.chat.username}") or
                     (hasattr(message.chat, 'username') and message.chat.username and
                      str(rule.source_channel).lower() == f"@{message.chat.username}".lower()))):
                    matching_rules.append(rule)
            
            if not matching_rules:
                # No rules match - don't send status to avoid noise
                self.logger.info(
                    f"ℹ️ No matching rules found for channel @{message.chat.username if hasattr(message.chat, 'username') and message.chat.username else message.chat.id} (message will be ignored)"
                )
                return
            
            self.logger.info(f"🎯 Found {len(matching_rules)} matching rules for message {message.id}")
            await messenger.send("rules_found_status", MessageRole.USER_STATUS,
                               count=len(matching_rules), message_id=message.id)
            
            # Process message against matching rules
            processed_successfully = False
            for i, rule in enumerate(matching_rules):
                try:
                    self.logger.info(f"📋 Processing rule {i+1}/{len(matching_rules)}: {rule.id} ({rule.source_channel} → {rule.target_channel})")
                    
                    # Send status update about which rule is being processed
                    await messenger.send("applying_rule_status", MessageRole.USER_STATUS,
                                       source=rule.source_channel, target=rule.target_channel)
                    
                    success = await self.process_rule(rule, message, client)
                    if success:
                        processed_successfully = True
                        self.logger.info(f"✅ Rule {rule.id} processed successfully")
                        
                        # NOTE: success report is sent by process_rule() when scheduling succeeds
                        
                        # Update the last processed message ID in the database
                        try:
                            from models import ChannelProcessingState
                            from sqlalchemy import select
                            
                            async with async_session() as session:  # type: ignore
                                result = await session.execute(
                                    select(ChannelProcessingState).where(
                                        ChannelProcessingState.user_id == self.user_id,
                                        ChannelProcessingState.channel_pair_id == rule.id
                                    )
                                )
                                state = result.scalar_one_or_none()
                                
                                if state and message.id > state.last_processed_message_id:
                                    state.last_processed_message_id = message.id
                                    state.updated_at = datetime.now(timezone.utc)
                                    await session.commit()
                                    self.logger.debug(f"📊 Updated processing state for rule {rule.id}")
                        except Exception as e:
                            self.logger.error(f"❌ Failed to update processing state for message {message.id}: {e}")
                        
                        break  # Stop after first successful rule
                    else:
                        self.logger.info(f"⚠️ Rule {rule.id} did not process message {message.id}")
                        # Don't send status for failed rule - just continue to next
                        
                except Exception as e:
                    # Update error statistics
                    self._update_stats('errors_count')
                    
                    self.logger.error(f"❌ Error processing rule {rule.id} for message {message.id}: {e}", exc_info=True)
                    
                    # Send error report to user (permanent)
                    await messenger.send("rule_processing_error_report", MessageRole.USER_REPORT,
                                       report_type="error",
                                       source=rule.source_channel,
                                       target=rule.target_channel,
                                       error=str(e))
                    
                    # Log error in database
                    async with async_session() as session:  # type: ignore
                        await self._log_worker_error(session, rule, message, "rule_processing_error", str(e))
                    continue
            
            # After processing, show waiting status
            if processed_successfully:
                self.logger.info(f"🎉 Message {message.id} processing completed successfully")
                # Success report already sent by process_rule()
            else:
                self.logger.info(f"⚠️ Message {message.id} was not processed by any rule")
            
            # Always show waiting status after processing
            await messenger.send("waiting_for_messages_status", MessageRole.USER_STATUS)

        except Exception as e:
            # Update error statistics
            self._update_stats('errors_count')
            
            self.logger.error(f"💥 Critical error in message handler: {e}", exc_info=True)
            await self._log_worker_status("message_handler_error", f"Critical error: {str(e)}", "error")
            
            # Send critical error report to user (permanent)
            await messenger.send("critical_handler_error", MessageRole.USER_REPORT,
                               report_type="error", error=str(e))
            # Don't re-raise to prevent worker crash, just log and continue
    
    async def process_rule(self, rule: ChannelPair, message: Message, client: Client) -> bool:
        """Process message according to a specific rule."""
        # Update rule execution statistics
        self._update_stats('rules_executed')

        # Initialize messenger for this rule processing
        from .unified_messenger import get_unified_messenger
        messenger = get_unified_messenger(self.user_id)

        self.logger.info(f"🔍 Starting rule processing: {rule.id} ({rule.source_channel} → {rule.target_channel})")

        # Source channel validation
        self.logger.info(f"🔍 Validating source channel for rule {rule.id}")
        
        source_id = await self._resolve_channel_identifier(rule.source_channel)
        if not source_id or message.chat.id != source_id:
            self.logger.info(f"❌ Source channel validation failed for rule {rule.id}")
            return False

        self.logger.debug(f"✅ Source channel validated for rule {rule.id}")

        # Ensure we have not processed this message before (or mark it immediately)
        self.logger.info(f"🔍 Checking if message {message.id} has been processed before for rule {rule.id}")
        
        should_continue = await self._mark_message_attempt(rule, message.id)
        if not should_continue:
            self.logger.info(
                f"⏭️ Skipping message {message.id} for rule {rule.id}: already processed up to this message"
            )
            await self._send_websocket_log(
                "duplicate_message_skipped",
                f"Сообщение {message.id} пропущено: уже было обработано ранее",
                "info",
            )
            return False

        self.logger.debug(f"✅ Message {message.id} marked for processing by rule {rule.id}")

        # Check if balance is negative
        self.logger.info(f"💰 Checking user balance for message processing")
        
        async with async_session() as session:  # type: ignore
            user = await session.get(User, self.user_id)
            if not user:
                self.logger.warning("⚠️ User not found for balance check")
                await self.user_logger.send_report("user_not_found", "error")
                return False
            
            # Only check if balance is negative
            current_balance = user.balance
            self.logger.debug(f"💰 Current balance: {current_balance:.3f}🔋")
            
            if current_balance < 0:
                self.logger.error(f"💸 Negative balance detected: {current_balance:.3f}🔋, stopping worker")
                # Send error report to user (permanent)
                payment_contact = os.getenv("PAYMENT_CONTACT", "@magellanvs")
                user_lang = await self.user_logger._get_user_language()
                report_message = get_localized_message(
                    "negative_balance_report",
                    lang=user_lang,
                    balance=current_balance,
                    contact=payment_contact
                )
                await self.user_logger.send_report(report_message, "error")
                
                # Log as insufficient funds post
                error_message = f"Insufficient funds. For top-up, please contact {payment_contact}\n\nНедостаточно средств. Для пополнения обратитесь к {payment_contact}"
                await self._log_insufficient_funds_post(session, rule, message, error_message)
                
                # Stop worker due to insufficient funds
                await self._log_worker_status("insufficient_funds", "Stopping worker due to insufficient funds", "error")
                await self._send_websocket_log('insufficient_funds', 'Worker stopped due to insufficient funds', 'error')
                
                # Exit the worker process
                os._exit(1)
        
        # Handle media groups (albums)
        if message.media_group_id:
            self.logger.info(f"📸 Processing media group {message.media_group_id} for rule {rule.id}")
            from .unified_messenger import get_unified_messenger
            messenger = get_unified_messenger(self.user_id)
            await messenger.send("processing_album_status", MessageRole.USER_STATUS,
                               album_id=message.media_group_id)
            result = await self.media_handler.handle_media_group(message, rule)
            if result:
                self.logger.info(f"✅ Media group {message.media_group_id} processed successfully")
            else:
                self.logger.warning(f"⚠️ Media group {message.media_group_id} processing failed")
            return result
        
        # Process text content
        self.logger.info(f"📝 Processing text content for message {message.id}")
        await messenger.send("processing_text", MessageRole.USER_STATUS)
        
        try:
            processed_text, has_ai_error = await self.process_text_content(rule, message, client)
            if processed_text == "UNSUPPORTED_FORMAT":
                self.logger.warning(f"⚠️ Message {message.id} has unsupported format, skipping")
                return False

            self.logger.info(f"✅ Text content processed successfully for message {message.id}")

            if has_ai_error:
                self.logger.warning(f"⚠️ AI processing had errors for message {message.id}")
                # AI error report is sent by process_text_content

        except Exception as e:
            self.logger.error(f"❌ Failed to process text content for message {message.id}: {e}")
            await messenger.send("text_processing_error", MessageRole.USER_REPORT,
                                report_type="error", error=str(e))
            return False

        # Prepare signature
        signature = format_signature(rule.caption_text, rule.caption_url)
        
        # Get target channel
        self.logger.debug(f"🎯 Resolving target channel: {rule.target_channel}")
        
        target_channel_id = await self._resolve_channel_identifier(rule.target_channel)
        if not target_channel_id:
            self.logger.error(f"❌ Could not resolve target channel: {rule.target_channel}")
            await messenger.send("target_channel_not_found", MessageRole.USER_REPORT,
                               report_type="error", channel=rule.target_channel)
            return False
        
        self.logger.debug(f"✅ Target channel resolved: {target_channel_id}")

        # Calculate schedule time
        self.logger.debug(f"⏰ Calculating schedule time for rule {rule.id}")
        await messenger.send("calculating_schedule", MessageRole.USER_STATUS)
        
        try:
            scheduled_time = await self.scheduler.determine_schedule_time(rule, target_channel_id)
            self.logger.info(f"⏰ Scheduled time calculated: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            self.logger.error(f"❌ Failed to calculate schedule time: {e}")
            await messenger.send("schedule_calculation_error", MessageRole.USER_REPORT,
                               report_type="error", error=str(e))
            return False
        
        # Schedule the message
        self.logger.info(f"📅 Scheduling message for {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
        await messenger.send("scheduling_message_status", MessageRole.USER_STATUS,
                           time=scheduled_time.strftime('%H:%M'))
        
        try:
            scheduled_msg = await self.scheduler.schedule_message(
                processed_text, target_channel_id, scheduled_time, message, signature=signature
            )
            
            if scheduled_msg:
                self.logger.info(f"✅ Message scheduled successfully with ID: {scheduled_msg.id}")
                
                balance_deducted = 0
                balance_after = 0
                async with async_session() as session:  # type: ignore
                    # Получаем баланс до списания
                    user_before = await session.get(User, self.user_id)
                    balance_before = user_before.balance if user_before else 0
                    
                    self.logger.debug(f"💰 Balance before deduction: {balance_before:.3f}🔋")
                    
                    # Списываем баланс только после успешного планирования
                    await self.balance_manager.deduct_balance(session, self.user_id, rule.model_id)
                    
                    # Получаем баланс после списания
                    user_after = await session.get(User, self.user_id)
                    balance_after = user_after.balance if user_after else 0
                    
                    # Вычисляем сколько списано
                    balance_deducted = balance_before - balance_after
                    
                    await self._log_scheduled_post(
                        session, rule.id, message, target_channel_id,
                        scheduled_msg, scheduled_time, processed_text, balance_after
                    )
                
                self.logger.info(get_localized_message("message_scheduled",
                    schedule_time=scheduled_time.strftime('%Y-%m-%d %H:%M:%S')))
                
                # === SEND SUCCESS REPORT (PERMANENT) ===
                # Get user language and format the report with full post text, time, and balance
                user_lang = await self.user_logger._get_user_language()
                
                # grace: Convert Markdown to HTML for proper formatting in bot report
                from uni_text_processor.text_formatting import markdown_to_telegram_html
                formatted_post_text = markdown_to_telegram_html(processed_text)
                
                report_message = get_localized_message(
                    "success_report",
                    lang=user_lang,
                    time=scheduled_time.strftime('%Y-%m-%d %H:%M:%S'),
                    text=formatted_post_text,  # Use HTML-formatted text
                    deducted=balance_deducted,
                    balance=balance_after
                )
                await self.user_logger.send_report(report_message, "success")
                
                # Log to dashboard via WebSocket
                if self._log_worker_status:
                    log_params = {
                        "id": scheduled_msg.id,
                        "time": scheduled_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "output_text": processed_text
                    }
                    
                    await self._log_worker_status("telegram_schedule_success",
                        "log_telegram_schedule_success", "success", **log_params)
                    
                    # Send insufficient balance notification if balance went negative
                    if user_after and balance_after < 0:
                        self.logger.warning(f"⚠️ Balance went negative after deduction: {balance_after:.3f}")
                        payment_contact = os.getenv("PAYMENT_CONTACT", "@magellanvs")
                        user_lang = await self.user_logger._get_user_language()
                        notification_message = get_localized_message(
                            "insufficient_funds_future",
                            lang=user_lang,
                            contact=payment_contact
                        )
                        await self.balance_manager.send_insufficient_balance_notification(
                            client, rule, target_channel_id, notification_message,
                            self.scheduler.determine_schedule_time
                        )
                
                self.logger.info(f"🎉 Rule {rule.id} processing completed successfully")
                return True
            else:
                self.logger.error(f"❌ Failed to schedule message for rule {rule.id}")
                # Get detailed error from scheduler if available
                detailed_error = getattr(self.scheduler, 'last_error_message', None)
                await messenger.send("scheduling_failed", MessageRole.USER_REPORT,
                                   report_type="error", detailed_error=detailed_error)
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to schedule message for rule {rule.id}: {e}", exc_info=True)
            # Get detailed error from scheduler if available
            detailed_error = getattr(self.scheduler, 'last_error_message', None)
            await messenger.send("scheduling_error", MessageRole.USER_REPORT,
                               report_type="error", error=str(e), detailed_error=detailed_error)
            return False
    
    async def process_text_content(self, rule: ChannelPair, message: Message, client: Client) -> tuple[str, bool]:
        """Apply text deletions and AI processing to message content."""
        # Get text content
        text = message.text or message.caption or ""
        
        # If no text, try to get via raw API
        if not text and message.text is None and message.caption is None:
            try:
                text = await self._get_message_via_raw_api(message)
            except Exception as e:
                self.logger.error(f"Failed to get message via raw API: {e}")
        
        # Check for unsupported content
        if not text and (message.sticker or message.voice or message.video_note):
            return "UNSUPPORTED_FORMAT", False

        # If still no text, create default based on media type
        if not text:
            if message.photo:
                text = "📸 Фотография"
            elif message.video:
                text = "🎥 Видео"
            elif message.document:
                text = "📄 Документ"
            elif message.audio:
                text = "🎵 Аудио"
            elif message.animation:
                text = "🎬 GIF анимация"
            else:
                text = "📎 Медиа файл"
        
        # Apply text deletions
        if rule.text_to_delete is not None and rule.text_to_delete.strip():
            original_length = len(text)
            for pattern in [p.strip() for p in rule.text_to_delete.split(',') if p.strip()]:
                text = text.replace(pattern, "")
            text = text.strip()
            self.logger.info(f"After deletions: {original_length} -> {len(text)} chars")
        
        # Apply AI processing if configured
        if rule.model_id is not None and text.strip():
            try:
                # Safely access model attributes with fallback to database query
                # First try to access the model relationship directly
                model_system_content = None
                model_name = None
                model_temperature = 0.1
                model_top_p = 0.9
                model_max_tokens = 500
                
                # Try to access model attributes directly (if loaded)
                # Use hasattr to safely check if model relationship is accessible
                if hasattr(rule, 'model') and rule.model is not None:
                    try:
                        model_system_content = rule.model.system_content
                        model_name = rule.model.model
                        model_temperature = rule.model.temperature or 0.1
                        model_top_p = rule.model.top_p or 0.9
                        model_max_tokens = rule.model.max_tokens or 500
                    except Exception as e:
                        self.logger.warning(f"Could not access model attributes directly: {e}")
                
                # If we couldn't access model attributes, fetch from database
                if model_system_content is None or model_name is None:
                    self.logger.info("Falling back to database query for model data")
                    async with async_session() as db_session:  # type: ignore
                        stmt = select(Model).where(Model.id == rule.model_id)
                        result = await db_session.execute(stmt)
                        model = result.scalar_one_or_none()
                        
                        if model:
                            model_system_content = model.system_content
                            model_name = model.model
                            model_temperature = model.temperature or 0.1
                            model_top_p = model.top_p or 0.9
                            model_max_tokens = model.max_tokens or 500
                        else:
                            self.logger.warning(f"Model with ID {rule.model_id} not found in database")
                            user_lang = await self.user_logger._get_user_language()
                            error_message = get_localized_message(
                                "ai_model_not_found",
                                lang=user_lang,
                                model_id=rule.model_id
                            )
                            await self.user_logger.send_report(error_message, "warning")
                            return text, False
                
                # Use rule-specific values or fall back to model defaults
                system_prompt = rule.system_content if rule.system_content is not None else model_system_content
                temperature = rule.temperature if rule.temperature is not None else model_temperature
                top_p = rule.top_p if rule.top_p is not None else model_top_p
                max_tokens = rule.max_tokens if rule.max_tokens is not None else model_max_tokens
                
                # Use AI processor through callback
                if self._process_with_hyperbolic_callback:
                    result = await self._process_with_hyperbolic_callback(
                        system_content=system_prompt,
                        user_content=text,
                        model_name=model_name,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens
                    )
                    
                    # Check if result is processed text or an error message
                    if result and isinstance(result, str):
                        # Check if this looks like an error message from our AI processor
                        is_error_message = (
                            result.startswith(('TimeoutError:', 'ClientError:', 'Exception:', 'API Error')) or
                            ': Request took' in result or
                            result.startswith(('ConnectionError', 'ConnectError', 'ServerDisconnectedError')) or
                            'API error' in result or
                            'API request failed' in result or
                            'API client error' in result or
                            '[ConnectError]:' in result
                        )
                        
                        if is_error_message:
                            # This is an error message from the AI processor
                            self.logger.warning(f"AI processing failed with detailed error: {result}")
                            user_lang = await self.user_logger._get_user_language()
                            error_message = get_localized_message(
                                "ai_error_detailed",
                                lang=user_lang,
                                error=result[:200]
                            )
                            await self.user_logger.send_report(error_message, "error")
                            return text, True
                        else:
                            # Successful processed text
                            processed_text = result
                            self.logger.info(f"AI processing successful: {len(processed_text)} chars output")
                            return processed_text, False
                    elif result:
                        # Non-string result
                        processed_text = str(result)
                        self.logger.info(f"AI processing successful: {len(processed_text)} chars output")
                        return processed_text, False
                    else:
                        # Empty result or None
                        self.logger.warning("AI processing failed, using original text")
                        await messenger.send("ai_error_empty", MessageRole.USER_REPORT, report_type="warning")
                        return text, True
                else:
                    # AI processing not available
                    self.logger.info("AI processing callback not available")
                    return text, False
            except Exception as e:
                self.logger.error(f"Failed to process text content with AI: {e}", exc_info=True)
                error_message = str(e)[:200]
                user_lang = await self.user_logger._get_user_language()
                localized_error = get_localized_message(
                    "ai_error_detailed",
                    lang=user_lang,
                    error=error_message
                )
                await self.user_logger.send_report(localized_error, "error")
                return text, False
        
        return text, False

    async def _add_processed_marker_to_message(self, message: Message):
        """Add processed marker to message to prevent reprocessing"""
        # Disabled - no longer adding green checkmarks to posts
        pass

    async def _mark_message_attempt(self, rule: ChannelPair, message_id: int) -> bool:
        """Record the message ID in the database before processing to avoid duplicates."""
        for attempt in range(2):
            async with async_session() as session:  # type: ignore
                try:
                    stmt = select(ChannelProcessingState).where(
                        ChannelProcessingState.user_id == self.user_id,
                        ChannelProcessingState.channel_pair_id == rule.id,
                    )
                    result = await session.execute(stmt)
                    state = result.scalar_one_or_none()

                    if state:
                        if message_id <= state.last_processed_message_id:
                            return False
                        state.last_processed_message_id = message_id
                        state.updated_at = datetime.utcnow()
                    else:
                        state = ChannelProcessingState(
                            user_id=self.user_id,
                            channel_pair_id=rule.id,
                            last_processed_message_id=message_id,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(state)

                    await session.commit()
                    return True
                except IntegrityError:
                    await session.rollback()
                    if attempt == 0:
                        continue
                    self.logger.warning(
                        f"Integrity error while recording message {message_id} for rule {rule.id}; skipping duplicate check"
                    )
                    return True
                except Exception as e:
                    await session.rollback()
                    self.logger.error(
                        f"Failed to record processing attempt for message {message_id} and rule {rule.id}: {e}"
                    )
                    return True  # Fallback to avoid blocking processing if DB logging fails
        return True
