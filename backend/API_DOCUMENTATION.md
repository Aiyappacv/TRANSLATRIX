# TRANSLATRIX PRO - API Documentation

## Base URL
```
Production: https://api.translatrix.pro
Development: http://localhost:8000
```

All API endpoints are prefixed with `/api/v1`

---

## Authentication

### Register New Tenant
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePassword123!",
  "company_name": "Acme Corp",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePassword123!"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Use Token
```http
GET /api/v1/users/me
Authorization: Bearer eyJ...
```

---

## File Management

### Upload File
```http
POST /api/v1/files/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <binary>
company_id: uuid
```

### List Files
```http
GET /api/v1/files?page=1&page_size=50
Authorization: Bearer {token}
```

### Get File Details
```http
GET /api/v1/files/{file_id}
Authorization: Bearer {token}
```

---

## OCR & Extraction

### Trigger OCR
```http
POST /api/v1/files/{file_id}/ocr
Authorization: Bearer {token}

{
  "provider": "paddleocr",
  "languages": ["en", "es"]
}
```

### Get OCR Result
```http
GET /api/v1/files/{file_id}/ocr-result
Authorization: Bearer {token}
```

### Extract Financial Data
```http
POST /api/v1/files/{file_id}/extract
Authorization: Bearer {token}
```

---

## Translation

### Translate Document
```http
POST /api/v1/files/{file_id}/translate
Authorization: Bearer {token}

{
  "target_language": "en",
  "provider": "openai"
}
```

### Get Translation Result
```http
GET /api/v1/files/{file_id}/translation-result
Authorization: Bearer {token}
```

---

## Financial Entries

### Create Entry
```http
POST /api/v1/entries
Authorization: Bearer {token}

{
  "file_id": "uuid",
  "document_type": "invoice",
  "extracted_data": {...}
}
```

### List Entries
```http
GET /api/v1/entries?status=draft&page=1&page_size=50
Authorization: Bearer {token}
```

### Update Entry
```http
PATCH /api/v1/entries/{entry_id}
Authorization: Bearer {token}

{
  "extracted_data": {...}
}
```

---

## Classification

### Classify Entry
```http
POST /api/v1/classification/classify/{entry_id}
Authorization: Bearer {token}
```

### Bulk Classify
```http
POST /api/v1/classification/bulk-classify
Authorization: Bearer {token}

{
  "entry_ids": ["uuid1", "uuid2"]
}
```

---

## Review & Approval

### Create Review Task
```http
POST /api/v1/review-tasks
Authorization: Bearer {token}

{
  "entry_id": "uuid",
  "assigned_to": "user-uuid"
}
```

### Submit Corrections
```http
POST /api/v1/review-tasks/{task_id}/corrections
Authorization: Bearer {token}

{
  "corrections": {...},
  "review_notes": "Fixed account codes"
}
```

### Approve Entry
```http
POST /api/v1/entries/{entry_id}/approve
Authorization: Bearer {token}

{
  "comments": "Looks good"
}
```

### Reject Entry
```http
POST /api/v1/entries/{entry_id}/reject
Authorization: Bearer {token}

{
  "comments": "Missing vendor information"
}
```

---

## SAP Integration

### Configure SAP Connection
```http
POST /api/v1/sap/config
Authorization: Bearer {token}

{
  "base_url": "https://sap.company.com",
  "client": "100",
  "username": "sap_user",
  "password": "sap_password",
  "environment": "production"
}
```

### Test SAP Connection
```http
POST /api/v1/sap/test-connection
Authorization: Bearer {token}
```

### Post Entry to SAP
```http
POST /api/v1/sap/entries/{entry_id}/post
Authorization: Bearer {token}

{
  "document_type": "SA",
  "force_repost": false
}
```

### Batch Post to SAP
```http
POST /api/v1/sap/entries/batch-post
Authorization: Bearer {token}

{
  "entry_ids": ["uuid1", "uuid2"],
  "document_type": "SA"
}
```

---

## Accounting Integrations

