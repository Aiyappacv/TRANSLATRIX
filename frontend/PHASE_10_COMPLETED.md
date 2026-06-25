# Phase 10 — Super Admin Platform Dashboard and Management

## Added routes

- `/super-admin`
- `/super-admin/dashboard`
- `/super-admin/companies`
- `/super-admin/companies/:companyId`
- `/super-admin/company-onboarding`
- `/super-admin/subscriptions`
- `/super-admin/billing`
- `/super-admin/integrations`
- `/super-admin/system-health`
- `/super-admin/job-queues`
- `/super-admin/error-center`
- `/super-admin/usage-analytics`
- `/super-admin/audit-logs`
- `/super-admin/support`
- `/super-admin/settings`

## Architecture

Phase 10 is isolated from company dashboards through `SuperAdminLayout`, a dedicated route tree, a platform navigation registry, and granular platform-only RBAC permissions. Tenant data views display an audited-access warning and should be backed by immutable audit events in production.

The platform provider registry is data-driven, so additional OCR, translation, ERP, or accounting providers can be added without changing the monitoring page structure.

## Production API expectations

The mock-backed `superAdminApi` defines contracts for dashboard KPIs, companies, tenant detail, providers, health services, queues, errors, subscriptions, invoices, audit records, support tickets, and platform settings. Replace mock mode with authenticated `/api/v1/super-admin/*` endpoints.
