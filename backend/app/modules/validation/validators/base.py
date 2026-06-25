"""Base Validator"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.orm import Session
import structlog

logger = structlog.get_logger(__name__)


class ValidationResult:
    """Validation result"""
    def __init__(self, is_valid: bool, message: str, severity: str = "error", details: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.message = message
        self.severity = severity
        self.details = details or {}


class BaseValidator(ABC):
    """Base validator interface"""

    @abstractmethod
    def validate(self, db: Session, entry: Any, parameters: Dict[str, Any]) -> ValidationResult:
        """Execute validation"""
        pass

    def get_validator_type(self) -> str:
        """Get validator type identifier"""
        return self.__class__.__name__.replace("Validator", "").lower()
