"""
Custom Exceptions for TRANSLATRIX PRO
Centralized exception definitions for consistent error handling
"""
from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class TranslatrixException(Exception):
    """Base exception for all application exceptions"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(TranslatrixException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(TranslatrixException):
    """Raised when user lacks required permissions"""
    pass


class TenantNotFoundError(TranslatrixException):
    """Raised when tenant is not found"""
    pass


class TenantInactiveError(TranslatrixException):
    """Raised when tenant is inactive or suspended"""
    pass


class CompanyNotFoundError(TranslatrixException):
    """Raised when company is not found"""
    pass


class UserNotFoundError(TranslatrixException):
    """Raised when user is not found"""
    pass


class UserInactiveError(TranslatrixException):
    """Raised when user account is inactive"""
    pass


class DuplicateEntryError(TranslatrixException):
    """Raised when attempting to create duplicate entry"""
    pass


class ValidationError(TranslatrixException):
    """Raised when validation fails"""
    pass


class FileProcessingError(TranslatrixException):
    """Raised when file processing fails"""
    pass


class OCRError(TranslatrixException):
    """Raised when OCR processing fails"""
    pass


class SAPError(TranslatrixException):
    """Raised when SAP integration fails"""
    pass


class AccountingIntegrationError(TranslatrixException):
    """Raised when accounting software integration fails"""
    pass


class StorageError(TranslatrixException):
    """Raised when storage operation fails"""
    pass


class IdempotencyError(TranslatrixException):
    """Raised when idempotency check fails"""
    pass


class NotFoundError(TranslatrixException):
    """Raised when resource is not found"""
    pass


class PermissionError(TranslatrixException):
    """Raised when user lacks permissions for operation"""
    pass


class ExternalServiceError(TranslatrixException):
    """Raised when external service call fails"""
    pass


class RateLimitError(TranslatrixException):
    """Raised when rate limit is exceeded"""
    pass


class ConfigurationError(TranslatrixException):
    """Raised when configuration is invalid"""
    pass


def http_exception_from_app_exception(exc: TranslatrixException) -> HTTPException:
    """
    Convert application exception to HTTPException
    Maps custom exceptions to appropriate HTTP status codes
    """
    exception_map = {
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        TenantNotFoundError: status.HTTP_404_NOT_FOUND,
        TenantInactiveError: status.HTTP_403_FORBIDDEN,
        CompanyNotFoundError: status.HTTP_404_NOT_FOUND,
        UserNotFoundError: status.HTTP_404_NOT_FOUND,
        UserInactiveError: status.HTTP_403_FORBIDDEN,
        DuplicateEntryError: status.HTTP_409_CONFLICT,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        FileProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        OCRError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        SAPError: status.HTTP_502_BAD_GATEWAY,
        AccountingIntegrationError: status.HTTP_502_BAD_GATEWAY,
        StorageError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        IdempotencyError: status.HTTP_409_CONFLICT,
        NotFoundError: status.HTTP_404_NOT_FOUND,
        PermissionError: status.HTTP_403_FORBIDDEN,
        ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = exception_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    return HTTPException(
        status_code=status_code,
        detail={
            "message": exc.message,
            "details": exc.details
        }
    )
