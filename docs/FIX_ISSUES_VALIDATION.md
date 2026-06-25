# Fix Issues Validation Matrix

> Every item numbered 1–122 in the supplied Fix Issues document was reviewed. The table below records the product-side implementation. Provider-specific operations that cannot be executed without customer credentials are explicitly identified in the limitations document.

## File processing and OCR — issues 1–6

| Issue | Resolution | Validation |
|---:|---|---|
| 1 | File upload now invokes the document pipeline automatically. | Automated smoke + source/build checks |
| 2 | Files list/detail expose Start Processing when processing has not started and the role has files:process. | Automated smoke + source/build checks |
| 3 | OCR capability switches are controlled inputs and persist through the settings API. | Automated smoke + source/build checks |
| 4 | The local pipeline advances OCR, extraction, translation, classification, entry generation, validation and review-task creation. | Automated smoke + source/build checks |
| 5 | Failures create readable API errors, Processing Log records, Error Center records and retry actions. | Automated smoke + source/build checks |
| 6 | Saved OCR and translation settings are attached to each run and influence the local pipeline. | Automated smoke + source/build checks |

## File management — issues 7–13

| Issue | Resolution | Validation |
|---:|---|---|
| 7 | Download actions are available in Files and File Detail. | Automated smoke + source/build checks |
| 8 | Frontend download uses the authenticated backend stream endpoint. | Automated smoke + source/build checks |
| 9 | Delete actions are available to files:manage roles in Files and File Detail. | Automated smoke + source/build checks |
| 10 | Delete uses confirmation, backend authorization, feedback, cascade cleanup and query refresh. | Automated smoke + source/build checks |
| 11 | Every file stores authenticated uploader metadata. | Automated smoke + source/build checks |
| 12 | Files table/detail show uploader name, email, role, company and timestamp. | Automated smoke + source/build checks |
| 13 | Uploader identity is derived from the bearer-token user and cannot be supplied by the browser. | Automated smoke + source/build checks |

## Shared links and batches — issues 14–20

| Issue | Resolution | Validation |
|---:|---|---|
| 14 | Validation performs actual local/public discovery instead of returning hard-coded zero counts. | Automated smoke + source/build checks |
| 15 | Local Upload, public/manual URLs, direct public Drive/Dropbox/OneDrive/SharePoint links and public S3/Azure XML listings are discoverable; private folders and SFTP correctly require provider credentials. | Product behavior implemented; live provider/IdP verification requires supplied credentials |
| 16 | Create Batch is present on shared-link list/detail screens. | Automated smoke + source/build checks |
| 17 | Create Batch calls the backend, imports/attaches discovered files and processes them. | Automated smoke + source/build checks |
| 18 | Created batches are persisted and immediately listed. | Automated smoke + source/build checks |
| 19 | Batch records contain discovered files, attached file IDs, entry previews and counts. | Automated smoke + source/build checks |
| 20 | Revalidate/sync persist results, record audit/log/error events and return actionable messages. | Automated smoke + source/build checks |

## Company Settings — issues 21–25

| Issue | Resolution | Validation |
|---:|---|---|
| 21 | Company Settings renders real data instead of an empty screen. | Automated smoke + source/build checks |
| 22 | Company Admin/settings:manage permission checks are enforced. | Automated smoke + source/build checks |
| 23 | GET response casing and defaults match the form schema. | Automated smoke + source/build checks |
| 24 | Loading, empty, unauthorized and error states are rendered. | Automated smoke + source/build checks |
| 25 | PUT saves company settings and persistence is verified after a new client session. | Automated smoke + source/build checks |

## Review Queue and task generation — issues 26–30

