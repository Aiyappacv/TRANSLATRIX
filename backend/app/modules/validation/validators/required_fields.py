"""Required Fields Validator"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from .base import BaseValidator, ValidationResult


class RequiredFieldsValidator(BaseValidator):
    """Validate required fields are present"""

    def validate(self, db: Session, entry: Any, parameters: Dict[str, Any]) -> ValidationResult:
        required_fields = parameters.get("required_fields", ["amount", "currency"])
        missing_fields = []

        for field in required_fields:
            value = getattr(entry, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)

        if missing_fields:
            return ValidationResult(
                is_valid=False,
                message=f"Missing required fields: {', '.join(missing_fields)}",
                severity="error",
                details={"missing_fields": missing_fields}
            )

        return ValidationResult(is_valid=True, message="All required fields present", severity="info")
