"""
Гибридный процессор для обработки накопленных и новых постов
"""
import asyncio
import os
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .worker import TelegramWorker

from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pyrogram.errors import FloodWait, PeerIdInvalid
from pyrogram.types import Message
from pyrogram.raw.functions.messages.get_scheduled_history import GetScheduledHistory
from pyrogram.raw.types.input_peer_channel import InputPeerChannel

from db import async_session
from models import ChannelProcessingState, ChannelPair
from .utils import get_localized_message
from .unified_messenger import MessageRole
from sqlalchemy import func
from models import ScheduledPost


class ProcessingState(Enum):
    STARTING = "starting"
    BATCH_PROCESSING = "batch_processing"
    LISTENING = "listening"
    STOPPING = "stopping"
    ERROR = "error"


class HybridProcessor:
    """Класс для гибридной обработки постов"""
    
    def __init__(self, worker: 'TelegramWorker'):
        self.worker = worker
        self.state = ProcessingState.STARTING
        
        # Настройки из .env
        self.batch_processing_enabled = os.getenv("BATCH_PROCESSING_ENABLED", "true").lower() == "true"
        self.batch_interval = int(os.getenv("BATCH_PROCESSING_INTERVAL", "1"))
        self.flood_wait_multiplier = float(os.getenv("FLOOD_WAIT_MULTIPLIER", "1.5"))
        self.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "100"))
        self.rule_switch_delay = int(os.getenv("RULE_SWITCH_DELAY", "0"))
        
        # Статистика
        self.total_processed = 0
        self.current_rule = 0
        self.total_rules = 0
    
    async def verify_client_readiness(self) -> bool:
        """Проверка готовности клиента"""
        try:
            if self.worker is not None:
                result = self.worker.is_connected()
                return bool(result) if result is not None else False
            return False
        except Exception:
            return False

    async def verify_channel_specific_readiness(self, channel_id: str) -> bool:
        """Проверка готовности для работы с каналом - оптимизированная версия"""
        try:
            if not self.worker.is_connected():
                return False

            # Быстрая проверка: если это username, сразу пробуем get_chat
            if channel_id.startswith('@'):
                try:
                    chat = await self.worker.client.get_chat(channel_id)
                    chat_id = getattr(chat, 'id', None)
                    if chat_id is not None:
                        await self.worker.messenger.send(
                            "channel_accessible_direct",
                            MessageRole.INTERNAL_LOG,
                            level="success",
                            channel_id=channel_id,
                            chat_id=chat_id
                        )
                        return True
                except Exception as e:
                    # Если не удалось, пробуем resolve
                    pass

            # Для числовых ID используем resolve
            try:
                resolved_id = await self.worker._resolve_channel_identifier(channel_id)
                if resolved_id:
                    # Пробуем получить chat чтобы убедиться что доступен
                    chat = await self.worker.client.get_chat(resolved_id)
                    await self.worker.messenger.send(
                        "channel_accessible_resolved",
                        MessageRole.INTERNAL_LOG,
                        level="success",
                        channel_id=channel_id,
                        resolved_id=resolved_id
                    )
                    return True
            except Exception as e:
                await self.worker.messenger.send(
                    "channel_access_failed",
                    MessageRole.WEBSOCKET_LOG,
                    level="error",
                    channel=channel_id,
                    error=str(e)
                )

            return False

        except Exception as e:
            await self.worker.messenger.send(
                "channel_verification_error",
                MessageRole.WEBSOCKET_LOG,
                level="error",
                channel=channel_id,
                error=str(e)
            )
            return False

    async def start_hybrid_processing(self, process_old_messages: bool = False, listen_for_new_messages: bool = True):
        """Запуск гибридной обработки"""
        try:
            # Единая проверка готовности клиента
            if not await self.verify_client_readiness():
                await self.worker.messenger.send("client_not_ready", MessageRole.INTERNAL_LOG, level="error")
                raise ConnectionError("Client not ready for processing")
            
            if not self.batch_processing_enabled:
                await self.worker.messenger.send("batch_disabled", MessageRole.INTERNAL_LOG, level="info")
                if listen_for_new_messages:
                    await self.start_listening_mode()
                else:
                    await self.worker.messenger.send("listening_skipped", MessageRole.INTERNAL_LOG, level="info")
                return
            
            # Этап 1: Пакетная обработка накопленных постов
            self.state = ProcessingState.BATCH_PROCESSING
            await self.worker.messenger.send("batch_start", MessageRole.INTERNAL_LOG, level="info")
            
            processed_count = await self.process_accumulated_posts(process_old_messages=process_old_messages)
            
            await self.worker.messenger.send("batch_complete", MessageRole.INTERNAL_LOG, level="success", processed=processed_count)
            
            # Store batch processing results for combined report in start_listening
            self._batch_processed_count = processed_count
            self._batch_rules_count = self.total_rules

            # Этап 2: Переход к прослушиванию новых
            if listen_for_new_messages:
                await self.worker.messenger.send("switching_to_listening", MessageRole.USER_STATUS)
                await self.start_listening_mode()
            else:
                await self.worker.messenger.send("listening_skipped", MessageRole.INTERNAL_LOG, level="info")
                # Don't send "listening mode skipped" status for VIP3 users
                vip_level = getattr(self.worker, 'vip_level', 0)
                if vip_level != 3:
                    await self.worker.messenger.send("listening_skipped_status", MessageRole.USER_STATUS)

        except Exception as e:
            self.state = ProcessingState.ERROR
            await self.worker.messenger.send("hybrid_error", MessageRole.INTERNAL_LOG, level="error", error=str(e))
            raise
    
    async def process_accumulated_posts(self, process_old_messages: bool = False):
        """Обработка накопленных постов по всем правилам"""
        channel_pairs = await self.worker.get_channel_pairs()
        
        if not channel_pairs:
            await self.worker.messenger.send("no_rules", MessageRole.INTERNAL_LOG, level="info")
            return 0
        
        self.total_rules = len(channel_pairs)
        total_posts = 0
        
        await self.worker.messenger.send("processing_rules", MessageRole.INTERNAL_LOG, level="info", rules_count=len(channel_pairs))

        # Предварительный прогрев клиента (один раз для всех каналов)
        self.worker.logger.info("🔄 Pre-warming client for all channels...")
        await self.worker._warm_up_client(limit=10)
        self.worker.logger.info("✅ Client pre-warmed")

        for i, channel_pair in enumerate(channel_pairs):
            self.current_rule = i + 1
            
            try:
                # Send status about which rule is being processed
                await self.worker.messenger.send("rule_processing_status", MessageRole.USER_STATUS,
                                               index=i+1,
                                               total=len(channel_pairs),
                                               source=channel_pair.source_channel,
                                               target=channel_pair.target_channel)
                
                posts_count = await self.process_channel_batch(channel_pair, process_old_messages=process_old_messages)
                total_posts += posts_count
                
                if posts_count > 0:
                    await self.worker.messenger.send("rule_processed", MessageRole.INTERNAL_LOG, level="success", rule_index=i+1, posts_count=posts_count)
                    # Reports for individual rules are sent by message_processor when scheduling
                else:
                    await self.worker.messenger.send("rule_no_posts", MessageRole.INTERNAL_LOG, level="info", rule_index=i+1)
                    # No need for permanent report when no posts found
                    
            except Exception as e:
                await self.worker.messenger.send("rule_error", MessageRole.INTERNAL_LOG, level="error", rule_index=i+1, error=str(e))
                # Send error report (permanent)
                await self.worker.messenger.send("rule_error_report", MessageRole.USER_REPORT,
                                               report_type="error",
                                               index=i+1,
                                               source=channel_pair.source_channel,
                                               error=str(e))
                continue
        
        self.total_processed = total_posts

        # VIP3 scheduled posts report after batch processing
        vip_level = getattr(self.worker, 'vip_level', 0)
        if vip_level == 3:
            self.worker.logger.info("🔍 [VIP3_REPORT] Calling check_and_report_scheduled_posts after batch processing for VIP3 user")
            await self.check_and_report_scheduled_posts()
        else:
            self.worker.logger.debug(f"🔍 [VIP3_REPORT] Skipping scheduled posts check for non-VIP3 user (VIP level: {vip_level})")

        return total_posts
    
    async def process_channel_batch(self, channel_pair: ChannelPair, process_old_messages: bool = False) -> int:
        """Обработка накопленных постов для одного правила"""
        try:
            if not self.worker.is_connected():
                await self.worker.messenger.send("client_not_connected", MessageRole.INTERNAL_LOG, level="error", rule_id=channel_pair.id)
                await self.worker.user_logger.send_report(self.worker._get_localized_message("client_disconnected", rule_id=channel_pair.id), "error")
                return 0

            # Extract values to avoid type issues
            channel_pair_id = int(str(channel_pair.id))
            source_channel = str(channel_pair.source_channel)

            # DIAGNOSTIC: Log batch processing start
            self.worker.logger.info(f"📊 [BATCH_DIAGNOSTIC] Starting batch processing for rule {channel_pair_id}: {source_channel} → {channel_pair.target_channel}")

            # Send status about which channel is being processed
            await self.worker.messenger.send("processing_channel_status", MessageRole.USER_STATUS,
                                           channel=source_channel)

            # Проверяем доступность канала
            try:
                if not await self.verify_channel_specific_readiness(source_channel):
                    await self.worker.messenger.send("channel_not_ready", MessageRole.INTERNAL_LOG, level="warning", channel=source_channel)
                    # Don't send report for inaccessible channels - just status
                    return 0
            except Exception as e:
                await self.worker.messenger.send("channel_access_error", MessageRole.INTERNAL_LOG, level="error", channel=source_channel, error=str(e))
                await self.worker.user_logger.send_report(get_localized_message("channel_access_denied", channel=source_channel, error=str(e)), "error")
                return 0

            processing_state = await self.get_processing_state(
                self.worker.user_id,
                channel_pair_id,
                process_old_messages=process_old_messages
            )

            last_processed_id = int(str(processing_state.last_processed_message_id))

            try:
                new_messages = await self.get_messages_after_id(
                    source_channel,
                    last_processed_id,
                    limit=self.max_batch_size
                )

                if not new_messages:
                    await self.worker.messenger.send("no_new_messages", MessageRole.INTERNAL_LOG, level="info", channel=source_channel, last_id=last_processed_id)
                    # No report needed for empty results
                    return 0

                # DIAGNOSTIC: Log messages found
                self.worker.logger.info(f"📊 [BATCH_DIAGNOSTIC] Found {len(new_messages)} messages for processing in {source_channel}")

                await self.worker.messenger.send("found_new_messages", MessageRole.INTERNAL_LOG, level="info", messages_count=len(new_messages), channel=source_channel)
                await self.worker.messenger.send("found_messages_status", MessageRole.USER_STATUS,
                                               count=len(new_messages), channel=source_channel)

            except Exception as e:
                await self.worker.messenger.send("get_messages_error", MessageRole.INTERNAL_LOG, level="error", channel=source_channel, error=str(e))
                await self.worker.user_logger.send_report(get_localized_message("channel_read_error", channel=source_channel, error=str(e)), "error")
                return 0
            
            media_groups = {}
            single_messages = []
            
            # Separate media groups and single messages
            for message in new_messages:
                if message.media_group_id:
                    if message.media_group_id not in media_groups:
                        media_groups[message.media_group_id] = []
                    media_groups[message.media_group_id].append(message)
                else:
                    single_messages.append(message)
            
            processed_count = 0
            
            # Process media groups
            for media_group_id, album_messages in media_groups.items():
                try:
                    album_messages.sort(key=lambda m: m.id)

                    highest_message_id = int(str(album_messages[-1].id)) if album_messages else 0
                    if highest_message_id == 0:
                        continue

                    async with async_session() as session:  # type: ignore
                        stmt = select(ChannelPair).options(selectinload(ChannelPair.model)).where(ChannelPair.id == channel_pair_id)
                        result = await session.execute(stmt)
                        fresh_channel_pair = result.scalar_one_or_none()
                        
                        if not fresh_channel_pair:
                            continue

                    album_messages.sort(key=lambda m: m.id)
                    for message in album_messages:
                        should_process = await self.worker.message_processor._mark_message_attempt(
                            fresh_channel_pair,
                            message.id
                        )

                        if not should_process:
                            # Skip logging for duplicate albums - not a real error
                            # Just break and move to next album
                            pass
                    else:
                        # All messages passed duplicate check, process the album
                        await self.worker.messenger.send("processing_album_status", MessageRole.USER_STATUS,
                                                       album_id=media_group_id)
                        await self.worker.media_handler._process_media_group(album_messages, fresh_channel_pair)
                        for message in album_messages:
                            await self.add_processed_marker(message)
                    processed_count += len(album_messages)
                    
                except Exception as e:
                    await self.worker.messenger.send("album_processing_error", MessageRole.INTERNAL_LOG, level="error", album_id=media_group_id, error=str(e))
                    await self.worker.user_logger.send_report(get_localized_message("album_error", album_id=media_group_id, error=str(e)), "error")
                    continue
            
            # Process single messages
            for i, message in enumerate(single_messages):
                try:
                    await self.add_processed_marker(message)

                    # DIAGNOSTIC: Log individual message processing
                    self.worker.logger.info(f"📊 [BATCH_DIAGNOSTIC] Processing message {i+1}/{len(single_messages)} (ID: {message.id})")

                    # Send status about which message is being processed
                    await self.worker.messenger.send("processing_message_status", MessageRole.USER_STATUS,
                                                   index=i+1,
                                                   total=len(single_messages),
                                                   message_id=message.id)

                    success = await self.worker.process_single_message(message, channel_pair)

                    if success:
                        processed_count += 1
                        # DIAGNOSTIC: Log successful processing
                        self.worker.logger.info(f"📊 [BATCH_DIAGNOSTIC] Successfully processed message {message.id}")
                    else:
                        # DIAGNOSTIC: Log failed processing
                        self.worker.logger.warning(f"📊 [BATCH_DIAGNOSTIC] Failed to process message {message.id}")

                except Exception as e:
                    await self.worker.messenger.send("message_processing_error", MessageRole.INTERNAL_LOG, level="error", message_id=message.id, error=str(e))
                    # DIAGNOSTIC: Log exception during processing
                    self.worker.logger.error(f"📊 [BATCH_DIAGNOSTIC] Exception processing message {message.id}: {str(e)}")
                    # Reports for individual message errors are sent by message_processor
                    continue
            
            # Show waiting status after processing channel
            await self.worker.messenger.send("waiting_for_messages_status", MessageRole.USER_STATUS)
            
            return processed_count
            
        except Exception as e:
            await self.worker.messenger.send("batch_processing_error", MessageRole.INTERNAL_LOG, level="error", error=str(e))
            await self.worker.user_logger.send_report(self.worker._get_localized_message("batch_processing_error", error=str(e)), "error")
            return 0

    async def is_channel_accessible(self, channel_id: str) -> bool:
        """Безопасная проверка доступности канала без вызова get_chat"""
        try:
            if not self.worker.is_connected():
                return False
            
            if channel_id.startswith('@'):
                if len(channel_id) < 2:
                    return False
                return True
            else:
                try:
                    channel_num = int(channel_id)
                    if channel_num >= 0:
                        return False
                except ValueError:
                    return False
            
            return True
            
        except Exception as e:
            return False

    async def get_messages_after_id(self, channel_id: str, after_id: int, limit: int = 100) -> List[Message]:
        """Получение сообщений после определенного ID"""
        try:
            if not self.worker.is_connected():
                return []

            resolved_channel_id = await self.worker._resolve_channel_identifier(channel_id)
            if not resolved_channel_id:
                return []
            
            await self.worker._warm_up_client(limit=5)
            
            try:
                await self.worker.client.resolve_peer(resolved_channel_id)
            except FloodWait as e:
                wait_seconds = int(getattr(e, "value", getattr(e, "x", 1)))
                await self.worker.handle_flood_wait(wait_seconds, f"resolving peer {channel_id}")
                await self.worker.client.resolve_peer(resolved_channel_id)
            except Exception:
                try:
                    dialogs = self.worker.client.get_dialogs(limit=10)
                    async for dialog in dialogs:  # type: ignore
                        pass
                    await self.worker.client.resolve_peer(resolved_channel_id)
                except FloodWait as e:
                    wait_seconds = int(getattr(e, "value", getattr(e, "x", 1)))
                    await self.worker.handle_flood_wait(wait_seconds, f"resolving peer {channel_id} after warmup")
                    await self.worker.client.resolve_peer(resolved_channel_id)
                except Exception:
                    return []
                    
            original_identifier = channel_id if (isinstance(channel_id, str) and channel_id.startswith('@')) else resolved_channel_id
            
            chat_id_for_history = resolved_channel_id
            try:
                chat = await self.worker.client.get_chat(original_identifier)
                chat_id_for_history = getattr(chat, 'id', resolved_channel_id)
            except Exception:
                pass
            
            messages = []
            history = self.worker.client.get_chat_history(
            # Не критично, если не удалось добавить метку
            # Основной источник истины - БД
                chat_id_for_history,
                limit=limit * 2
            )
            async for message in history:  # type: ignore
                if message.id <= after_id:
                    break
                
                if message.text or (message.media and message.caption):
                    messages.append(message)
                
                if len(messages) >= limit:
                    break
            
            messages.sort(key=lambda x: x.id)
            return messages
                
        except FloodWait as e:
            wait_seconds = int(getattr(e, "value", getattr(e, "x", 1)))
            await self.worker.handle_flood_wait(wait_seconds, f"fetching messages from {channel_id}")
            return await self.get_messages_after_id(channel_id, after_id, limit)
        except (PeerIdInvalid, Exception):
            return []

    async def _get_latest_message_id(self, channel_id: str) -> int:
        """Получение ID последнего сообщения в канале"""
        try:
            if not self.worker.is_connected():
                return 0
            
            resolved_channel_id = await self.worker._resolve_channel_identifier(channel_id)
            if not resolved_channel_id:
                return 0
            
            history = self.worker.client.get_chat_history(resolved_channel_id, limit=1)
            async for message in history:  # type: ignore
                return message.id
            
            return 0
        except Exception:
            return 0

    async def _warm_up_client(self, limit: int = 10) -> bool:
        """Прогревает клиент"""
        try:
            count = 0
            dialogs = self.worker.client.get_dialogs(limit=limit)
            async for dialog in dialogs:  # type: ignore
                count += 1
                if count >= limit:
                    break
            return True
        except Exception:
            return False
    
    async def add_processed_marker(self, message: Message):
        """Добавление зеленой галочки в начало текста обработанного поста"""
        # Disabled - no longer adding green checkmarks to posts
        pass

    async def get_processing_state(self, user_id: int, channel_pair_id: int, process_old_messages: bool = False) -> ChannelProcessingState:
        """Получение состояния обработки для правила"""
        async with async_session() as session:  # type: ignore
            result = await session.execute(
                select(ChannelProcessingState).where(
                    ChannelProcessingState.user_id == user_id,
                    ChannelProcessingState.channel_pair_id == channel_pair_id
                )
            )
            state = result.scalar_one_or_none()
            
            if not state:
                # Для нового правила определяем стартовую позицию
                try:
                    # Получаем channel_pair для определения source_channel
                    from models import ChannelPair
                    channel_pair_result = await session.execute(
                        select(ChannelPair).where(ChannelPair.id == channel_pair_id)
                    )
                    channel_pair = channel_pair_result.scalar_one_or_none()
                    
                    if channel_pair:
                        source_channel = str(channel_pair.source_channel)
                        if process_old_messages:
                            # Если нужно обработать старые сообщения, начинаем с позиции
                            # которая ограничит обработку последними 50 сообщениями
                            latest_message_id = await self._get_latest_message_id(source_channel)
                            # Начинаем с ID, который даст нам максимум 50 последних сообщений
                            last_message_id = max(0, latest_message_id - 50)
                        else:
                            # Для обычного режима начинаем с последнего сообщения
                            last_message_id = await self._get_latest_message_id(source_channel)
                    else:
                        last_message_id = 0
                except Exception:
                    last_message_id = 0
                
                # Создаем новое состояние
                state = ChannelProcessingState(
                    user_id=user_id,
                    channel_pair_id=channel_pair_id,
                    last_processed_message_id=last_message_id
                )
                session.add(state)
                await session.commit()
                await session.refresh(state)
            
            return state

    async def update_last_processed_id(self, user_id: int, channel_pair_id: int, message_id: int):
        """Обновление ID последнего обработанного сообщения"""
        async with async_session() as session:  # type: ignore
            result = await session.execute(
                select(ChannelProcessingState).where(
                    ChannelProcessingState.user_id == user_id,
                    ChannelProcessingState.channel_pair_id == channel_pair_id
                )
            )
            state = result.scalar_one_or_none()
            
            if state:
                state.last_processed_message_id = message_id
                state.updated_at = datetime.utcnow()
                await session.commit()
    
    async def start_listening_mode(self):
        """Переход в режим прослушивания новых сообщений"""
        self.state = ProcessingState.LISTENING
        
        await self.worker.messenger.send("starting_listening_status", MessageRole.USER_STATUS)
        
        if not self.worker.is_connected():
            await self.worker.messenger.send("client_not_ready_listening", MessageRole.USER_REPORT, report_type="error")
            raise ConnectionError("Telegram client not ready for listening")
        
        # start_listening will send the "ready" report and "waiting" status
        await self.worker.start_listening()

    async def check_and_report_scheduled_posts(self):
        """Проверить и отправить отчет о запланированных постах для VIP3"""
        try:
            self.worker.logger.info("🔍 [VIP3_REPORT] Starting scheduled posts check")

            # Получаем все правила обработки для пользователя
            channel_pairs = await self.worker.get_channel_pairs()

            if not channel_pairs:
                self.worker.logger.info("🔍 [VIP3_REPORT] No channel pairs found")
                await self.worker.messenger.send(
                    "vip3_no_scheduled_posts",
                    MessageRole.USER_REPORT
                )
                return

            self.worker.logger.info(f"🔍 [VIP3_REPORT] Found {len(channel_pairs)} channel pairs")

            # Словарь для хранения результатов: {channel_name: count}
            scheduled_posts_info = {}

            # Проверяем каждый канал-чистовик
            for channel_pair in channel_pairs:
                try:
                    self.worker.logger.debug(f"🔍 [VIP3_REPORT] Checking channel pair {channel_pair.id}: {channel_pair.target_channel}")

                    # Получаем количество запланированных постов для этого правила
                    count = await self._get_scheduled_posts_count(channel_pair.id)

                    # Получаем реальное название канала
                    channel_name = await self._get_channel_name(channel_pair.target_channel)
                    self.worker.logger.info(f"🔍 [VIP3_REPORT] Channel {channel_pair.target_channel} -> '{channel_name}', count: {count}")
                    
                    # Включаем ВСЕ каналы в отчет (даже с 0 постов)
                    scheduled_posts_info[channel_name] = count

                except Exception as e:
                    self.worker.logger.error(f"❌ [VIP3_REPORT] Error checking scheduled posts for {channel_pair.target_channel}: {e}")
                    continue

            # Формируем отчет
            if scheduled_posts_info:
                self.worker.logger.info(f"🔍 [VIP3_REPORT] Found scheduled posts info for {len(scheduled_posts_info)} channels")

                # Сортируем по количеству постов (по возрастанию)
                sorted_channels = sorted(
                    scheduled_posts_info.items(),
                    key=lambda x: x[1],
                    reverse=False
                )

                # Проверяем наличие каналов с малым количеством запланированных постов
                alarm_threshold = int(os.getenv("REMAINING_POSTS_ALARM", "5"))
                has_low_posts = any(count < alarm_threshold for _, count in sorted_channels)
                
                # Формируем текст отчета
                report_lines = []
                for channel_name, count in sorted_channels:
                    report_lines.append(
                        get_localized_message(
                            "vip3_scheduled_posts_item",
                            lang=await self.worker.messenger._get_user_language(),
                            channel_name=channel_name,
                            count=count
                        )
                    )

                # Добавляем заголовок
                header = get_localized_message(
                    "vip3_scheduled_posts_header",
                    lang=await self.worker.messenger._get_user_language()
                )
                
                # Добавляем красный alarm-эмодзи в начало, если есть каналы с малым количеством постов
                if has_low_posts:
                    header = f"🚨 {header}"

                report_text = f"{header}\n" + "\n".join(report_lines)

                self.worker.logger.info("📤 [VIP3_REPORT] Sending scheduled posts report")
                self.worker.logger.info(f"📤 [VIP3_REPORT] Report text:\n{report_text}")

                # Отправляем полный отчет с деталями как статусное сообщение (перезаписывается)
                await self.worker.messenger.send(
                    report_text,
                    MessageRole.USER_STATUS
                )
            else:
                self.worker.logger.info("🔍 [VIP3_REPORT] No scheduled posts found in any channel")
                # Нет запланированных постов - отправляем как статусное сообщение
                await self.worker.messenger.send(
                    "vip3_no_scheduled_posts",
                    MessageRole.USER_STATUS
                )

        except Exception as e:
            self.worker.logger.error(f"❌ [VIP3_REPORT] Error in check_and_report_scheduled_posts: {e}")
            import traceback
            traceback.print_exc()

    async def _get_scheduled_posts_count(self, channel_pair_id: int) -> int:
        """Получить количество запланированных постов для правила из Telegram"""
        try:
            # Get channel pair to find target channel
            async with async_session() as session:
                result = await session.execute(
                    select(ChannelPair).where(ChannelPair.id == channel_pair_id)
                )
                channel_pair = result.scalar_one_or_none()

                if not channel_pair:
                    self.worker.logger.warning(f"🔍 [VIP3_REPORT] Channel pair {channel_pair_id} not found")
                    return 0

            # Resolve target channel ID
            target_channel = str(channel_pair.target_channel)
            resolved_channel_id = await self.worker._resolve_channel_identifier(target_channel)

            if not resolved_channel_id:
                self.worker.logger.warning(f"🔍 [VIP3_REPORT] Could not resolve channel {target_channel}")
                return 0

            # Use the existing scheduler's GetScheduledHistory implementation
            # This is the same logic used in scheduler.py for determining schedule times
            try:
                peer = await self.worker.client.resolve_peer(resolved_channel_id)
                
                if not isinstance(peer, InputPeerChannel):
                    self.worker.logger.warning(f"🔍 [VIP3_REPORT] Target {target_channel} is not a channel")
                    return 0
                
                # Use the resolved peer directly instead of wrapping it in InputPeer()
                scheduled_history = await self.worker.client.invoke(
                    GetScheduledHistory(peer=peer, hash=0)  # type: ignore
                )
                
                count = len(scheduled_history.messages)
                
                self.worker.logger.info(
                    f"🔍 [VIP3_REPORT] Channel {target_channel} (ID: {resolved_channel_id}): "
                    f"{count} scheduled messages from Telegram"
                )

                return count

            except Exception as e:
                self.worker.logger.error(
                    f"❌ [VIP3_REPORT] Error getting scheduled history from Telegram for {target_channel}: {e}"
                )
                return 0

        except Exception as e:
            self.worker.logger.error(f"❌ [VIP3_REPORT] Error in _get_scheduled_posts_count: {e}")
            return 0

    async def _get_channel_name(self, channel_identifier: str) -> str:
        """Получить реальное название канала"""
        try:
            if not self.worker.is_connected():
                self.worker.logger.debug(f"🔍 [VIP3_REPORT] Client not connected, using identifier: {channel_identifier}")
                return channel_identifier

            # Пробуем получить информацию о канале
            chat = await self.worker.client.get_chat(channel_identifier)

            # Приоритет: title > username > identifier
            if hasattr(chat, 'title') and chat.title:
                self.worker.logger.debug(f"🔍 [VIP3_REPORT] Got channel title: {chat.title}")
                return chat.title
            elif hasattr(chat, 'username') and chat.username:
                channel_name = f"@{chat.username}"
                self.worker.logger.debug(f"🔍 [VIP3_REPORT] Got channel username: {channel_name}")
                return channel_name
            else:
                self.worker.logger.debug(f"🔍 [VIP3_REPORT] Using original identifier: {channel_identifier}")
                return channel_identifier

        except Exception as e:
            self.worker.logger.debug(f"🔍 [VIP3_REPORT] Could not get chat info for {channel_identifier}: {e}")
            return channel_identifier

    async def get_channel_pairs(self):
        """Получение правил обработки каналов из БД"""
        async with async_session() as session:  # type: ignore
            result = await session.execute(
                select(ChannelPair)
                .where(ChannelPair.user_id == self.worker.user_id)
                .options(selectinload(ChannelPair.model))
            )
            return result.scalars().all()
