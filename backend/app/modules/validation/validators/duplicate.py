"""Duplicate Detection Validator"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from .base import BaseValidator, ValidationResult


class DuplicateValidator(BaseValidator):
    """Detect duplicate entries"""

    def validate(self, db: Session, entry: Any, parameters: Dict[str, Any]) -> ValidationResult:
        from app.modules.entries.models import FinancialEntry

        # Check for duplicates based on amount and date
        duplicates = db.query(FinancialEntry).filter(
            FinancialEntry.tenant_id == entry.tenant_id,
            FinancialEntry.id != entry.id,
            FinancialEntry.amount == entry.amount,
            FinancialEntry.entry_date == entry.entry_date,
        ).count()

        if duplicates > 0:
            return ValidationResult(
                is_valid=False,
                message=f"Found {duplicates} potential duplicate(s)",
                severity="warning",
                details={"duplicate_count": duplicates}
            )

        return ValidationResult(is_valid=True, message="No duplicates found", severity="info")
