"""Invoice Entry Extractor"""
import re
from typing import List, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class InvoiceExtractor:
    """Extract financial entries from invoice documents"""

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract entries from invoice text"""
        entries = []

        # Extract invoice number
        invoice_match = re.search(r'invoice\s*[#:]?\s*(\S+)', text, re.IGNORECASE)
        invoice_number = invoice_match.group(1) if invoice_match else None

        # Extract date
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
        entry_date = date_match.group(1) if date_match else None

        # Extract amount (simple pattern)
        amount_matches = re.findall(r'\$?(\d+[.,]\d{2})', text)

        # Extract vendor
        vendor_match = re.search(r'(?:from|vendor|supplier):\s*([^\n]+)', text, re.IGNORECASE)
        vendor = vendor_match.group(1).strip() if vendor_match else None

        # Create entry
        if amount_matches:
            total = max([float(amt.replace(',', '')) for amt in amount_matches])

            entry = {
                "source_page": 1,
                "original_description": text[:500],
                "amount": total,
                "currency": "USD",
                "vendor_name": vendor,
                "invoice_number": invoice_number,
                "entry_date": entry_date,
                "category": "expenses",
            }
            entries.append(entry)

        logger.info("invoice_extraction_complete", entries_count=len(entries))
        return entries
