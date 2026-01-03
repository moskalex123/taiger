"""
Telegram Worker - Точка входа
Упрощенный файл для запуска воркера
"""
import os
import asyncio
import argparse
import logging
import threading
import uvicorn
import time
from pyrogram.sync import idle

from telegram_worker import TelegramWorker, create_app
from telegram_worker.unified_messenger import MessageRole

# Global worker instance
worker_instance = None


async def main(user_id: int, process_old_messages: bool = False, skip_listening: bool = False):
    """Main worker function."""
    global worker_instance
    
    # Initialize worker
    try:
        # Start timing startup
        startup_start = time.time()
        logging.info(f"🚀 Starting worker initialization for user_id: {user_id}")
        worker_instance = TelegramWorker(user_id=user_id)
        worker_instance.auto_scheduled = skip_listening
        
        # Call async initialization
        await worker_instance.initialize()
        
        # Set worker instance in API
        app.set_worker_instance(worker_instance)
        
        logging.info(f"✅ Worker object created for user_id: {user_id}")
        
        # Connect to Telegram first
        logging.info("🔗 Connecting to Telegram...")
        await worker_instance.connect()
        worker_instance.auto_scheduled = skip_listening
        
        if worker_instance.is_connected():
            # Load rules from database after connection
            logging.info("Загрузка правил каналов из базы данных...")
            await worker_instance._load_rules_from_db()
            
            # Wait for client to be fully ready before starting hybrid processing
            logging.info("⏳ Waiting for Telegram client to be fully ready...")

            # Активная проверка готовности с таймаутом
            max_wait_time = 15  # Максимальное время ожидания (было 14)
            check_interval = 0.5  # Проверять каждые 0.5 секунды
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                if worker_instance.is_connected():
                    # Дополнительная проверка: попробуем получить информацию о пользователе
                    try:
                        await worker_instance.client.get_me()
                        logging.info("✅ Client is fully ready for channel processing")
                        break
                    except Exception as e:
                        logging.warning(f"Client connected but not ready yet: {e}")

                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
            else:
                # Таймаут достигнут
                logging.error("❌ Client not ready after timeout")
                raise ConnectionError("Client not ready for processing")

            logging.info(f"⏱️ Client ready check completed in {elapsed_time:.1f}s")
            
            # Set worker status to active to trigger registration
            await worker_instance._update_worker_status("active")

            # DIAGNOSTIC: Verify worker registration
            from worker_registry import worker_registry
            is_registered = worker_registry.is_worker_running(user_id)
            worker_info = worker_registry.get_worker_info(user_id)
            logging.info(f"DIAGNOSTIC: After status update - user_id={user_id}, is_registered={is_registered}, info={worker_info}")

            # FIX: Ensure worker is properly registered before proceeding
            if not is_registered:
                logging.error(f"CRITICAL: Worker {user_id} failed to register properly, attempting manual registration")
                try:
                    import os
                    worker_registry.add_worker(user_id, os.getpid(), vip_level=2, auto_scheduled=skip_listening)
                    logging.info(f"MANUAL REGISTRATION: Worker {user_id} manually registered with PID {os.getpid()}")
                    is_registered = worker_registry.is_worker_running(user_id)
                    worker_info = worker_registry.get_worker_info(user_id)
                    logging.info(f"DIAGNOSTIC: After manual registration - user_id={user_id}, is_registered={is_registered}, info={worker_info}")
                except Exception as e:
                    logging.error(f"MANUAL REGISTRATION FAILED: {e}")

            # Start hybrid processing (batch + listening) after connection is fully ready
            listening_enabled = not skip_listening

            logging.info("🔗 Starting hybrid processing...")
            try:
                await worker_instance.hybrid_processor.start_hybrid_processing(
                    process_old_messages=process_old_messages,
                    listen_for_new_messages=listening_enabled
                )
                logging.info("✅ Hybrid processing completed successfully")
            except Exception as e:
                logging.error(f"❌ Hybrid processing failed: {e}", exc_info=True)
                raise

            if listening_enabled:
                logging.info(f"✅ Worker for user {user_id} connected and listening")

                logging.info(f"⏳ Worker entering idle state, waiting for messages...")
                # UnifiedMessenger will handle this in start_listening()

                # Start periodic status logging
                async def periodic_status_log():
                    consecutive_not_found = 0  # Track consecutive "not_found" responses
                    while worker_instance and worker_instance.is_connected():
                        try:
                            await asyncio.sleep(30)  # Log every 30 seconds
                            if worker_instance and worker_instance.is_connected():
                                # Send heartbeat to update activity timestamp
                                try:
                                    import aiohttp
                                    from telegram_worker.utils import get_api_base_url
                                    session = await worker_instance._get_http_session()
                                    async with session.post(
                                        f"{get_api_base_url()}/api/internal/worker-heartbeat",
                                        json={"user_id": user_id},
                                        timeout=aiohttp.ClientTimeout(total=5)
                                    ) as response:
                                        if response.status == 200:
                                            # Parse response to check if worker is still registered
                                            try:
                                                response_data = await response.json()
                                                status = response_data.get("status")
                                                
                                                if status == "not_found":
                                                    consecutive_not_found += 1
                                                    logging.warning(f"Heartbeat returned 'not_found' ({consecutive_not_found}/3) - worker may have been stopped by TMA")
                                                    
                                                    # Stop worker after 3 consecutive "not_found" responses
                                                    if consecutive_not_found >= 3:
                                                        logging.info("Worker removed from registry by TMA - initiating graceful shutdown")
                                                        # Break the loop to trigger worker disconnect
                                                        break
                                                elif status == "success":
                                                    consecutive_not_found = 0  # Reset counter on success
                                                    logging.debug("Heartbeat sent successfully")
                                                else:
                                                    logging.debug(f"Heartbeat response: {status}")
                                                    consecutive_not_found = 0
                                            except Exception as json_error:
                                                logging.warning(f"Failed to parse heartbeat response: {json_error}")
                                                consecutive_not_found = 0
                                        else:
                                            logging.warning(f"Failed to send heartbeat: HTTP {response.status}")
                                except Exception as e:
                                    logging.warning(f"Failed to send heartbeat: {e}")
                        except Exception as e:
                            logging.error(f"Error in periodic status log: {e}")
                            break
                    
                    # If we exit the loop due to not_found, disconnect the worker
                    if consecutive_not_found >= 3 and worker_instance:
                        logging.info("Disconnecting worker due to removal from registry")
                        try:
                            await worker_instance.disconnect()
                        except Exception as e:
                            logging.error(f"Error disconnecting worker: {e}")
                        # Exit the process to ensure clean shutdown
                        import sys
                        logging.info("Exiting worker process")
                        sys.exit(0)

                # Start periodic logging in background
                asyncio.create_task(periodic_status_log())

                # Ensure the event loop is properly running for message handling
                logging.info("🔄 Starting event loop for message handling...")
                await idle()
        else:
            logging.error(f"❌ Worker for user {user_id} failed to connect")
            await worker_instance.messenger.send("connection_failed", MessageRole.WEBSOCKET_LOG, level="error")
            
    except Exception as e:
        logging.error(f"💥 Worker error: {e}", exc_info=True)
        if worker_instance:
            await worker_instance.messenger.send("worker_error", MessageRole.WEBSOCKET_LOG, level="error", error=str(e))
        raise
    finally:
        # Calculate and log startup time
        startup_time = time.time() - startup_start
        logging.info(f"📊 Worker startup time: {startup_time:.2f}s")
        
        if worker_instance:
            logging.info(f"🔌 Disconnecting worker for user {user_id}")
            await worker_instance.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Worker Process")
    parser.add_argument("--user_id", required=True, type=int, help="User ID from database")
    parser.add_argument("--port", type=int, default=8000, help="Port for API endpoints")
    parser.add_argument("--process-old-messages", action="store_true", help="Process all old messages from the beginning")
    parser.add_argument("--skip-listening", action="store_true", help="Skip listening for new messages (auto-started worker)")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create FastAPI app
    app = create_app()
    
    # Run FastAPI in separate thread
    app_config = uvicorn.Config(app, host="0.0.0.0", port=args.port, log_level="info")
    server = uvicorn.Server(app_config)
    
    api_thread = threading.Thread(target=server.run, daemon=True)
    api_thread.start()
    
    logging.info(f"Worker API running at http://0.0.0.0:{args.port}")
    
    # Run worker
    try:
        asyncio.run(main(user_id=args.user_id, process_old_messages=args.process_old_messages, skip_listening=args.skip_listening))
    except KeyboardInterrupt:
        logging.info("Worker interrupted by user")
    except Exception as e:
        logging.error(f"Worker failed: {e}", exc_info=True)
        import sys
        sys.exit(1)