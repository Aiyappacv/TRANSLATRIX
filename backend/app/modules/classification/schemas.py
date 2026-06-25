"""Classification Schemas"""
from pydantic import BaseModel, UUID4
from decimal import Decimal


class ClassificationResponse(BaseModel):
    """Classification result"""
    id: UUID4
    entry_id: UUID4
    category: str
    subcategory: str = None
    confidence: Decimal
    reason: str = None
    classification_method: str

    class Config:
        from_attributes = True
