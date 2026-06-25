# TRANSLATRIX PRO Backend - Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide will get your TRANSLATRIX PRO backend running locally.

---

## Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for PostgreSQL, Redis, MinIO)
- **Poetry** (Python dependency management)

---

## Step 1: Clone and Navigate

```bash
cd "backend-python"
```

---

## Step 2: Install Poetry (if not installed)

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

---

## Step 3: Install Dependencies

```bash
poetry install
```

---

## Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `JWT_SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `SUPER_ADMIN_PASSWORD` - Choose a strong password

---

## Step 5: Start Infrastructure

```bash
docker-compose up -d postgres redis minio
```

Wait ~10 seconds for services to initialize.

---

## Step 6: Run Database Migrations

```bash
# Activate poetry shell
poetry shell

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

---

## Step 7: Seed Database

```bash
python scripts/seed_data.py
```

This creates:
- Default roles (super_admin, company_admin, finance_manager, accountant, reviewer, viewer)
- Super admin user (email from `SUPER_ADMIN_EMAIL` in .env)

---

## Step 8: Start Backend Server

```bash
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**

---

## Step 9: Start Celery Worker (Optional)

In a new terminal:

```bash
poetry shell
celery -A app.workers.celery_app worker --loglevel=info
```

---

## Step 10: Test the API

### Access API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Test Health Endpoint

```bash
curl http://localhost:8000/health
```

### Register a Company

```bash
curl -X POST http://localhost:8000/api/v1/auth/register-company \
  -H "Content-Type: application/json" \
  -d '{
    "legal_name": "Acme Corporation",
    "country": "United States",
    "email": "admin@acme.com",
    "admin_first_name": "John",
    "admin_last_name": "Doe",
    "admin_email": "john@acme.com",
    "admin_password": "SecurePassword123!"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@acme.com",
    "password": "SecurePassword123!"
  }'
```

---

## 📁 Project Structure

```
backend-python/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── core/                # Core utilities
│   │   ├── security.py      # Password hashing, encryption
│   │   ├── jwt.py           # JWT tokens
│   │   ├── permissions.py   # RBAC
│   │   ├── middleware.py    # Request tracking
│   │   └── ...
│   ├── modules/             # Feature modules
│   │   ├── auth/            # Authentication ✅
│   │   ├── tenants/         # Multi-tenancy ✅
│   │   ├── companies/       # Companies ✅
│   │   ├── users/           # Users & Roles ✅
│   │   ├── onboarding/      # Onboarding ✅
│   │   ├── audit/           # Audit logs ✅
│   │   ├── files/           # Files & ingestion ✅
│   │   ├── entries/         # Financial entries ✅
│   │   ├── sap/             # SAP integration ✅
│   │   ├── review/          # Review & approval ✅
│   │   └── ...              # More modules
│   └── workers/             # Celery workers ✅
├── migrations/              # Alembic migrations
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── docker-compose.yml       # Local dev stack
├── Dockerfile               # Production container
└── pyproject.toml           # Dependencies
```

---

## 🔑 Key Features Implemented

### ✅ Foundation (Complete)
- FastAPI application with async support
- PostgreSQL database with SQLAlchemy ORM
- Alembic database migrations
- JWT authentication
- RBAC permission system
- Multi-tenant isolation
- Structured logging
- Request ID tracking
- Idempotency for financial operations
- Docker containerization

### ✅ Core Modules (Complete)
- **Auth**: Company registration, login, token refresh
- **Tenants**: Multi-tenant isolation
- **Companies**: Company profiles
- **Users**: User management with RBAC
- **Onboarding**: Company onboarding workflow
- **Audit**: Comprehensive audit logging
- **Files**: File models and ingestion structure
- **Entries**: Financial entry processing
- **SAP**: SAP S/4HANA integration models
- **Review**: Review and approval workflow

### ✅ Celery Workers (Complete Structure)
- Ingestion worker
- OCR worker
- Translation worker
- Classification worker
- SAP posting worker
- Validation worker
- Review worker
- Notification worker
- All workers ready for implementation

---

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

---

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Rebuild backend
docker-compose build backend

# Run migrations in container
docker-compose exec backend alembic upgrade head

