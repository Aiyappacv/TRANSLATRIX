"""Confidence Threshold Validator"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from .base import BaseValidator, ValidationResult


class ConfidenceValidator(BaseValidator):
    """Validate confidence scores meet threshold"""

    def validate(self, db: Session, entry: Any, parameters: Dict[str, Any]) -> ValidationResult:
        min_confidence = parameters.get("min_confidence", 0.7)

        if entry.classification_confidence is None:
            return ValidationResult(
                is_valid=False,
                message="No classification confidence available",
                severity="warning"
            )

        confidence = float(entry.classification_confidence)

        if confidence < min_confidence:
            return ValidationResult(
                is_valid=False,
                message=f"Confidence {confidence} below threshold {min_confidence}",
                severity="warning",
                details={"confidence": confidence, "threshold": min_confidence}
            )

        return ValidationResult(is_valid=True, message="Confidence acceptable", severity="info")
