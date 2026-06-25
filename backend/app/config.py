"""
Application Configuration
Centralized configuration management using Pydantic Settings
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "TRANSLATRIX PRO"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str = "postgresql://translatrix:translatrix_password@localhost:5432/translatrix_pro"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8
    # Development-only bypass for seeded/demo accounts. This is ignored in production.
    DEV_DISABLE_MFA: bool = False
    SEED_DEVELOPMENT: bool = True
    RUN_DB_BOOTSTRAP: bool = True

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Object Storage
    STORAGE_PROVIDER: str = "s3"  # s3, azure, minio, local
    LOCAL_STORAGE_DIR: str = "storage_data"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "translatrix-files"
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_CONTAINER_NAME: Optional[str] = None

    # MinIO Storage
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: Optional[str] = None
    MINIO_SECURE: bool = False

    # OCR Services
    OCR_PRIMARY_PROVIDER: str = "mistral"  # mistral, paddleocr, azure, aws, google
    PADDLEOCR_LANG: str = "en,es,fr,de,it,pt"
    PADDLEOCR_CONFIDENCE_THRESHOLD: float = 0.75
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    AZURE_DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_OCR_MODEL: str = "mistral-ocr-latest"
    AWS_TEXTRACT_REGION: str = "us-east-1"
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = None

    # AI / Gemini Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_EXTRACTION_MODEL: str = "gemini-2.5-pro"

    # Multi-page extraction chunking — large PDFs are split into page-range
    # chunks and sent to Gemini independently rather than as one request, so
    # a 500-page document never depends on a single call staying within
    # Gemini's output token budget (see app/modules/extraction/chunking.py).
    EXTRACTION_CHUNK_SIZE: int = 20
    MAX_EXTRACTION_WORKERS: int = 25
    EXTRACTION_MAX_RETRIES: int = 3
    EXTRACTION_RETRY_BACKOFF_BASE: float = 2.0

    # Model used for the lightweight document-classification call (page-1-only)
    # that determines which per-type schema guidance to apply. A smaller/faster
    # model works well here since this is a single-label classification task.
    EXTRACTION_CLASSIFY_MODEL: str = "gemini-2.5-flash-lite"

    # Surya OCR — neural OCR engine for scanned PDFs and images.
    # Surya is used for all OCR; Gemini receives only extracted text (no file uploads).
    SURYA_OCR_ENABLED: bool = True
    MAX_OCR_WORKERS: int = 25
    OCR_DPI: int = 200
    OCR_BATCH_SIZE: int = 25
    # Minimum average characters per page for a PDF to be considered digitally
    # generated (uses PyMuPDF fast path instead of Surya neural OCR).
    OCR_EMBEDDED_TEXT_MIN_CHARS: int = 50

    # Background job pool concurrency — metadata (checksum/page-count/
    # language/embeddings, runs on every upload) and extraction (Gemini
    # chunked extraction, can take minutes per document) are separate
    # BackgroundWorker pools so a handful of slow extraction jobs can never
    # delay the registry status update for a newly-uploaded document by
    # occupying every worker slot in a shared queue (see app/modules/ingestion/worker.py).
    METADATA_WORKER_CONCURRENCY: int = 4
    EXTRACTION_WORKER_CONCURRENCY: int = 4

    # SAP S/4HANA
    SAP_ENABLED: bool = False
    SAP_BASE_URL: Optional[str] = None
    SAP_CLIENT: Optional[str] = None
    SAP_USERNAME: Optional[str] = None
    SAP_PASSWORD: Optional[str] = None
    SAP_API_VERSION: str = "v1"

    # Accounting Integrations
    QUICKBOOKS_CLIENT_ID: Optional[str] = None
    QUICKBOOKS_CLIENT_SECRET: Optional[str] = None
    XERO_CLIENT_ID: Optional[str] = None
    XERO_CLIENT_SECRET: Optional[str] = None
    ZOHO_CLIENT_ID: Optional[str] = None
    ZOHO_CLIENT_SECRET: Optional[str] = None

    # File Upload Limits
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_TYPES: str = "pdf,docx,xlsx,csv,png,jpg,jpeg,tiff,xml,json,txt"
    FRONTEND_UPLOAD_DIR: str = "/app/data/uploads"
    # Chunk size for streaming uploads to storage — files are never fully
    # buffered in memory regardless of size (see DataIntakeService.register_upload).
    UPLOAD_CHUNK_SIZE_MB: int = 8
    # Upper bound on concurrent file uploads processed within one batch request.
    MAX_CONCURRENT_UPLOADS: int = 8

    @property
    def allowed_file_types_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_FILE_TYPES.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def upload_chunk_size_bytes(self) -> int:
        return self.UPLOAD_CHUNK_SIZE_MB * 1024 * 1024

    # Monitoring & Logging
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_PORT: int = 9090

    # Super Admin
    SUPER_ADMIN_EMAIL: str = "admin@translatrix.pro"
    SUPER_ADMIN_PASSWORD: str = Field(..., min_length=8)

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Confidence Thresholds
    CONFIDENCE_AUTO_PROCESS: float = 0.90
    CONFIDENCE_FLAG_REVIEW: float = 0.75
    CONFIDENCE_REQUIRE_MANUAL: float = 0.75

    # Retry Policies
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 2
    RETRY_BACKOFF_MULTIPLIER: float = 2.0

    # Timeout Configurations (in seconds)
    HTTP_TIMEOUT: int = 30
    SAP_TIMEOUT: int = 60
    OCR_TIMEOUT: int = 120

    # Processing Limits
    MAX_CONCURRENT_JOBS: int = 10
    MAX_BATCH_SIZE: int = 100

    # Email Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@translatrix.pro"

    # Webhook Settings
    WEBHOOK_TIMEOUT: int = 15
    WEBHOOK_MAX_RETRIES: int = 3

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENV == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENV == "development"


# Global settings instance
settings = Settings()
