# TRANSLATRIX PRO - Backend

Enterprise SaaS AI-Finance Automation Platform Backend

## Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Queue**: Celery + Redis
- **Storage**: AWS S3 / Azure Blob / MinIO
- **OCR**: PaddleOCR + Cloud OCR fallback
- **Translation**: OpenAI / Azure OpenAI / DeepL
- **Auth**: JWT with RBAC
- **Containerization**: Docker + Kubernetes

## Features

- Multi-tenant SaaS architecture
- Company registration and onboarding
- Shared financial link ingestion
- PaddleOCR and cloud OCR integration
- Multi-language translation with preservation of financial data
- Financial entry extraction and classification
- SAP S/4HANA integration
- Extensible accounting software connectors (QuickBooks, Xero, Zoho, etc.)
- Review and approval workflows
- Comprehensive audit logging
- Analytics and monitoring

## Project Structure

```
backend-python/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection and session
│   ├── dependencies.py        # Dependency injection
│   ├── exceptions.py          # Custom exceptions
│   ├── core/                  # Core utilities
│   │   ├── security.py
│   │   ├── jwt.py
│   │   ├── permissions.py
│   │   ├── middleware.py
│   │   ├── tenant_context.py
│   │   └── ...
│   ├── modules/               # Feature modules
│   │   ├── auth/
│   │   ├── companies/
│   │   ├── sap/
│   │   └── ...
│   └── workers/               # Celery workers
├── migrations/                # Alembic migrations
├── tests/                     # Test suite
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Install dependencies:

```bash
pip install poetry
poetry install
```

4. Run database migrations:

```bash
alembic upgrade head
```

5. Start the development server:

```bash
uvicorn app.main:app --reload
```

### Using Docker

```bash
docker-compose up -d
```

## Development

### Run Tests

```bash
pytest
pytest --cov=app tests/
```

### Code Formatting

```bash
black app/
ruff check app/
```

### Create Migration

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Start Celery Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

See `.env.example` for all configuration options.

## Production Deployment

1. Set production environment variables
2. Use proper secrets management (Vault, AWS Secrets Manager)
3. Enable HTTPS
4. Configure database backups
5. Set up monitoring and alerting
6. Scale workers as needed

## Security

- JWT-based authentication
- Role-based access control (RBAC)
- Tenant isolation on all queries
- Encrypted secrets storage
- Audit logging for all critical actions
- File validation and virus scanning
- Idempotency for financial postings

## License

Proprietary - TRANSLATRIX PRO