### List Available Connectors
```http
GET /api/v1/accounting-integrations
Authorization: Bearer {token}

Response:
{
  "connectors": [
    {
      "id": "quickbooks",
      "name": "QuickBooks Online",
      "capabilities": ["journal_entries", "invoices"],
      "status": "placeholder"
    },
    {
      "id": "manual_json",
      "name": "Manual JSON Export",
      "capabilities": ["journal_entries", "invoices"],
      "status": "active"
    }
  ]
}
```

### Test Connector
```http
POST /api/v1/accounting-integrations/{connector_id}/test
Authorization: Bearer {token}

{
  "connector_id": "webhook",
  "config": {
    "webhook_url": "https://your-endpoint.com/webhook"
  }
}
```

### Post to Connector
```http
POST /api/v1/accounting-integrations/{connector_id}/post/{entry_id}
Authorization: Bearer {token}

{
  "config": {
    "webhook_url": "https://your-endpoint.com/webhook"
  }
}
```

---

## Analytics

### Dashboard Statistics
```http
GET /api/v1/analytics/dashboard?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}

Response:
{
  "period": {...},
  "files": {"total": 150, "processed": 145},
  "entries": {"total": 200},
  "reviews": {"pending": 10, "completed": 180},
  "sap_posting": {"posted": 170, "failed": 5}
}
```

### Processing Metrics
```http
GET /api/v1/analytics/processing-metrics?period_type=daily&limit=30
Authorization: Bearer {token}
```

---

## Audit Logs

### Query Audit Logs
```http
GET /api/v1/audit/logs?entity_type=entry&action=create&page=1
Authorization: Bearer {token}
```

### Get Entity History
```http
GET /api/v1/audit/logs/entity/{entity_type}/{entity_id}
Authorization: Bearer {token}
```

---

## Notifications

### Get Notifications
```http
GET /api/v1/notifications?unread_only=true&page=1
Authorization: Bearer {token}
```

### Mark as Read
```http
POST /api/v1/notifications/{notification_id}/read
Authorization: Bearer {token}
```

### Mark All as Read
```http
POST /api/v1/notifications/mark-all-read
Authorization: Bearer {token}
```

---

## Monitoring

### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "app_name": "TRANSLATRIX PRO",
  "environment": "production"
}
```

### Detailed Health Check
```http
GET /api/v1/monitoring/health/detailed

Response:
{
  "overall_status": "healthy",
  "checks": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "storage": {"status": "healthy"},
    "celery": {"status": "healthy"}
  }
}
```

### Prometheus Metrics
```http
GET /api/v1/monitoring/metrics
```

---

## Error Responses

### Standard Error Format
```json
{
  "message": "Error description",
  "details": {
    "field": "Additional context"
  }
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `502` - External Service Error

---

## Rate Limiting

Default limits:
- 60 requests per minute per user
- 1000 requests per hour per tenant

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200
```

---

## Pagination

List endpoints support pagination:
```http
GET /api/v1/entries?page=1&page_size=50

Response:
{
  "items": [...],
  "total": 500,
  "page": 1,
  "page_size": 50,
  "pages": 10
}
```

---

## Webhooks

Configure webhooks for events:

### Events
- `file.uploaded`
- `file.processed`
- `entry.created`
- `entry.approved`
- `entry.posted_to_sap`
- `review.assigned`
- `review.completed`

### Webhook Payload
```json
{
  "event": "entry.approved",
  "timestamp": "2024-01-15T10:30:00Z",
  "tenant_id": "uuid",
  "data": {
    "entry_id": "uuid",
    "approved_by": "uuid"
  }
}
```

---

## SDK Examples

### Python
```python
import requests

BASE_URL = "https://api.translatrix.pro/api/v1"
token = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Upload file
with open("invoice.pdf", "rb") as f:
    files = {"file": f}
    data = {"company_id": "company-uuid"}
    response = requests.post(
        f"{BASE_URL}/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data
    )
```

### JavaScript/TypeScript
```typescript
const BASE_URL = "https://api.translatrix.pro/api/v1";
const token = "your-jwt-token";

// Get entries
const response = await fetch(`${BASE_URL}/entries`, {
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  }
});

const entries = await response.json();
```

---

## Postman Collection

Import our Postman collection: [Download](https://api.translatrix.pro/postman-collection.json)

---

**Last Updated**: June 2024
**API Version**: v1
