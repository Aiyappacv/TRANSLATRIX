# Safe Development Test Credentials

All accounts below are created only when `SEED_DEVELOPMENT=true` or when `python scripts/seed_development.py` is run in a non-production environment.

**Password for every account:** `DevOnly!2026`

| Role | Email |
|---|---|
| Spectra Super Admin | `super.admin@translatrix.example.com` |
| Company Owner | `owner@translatrix.example.com` |
| Company Admin | `admin@translatrix.example.com` |
| Finance Manager | `finance.manager@translatrix.example.com` |
| Finance User | `finance.user@translatrix.example.com` |
| Reviewer | `reviewer@translatrix.example.com` |
| Approver | `approver@translatrix.example.com` |
| SAP Poster | `sap.poster@translatrix.example.com` |
| Integration Manager | `integrations@translatrix.example.com` |
| Auditor | `auditor@translatrix.example.com` |
| Read Only | `readonly@translatrix.example.com` |

Development company: `company@translatrix.example.com`.

When a Company Admin enables MFA for all users or privileged roles, the next login becomes a two-step TOTP flow. The first enrollment response shows a development setup secret; enter the current six-digit code from an authenticator application to finish login. Disable development seeding and use production-safe enrollment delivery before deployment.

The seed script refuses to run when `APP_ENV=production`. Change all passwords and secret keys before any shared deployment.
