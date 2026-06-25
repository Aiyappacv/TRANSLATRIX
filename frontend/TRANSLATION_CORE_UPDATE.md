# TRANSLATRIX PRO — Translation Core Update

## Updated workflow

The translation page now supports two input modes:

1. Manual file upload
2. Pasted OCR or financial text

Both modes use the same processing flow:

`Input → OCR/direct parsing → English translation → financial categorization → reviewer confirmation`

## Added frontend capabilities

- Clean, balanced translation workspace
- Single-file drag-and-drop upload
- PDF, image, CSV, XLS/XLSX, DOCX, and TXT selection
- Automatic source-language detection option
- Translation-provider selection
- Financial-value preservation controls
- Side-by-side original and English evidence
- Automatic category and subcategory suggestion
- Categorization confidence and explanation
- Suggested GL account and account name
- Detected vendor, amount, currency, and document type
- Editable reviewer category and subcategory
- Reviewer note and classification confirmation
- Recent translation jobs and segment-level review

## Backend endpoints represented by the frontend

```text
POST  /files/upload
POST  /translations/translate
POST  /translations/files/:fileId/translate
GET   /translations/:translationId/classification
POST  /translations/:translationId/classify
PATCH /translations/:translationId/classification
POST  /translations/:translationId/approve
POST  /translations/:translationId/retry
```

## Important backend note

The translation workbench now calls the real FastAPI compatibility API and persists jobs, classifications, approvals, corrections, and file metadata in the backend. Live OCR and provider-quality translation still require the optional OCR packages and configured third-party credentials described in the integrated product limitations.

## Validation completed

- TypeScript strict typecheck: passed
- ESLint: passed
- Unit and integration tests: 34 passed
- Production Vite build: passed