| Issue | Resolution | Validation |
|---:|---|---|
| 26 | Review Queue is populated from generated review tasks. | Automated smoke + source/build checks |
| 27 | Entry generation automatically creates company-scoped review tasks. | Automated smoke + source/build checks |
| 28 | Tasks retain company scope and assignment/status data. | Automated smoke + source/build checks |
| 29 | Queue counts and filters use persisted task status. | Automated smoke + source/build checks |
| 30 | Review mutations invalidate and refresh task/list queries. | Automated smoke + source/build checks |

## Approver permissions — issues 31–34

| Issue | Resolution | Validation |
|---:|---|---|
| 31 | Approvers have scoped read-only files:read permission. | Automated smoke + source/build checks |
| 32 | Approver source-file and preview access is enabled without upload/process/manage rights. | Automated smoke + source/build checks |
| 33 | Approvers can view source, extracted data, translation and validation evidence. | Automated smoke + source/build checks |
| 34 | Backend and frontend block Approver upload, process, correction-table edits and deletion. | Automated smoke + source/build checks |

## Approval actions and status synchronization — issues 35–45

| Issue | Resolution | Validation |
|---:|---|---|
| 35 | Approve Entry has a wired mutation and backend endpoint. | Automated smoke + source/build checks |
| 36 | Mark Reviewed transitions the task/entry and approval remains available when validation permits. | Automated smoke + source/build checks |
| 37 | Button disabled-state logic now explains blocking validation/checklist conditions. | Automated smoke + source/build checks |
| 38 | Approver permission mapping includes review:approve. | Automated smoke + source/build checks |
| 39 | Frontend calls POST /entries/{id}/approve and refreshes dependent data. | Automated smoke + source/build checks |
| 40 | Approved state persists in the database. | Automated smoke + source/build checks |
| 41 | Blocking validation errors are shown as an explicit reason rather than silent disablement. | Automated smoke + source/build checks |
| 42 | Reject updates both detail and outer entry/review lists. | Automated smoke + source/build checks |
| 43 | Mark Reviewed updates both detail and outer status. | Automated smoke + source/build checks |
| 44 | Status normalization consistently maps needs review, in review, reviewed, changes requested, approved and rejected. | Automated smoke + source/build checks |
| 45 | Entry, review, history, analytics and posting queries are invalidated after actions. | Automated smoke + source/build checks |

## Request Correction — issues 46–50

| Issue | Resolution | Validation |
|---:|---|---|
| 46 | Request Correction uses a working backend transition. | Automated smoke + source/build checks |
| 47 | Correction comments and status persist after refresh. | Automated smoke + source/build checks |
| 48 | A correction request creates a persisted review-history event. | Automated smoke + source/build checks |
| 49 | Correction status/comment appear in entry detail and review queue. | Automated smoke + source/build checks |
| 50 | Approval History includes the correction event. | Automated smoke + source/build checks |

## Approval History — issues 51–54

| Issue | Resolution | Validation |
|---:|---|---|
| 51 | Approval History retrieves real immutable events. | Automated smoke + source/build checks |
| 52 | Reviewed, rejected, correction and approval actions all append history. | Automated smoke + source/build checks |
| 53 | History records include entity IDs, old/new state, actor, role, company, time and comments. | Automated smoke + source/build checks |
| 54 | History page renders and filters those records. | Automated smoke + source/build checks |

## SAP posting eligibility — issues 55–62

| Issue | Resolution | Validation |
|---:|---|---|
| 55 | Ready-to-post counts are derived only from eligible entries. | Automated smoke + source/build checks |
| 56 | Unapproved records do not receive an enabled Post action. | Automated smoke + source/build checks |
| 57 | Backend eligibility requires approved status, valid validation and no error-severity issues. | Automated smoke + source/build checks |
| 58 | Posting is blocked until SAP settings contain a usable endpoint. | Product behavior implemented; live provider/IdP verification requires supplied credentials |
| 59 | Posting is blocked until a successful real or explicitly marked development-simulation connection test. | Product behavior implemented; live provider/IdP verification requires supplied credentials |
| 60 | UI surfaces the specific posting block reason. | Automated smoke + source/build checks |
| 61 | The backend repeats all eligibility/connection checks even when called directly. | Automated smoke + source/build checks |
| 62 | Ineligible attempts return 422 and do not create failed posting records. | Automated smoke + source/build checks |

