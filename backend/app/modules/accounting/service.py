"""Accounting Service"""
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from decimal import Decimal
import structlog

from app.modules.accounting.models import AccountingEntry, AccountingEntryType
from app.modules.entries.models import FinancialEntry
from app.modules.sap_mapping.service import SAPMappingService

logger = structlog.get_logger(__name__)


class AccountingService:
    """Accounting entry generation with debit/credit balancing"""

    def __init__(self):
        self.sap_service = SAPMappingService()

    def generate_entries(
        self, db: Session, financial_entry_id: UUID, tenant_id: UUID
    ) -> List[AccountingEntry]:
        """Generate balanced debit/credit entries"""
        # Get financial entry
        fin_entry = db.query(FinancialEntry).filter(
            FinancialEntry.id == financial_entry_id,
            FinancialEntry.tenant_id == tenant_id,
        ).first()

        if not fin_entry:
            raise ValueError("Financial entry not found")

        # Get GL account suggestions
        gl_suggestions = self.sap_service.suggest_gl_accounts(
            db, tenant_id, fin_entry.category or "expenses", float(fin_entry.amount)
        )

        entries = []

        # Create debit entry
        debit_gl = gl_suggestions[0] if gl_suggestions else {"gl_account": "600000", "account_name": "Expenses"}
        debit_entry = AccountingEntry(
            tenant_id=tenant_id,
            financial_entry_id=financial_entry_id,
            entry_type=AccountingEntryType.DEBIT,
            gl_account=debit_gl["gl_account"],
            account_name=debit_gl["account_name"],
            amount=fin_entry.amount,
            currency=fin_entry.currency or "USD",
            description=fin_entry.translated_description or fin_entry.original_description,
        )
        db.add(debit_entry)
        entries.append(debit_entry)

        # Create credit entry (balancing)
        credit_gl = gl_suggestions[1] if len(gl_suggestions) > 1 else {"gl_account": "100000", "account_name": "Cash"}
        credit_entry = AccountingEntry(
            tenant_id=tenant_id,
            financial_entry_id=financial_entry_id,
            entry_type=AccountingEntryType.CREDIT,
            gl_account=credit_gl["gl_account"],
            account_name=credit_gl["account_name"],
            amount=fin_entry.amount,
            currency=fin_entry.currency or "USD",
            description=f"Payment for {fin_entry.translated_description or fin_entry.original_description}",
        )
        db.add(credit_entry)
        entries.append(credit_entry)

        db.commit()

        logger.info("accounting_entries_generated", financial_entry_id=financial_entry_id, entries=len(entries))
        return entries
