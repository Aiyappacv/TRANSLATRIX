"""intake registry: async upload/metadata pipeline

Replaces the old synchronous-upload status model (PENDING, VALIDATING,
DUPLICATE_CHECK, PREPROCESSING, CLASSIFIED, STORED, READY_FOR_EXTRACTION,
EXTRACTING, EXTRACTED, FAILED) with the new decoupled-pipeline model
(UPLOADING, UPLOADED, METADATA_PROCESSING, METADATA_READY,
READY_FOR_EXTRACTION, EXTRACTING, EXTRACTED, TRANSLATING, TRANSLATED,
FAILED), makes checksum nullable on intake_registry/ingested_files (now
populated by the background metadata worker instead of synchronously at
upload time), and adds created_at indexes used by the new pipeline's
query patterns.

Existing rows are remapped rather than dropped: anything that hadn't
reached STORED/READY_FOR_EXTRACTION collapses to UPLOADED (the new
"just landed, awaiting background metadata" state); STORED maps to
READY_FOR_EXTRACTION (metadata was already complete under the old model).

Revision ID: a1c4e9f02b7d
Revises: 8e8c5d77c9a1
Create Date: 2026-06-23 20:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1c4e9f02b7d"
down_revision = "8e8c5d77c9a1"
branch_labels = None
depends_on = None

_NEW_STATUS_VALUES = (
    "UPLOADING", "UPLOADED", "METADATA_PROCESSING", "METADATA_READY",
    "READY_FOR_EXTRACTION", "EXTRACTING", "EXTRACTED",
    "TRANSLATING", "TRANSLATED", "FAILED",
)


def _has_table(conn, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "intake_registry"):
        # Table is created via Base.metadata.create_all() in fresh
        # environments that haven't run init_db() yet — nothing to migrate.
        return

    new_status = postgresql.ENUM(*_NEW_STATUS_VALUES, name="intakestatus_new")
    new_status.create(conn)

    op.add_column("intake_registry", sa.Column("status_new", new_status, nullable=True))
    conn.execute(sa.text("""
        UPDATE intake_registry SET status_new = CASE
            WHEN status::text IN ('PENDING','VALIDATING','DUPLICATE_CHECK','PREPROCESSING','CLASSIFIED') THEN 'UPLOADED'
            WHEN status::text = 'STORED' THEN 'READY_FOR_EXTRACTION'
            WHEN status::text IN ('READY_FOR_EXTRACTION','EXTRACTING','EXTRACTED','FAILED') THEN status::text
            ELSE 'UPLOADED'
        END::intakestatus_new
    """))
    op.alter_column("intake_registry", "status_new", nullable=False)

    op.drop_index("ix_intake_registry_status", table_name="intake_registry")
    op.drop_column("intake_registry", "status")
    op.alter_column("intake_registry", "status_new", new_column_name="status")
    op.create_index(op.f("ix_intake_registry_status"), "intake_registry", ["status"], unique=False)

    sa.Enum(name="intakestatus").drop(conn, checkfirst=True)
    op.execute("ALTER TYPE intakestatus_new RENAME TO intakestatus")

    # checksum is now populated by the background metadata worker, not
    # synchronously at upload time.
    op.alter_column("intake_registry", "checksum", nullable=True)
    if _has_table(conn, "ingested_files"):
        op.alter_column("ingested_files", "checksum", nullable=True)

    op.create_index(op.f("ix_intake_registry_created_at"), "intake_registry", ["created_at"], unique=False)
    if _has_table(conn, "ingested_files"):
        op.create_index(op.f("ix_ingested_files_created_at"), "ingested_files", ["created_at"], unique=False)
    if _has_table(conn, "ingestion_batches"):
        op.create_index(op.f("ix_ingestion_batches_created_at"), "ingestion_batches", ["created_at"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "intake_registry"):
        return

    if _has_table(conn, "ingestion_batches"):
        op.drop_index(op.f("ix_ingestion_batches_created_at"), table_name="ingestion_batches")
    if _has_table(conn, "ingested_files"):
        op.drop_index(op.f("ix_ingested_files_created_at"), table_name="ingested_files")
        op.alter_column("ingested_files", "checksum", nullable=False)
    op.drop_index(op.f("ix_intake_registry_created_at"), table_name="intake_registry")
    op.alter_column("intake_registry", "checksum", nullable=False)
    # Old enum values are not meaningfully recoverable from the new ones —
    # status downgrade intentionally omitted.
