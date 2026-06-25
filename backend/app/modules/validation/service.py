"""Validation Service"""
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from app.modules.validation.engine import ValidationEngine
from app.modules.validation.models import ValidationResult as ValidationResultModel, ValidationSeverity
from app.modules.entries.models import FinancialEntry

logger = structlog.get_logger(__name__)


class ValidationService:
    """Validation orchestration service"""

    def __init__(self):
        self.engine = ValidationEngine()

    def validate_entry(
        self, db: Session, entry_id: UUID, tenant_id: UUID
    ) -> List[ValidationResultModel]:
        """Validate a financial entry against all active rules"""
        # Get entry
        entry = db.query(FinancialEntry).filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.tenant_id == tenant_id,
        ).first()

        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        # Get active rules
        rules = self.engine.get_active_rules(db, tenant_id)

        results = []

        for rule in rules:
            # Execute validation
            validation_result = self.engine.execute_validation(db, entry, rule)

            if validation_result:
                # Map severity
                severity_enum = ValidationSeverity.ERROR
                if validation_result.severity == "warning":
                    severity_enum = ValidationSeverity.WARNING
                elif validation_result.severity == "info":
                    severity_enum = ValidationSeverity.INFO

                # Save result
                result_model = ValidationResultModel(
                    tenant_id=tenant_id,
                    entry_id=entry_id,
                    rule_id=rule.id,
                    is_valid=validation_result.is_valid,
                    severity=severity_enum,
                    message=validation_result.message,
                    details=validation_result.details,
                )
                db.add(result_model)
                results.append(result_model)

        db.commit()

        logger.info("validation_complete", entry_id=entry_id, results_count=len(results))
        return results

    def get_validation_results(
        self, db: Session, entry_id: UUID, tenant_id: UUID
    ) -> List[ValidationResultModel]:
        """Get validation results for an entry"""
        return db.query(ValidationResultModel).filter(
            ValidationResultModel.entry_id == entry_id,
            ValidationResultModel.tenant_id == tenant_id,
        ).all()
