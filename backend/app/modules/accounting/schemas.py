"""Accounting Schemas"""
from pydantic import BaseModel, UUID4
from decimal import Decimal


class AccountingEntryResponse(BaseModel):
    """Accounting entry response"""
    id: UUID4
    financial_entry_id: UUID4
    entry_type: str
    gl_account: str
    account_name: str
    amount: Decimal
    currency: str

    class Config:
        from_attributes = True
