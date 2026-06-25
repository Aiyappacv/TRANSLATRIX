"""Entries Schemas"""
from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class FinancialEntryResponse(BaseModel):
    """Financial entry response"""
    id: UUID4
    file_id: UUID4
    source_page: Optional[int] = None
    source_row: Optional[int] = None
    original_description: Optional[str] = None
    translated_description: Optional[str] = None
    entry_date: Optional[date] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    vendor_name: Optional[str] = None
    category: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
