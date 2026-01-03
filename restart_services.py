#!/usr/bin/env python3
"""
Script to restart project services
"""
import os
import sys
import subprocess
import time
import signal

def stop_services():
    """Stop all project services"""
    print("Stopping project services...")
    
    # Kill any existing uvicorn processes
    try:
        subprocess.run(["pkill", "-f", "uvicorn main:app"], check=False)
        time.sleep(2)
    except Exception as e:
        print(f"Error stopping uvicorn: {e}")
    
    # Kill any existing serve processes
    try:
        subprocess.run(["pkill", "-f", "serve -s"], check=False)
        time.sleep(2)
    except Exception as e:
        print(f"Error stopping serve: {e}")
    
    # Kill any existing nginx processes
    try:
        subprocess.run(["pkill", "-f", "nginx"], check=False)
        time.sleep(2)
    except Exception as e:
        print(f"Error stopping nginx: {e}")

def start_api_service():
    """Start the API service"""
    print("Starting API service...")
    try:
        # Change to project directory
        os.chdir("/opt/taiger")
        
        # Start API service in background
        with open("/tmp/api.log", "w") as api_log:
            subprocess.Popen([
                sys.executable, "-m", "uvicorn", "main:app", 
                "--host", "0.0.0.0", "--port", "8000"
            ], stdout=api_log, stderr=api_log, preexec_fn=os.setsid)
        
        print("API service started")
        return True
    except Exception as e:
        print(f"Error starting API service: {e}")
        return False

def start_frontend_service():
    """Start the frontend service"""
    print("Starting frontend service...")
    try:
        # Change to frontend directory
        os.chdir("/opt/taiger/frontend")
        
        # Start frontend service in background
        with open("/tmp/frontend.log", "w") as frontend_log:
            subprocess.Popen([
                "npx", "serve", "-s", "-l", "3000"
            ], stdout=frontend_log, stderr=frontend_log, preexec_fn=os.setsid)
        
        print("Frontend service started")
        return True
    except Exception as e:
        print(f"Error starting frontend service: {e}")
        return False

def start_nginx():
    """Start nginx service"""
    print("Starting nginx service...")
    try:
        # Start nginx
        subprocess.run(["nginx"], check=True)
        print("Nginx service started")
        return True
    except Exception as e:
        print(f"Error starting nginx: {e}")
        return False

def main():
    """Main function to restart all services"""
    print("Restarting project services...")
    
    # Stop existing services
    stop_services()
    
    # Wait a bit for services to stop
    time.sleep(5)
    
    # Start services in order
    success = True
    
    # Start API service
    if not start_api_service():
        success = False
    
    # Wait a bit for API to start
    time.sleep(5)
    
    # Start frontend service
    if not start_frontend_service():
        success = False
    
    # Wait a bit for frontend to start
    time.sleep(5)
    
    # Start nginx
    if not start_nginx():
        success = False
    
    if success:
        print("All services restarted successfully!")
        print("API: http://localhost:8000")
        print("Frontend: http://localhost:3000")
        print("Nginx: http://localhost")
    else:
        print("Some services failed to start. Check logs for details.")

if __name__ == "__main__":
    main()