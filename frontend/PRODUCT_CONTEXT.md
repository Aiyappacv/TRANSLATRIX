# TRANSLATRIX PRO — Product Context

TRANSLATRIX PRO is an enterprise AI-finance SaaS platform owned by SPECTRA AI.

## Hierarchy

SPECTRA AI Super Admin registers and manages client companies. Each client company has a Company Admin. The Company Admin assigns company subroles such as Finance Manager, Finance User, Reviewer, Approver, SAP Poster, Integration Manager, and Auditor.

## End-to-end workflow

Register company → Onboard tenant → Connect shared links/local uploads → Discover files → Create batches → Virus scan → PaddleOCR/cloud fallback → Extract text/tables → Translate to English → Classify financial entries → Map SAP T-Codes/accounting software actions → Validate debit/credit accounting entries → Human review/approval → Post to SAP/accounting software → Store audit logs, document numbers, analytics, and error traces.

## Core product rules

- PaddleOCR is the primary OCR engine.
- Cloud OCR fallback is available for low-confidence/failed OCR.
- Translation to English is a first-class workflow.
- Every workflow is company/tenant scoped.
- Human review is required before posting.
- SAP/accounting posting must be idempotent and audit-visible.
- Navigation and actions must respect RBAC permissions.