## SAP posting queue — issues 63–66

| Issue | Resolution | Validation |
|---:|---|---|
| 63 | Eligible approved entries generate company-scoped posting records. | Automated smoke + source/build checks |
| 64 | Posting records use the authenticated company scope. | Automated smoke + source/build checks |
| 65 | Only approved and validated entries are included. | Automated smoke + source/build checks |
| 66 | Posting results and source-entry status persist after completion. | Product behavior implemented; live provider/IdP verification requires supplied credentials |

## Integration catalog and dynamic navigation — issues 67–72

| Issue | Resolution | Validation |
|---:|---|---|
| 67 | SAP S/4HANA is included in the Enterprise Integrations catalog. | Automated smoke + source/build checks |
| 68 | SAP card exposes configuration, test state, last check and health/status. | Product behavior implemented; live provider/IdP verification requires supplied credentials |
| 69 | Posting navigation is generated from connected integrations instead of a fixed list. | Automated smoke + source/build checks |
| 70 | Provider-specific posting/export links appear when configured and permitted. | Product behavior implemented; live provider/IdP verification requires supplied credentials |
| 71 | Unconfigured destinations are not presented as active posting targets. | Product behavior implemented; live provider/IdP verification requires supplied credentials |
| 72 | Dynamic navigation also applies RBAC checks. | Product behavior implemented; live provider/IdP verification requires supplied credentials |

## Tally export — issues 73–79

| Issue | Resolution | Validation |
|---:|---|---|
| 73 | Existing Tally export creation behavior is preserved. | Automated smoke + source/build checks |
| 74 | Export jobs persist after refresh. | Automated smoke + source/build checks |
| 75 | Download now uses an authenticated blob/file stream and no longer opens a missing site URL. | Automated smoke + source/build checks |
| 76 | Backend creates and stores actual XML/JSON/CSV content. | Automated smoke + source/build checks |
| 77 | Download metadata points to a protected content stream. | Automated smoke + source/build checks |
| 78 | FileResponse supplies filename and content type headers. | Automated smoke + source/build checks |
| 79 | Frontend fetches the stream with auth and triggers a browser download. | Automated smoke + source/build checks |

## Audit Logs — issues 80–83

| Issue | Resolution | Validation |
|---:|---|---|
| 80 | Audit Logs is populated from real application events. | Automated smoke + source/build checks |
| 81 | Login, users, uploads, links, review, export, tests and posting actions are logged. | Automated smoke + source/build checks |
| 82 | Audit records include actor, action, entity, company, timestamp, result and value metadata. | Automated smoke + source/build checks |
| 83 | Audit records are append-only in company-scoped persisted state. | Automated smoke + source/build checks |

## Auditor role — issues 84–86

| Issue | Resolution | Validation |
|---:|---|---|
| 84 | Auditors can list existing company entries. | Automated smoke + source/build checks |
| 85 | Auditors have read-only files, entries, validation, history, posting and audit access. | Automated smoke + source/build checks |
| 86 | Auditor mutation endpoints remain forbidden and action controls are hidden. | Automated smoke + source/build checks |

## Processing Logs — issues 87–89

| Issue | Resolution | Validation |
|---:|---|---|
| 87 | Processing Logs is populated. | Automated smoke + source/build checks |
| 88 | Upload/OCR/extraction/translation/entry/validation/retry/failure/completion stages append records. | Automated smoke + source/build checks |
| 89 | Records include stage, status, file/batch/job IDs, timestamp, duration/source and errors where available. | Automated smoke + source/build checks |

## Error Center — issues 90–93

