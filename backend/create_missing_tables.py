"""
Quick script to create missing database tables
Run this to fix the "file_extraction_results does not exist" error
"""
from app.database import engine, Base
from app.modules.extraction.models import FileExtractionResult
from app.modules.ocr.models import OCRResult

print("Creating missing database tables...")

# Import all models to ensure they're registered with Base
print("Imported models:")
print(f"  - FileExtractionResult: {FileExtractionResult.__tablename__}")
print(f"  - OCRResult: {OCRResult.__tablename__}")

# Create all tables
print("\nCreating tables...")
Base.metadata.create_all(bind=engine)

print("\n[SUCCESS] All tables created!")
print("\nYou can now:")
print("1. Test the extraction endpoint: POST /api/v1/files/{file_id}/extract")
print("2. Run the test scripts:")
print("   - python test_extraction.py")
