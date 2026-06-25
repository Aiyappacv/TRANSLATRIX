"""Spreadsheet Entry Extractor"""
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class SpreadsheetExtractor:
    """Extract financial entries from spreadsheet data"""

    def extract(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract entries from spreadsheet tables"""
        entries = []

        for table in tables:
            headers = [str(h).lower() for h in table.get("headers", [])]
            rows = table.get("rows", [])

            # Find relevant columns
            amount_col = self._find_column(headers, ["amount", "total", "value"])
            desc_col = self._find_column(headers, ["description", "item", "details"])
            date_col = self._find_column(headers, ["date"])

            for row_idx, row in enumerate(rows):
                if len(row) <= max(filter(None, [amount_col, desc_col, date_col])):
                    continue

                try:
                    amount = float(str(row[amount_col]).replace(',', '').replace('$', '')) if amount_col is not None else None
                    if amount and amount > 0:
                        entry = {
                            "source_row": row_idx + 1,
                            "original_description": str(row[desc_col]) if desc_col is not None else "",
                            "amount": amount,
                            "currency": "USD",
                            "entry_date": str(row[date_col]) if date_col is not None else None,
                        }
                        entries.append(entry)
                except (ValueError, IndexError):
                    continue

        logger.info("spreadsheet_extraction_complete", entries_count=len(entries))
        return entries

    def _find_column(self, headers: List[str], keywords: List[str]) -> int:
        """Find column index by keywords"""
        for idx, header in enumerate(headers):
            if any(kw in header for kw in keywords):
                return idx
        return None
