"""SAP Mapping Schemas"""
from pydantic import BaseModel, UUID4
from typing import List, Optional


class SAPMappingResponse(BaseModel):
    """SAP mapping response"""
    tcode: Optional[str] = None
    gl_accounts: List[dict] = []