| Issue | Resolution | Validation |
|---:|---|---|
| 90 | Error Center is populated from backend failures. | Automated smoke + source/build checks |
| 91 | SAP and other integration/posting failures create visible records. | Automated smoke + source/build checks |
| 92 | OCR, processing, shared-link, export, test and posting errors use the common error recorder. | Automated smoke + source/build checks |
| 93 | Records include severity/category, code, source entity, message, time, retry and resolution state. | Automated smoke + source/build checks |

## Analytics — issues 94–103

| Issue | Resolution | Validation |
|---:|---|---|
| 94 | Existing file/entry totals remain connected. | Automated smoke + source/build checks |
| 95 | Failed posting metrics are included. | Automated smoke + source/build checks |
| 96 | Error totals are included. | Automated smoke + source/build checks |
| 97 | Approval-state totals are included. | Automated smoke + source/build checks |
| 98 | Validation-state totals are included. | Automated smoke + source/build checks |
| 99 | Average confidence is calculated from persisted entry confidence. | Automated smoke + source/build checks |
| 100 | Processing volume chart receives real time-series points. | Automated smoke + source/build checks |
| 101 | Confidence trend chart receives real time-series points. | Automated smoke + source/build checks |
| 102 | All analytics are company-scoped backend aggregates. | Automated smoke + source/build checks |
| 103 | Mutations invalidate analytics queries so counts refresh. | Automated smoke + source/build checks |

## OCR Settings — issues 104–109

| Issue | Resolution | Validation |
|---:|---|---|
| 104 | OCR extraction toggles are interactive. | Automated smoke + source/build checks |
| 105 | Controlled Switch state binding and disabled logic are corrected. | Automated smoke + source/build checks |
| 106 | Company Admin settings permission is recognized. | Automated smoke + source/build checks |
| 107 | GET/PUT /settings/ocr are connected. | Automated smoke + source/build checks |
| 108 | Values persist after refresh. | Automated smoke + source/build checks |
| 109 | Saved OCR capabilities are captured by processing runs. | Automated smoke + source/build checks |

## Translation Settings — issues 110–114

| Issue | Resolution | Validation |
|---:|---|---|
| 110 | All three Translation Settings switches are interactive. | Automated smoke + source/build checks |
| 111 | Controlled state and save handling are corrected. | Automated smoke + source/build checks |
| 112 | GET/PUT /settings/translation persist the values. | Automated smoke + source/build checks |
| 113 | Preservation/review-threshold settings are applied to local processing and review routing metadata. | Automated smoke + source/build checks |
| 114 | Confidence threshold is schema/backend validated to the accepted range. | Automated smoke + source/build checks |

## Security Settings — issues 115–122

| Issue | Resolution | Validation |
|---:|---|---|
| 115 | Security Settings switches are interactive. | Automated smoke + source/build checks |
| 116 | MFA-for-all and MFA-for-privileged switches are controllable. | Automated smoke + source/build checks |
| 117 | Password-policy switches are controllable. | Automated smoke + source/build checks |
| 118 | Save/Cancel and dirty-state behavior work. | Automated smoke + source/build checks |
| 119 | GET/PUT /settings/security persist the policy. | Automated smoke + source/build checks |
| 120 | The MFA badge now derives from the current form values and matches the switches. | Automated smoke + source/build checks |
| 121 | MFA, password, session, IP and audit-retention logic is enforced; TOTP setup/verification is included in login. | Automated smoke + source/build checks |
| 122 | MFA, password complexity/expiry, session timeout, IP restrictions and audit retention are enforced. SSO configuration is persisted and remains credential/IdP dependent, as documented. | Product behavior implemented; live provider/IdP verification requires supplied credentials |

## Preserved working behavior

The original working login, Super Admin, Company Admin, user lifecycle, file persistence, company isolation, Finance User RBAC, Reviewer RBAC, Tally job persistence, integration pages and existing analytics totals were retained while the incomplete workflows were extended.
