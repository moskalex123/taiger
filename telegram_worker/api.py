"""
FastAPI эндпоинты для Telegram Worker
"""
from fastapi import FastAPI, HTTPException
from .models import WorkerStatus, ReloadRulesResponse, ProcessingControlResponse


def create_app() -> FastAPI:
    """Create FastAPI application for Telegram Worker"""
    app = FastAPI(title="Telegram Worker Service")
    
    # Global worker instance reference
    worker_instance = None
    
    def set_worker_instance(worker):
        """Set the global worker instance"""
        nonlocal worker_instance
        worker_instance = worker
    
    @app.get("/_health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "telegram_worker"}

    @app.get("/status", response_model=WorkerStatus)
    async def get_status():
        """Get worker status."""
        if not worker_instance:
            raise HTTPException(status_code=503, detail="Worker not initialized")
        
        status = await worker_instance.get_status()
        return WorkerStatus(**status)

    @app.post("/reload_rules", response_model=ReloadRulesResponse)
    async def reload_rules():
        """Reload channel rules."""
        if not worker_instance:
            raise HTTPException(status_code=503, detail="Worker not initialized")
        
        rules_count = await worker_instance.reload_rules()
        return ReloadRulesResponse(status="success", rules_count=rules_count)

    @app.post("/pause", response_model=ProcessingControlResponse)
    async def pause_processing():
        """Pause message processing."""
        if not worker_instance:
            raise HTTPException(status_code=503, detail="Worker not initialized")
        
        worker_instance.pause_processing()
        return ProcessingControlResponse(status="paused", is_processing=False)

    @app.post("/resume", response_model=ProcessingControlResponse)
    async def resume_processing():
        """Resume message processing."""
        if not worker_instance:
            raise HTTPException(status_code=503, detail="Worker not initialized")
        
        worker_instance.resume_processing()
        return ProcessingControlResponse(status="resumed", is_processing=True)

    @app.post("/stop")
    async def stop_worker():
        """Stop the worker gracefully."""
        if worker_instance:
            await worker_instance.disconnect()
        return {"status": "stopped"}
    
    # Store the setter function in the app for external access
    app.set_worker_instance = set_worker_instance
    
    return app