# Authentication configuration

This deployment package does not include example users, shared passwords, prefilled credentials, or frontend-generated sessions.

Authentication is provided by the backend endpoints:

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/refresh`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

Create users and role assignments through the backend or the authorized Users & Roles workflow.
