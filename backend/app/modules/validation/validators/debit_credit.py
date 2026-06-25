"""Debit-Credit Balance Validator"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
from .base import BaseValidator, ValidationResult


class DebitCreditValidator(BaseValidator):
    """Validate debit equals credit"""

    def validate(self, db: Session, entry: Any, parameters: Dict[str, Any]) -> ValidationResult:
        from app.modules.accounting.models import AccountingEntry, AccountingEntryType

        # Get accounting entries
        accounting_entries = db.query(AccountingEntry).filter(
            AccountingEntry.financial_entry_id == entry.id
        ).all()

        if not accounting_entries:
            return ValidationResult(
                is_valid=False,
                message="No accounting entries found",
                severity="warning"
            )

        debit_total = sum(e.amount for e in accounting_entries if e.entry_type == AccountingEntryType.DEBIT)
        credit_total = sum(e.amount for e in accounting_entries if e.entry_type == AccountingEntryType.CREDIT)

        if debit_total != credit_total:
            return ValidationResult(
                is_valid=False,
                message=f"Debit ({debit_total}) does not equal Credit ({credit_total})",
                severity="error",
                details={"debit": float(debit_total), "credit": float(credit_total)}
            )

        return ValidationResult(is_valid=True, message="Debit equals credit", severity="info")
