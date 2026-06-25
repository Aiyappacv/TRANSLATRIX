# TRANSLATRIX PRO Frontend

Production-ready React and TypeScript frontend for a multi-tenant financial-document automation platform. The application covers company onboarding, ingestion, OCR, translation, accounting extraction, human review, SAP/accounting posting, platform administration, role-specific dashboards, settings, analytics, auditability, and production hardening through Phase 14.

## Technology stack

- React 18, TypeScript, Vite 8, React Router 7
- Tailwind CSS and Radix/ShadCN-style UI primitives
- TanStack Query and TanStack Table
- Zustand authentication, tenant, and UI state
- React Hook Form and Zod validation
- Recharts analytics
- Lazy-loaded Monaco JSON viewer and React PDF viewer
- Vitest, React Testing Library, MSW, and Playwright

## Requirements

- Node.js 20.19+ or 22.12+
- npm 10+

## Local setup

```bash
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`.

Production authentication is backend-driven. This package contains no example login accounts, shared passwords, or prefilled credentials. The production service layer always uses the backend API.

## Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `VITE_APP_NAME` | Browser/app name | `TRANSLATRIX PRO` |
| `VITE_API_BASE_URL` | Backend API root | `https://api.example.com/api/v1` |
| `VITE_ENVIRONMENT` | Environment label | `local`, `staging`, `production` |
| `VITE_MAINTENANCE_MODE` | Replace the router with maintenance UI | `false` |
| `VITE_SENTRY_DSN` | Reserved error-monitoring DSN | empty locally |
| `VITE_FEATURE_ROLE_DASHBOARDS` | Role dashboard feature flag | `true` |
| `VITE_FEATURE_CLOUD_OCR_FALLBACK` | Cloud OCR fallback feature flag | `true` |
| `VITE_FEATURE_SAP_POSTING` | SAP posting feature flag | `true` |
| `VITE_FEATURE_ACCOUNTING_CONNECTORS` | Accounting connector feature flag | `true` |
| `VITE_FEATURE_ADVANCED_AUDIT_DIFF` | JSON audit diff feature flag | `true` |

Never commit real secrets. Browser environment variables are visible to the client. Store credentials, SAP secrets, OAuth client secrets, and signing keys on the backend.

## Commands

```bash
npm run dev          # Start local Vite server
npm run typecheck    # TypeScript verification
npm run lint         # ESLint verification
npm test             # Vitest + RTL + MSW tests
npm run test:watch   # Watch tests
npm run test:e2e     # Playwright browser smoke tests
npm run build        # Typecheck and production build
npm run preview      # Preview the production build
npm run verify       # Lint, tests, build, and security audit
```

Install the Playwright browser once before the first E2E run:

```bash
npx playwright install chromium
```

To use an existing Chromium installation instead of downloading one:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chromium npm run test:e2e
```

## Production architecture

```text
src/
  app/              Router, providers, access routes, query client, navigation config
  components/       Shared UI, layout, dashboards, settings, monitoring, finance workflows
  config/           Environment and feature flags
  hooks/            Authentication, toasts, unsaved-change protection
  layouts/          Authenticated company and Super Admin shells
  mocks/            Typed phase/domain mock datasets and mock handlers
  pages/            Route-level feature pages, lazy-loaded by the router
  schemas/          Zod form and API validation contracts
  services/         Typed domain API services and API client/interceptors
  store/            Zustand auth, tenant, and UI stores
  tests/            Unit, integration/MSW, and Playwright tests
  types/            Shared domain contracts
  utils/            RBAC, formatting, dashboard routing, class utilities
