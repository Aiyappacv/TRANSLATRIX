# TRANSLATRIX PRO — Backend API Contract

The frontend service layer is typed and ready for FastAPI integration.

## Core endpoint groups

- `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/me`
- `/companies`, `/companies/current`, `/companies/:id/users`
- `/onboarding`, `/onboarding/draft`, `/onboarding/submit`
- `/shared-links`, `/shared-links/:id`, `/shared-links/validate`
- `/batches`, `/batches/:id`, `/batches/:id/retry`
- `/files`, `/files/:id`, `/files/:id/ocr/retry`, `/files/:id/translation/retry`
- `/entries`, `/entries/:id`, `/entries/validation-issues`
- `/review`, `/review/:id/approve`, `/review/:id/reject`
- `/sap/postings`, `/sap/payload`, `/integrations`
- `/analytics`, `/audit`, `/settings`, `/super-admin`
