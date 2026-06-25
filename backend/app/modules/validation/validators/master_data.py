"""Master Data Validator"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from .base import BaseValidator, ValidationResult


class MasterDataValidator(BaseValidator):
    """Validate master data existence"""

    def validate(self, db: Session, entry: Any, parameters: Dict[str, Any]) -> ValidationResult:
        # Placeholder - in production, check against master data tables
        # For now, just validate GL account format
        from app.modules.accounting.models import AccountingEntry

        accounting_entries = db.query(AccountingEntry).filter(
            AccountingEntry.financial_entry_id == entry.id
        ).all()

        invalid_accounts = []
        for acc_entry in accounting_entries:
            if not acc_entry.gl_account or len(acc_entry.gl_account) < 5:
                invalid_accounts.append(acc_entry.gl_account)

        if invalid_accounts:
            return ValidationResult(
                is_valid=False,
                message=f"Invalid GL accounts: {', '.join(invalid_accounts)}",
                severity="error",
                details={"invalid_accounts": invalid_accounts}
            )

        return ValidationResult(is_valid=True, message="Master data valid", severity="info")
