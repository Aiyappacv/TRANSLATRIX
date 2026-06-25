"""
Monitoring Schemas
Request/response schemas for monitoring endpoints
"""
from pydantic import BaseModel
from typing import Dict, Any


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    checks: Dict[str, Any]


class SystemInfoResponse(BaseModel):
    """System information response"""
    python_version: str
    platform: str
    processor: str
    timestamp: str
