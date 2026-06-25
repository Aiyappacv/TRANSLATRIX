# External Credentials and Production Boundaries

The local product workflow is implemented and tested without fabricating successful third-party responses. The following capabilities require customer-owned credentials, endpoints or infrastructure before live execution can be verified.

## Shared-link providers

Implemented without credentials:

- Local Upload discovery.
- Direct/public HTTP file URLs.
- Public HTML directory links.
- Public XML listings such as accessible S3/Azure object lists.
- Public direct-file transformations for common Google Drive, Dropbox, OneDrive and SharePoint links.

Credentials/provider API configuration is still required for private Google Drive folders, private OneDrive/SharePoint sites, Dropbox teams, SFTP, private AWS S3 and private Azure Blob containers. The application now reports this requirement instead of returning a misleading successful zero-file result.

## SAP and accounting platforms

- A normal connection test performs a real network request and only marks the connector connected after a successful response.
- SAP live posting treats the configured SAP base URL as the posting endpoint and supports basic/bearer-style credentials available to the backend. Exact SAP OData/BAPI contracts, OAuth token exchange, certificates and response mapping must be configured for the customer's SAP landscape.
- QuickBooks, Xero, Zoho Books, NetSuite, Workday and ServiceNow require OAuth/client credentials, callback URLs, tenant IDs and approved scopes.
- `mock://` connection/posting behavior is an explicit development simulation only and is disabled in production.

## OCR and translation

- The default container includes Tesseract and the local document pipeline handles PDF text, images, DOCX, XLSX/CSV and text-based formats.
- PaddleOCR remains optional because of its large model/runtime footprint; install `requirements-ml.txt` when PaddleOCR is required.
- Cloud OCR fallback needs Azure Document Intelligence, AWS Textract or Google Cloud credentials.
- External-quality translation needs OpenAI, Azure OpenAI or DeepL credentials. The local pipeline preserves workflow state and extracted content but is not a substitute for a configured multilingual provider.

## Security and communications

- TOTP MFA setup and verification, password policy/expiry, session timeout, IP restrictions and audit retention are implemented.
- Enterprise SSO requires customer IdP metadata, certificates, ACS/redirect URLs and an approved OIDC/SAML configuration. The settings are persisted, but a generic product cannot complete a customer-specific IdP handshake without those details.
- Email invitation and password-reset delivery requires SMTP configuration.

## Production operations

Before production:

- Replace all development passwords and secrets.
- Set `APP_ENV=production`, `SEED_DEVELOPMENT=false` and `RUN_DB_BOOTSTRAP` according to the deployment process.
- Configure TLS, a secret manager, database backups, object storage, monitoring, log retention and rate limits.
- Store connector secrets in a production secret store rather than the development-compatible database state store.
- Run provider-specific acceptance tests and Docker/container security scans in the target infrastructure.
