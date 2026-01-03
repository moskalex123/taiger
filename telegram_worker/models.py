"""
Pydantic модели для Telegram Worker API
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WorkerStatus(BaseModel):
    user_id: int
    status: str
    is_connected: bool
    is_processing: bool
    rules_count: int
    last_activity: Optional[datetime] = None
    current_balance: Optional[float] = None


class ReloadRulesResponse(BaseModel):
    status: str
    rules_count: int


class ProcessingControlResponse(BaseModel):
    status: str
    is_processing: bool


class AuthRequiredSignal(BaseModel):
    user_id: int
    error_type: str
    message: str