"""
Create a test extraction result using direct SQL
"""
from app.database import engine
from sqlalchemy import text
from uuid import UUID
import datetime

# File ID from test
FILE_ID = "e187f20d-f25a-4a7d-b8f8-4a0c14b0f8aa"

# Sample financial document text (German to English)
SAMPLE_TEXT = """Rechnung #INV-2024-001
Datum: 15/03/2024
Betrag: €1,250.50
Steuer-ID: DE123456789
Verkäufer: Acme Corp GmbH
Kunde: Tech Solutions Ltd
Kontokode: GL-4500-001
Referenz: REF-2024-Q1-045
Gesamt: €1,500.60

Dies ist eine Testrechnung für die Übersetzung.
Alle Finanzdaten sollten exakt erhalten bleiben."""

print("Creating test extraction result using direct SQL...")
print("=" * 60)

with engine.connect() as conn:
    # Get file and tenant info
    result = conn.execute(text("""
        SELECT tenant_id, original_filename
        FROM ingested_files
        WHERE id = :file_id
    """), {"file_id": FILE_ID})

    file_info = result.fetchone()

    if not file_info:
        print(f"[ERROR] File {FILE_ID} not found!")
        exit(1)

    tenant_id = str(file_info[0])
    filename = file_info[1]

    print(f"[OK] Found file: {filename}")
    print(f"    Tenant: {tenant_id}")

    # Check if extraction exists
    result = conn.execute(text("""
        SELECT id FROM file_extraction_results WHERE file_id = :file_id
    """), {"file_id": FILE_ID})

    existing = result.fetchone()

    if existing:
        print(f"[INFO] Updating existing extraction...")
        conn.execute(text("""
            UPDATE file_extraction_results
            SET extracted_text = :text,
                status = 'completed',
                word_count = :word_count,
                confidence_score = 0.95,
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE file_id = :file_id
        """), {"text": SAMPLE_TEXT, "word_count": len(SAMPLE_TEXT.split()), "file_id": FILE_ID})
    else:
        print(f"[INFO] Creating new extraction...")
        conn.execute(text("""
            INSERT INTO file_extraction_results (
                tenant_id, file_id, method, use_ocr, status,
                extracted_text, confidence_score, page_count, word_count,
                has_tables, has_images, processing_time_seconds,
                parser_version, completed_at
            ) VALUES (
                :tenant_id, :file_id, 'native_text', false, 'completed',
                :text, 0.95, 1, :word_count,
                false, false, 0.5,
                'test-v1', CURRENT_TIMESTAMP
            )
        """), {
            "tenant_id": tenant_id,
            "file_id": FILE_ID,
            "text": SAMPLE_TEXT,
            "word_count": len(SAMPLE_TEXT.split())
        })

    conn.commit()

    print(f"[SUCCESS] Test extraction created!")
    print(f"\nExtracted text preview:")
    print(f"{SAMPLE_TEXT[:150]}...")
    print(f"\nWord count: {len(SAMPLE_TEXT.split())}")
    print(f"\nReady to test translation!")
    print(f"  File ID: {FILE_ID}")
    print(f"  Source: de (German)")
    print(f"  Target: en (English)")

print("=" * 60)
