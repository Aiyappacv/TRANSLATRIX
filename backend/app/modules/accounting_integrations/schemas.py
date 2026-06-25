"""
Accounting Integrations Schemas
Request/response schemas for accounting software integrations
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ConnectorInfo(BaseModel):
    """Connector information"""
    id: str
    name: str
    capabilities: List[str]
    status: str


class ConnectorListResponse(BaseModel):
    """List of available connectors"""
    connectors: List[ConnectorInfo]
    total: int


class ConnectorConfigCreate(BaseModel):
    """Create connector configuration"""
    connector_id: str = Field(..., description="Connector identifier")
    config: Dict[str, Any] = Field(..., description="Connector-specific configuration")


class ConnectorTestRequest(BaseModel):
    """Test connector connection"""
    connector_id: str
    config: Optional[Dict[str, Any]] = None


class ConnectorTestResponse(BaseModel):
    """Connector test response"""
    connector_id: str
    connected: bool
    message: Optional[str] = None


class PostingRequest(BaseModel):
    """Post entry to accounting software"""
    entry_id: str
    connector_id: str
    config: Optional[Dict[str, Any]] = None


class PostingResponse(BaseModel):
    """Posting response"""
    connector_id: str
    entry_id: str
    document_number: Optional[str]
    status: str
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
