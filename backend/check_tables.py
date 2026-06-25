import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from env
db_url = os.getenv("DATABASE_URL")
print(f"Connecting to database...")

try:
    # Parse the database URL
    # postgresql://user:pass@host:port/dbname
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Check for OCR tables
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        ORDER BY table_name
    """)

    tables = [row[0] for row in cur.fetchall()]
    print(f"\nAll tables in database:")
    for table in tables:
        print(f"  - {table}")

    ocr_tables = [t for t in tables if 'ocr' in t.lower()]
    print(f"\nOCR-related tables:")
    for table in ocr_tables:
        print(f"  - {table}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")
