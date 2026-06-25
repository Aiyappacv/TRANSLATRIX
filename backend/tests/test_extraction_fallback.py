import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.modules.extraction.adapters.mistral_fallback import MistralFallbackExtractor
from app.modules.extraction.adapters.base import ExtractionResult, ExtractionError


class TestMistralFallbackExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = MistralFallbackExtractor()
        # Create a small temporary file path (doesn't need to exist for this unit test when mocked)
        self.test_path = Path("/tmp/test_invoice.pdf")

    @patch("app.modules.extraction.adapters.mistral_fallback.MistralOCRProvider.recognize_pdf")
    def test_invoice_parsing(self, mock_recognize):
        # Mock the OCR result to return a minimal structure
        ocr = MagicMock()
        ocr.full_text = "Invoice No: INV-123\nTotal: $123.45\nVendor: ACME CORP"
        ocr.pages = [MagicMock()]
        ocr.total_pages = 1
        ocr.overall_confidence = 0.92
        mock_recognize.return_value = ocr

        result = self.extractor.extract(self.test_path, document_type="invoice")
        self.assertIsInstance(result, ExtractionResult)
        # Ensure extracted_fields exist in metadata
        self.assertIn("extracted_fields", result.metadata)
        ef = result.metadata.get("extracted_fields")
        self.assertIn("total_amount", ef)

    @patch("app.modules.extraction.adapters.mistral_fallback.MistralOCRProvider.recognize_pdf")
    def test_banking_parsing(self, mock_recognize):
        ocr = MagicMock()
        ocr.full_text = "Bank: Big Bank\nAccount No: 123456789012\nIFSC: ABCD0123456"
        ocr.pages = [MagicMock()]
        ocr.total_pages = 1
        ocr.overall_confidence = 0.85
        mock_recognize.return_value = ocr

        result = self.extractor.extract(self.test_path, document_type="banking_document")
        self.assertIsInstance(result, ExtractionResult)
        ef = result.metadata.get("extracted_fields")
        self.assertIsNotNone(ef)
        self.assertEqual(ef.get("account_number"), "123456789012")


if __name__ == "__main__":
    unittest.main()
