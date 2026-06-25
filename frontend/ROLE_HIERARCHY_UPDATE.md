# Role hierarchy update

The frontend supports the established multi-tenant role hierarchy without embedding deployment credentials or tenant records.

## Platform level

- Super Admin manages tenant onboarding, platform monitoring, subscriptions, integrations, system health, job queues, error handling, usage analytics, audit logs, and support workflows.
- Platform access is determined by roles returned from the backend authentication service.

## Company level

Each backend-provisioned company can assign the supported roles:

- Company Admin
- Finance Manager
- Finance User
- Reviewer
- Approver
- SAP Poster
- Integration Manager
- Auditor

## Authentication behavior

- The login form is empty by default.
- No shared passwords, example accounts, or selectable credential cards are included.
- User identity, company membership, roles, and permissions are loaded from backend APIs.
- Route guards and role-aware navigation remain unchanged.

## Deployment requirement

Configure the backend base URL and authentication endpoints in the environment variables before deployment. Test credentials should be supplied only through secure CI or local environment variables and must not be committed to the frontend source.
