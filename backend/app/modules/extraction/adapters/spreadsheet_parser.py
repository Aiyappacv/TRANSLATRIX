"""
Spreadsheet Parser Adapter
Extract data from Excel (XLSX) and CSV files
"""
from pathlib import Path
from typing import List, Dict, Any
import structlog

from .base import BaseExtractor, ExtractionResult, ExtractionError

logger = structlog.get_logger(__name__)


class SpreadsheetExtractor(BaseExtractor):
    """
    Spreadsheet extractor using pandas
    Handles Excel (.xlsx, .xls) and CSV files
    """

    def __init__(self):
        self.supported_mimes = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
            "application/vnd.ms-excel",  # .xls
            "text/csv",  # .csv
        ]

    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        """Check if this is a spreadsheet file"""
        return mime_type in self.supported_mimes or file_path.suffix.lower() in [
            ".xlsx",
            ".xls",
            ".csv",
        ]

    def extract(
        self,
        file_path: Path,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract content from spreadsheet file

        Args:
            file_path: Path to spreadsheet file
            extract_tables: Whether to extract tables (sheets)
            extract_metadata: Whether to extract metadata

        Returns:
            ExtractionResult with extracted content
        """
        try:
            import pandas as pd

            logger.info("extracting_spreadsheet", file_path=str(file_path))

            file_ext = file_path.suffix.lower()
            tables = []
            text_parts = []

            # Read based on file type
            if file_ext == ".csv":
                # CSV file - single sheet
                df = pd.read_csv(file_path)
                sheet_name = "Sheet1"
                tables, text_parts = self._process_dataframe(df, sheet_name)

            else:
                # Excel file - multiple sheets
                excel_file = pd.ExcelFile(file_path)

                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheet_tables, sheet_text = self._process_dataframe(df, sheet_name)
                    tables.extend(sheet_tables)
                    text_parts.extend(sheet_text)

            full_text = "\n\n".join(text_parts)

            # Metadata (basic for now)
            metadata = {
                "file_type": file_ext,
                "sheet_count": len(tables) if file_ext != ".csv" else 1,
            }

            # Spreadsheets have structured data - high confidence
            confidence = 0.99 if tables else 0.0

            logger.info(
                "spreadsheet_extraction_complete",
                sheets=len(tables),
                text_length=len(full_text),
                confidence=confidence,
            )

            return ExtractionResult(
                text=full_text,
                tables=tables,
                metadata=metadata,
                page_count=len(tables),  # Use sheet count as page count
                confidence=confidence,
            )

        except ImportError as e:
            raise ExtractionError(f"Required pandas library not installed: {str(e)}")
        except Exception as e:
            logger.error("spreadsheet_extraction_error", error=str(e), file_path=str(file_path))
            raise ExtractionError(f"Failed to extract spreadsheet content: {str(e)}")

    def _process_dataframe(
        self, df: Any, sheet_name: str
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Process a pandas DataFrame into table structure and text

        Args:
            df: Pandas DataFrame
            sheet_name: Name of the sheet

        Returns:
            Tuple of (tables list, text parts list)
        """
        tables = []
        text_parts = []

        if df.empty:
            return tables, text_parts

        # Convert DataFrame to table structure
        headers = df.columns.tolist()
        rows = df.values.tolist()

        # Replace NaN with empty string
        import numpy as np
        rows = [
            [str(cell) if not (isinstance(cell, float) and np.isnan(cell)) else "" for cell in row]
            for row in rows
        ]

        tables.append({
            "sheet_name": sheet_name,
            "headers": [str(h) for h in headers],
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(headers),
        })

        # Convert to text representation
        text_parts.append(f"Sheet: {sheet_name}")
        text_parts.append(f"Columns: {', '.join(str(h) for h in headers)}")
        text_parts.append(f"Rows: {len(rows)}")

        return tables, text_parts

    def get_supported_formats(self) -> List[str]:
        """Return supported MIME types"""
        return self.supported_mimes
