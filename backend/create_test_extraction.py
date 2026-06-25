"""
Create a test extraction result for testing translation
"""
from app.database import get_db
from app.modules.extraction.models import FileExtractionResult, ExtractionMethod, ExtractionStatus
from uuid import UUID
import datetime

# File ID from test
FILE_ID = "e187f20d-f25a-4a7d-b8f8-4a0c14b0f8aa"

# Sample financial document text (German to English)
SAMPLE_TEXT = """
Rechnung #INV-2024-001
Datum: 15/03/2024
Betrag: €1,250.50
Steuer-ID: DE123456789
Verkäufer: Acme Corp GmbH
Kunde: Tech Solutions Ltd
Kontokode: GL-4500-001
Referenz: REF-2024-Q1-045
Gesamt: €1,500.60

Dies ist eine Testrechnung für die Übersetzung.
Alle Finanzdaten sollten exakt erhalten bleiben.
"""

print("Creating test extraction result...")
print("=" * 60)

db = next(get_db())

try:
    # Check if file exists
    from app.modules.files.models import IngestedFile
    file = db.query(IngestedFile).filter(IngestedFile.id == UUID(FILE_ID)).first()

    if not file:
        print(f"[ERROR] File {FILE_ID} not found in database!")
        print("Please upload a file first or use a different file ID")
        exit(1)

    print(f"[OK] Found file: {file.original_filename}")
    print(f"    Tenant: {file.tenant_id}")

    # Check if extraction already exists
    existing = db.query(FileExtractionResult).filter(
        FileExtractionResult.file_id == UUID(FILE_ID)
    ).first()

    if existing:
        print(f"[INFO] Extraction already exists, updating...")
        existing.extracted_text = SAMPLE_TEXT
        existing.status = ExtractionStatus.COMPLETED
        existing.word_count = len(SAMPLE_TEXT.split())
        existing.confidence_score = 0.95
        existing.completed_at = datetime.datetime.utcnow()
    else:
        print(f"[INFO] Creating new extraction...")
        extraction = FileExtractionResult(
            tenant_id=file.tenant_id,
            file_id=file.id,
            method=ExtractionMethod.NATIVE_TEXT,
            use_ocr=False,
            status=ExtractionStatus.COMPLETED,
            extracted_text=SAMPLE_TEXT,
            extracted_tables=None,
            extracted_metadata={"test": True, "language": "de"},
            confidence_score=0.95,
            page_count=1,
            word_count=len(SAMPLE_TEXT.split()),
            has_tables=False,
            has_images=False,
            processing_time_seconds=0.5,
            parser_version="test-v1",
            completed_at=datetime.datetime.utcnow()
        )
        db.add(extraction)

    db.commit()

    print(f"[SUCCESS] Test extraction created!")
    print(f"\nExtracted text preview:")
    print(f"{SAMPLE_TEXT[:200]}...")
    print(f"\nWord count: {len(SAMPLE_TEXT.split())}")
    print(f"\nYou can now test translation with:")
    print(f"  File ID: {FILE_ID}")
    print(f"  Source language: de (German)")
    print(f"  Target language: en (English)")

except Exception as e:
    print(f"[ERROR] {e}")
    db.rollback()
finally:
    db.close()

print("=" * 60)
