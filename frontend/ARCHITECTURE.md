# TRANSLATRIX PRO Frontend Architecture

## Design intent

TRANSLATRIX PRO is presented as a premium enterprise finance operations cockpit, not a translator utility. The interface uses a deep navy shell, calm slate work surfaces, precise tabular financial values, semantic status badges, and progressive disclosure in cards, tabs, and drawers.

## Application layers

- `src/app` contains routing, providers, query client, protected routes, and RBAC-ready route config.
- `src/layouts` contains the auth and dashboard shells.
- `src/pages` contains route-level screens by domain.
- `src/components` contains reusable UI primitives and workflow components.
- `src/services` contains typed API modules grouped by backend domain.
- `src/store` contains local auth, tenant, and UI state.
- `src/schemas` contains Zod validation schemas.
- `src/types` contains domain models aligned with ingestion, OCR, entries, SAP posting, audit, and analytics.

## Backend integration path

All runtime service modules call the real FastAPI compatibility API through `apiRequest`. Historical fixtures remain isolated under `src/mocks` for test/reference use and are not imported by production services.

## Production UX controls

- RBAC-aware navigation and protected routes.
- Human approval controls before posting.
- PaddleOCR evidence and confidence surfaces.
- SAP payload preview in Monaco.
- Audit timeline with actor, timestamp, status, old/new values.
- TanStack Table grids for finance-scale sorting, filtering, pagination, and export-ready workflows.


## Extensible accounting connector architecture

Phase 9 uses a canonical accounting payload and provider registry. Connector metadata declares provider identity, supported actions, authentication modes, environment support, and dynamic connection fields. The generic integration detail page consumes this metadata and exposes connection settings, field/category/account/tax mappings, master-data synchronization, and connector logs without provider-specific page forks.

SAP retains dedicated posting and settings screens because its operational workflow includes T-Codes, company codes, immutable approval locks, idempotent document creation, document numbers, fiscal years, and structured SAP response handling.
