# Phase 8 — Human Review and Approval Workflow

Implemented and production-build validated:

- Review queue with all required status filters and counts.
- Row selection and RBAC-aware bulk assignment, approval, rejection, correction request, and CSV export.
- Three-panel review task detail page.
- Original document preview, translation, extracted finance data, confidence, validation, and SAP payload.
- Full editable accounting header, debit lines, credit lines, GL accounts, tax codes, cost centers, currencies, amounts, and memos.
- Complete eight-item approval checklist.
- Save review, approve, reject, request changes, and second-approval routing.
- Granular review permissions by role.
- Persistent mock review state and approval history using localStorage, with backend-ready API routes.
- Approval timeline and audit table containing actor, role, decision, field, old/new values, timestamp, and comments.
- Corrected router imports and route names.
- Corrected pre-existing TypeScript export conflicts so `npm run build` succeeds.

## Important after replacing the project

Log out and sign in again so the authenticated session reloads the latest granular review permissions from the backend.

## Validation

`npm run build` completes successfully.