```

### Data flow

1. A route page calls a typed domain service through TanStack Query or a mutation.
2. `apiRequest` sends the request to the configured FastAPI base URL and normalizes backend errors.
3. In backend mode, `apiRequest` sends tenant/company/authentication headers.
4. A `401` triggers one synchronized refresh request and retries the original request.
5. Failed refresh clears the local session; API errors emit a global toast event.
6. Mutations expose pending, success, failure, confirm, and dirty-state UI.

## Major routes

### Company workspace

```text
/app/dashboard/:dashboardRole
/app/ingestion/shared-links
/app/ingestion/batches
/app/files
/app/processing/translation
/app/entries
/app/review
/app/posting/sap
/app/integrations
/app/analytics
/app/audit
/app/monitoring/processing-logs
/app/monitoring/error-center
/app/settings/company
/app/settings/users-roles
/app/settings/approval-rules
/app/settings/sap-tcode-mapping
/app/settings/gl-account-mapping
/app/settings/ocr
/app/settings/translation
/app/settings/security
```

### Platform administration

```text
/super-admin/dashboard
/super-admin/companies
/super-admin/company-onboarding
/super-admin/subscriptions
/super-admin/billing
/super-admin/integrations
/super-admin/system-health
/super-admin/job-queues
/super-admin/error-center
/super-admin/usage-analytics
/super-admin/audit-logs
/super-admin/support
/super-admin/settings
```

### System routes

```text
/auth/login
/auth/register
/app/unauthorized
/app/forbidden
/maintenance
/* (not found)
```

## Role dashboard behavior

`RoleBasedDashboardRouter` reads the authenticated user’s roles and active role, verifies that a requested role belongs to the user, redirects to the correct dashboard slug, and supports a dashboard switcher for users with multiple company roles.

Supported company roles:

- Company Owner
- Company Admin
- Finance Manager
- Finance User
- Reviewer
- Approver
- SAP Poster
- Integration Manager
- Auditor
- Read-only User

Navigation and buttons are hidden or disabled through permission checks, not only role-name checks. Backend authorization remains mandatory for every protected operation.

## Backend API connection guide

1. Set `VITE_API_BASE_URL` to the deployed FastAPI compatibility API.
2. Set `VITE_API_BASE_URL` to the API version root.
3. Match backend DTOs to the contracts in `src/types` and `src/schemas`.
4. Update only the relevant service in `src/services`; page components should remain unchanged.
5. Return structured API errors:

```json
{
  "message": "Posting period is closed",
  "code": "SAP_POSTING_PERIOD_CLOSED",
  "details": {}
}
```

The API client sends, when available:

```text
Authorization: Bearer <access-token>
X-Tenant-ID: <tenant-id>
X-Company-ID: <company-id>
Accept: application/json
Content-Type: application/json
```

Recommended backend requirements:

- HttpOnly or otherwise securely managed refresh tokens
- Tenant and permission enforcement on every endpoint
- Idempotency keys for posting/retry operations
- Immutable audit records for financial state changes
- Signed upload URLs and malware scanning
- Server-side pagination/filtering for production-scale tables

See `BACKEND_API_CONTRACT.md` for additional endpoint guidance.

## Adding a new accounting integration

1. Add the provider metadata and capabilities to the integration catalog types/mock data.
2. Create or extend a typed provider configuration contract in `src/types`.
3. Add Zod validation in `src/schemas/integration.schema.ts`.
4. Add service methods in `src/services/integrationApi.ts` or a provider-specific service.
5. Reuse `AccountingIntegrationsPage` and `IntegrationDetailPage`, or add a provider-specific page only when required.
6. Add RBAC permissions for read, configure, test, sync, post, or retry actions.
7. Add connection, mapping, posting, retry, and error tests.
8. Never expose provider secrets in browser state or persisted mock payloads in production mode.

## Adding a route or page

1. Create the page under the appropriate `src/pages/<domain>` directory.
2. Export a named page component.
3. Lazy-load it in `src/app/router.tsx`.
4. Wrap it with `secure(...)` and the minimum required permission.
5. Add its navigation entry in `src/app/routeConfig.ts` when it should be visible.
6. Add page title metadata through `PageHeader`.
7. Include loading, empty, error, mutation feedback, mobile, and keyboard states.
8. Add unit or integration coverage for its critical behavior.

## Testing strategy

The automated suite covers:

- Login and company-scoped session creation
- Company registration
- Shared-link validation and creation
- Batch table data contract
- Entry review save and approval
- SAP posting execution
- Super Admin company table data
- Role dashboard routing and multi-role selection
- Phase 0–10 regression contracts
- MSW-isolated API client contract
- Playwright role-login/dashboard smoke flow

MSW runs in Node during integration tests and rejects unhandled network requests. Playwright starts the Vite development server automatically.

## Performance and reliability

- All major routes are lazy-loaded.
- Monaco and PDF rendering load only when opened.
- Recharts, Radix, TanStack, React core, PDF, and Monaco are separated into cached chunks.
- Large tables memoize column definitions and paginate filtered records.
- Route/page skeletons, empty states, and retry states are reusable.
- Error boundaries protect the application shell.
- Unsaved settings warn on refresh/navigation.
- Financial/destructive actions use confirmation dialogs.
- Page controls include accessible labels, focus states, and keyboard-compatible primitives.

## Production verification

Run before deployment:

```bash
npm ci
npm run verify
npx playwright install chromium
npm run test:e2e
```

Current verified state of this package:

- ESLint: passing
- TypeScript: passing
- Vitest: 5 files, 26 tests passing
- Vite production build: passing
- npm security audit: 0 vulnerabilities

Detailed Phase 11–14 implementation notes are in `PHASE_11_TO_14_COMPLETED.md`.

## Phase-completion remediation

The June 2026 completion pass wires all actions identified as incomplete in Phases 9, 10, 12, 13, and 14, adds persistent mock mutations, improves login role selection, and adds focused interaction tests. See `FULL_COMPLETION_REPORT.md` for the verified change list.
