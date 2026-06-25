"""
Standardized API Response Format
Consistent response structure across all endpoints
"""
from typing import Any, Optional, Dict, List
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel):
    """Paginated API response"""

    success: bool = True
    message: Optional[str] = None
    data: List[Any]
    pagination: PaginationMeta


def success_response(
    data: Any = None,
    message: str = "Success",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a success response

    Args:
        data: Response data
        message: Success message
        meta: Optional metadata

    Returns:
        Standardized success response dictionary
    """
    response = APIResponse(
        success=True,
        message=message,
        data=data,
        meta=meta
    )
    return response.model_dump(exclude_none=True)


def error_response(
    message: str = "Error occurred",
    errors: Optional[List[Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an error response

    Args:
        message: Error message
        errors: List of error details
        meta: Optional metadata

    Returns:
        Standardized error response dictionary
    """
    response = APIResponse(
        success=False,
        message=message,
        errors=errors or [],
        meta=meta
    )
    return response.model_dump(exclude_none=True)


def paginated_response(
    data: List[Any],
    page: int,
    page_size: int,
    total_items: int,
    message: str = "Success"
) -> Dict[str, Any]:
    """
    Create a paginated response

    Args:
        data: List of items for current page
        page: Current page number (1-indexed)
        page_size: Items per page
        total_items: Total number of items
        message: Success message

    Returns:
        Standardized paginated response dictionary
    """
    total_pages = (total_items + page_size - 1) // page_size

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )

    response = PaginatedResponse(
        message=message,
        data=data,
        pagination=pagination
    )

    return response.model_dump()
