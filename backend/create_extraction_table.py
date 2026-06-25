"""
Direct table creation for file_extraction_results
This bypasses SQLAlchemy's foreign key dependency checking
"""
from app.database import engine
from sqlalchemy import text

# Direct SQL to create the file_extraction_results table
create_table_sql = """
CREATE TABLE IF NOT EXISTS file_extraction_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    file_id UUID NOT NULL UNIQUE REFERENCES ingested_files(id),

    -- Extraction configuration
    method VARCHAR(50) NOT NULL,
    use_ocr BOOLEAN NOT NULL DEFAULT FALSE,

    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,

    -- Extracted content
    extracted_text TEXT,
    extracted_tables JSONB,
    extracted_metadata JSONB,

    -- Quality metrics
    confidence_score NUMERIC(5, 2),
    page_count INTEGER,
    word_count INTEGER,
    has_tables BOOLEAN NOT NULL DEFAULT FALSE,
    has_images BOOLEAN NOT NULL DEFAULT FALSE,

    -- Processing metadata
    processing_time_seconds NUMERIC(10, 2),
    parser_version VARCHAR(50),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_file_extraction_results_tenant_id ON file_extraction_results(tenant_id);
CREATE INDEX IF NOT EXISTS idx_file_extraction_results_status ON file_extraction_results(status);
"""

print("Creating file_extraction_results table...")
print("=" * 60)

with engine.connect() as conn:
    conn.execute(text(create_table_sql))
    conn.commit()
    print("[SUCCESS] file_extraction_results table created!")

    # Verify the table exists
    result = conn.execute(text("SELECT COUNT(*) FROM pg_tables WHERE tablename = 'file_extraction_results'"))
    count = result.scalar()

    if count > 0:
        print("[VERIFIED] Table exists in database!")
    else:
        print("[ERROR] Table creation may have failed!")

print("=" * 60)
print("\nYou can now test the translation endpoint:")
print("POST /api/v1/files/{file_id}/translate")
