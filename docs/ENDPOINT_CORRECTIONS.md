# Final Endpoint and Workflow Corrections

The original backend routes remain present. The React application uses the compatibility API under `/api/v1/frontend`, which supplies the frontend's expected method, path, casing, payload, response, RBAC and company-scope contract.

## Corrections added during the final fix cycle

| Area | Previous behavior | Final correction |
|---|---|---|
| MFA | Security switches did not affect login. | Added TOTP setup/verification challenge endpoints and a two-step login UI. |
| File processing | Upload persisted a file but no initial processing action/workflow existed. | Upload automatically runs the local pipeline; `POST /files/{id}/process` supports explicit rerun. |
| File download | Backend route existed but no visible frontend action. | Added authenticated browser download from `GET /files/{id}/download`. |
| File deletion | No visible action. | Added authorized `DELETE /files/{id}`, confirmation, cascade cleanup and query refresh. |
| Uploader audit | Uploader was not visible. | File response stores authenticated uploader identity and timestamp. |
| Shared links | Validation returned hard-coded zero files and no batch action. | Added local/public discovery, revalidation/sync, Create Batch and discovered-file attachment/import. |
| Review | No generated tasks/history; actions became stale. | Processing creates tasks; all actions persist history and invalidate lists/analytics/posting data. |
| Approver/Auditor | Evidence pages were visible but linked records were blocked or empty. | Added scoped read-only access without mutation permissions. |
| SAP | Unapproved/unconfigured items could appear ready or attempt posting. | Eligibility requires approved + valid; backend blocks posting until a successful connection test. |
| Connection tests | A populated URL could be reported as connected without network validation. | HTTP/HTTPS tests now perform a real probe. `mock://` is an explicit non-production simulation only. |
| Integration navigation | SAP was missing and posting destinations were static. | Added SAP provider and connected-provider/RBAC-based posting navigation. |
| Tally | Job existed but browser download URL failed. | Backend stores real XML/JSON/CSV and streams it through an authenticated endpoint. |
| Monitoring | Audit, processing and error pages were empty. | Business actions and failures append company-scoped persisted events. |
| Analytics | Only basic totals were populated. | Added approval, validation, posting, error, confidence and trend aggregates. |
| Settings | OCR, translation and security switches were visually present but not state-bound. | Fixed the shared Switch control, form bindings, persistence and policy use. |

## Important current operations

| Method | Compatibility path | Purpose |
|---|---|---|
| POST | `/auth/login` | Password validation and either session or MFA challenge |
| POST | `/auth/mfa/verify` | Verify TOTP and issue the authenticated session |
| POST | `/auth/mfa/setup` | Start authenticated MFA re-enrollment |
| POST | `/files/upload` | Persist and process a local file |
| POST | `/files/{fileId}/process` | Explicitly rerun the document pipeline |
| GET | `/files/{fileId}/download` | Authenticated file stream |
| DELETE | `/files/{fileId}` | Authorized deletion and linked-data cleanup |
| POST | `/shared-links/{sourceId}/create-batch` | Revalidate, import/attach files and create a batch |
| POST | `/entries/{entryId}/mark-reviewed` | Persist reviewed state/history |
| POST | `/entries/{entryId}/request-correction` | Persist correction state/comment/history |
| POST | `/entries/{entryId}/approve` | Approve a valid entry |
| POST | `/entries/{entryId}/reject` | Reject and log an entry |
| POST | `/posting/sap/{postingId}/execute` | Enforced eligible/configured SAP posting |
| GET | `/integrations/tallyprime/exports/{exportId}/content` | Authenticated generated-file stream |
| GET | `/audit/logs` | Company audit records |
| GET | `/monitoring/processing-logs` | Processing records |
| GET | `/monitoring/errors` | Company Error Center records |
| GET | `/analytics/enterprise` | Company-scoped operational analytics |

## External-provider boundary

Private Drive/Microsoft/Dropbox/SFTP/S3/Azure data and live SAP/accounting operations cannot be validated without customer credentials. The application now returns explicit not-configured/failed states instead of fabricated success. See `LIMITATIONS.md`.
