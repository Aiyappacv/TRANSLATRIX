"""
Idempotency Management
Prevent duplicate financial postings and critical operations
"""
import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from redis import Redis
from app.config import settings

# Initialize Redis client for idempotency tracking
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


def generate_idempotency_key(data: Dict[str, Any]) -> str:
    """
    Generate deterministic idempotency key from data

    Args:
        data: Dictionary containing key fields for uniqueness

    Returns:
        SHA-256 hash as idempotency key
    """
    # Sort keys to ensure consistent ordering
    sorted_data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(sorted_data.encode()).hexdigest()


def check_idempotency_key(key: str) -> Optional[Dict[str, Any]]:
    """
    Check if idempotency key was already used

    Args:
        key: Idempotency key to check

    Returns:
        Previous result if key exists, None otherwise
    """
    result = redis_client.get(f"idempotency:{key}")
    if result:
        return json.loads(result)
    return None


def store_idempotency_result(
    key: str,
    result: Dict[str, Any],
    ttl_hours: int = 24
) -> None:
    """
    Store result with idempotency key

    Args:
        key: Idempotency key
        result: Result data to store
        ttl_hours: Time-to-live in hours (default 24)
    """
    ttl_seconds = ttl_hours * 3600
    redis_client.setex(
        f"idempotency:{key}",
        ttl_seconds,
        json.dumps(result)
    )


def create_posting_idempotency_key(
    tenant_id: str,
    entry_id: str,
    posting_type: str,
    amount: float,
    date: str
) -> str:
    """
    Create idempotency key for financial postings

    Args:
        tenant_id: Tenant ID
        entry_id: Financial entry ID
        posting_type: Type of posting (sap, quickbooks, etc.)
        amount: Transaction amount
        date: Transaction date

    Returns:
        Idempotency key
    """
    data = {
        "tenant_id": tenant_id,
        "entry_id": entry_id,
        "posting_type": posting_type,
        "amount": amount,
        "date": date,
    }
    return generate_idempotency_key(data)


def is_duplicate_posting(
    tenant_id: str,
    entry_id: str,
    posting_type: str,
    amount: float,
    date: str
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if posting is a duplicate

    Args:
        tenant_id: Tenant ID
        entry_id: Financial entry ID
        posting_type: Type of posting
        amount: Transaction amount
        date: Transaction date

    Returns:
        Tuple of (is_duplicate, previous_result)
    """
    key = create_posting_idempotency_key(
        tenant_id, entry_id, posting_type, amount, date
    )
    previous_result = check_idempotency_key(key)
    return previous_result is not None, previous_result


def mark_posting_complete(
    tenant_id: str,
    entry_id: str,
    posting_type: str,
    amount: float,
    date: str,
    result: Dict[str, Any]
) -> None:
    """
    Mark posting as complete with result

    Args:
        tenant_id: Tenant ID
        entry_id: Financial entry ID
        posting_type: Type of posting
        amount: Transaction amount
        date: Transaction date
        result: Posting result data
    """
    key = create_posting_idempotency_key(
        tenant_id, entry_id, posting_type, amount, date
    )
    store_idempotency_result(key, result, ttl_hours=72)  # Keep for 3 days
