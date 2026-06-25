"""Validation Engine"""
from typing import Dict, List
from sqlalchemy.orm import Session
from uuid import UUID
import structlog

from app.modules.validation.validators.base import BaseValidator
from app.modules.validation.validators.required_fields import RequiredFieldsValidator
from app.modules.validation.validators.debit_credit import DebitCreditValidator
from app.modules.validation.validators.confidence import ConfidenceValidator
from app.modules.validation.validators.duplicate import DuplicateValidator
from app.modules.validation.validators.master_data import MasterDataValidator
from app.modules.validation.models import ValidationRule, ValidationRuleType

logger = structlog.get_logger(__name__)


class ValidationEngine:
    """Validation rule engine and validator registry"""

    def __init__(self):
        # Register validators
        self.validators: Dict[ValidationRuleType, BaseValidator] = {
            ValidationRuleType.REQUIRED_FIELDS: RequiredFieldsValidator(),
            ValidationRuleType.DEBIT_CREDIT_BALANCE: DebitCreditValidator(),
            ValidationRuleType.CONFIDENCE_THRESHOLD: ConfidenceValidator(),
            ValidationRuleType.DUPLICATE_CHECK: DuplicateValidator(),
            ValidationRuleType.MASTER_DATA: MasterDataValidator(),
        }

    def get_active_rules(self, db: Session, tenant_id: UUID) -> List[ValidationRule]:
        """Get active validation rules for tenant"""
        return db.query(ValidationRule).filter(
            ValidationRule.tenant_id == tenant_id,
            ValidationRule.is_active == True,
        ).order_by(ValidationRule.priority.desc()).all()

    def execute_validation(
        self, db: Session, entry: any, rule: ValidationRule
    ) -> any:
        """Execute a single validation rule"""
        validator = self.validators.get(rule.rule_type)

        if not validator:
            logger.warning("validator_not_found", rule_type=rule.rule_type)
            return None

        parameters = rule.parameters or {}

        try:
            result = validator.validate(db, entry, parameters)
            logger.info(
                "validation_executed",
                rule_name=rule.name,
                is_valid=result.is_valid,
                severity=result.severity,
            )
            return result
        except Exception as e:
            logger.error("validation_error", rule_name=rule.name, error=str(e))
            return None
