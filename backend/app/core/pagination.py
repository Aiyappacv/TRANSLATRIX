"""
Pagination Utilities
Consistent pagination across all list endpoints
"""
from typing import Any, List, TypeVar, Generic
from sqlalchemy.orm import Query
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for API requests"""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate SQL offset from page and page_size"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Return page_size as SQL limit"""
        return self.page_size


class PagedResult(Generic[T]):
    """Generic paged result container"""

    def __init__(
        self,
        items: List[T],
        total_items: int,
        page: int,
        page_size: int
    ):
        self.items = items
        self.total_items = total_items
        self.page = page
        self.page_size = page_size
        self.total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        self.has_next = page < self.total_pages
        self.has_previous = page > 1


def paginate_query(
    query: Query,
    page: int = 1,
    page_size: int = 20
) -> PagedResult[Any]:
    """
    Paginate a SQLAlchemy query

    Args:
        query: SQLAlchemy query to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PagedResult with items and pagination metadata
    """
    # Get total count
    total_items = query.count()

    # Calculate offset
    offset = (page - 1) * page_size

    # Get page items
    items = query.offset(offset).limit(page_size).all()

    return PagedResult(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size
    )


def paginate_list(
    items: List[T],
    page: int = 1,
    page_size: int = 20
) -> PagedResult[T]:
    """
    Paginate a Python list

    Args:
        items: List to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PagedResult with items and pagination metadata
    """
    total_items = len(items)

    # Calculate start and end indices
    start = (page - 1) * page_size
    end = start + page_size

    # Get page items
    page_items = items[start:end]

    return PagedResult(
        items=page_items,
        total_items=total_items,
        page=page,
        page_size=page_size
    )
