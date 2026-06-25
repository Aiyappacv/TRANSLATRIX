"""Validation Schemas"""
from pydantic import BaseModel, UUID4
from typing import Optional, Dict, Any
from datetime import datetime


class ValidationResultResponse(BaseModel):
    """Validation result response"""
    id: UUID4
    entry_id: UUID4
    rule_id: UUID4
    is_valid: bool
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
