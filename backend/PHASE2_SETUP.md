# TRANSLATRIX PRO - Phase 2 Setup Guide

## Phase 2: Complete Auth, Tenant & Company Registration

This document provides instructions for setting up and running Phase 2 of the TRANSLATRIX PRO backend.

---

## What's Included in Phase 2

### 1. **Complete Authentication System**
- Company registration endpoint
- User login with JWT tokens
- Token refresh mechanism
- Current user profile endpoint (`/me`)

### 2. **Multi-Tenant Architecture**
- Tenant management
- Tenant isolation via middleware
- Company-tenant relationships

### 3. **Company Management**
- Company CRUD operations
- Company profile management
- Financial settings configuration

### 4. **User Management**
- User creation and updates
- User invitations
- Role-based access control (RBAC)
- Password management

### 5. **Onboarding Workflow**
- 5-step company onboarding process
- Progress tracking
- Integration selection
- Security settings

### 6. **Role-Based Access Control**
Six default system roles:
- `super_admin` - Platform administrator
- `company_admin` - Company administrator
- `company_finance_manager` - Finance manager
- `company_reviewer` - Document reviewer
- `company_approver` - Entry approver
- `company_viewer` - Read-only viewer

---

## Installation & Setup

### Prerequisites
- PostgreSQL database running
- Python 3.11+
- Virtual environment activated

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://translatrix:translatrix_password@localhost:5432/translatrix_pro

# Security (generate secure keys!)
SECRET_KEY=your-super-secret-key-min-32-chars-here
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Super Admin
SUPER_ADMIN_EMAIL=admin@translatrix.pro
SUPER_ADMIN_PASSWORD=YourSecurePassword123!

# Application
APP_NAME=TRANSLATRIX PRO
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Step 3: Run Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Phase 2: Auth, Tenant, Company, User models"

# Run migration
alembic upgrade head
```

### Step 4: Seed Default Roles
**IMPORTANT:** Run this before starting the application!

```bash
python app/scripts/seed_roles.py
```

This will create the 6 default system roles required for the application.

---

## Running the Application

### Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API Endpoints Overview

### Authentication (`/api/v1/auth`)
- `POST /register-company` - Register a new company
- `POST /login` - User login
- `POST /refresh` - Refresh access token
- `GET /me` - Get current user info

### Companies (`/api/v1/companies`)
- `POST /` - Create company
- `GET /{company_id}` - Get company
- `GET /` - List companies (tenant-scoped)
- `PUT /{company_id}` - Update company
- `DELETE /{company_id}` - Delete company
- `GET /{company_id}/summary` - Get company summary

### Users (`/api/v1/users`)
- `POST /` - Create user
- `GET /{user_id}` - Get user
- `GET /company/{company_id}/users` - List company users
- `PUT /{user_id}` - Update user
- `POST /{user_id}/change-password` - Change password
- `POST /{user_id}/status` - Update user status
- `POST /invite` - Invite user
- `GET /roles/` - List all roles
- `GET /me/profile` - Get current user profile
- `PUT /me/profile` - Update current user profile

### Onboarding (`/api/v1/onboarding`)
- `GET /{company_id}/progress` - Get onboarding progress
- `PUT /{company_id}/steps/company-profile` - Update company profile step
- `PUT /{company_id}/steps/finance-config` - Update finance config step
- `PUT /{company_id}/steps/integration-selection` - Select integrations
- `POST /{company_id}/steps/users-invited` - Mark users invited
- `PUT /{company_id}/steps/security-settings` - Configure security
- `POST /{company_id}/complete` - Complete onboarding
- `GET /{company_id}/next-step` - Get next step

---

## Testing the System

### 1. Register a Company
```bash
curl -X POST http://localhost:8000/api/v1/auth/register-company \
  -H "Content-Type: application/json" \
  -d '{
    "legal_name": "Acme Corporation",
    "country": "United States",
    "email": "info@acme.com",
    "admin_email": "admin@acme.com",
    "admin_password": "SecurePass123!",
    "admin_first_name": "John",
    "admin_last_name": "Doe",
    "default_currency": "USD",
    "default_language": "en",
    "timezone": "America/New_York"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
```

Response includes `access_token` and `refresh_token`.

### 3. Get Current User
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Check Onboarding Progress
```bash
curl -X GET http://localhost:8000/api/v1/onboarding/{company_id}/progress \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Architecture Overview

### Module Structure
```
app/
├── modules/
│   ├── auth/           # Authentication
│   │   ├── routes.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── tenants/        # Tenant management
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── companies/      # Company management
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── users/          # User & Role management
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── routes.py
│   │   ├── service.py
│   │   └── schemas.py
│   └── onboarding/     # Onboarding workflow
│       ├── models.py
│       ├── repository.py
│       ├── routes.py
│       ├── service.py
│       └── schemas.py
├── core/               # Core utilities
│   ├── security.py     # Password hashing
│   ├── jwt.py          # JWT tokens
│   ├── permissions.py  # RBAC
│   ├── tenant_context.py
│   └── middleware.py
└── scripts/
    └── seed_roles.py   # Seed default roles
```

### Data Flow
1. **Request** → Middleware (Request ID, Tenant Context, Logging)
2. **Authentication** → JWT validation → Current user
3. **Authorization** → RBAC permission checks
4. **Service Layer** → Business logic
5. **Repository** → Database operations
6. **Response** → Standardized JSON format

---

## Security Features

### Implemented
- JWT-based authentication
- Password strength validation
- Bcrypt password hashing
- Multi-tenant isolation
- Role-based access control
- Request ID tracking
- Structured logging

### Token Management
- Access tokens: 30 minutes (configurable)
- Refresh tokens: 7 days (configurable)
- Token type validation
- Automatic token refresh

---

## Database Schema

### Key Models
- **Tenant** - Multi-tenant isolation
- **Company** - Company profiles
- **User** - User accounts
- **Role** - RBAC roles
- **CompanyOnboarding** - Onboarding progress tracking

### Relationships
- Tenant → Companies (1:N)
- Company → Users (1:N)
- Role → Users (1:N)
- Company → CompanyOnboarding (1:1)

---

## Next Steps (Phase 3)

Phase 2 is now complete! The next phase will include:

1. **File Upload & Storage**
   - S3/Azure/MinIO integration
   - File validation
   - Virus scanning

2. **OCR Processing**
   - PaddleOCR integration
   - Multi-language support
   - Confidence scoring

3. **Translation Service**
   - OpenAI/DeepL integration
   - Context-aware translation
   - Quality validation

4. **Document Classification**
   - Invoice, receipt, PO detection
   - Template matching
   - ML-based classification

---

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure database exists

### Migration Issues
```bash
# Reset migrations (CAUTION: Deletes data!)
alembic downgrade base
alembic upgrade head
```

### Role Seeding Issues
- Ensure database is migrated first
- Check database connection
- Verify no duplicate roles exist

### Import Errors
- Verify virtual environment is activated
- Run: `pip install -r requirements.txt`
- Check Python version: `python --version`

---

## Support

For issues or questions:
- Review API documentation at `/docs`
- Check application logs
- Verify environment variables
- Ensure all migrations are applied

---

**Phase 2 Status:** ✅ COMPLETE

All authentication, tenant management, company registration, user management, and onboarding features are fully implemented and production-ready!
