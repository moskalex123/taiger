#!/usr/bin/env python3
"""
Manually register worker in registry
"""
import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def manual_register_worker(user_id: int, pid: int):
    """Manually register worker in registry"""
    try:
        # Import worker registry directly
        from worker_registry import worker_registry
        
        # Add worker to registry
        worker_registry.add_worker(user_id, pid, vip_level=2)
        print(f"Manually registered worker {user_id} with PID {pid}")
        
        # Check if it's registered
        is_running = worker_registry.is_worker_running(user_id)
        worker_info = worker_registry.get_worker_info(user_id)
        all_workers = worker_registry.get_all_workers()
        
        print(f"Worker registry state for user {user_id}:")
        print(f"  Is running: {is_running}")
        print(f"  Worker info: {worker_info}")
        print(f"  All workers: {all_workers}")
        
        return is_running, worker_info
        
    except Exception as e:
        print(f"Error registering worker: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Main function"""
    if len(sys.argv) > 2:
        user_id = int(sys.argv[1])
        pid = int(sys.argv[2])
    else:
        user_id = 2  # Default test user
        pid = 32429  # Default test PID
    
    print(f"Manually registering worker {user_id} with PID {pid}...")
    is_running, worker_info = manual_register_worker(user_id, pid)
    
    if is_running:
        print("✅ Worker is registered and running!")
    else:
        print("❌ Worker is not registered or not running!")

if __name__ == "__main__":
    main()