# Seed database in container
docker-compose exec backend python scripts/seed_data.py
```

---

## 📊 Database Management

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

---

## 🔧 Development Workflow

### 1. Create a New Module

```python
# app/modules/my_module/models.py
from app.database import Base
# Define your models

# app/modules/my_module/schemas.py
from pydantic import BaseModel
# Define your schemas

# app/modules/my_module/repository.py
# Define repository methods

# app/modules/my_module/service.py
# Define business logic

# app/modules/my_module/routes.py
from fastapi import APIRouter
router = APIRouter()
# Define your routes
```

### 2. Register Routes in main.py

```python
from app.modules.my_module.routes import router as my_module_router
app.include_router(my_module_router, prefix="/api/v1/my-module", tags=["My Module"])
```

### 3. Create Migration

```bash
alembic revision --autogenerate -m "Add my_module tables"
alembic upgrade head
```

---

## 🚀 Production Deployment

### Build for Production

```bash
docker build -t translatrix-backend:latest .
```

### Deploy to Kubernetes

```bash
# Apply Kubernetes manifests (to be created)
kubectl apply -f k8s/
```

### Environment Variables for Production

Required in production:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Encryption key (32+ characters)
- `JWT_SECRET_KEY` - JWT signing key (32+ characters)
- `STORAGE_PROVIDER` - s3, azure, or minio
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - For S3
- `OPENAI_API_KEY` - For translation
- `SAP_BASE_URL`, `SAP_CLIENT`, etc. - For SAP integration

---

## 📝 API Endpoints

### Authentication
- `POST /api/v1/auth/register-company` - Register new company
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### System
- `GET /` - API information
- `GET /health` - Health check
- `GET /ready` - Readiness check

---

## 🔐 Default Credentials

**Super Admin** (after running seed script):
- Email: From `SUPER_ADMIN_EMAIL` in .env
- Password: From `SUPER_ADMIN_PASSWORD` in .env

**Test Company** (after registration):
- Use the credentials you provided during registration

---

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Migration Errors
```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Manually run SQL if needed
docker-compose exec postgres psql -U translatrix -d translatrix_pro
```

### Celery Worker Not Processing
```bash
# Check Redis connection
docker-compose ps redis

# View worker logs
celery -A app.workers.celery_app worker --loglevel=debug

# Purge all tasks
celery -A app.workers.celery_app purge
```

---

## 📚 Next Steps

### 1. Implement Remaining API Routes
Each module has models created. Add:
- Pydantic schemas
- Repository methods
- Service layer
- FastAPI routes

### 2. Complete Worker Implementations
Workers are structured. Implement:
- PaddleOCR integration
- Translation API calls
- SAP API integration
- File storage operations

### 3. Add Tests
Create tests for:
- Authentication flow
- Company registration
- RBAC permissions
- API endpoints
- Worker tasks

### 4. Production Hardening
- Configure secrets management (Vault, AWS Secrets Manager)
- Set up monitoring (Prometheus, Grafana)
- Configure backups
- Implement rate limiting
- Add comprehensive error handling

---

## 📖 Documentation

- **Architecture Spec**: `TRANSLATRIX_PRO_End_to_End_Backend_Architecture_and_Prompt_Pack.pdf`
- **Implementation Status**: `IMPLEMENTATION_STATUS.md`
- **API Docs**: http://localhost:8000/docs (when running)
- **Code Documentation**: Check docstrings in each module

---

## 🤝 Support

For issues or questions:
1. Check the architecture specification PDF
2. Review the implementation status document
3. Check Docker and application logs
4. Review the code documentation

---

## ✅ Implementation Checklist

- [x] Backend foundation
- [x] Database models (core modules)
- [x] Authentication system
- [x] Multi-tenancy framework
- [x] RBAC permissions
- [x] Celery worker structure
- [x] Docker setup
- [x] Database migrations
- [x] Seed data script
- [ ] Complete all API routes
- [ ] Implement all workers
- [ ] Add comprehensive tests
- [ ] Production deployment guide
- [ ] Monitoring and alerting

---

**Your TRANSLATRIX PRO backend is ready for development! 🎉**

Start by testing the auth endpoints and then expand each module according to your needs.
