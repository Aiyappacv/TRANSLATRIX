"""
Accounting Worker
Generate accounting entries with debit/credit logic
"""
from typing import Dict, Any
from decimal import Decimal
from celery import Task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.modules.entries.models import FinancialEntry, EntryStatus
from app.modules.accounting.models import AccountingEntry, AccountingLine
from app.modules.accounting.service import generate_accounting_lines
import structlog
import uuid

logger = structlog.get_logger(__name__)


class AccountingTask(Task):
    """Base task with error handling"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("accounting_task_failed", task_id=task_id, error=str(exc))


@celery_app.task(
    name="accounting.generate",
    bind=True,
    base=AccountingTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def generate_accounting_entry(self, entry_id: str) -> Dict[str, Any]:
    """
    Generate accounting entry with debit/credit lines
    """
    db = SessionLocal()
    try:
        logger.info("generating_accounting_entry", entry_id=entry_id)

        entry = db.query(FinancialEntry).filter(FinancialEntry.id == uuid.UUID(entry_id)).first()
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        # Generate accounting lines
        lines = generate_accounting_lines(entry)

        # Create accounting entry
        accounting_entry = AccountingEntry(
            tenant_id=entry.tenant_id,
            financial_entry_id=entry.id,
            entry_date=entry.entry_date,
            description=entry.translated_description or entry.original_description,
            total_debit=sum(line['debit'] for line in lines),
            total_credit=sum(line['credit'] for line in lines),
            currency=entry.currency or 'USD'
        )
        db.add(accounting_entry)
        db.flush()

        # Create lines
        for line in lines:
            accounting_line = AccountingLine(
                accounting_entry_id=accounting_entry.id,
                account_code=line['account_code'],
                account_name=line['account_name'],
                debit_amount=Decimal(str(line['debit'])),
                credit_amount=Decimal(str(line['credit'])),
                description=line.get('description')
            )
            db.add(accounting_line)

        entry.status = EntryStatus.ACCOUNTING_GENERATED
        db.commit()

        # Trigger validation
        from app.workers.validation_worker import validate_accounting_entry
        validate_accounting_entry.delay(str(accounting_entry.id))

        logger.info("accounting_entry_generated", entry_id=entry_id, accounting_entry_id=str(accounting_entry.id))
        return {"entry_id": entry_id, "accounting_entry_id": str(accounting_entry.id)}

    except Exception as e:
        logger.error("accounting_generation_failed", entry_id=entry_id, error=str(e))
        raise
    finally:
        db.close()
