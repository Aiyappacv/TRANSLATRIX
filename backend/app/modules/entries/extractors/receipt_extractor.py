"""Receipt Entry Extractor"""
import re
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class ReceiptExtractor:
    """Extract financial entries from receipt documents"""

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract entries from receipt text"""
        entries = []

        # Extract total amount
        total_match = re.search(r'total[:\s]*\$?(\d+[.,]\d{2})', text, re.IGNORECASE)
        if total_match:
            amount = float(total_match.group(1).replace(',', ''))

            entry = {
                "source_page": 1,
                "original_description": text[:200],
                "amount": amount,
                "currency": "USD",
                "category": "expenses",
            }
            entries.append(entry)

        return entries
