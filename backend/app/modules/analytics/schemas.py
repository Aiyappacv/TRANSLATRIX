"""
Analytics Schemas
Request/response schemas for analytics
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class DashboardStatistics(BaseModel):
    """Dashboard statistics response"""
    period: Dict[str, str]
    files: Dict[str, Any]
    entries: Dict[str, Any]
    reviews: Dict[str, Any]
    sap_posting: Dict[str, Any]


class ProcessingMetricsResponse(BaseModel):
    """Processing metrics response"""
    period_type: str
    metrics: List[Dict[str, Any]]


class UserActivityResponse(BaseModel):
    """User activity response"""
    user_id: str
    period: Dict[str, str]
    files_uploaded: int
    reviews_completed: int
