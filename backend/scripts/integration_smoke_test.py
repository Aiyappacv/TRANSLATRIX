"""End-to-end smoke test for the integrated frontend API.

Runs the real FastAPI application against a temporary SQLite database and local
upload directory. It deliberately avoids third-party credentials while testing
all local workflows required by the web application: authentication, RBAC,
settings, upload/processing, shared-link batches, review decisions, posting
safeguards, exports, audit/monitoring, analytics, persistence, and deletion.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB_PATH = Path("/tmp/translatrix_frontend_integration_smoke.db")
UPLOAD_PATH = Path("/tmp/translatrix_frontend_integration_uploads")
EXPORT_PATH = Path("/tmp/translatrix_frontend_integration_exports")
for path in (DB_PATH,):
    if path.exists():
        path.unlink()
for path in (UPLOAD_PATH, EXPORT_PATH):
    if path.exists():
        shutil.rmtree(path)

os.environ.update({
    "SECRET_KEY": "development-secret-key-minimum-32-characters-long",
    "JWT_SECRET_KEY": "development-jwt-secret-minimum-32-characters",
    "SUPER_ADMIN_PASSWORD": "DevOnly!2026",
    "DATABASE_URL": f"sqlite:///{DB_PATH}",
    "APP_ENV": "development",
    "DEBUG": "false",
    "FRONTEND_UPLOAD_DIR": str(UPLOAD_PATH),
    "FRONTEND_EXPORT_DIR": str(EXPORT_PATH),
    "DEV_SEED_PASSWORD": "DevOnly!2026",
})

from fastapi.testclient import TestClient

from app.main import app
from scripts.seed_development import main as seed_development
from app.modules.frontend_api.mfa import totp_code

BASE = "/api/v1/frontend"
PASSWORD = "DevOnly!2026"


def login(client: TestClient, email: str) -> tuple[dict[str, str], dict]:
    response = client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, (email, response.status_code, response.text)
    payload = response.json()
    return {"Authorization": f"Bearer {payload['accessToken']}"}, payload


def expect(client: TestClient, method: str, path: str, expected: int, headers=None, **kwargs):
    response = client.request(method, f"{BASE}{path}", headers=headers, **kwargs)
    assert response.status_code == expected, (method, path, expected, response.status_code, response.text)
    return response


def upload(client: TestClient, headers: dict[str, str], name: str, amount: int) -> dict:
    body = f"INVOICE\nInvoice No: INV-{amount}\nInvoice Date: 21/06/2026\nVendor: ACME Supplies\nOffice expense INR {amount}.00\nTotal Amount: INR {amount}.00\n".encode()
    item = expect(client, "POST", "/files/upload", 201, headers, files={"file": (name, body, "text/plain")}).json()
    assert item["ocrStatus"] == "completed"
    assert item["extractionStatus"] == "completed"
    assert item["translationStatus"] == "completed"
    assert item["entriesExtracted"] == 1
    downloaded = expect(client, "GET", f"/files/{item['id']}/download", 200, headers)
    assert downloaded.content == body
    return item


def metric_map(payload: dict) -> dict[str, str]:
    return {item["key"]: item["value"] for item in payload["metrics"]}


def main() -> None:
    seed_development()

    with TestClient(app) as client:
        admin, admin_session = login(client, "admin@translatrix.example.com")
        finance, _ = login(client, "finance.user@translatrix.example.com")
        reviewer, _ = login(client, "reviewer@translatrix.example.com")
        approver, _ = login(client, "approver@translatrix.example.com")
        sap_poster, _ = login(client, "sap.poster@translatrix.example.com")
        integrations, _ = login(client, "integrations@translatrix.example.com")
        auditor, _ = login(client, "auditor@translatrix.example.com")
        super_admin, _ = login(client, "super.admin@translatrix.example.com")

        # Authentication, tenant scope, and role protections.
        assert admin_session["user"]["roles"][0] == "company_admin"
        expect(client, "GET", "/super-admin/dashboard", 200, super_admin)
        expect(client, "GET", "/super-admin/dashboard", 403, admin)
        expect(client, "GET", "/settings/company", 403, finance)
        expect(client, "POST", "/files/upload", 403, approver, files={"file": ("denied.txt", b"denied", "text/plain")})

        # Company and processing settings render, save, and persist.
        company = expect(client, "GET", "/settings/company", 200, admin).json()
        company["phone"] = "+91-9000000000"
        expect(client, "PUT", "/settings/company", 200, admin, json=company)
        assert expect(client, "GET", "/settings/company", 200, admin).json()["phone"] == "+91-9000000000"

        ocr = expect(client, "GET", "/settings/ocr", 200, admin).json()
        ocr.update({"tableExtractionEnabled": False, "layoutAnalysisEnabled": False, "handwritingEnabled": True})
        expect(client, "PUT", "/settings/ocr", 200, admin, json=ocr)
        saved_ocr = expect(client, "GET", "/settings/ocr", 200, admin).json()
        assert saved_ocr["tableExtractionEnabled"] is False and saved_ocr["handwritingEnabled"] is True

        translation = expect(client, "GET", "/settings/translation", 200, admin).json()
        translation.update({"preserveNumbers": False, "preserveNames": False, "humanReviewBelowThreshold": True, "confidenceThreshold": 75})
        expect(client, "PUT", "/settings/translation", 200, admin, json=translation)
        saved_translation = expect(client, "GET", "/settings/translation", 200, admin).json()
        assert saved_translation["preserveNumbers"] is False and saved_translation["confidenceThreshold"] == 75

        security = expect(client, "GET", "/settings/security", 200, admin).json()
        security.update({
            "mfaRequired": False,
            "mfaRequiredForPrivilegedRoles": False,
            "passwordMinimumLength": 12,
            "passwordRequireUppercase": True,
            "passwordRequireLowercase": True,
            "passwordRequireNumber": True,
            "passwordRequireSymbol": True,
            "sessionTimeoutMinutes": 45,
            "auditRetentionDays": 180,
        })
        expect(client, "PUT", "/settings/security", 200, admin, json=security)
        saved_security = expect(client, "GET", "/settings/security", 200, admin).json()
        assert saved_security["sessionTimeoutMinutes"] == 45 and saved_security["auditRetentionDays"] == 180
        expect(client, "POST", "/auth/change-password", 422, admin, json={"currentPassword": PASSWORD, "newPassword": "weak"})

        # Finance users can upload/process. Uploader identity comes from the token.
        files = [
            upload(client, finance, "correction-invoice.txt", 1100),
            upload(client, finance, "rejected-invoice.txt", 2200),
            upload(client, finance, "approved-invoice.txt", 3300),
        ]
        assert all(item["uploadedBy"]["email"] == "finance.user@translatrix.example.com" for item in files)
        assert files[0]["processingSettings"]["ocr"]["tableExtractionEnabled"] is False
        expect(client, "POST", f"/files/{files[0]['id']}/process", 403, approver)
        assert expect(client, "GET", f"/files/{files[0]['id']}", 200, approver).json()["id"] == files[0]["id"]
        expect(client, "DELETE", f"/files/{files[0]['id']}", 403, approver)

        # Local-upload shared source discovers files and creates a populated batch.
        validation = expect(client, "POST", "/shared-links/validate", 200, admin, json={"name": "Local uploads", "sourceType": "Local Upload", "url": ""}).json()
        assert validation["filesFound"] == 3 and validation["supportedFilesCount"] == 3
        link = expect(client, "POST", "/shared-links", 200, admin, json={"name": "Local uploads", "clientName": "TRANSLATRIX Development", "sourceType": "Local Upload", "url": "", "authenticationType": "None"}).json()
        batch_result = expect(client, "POST", f"/shared-links/{link['id']}/create-batch", 200, admin).json()
        batch = expect(client, "GET", f"/batches/{batch_result['batchId']}", 200, admin).json()
        assert batch["totalFiles"] == 3 and batch["processedFiles"] == 3 and batch["extractedEntries"] == 3

        # Processing creates financial entries and review tasks.
        entries = expect(client, "GET", "/entries", 200, finance).json()
        tasks = expect(client, "GET", "/review/tasks", 200, reviewer).json()
        assert len(entries) == 3 and len(tasks) == 3
        by_source = {item["sourceFile"]: item for item in entries}
        correction = by_source["correction-invoice.txt"]
        rejected = by_source["rejected-invoice.txt"]
        approved = by_source["approved-invoice.txt"]

        # Request correction, rejection, and approval persist and synchronize lists/history.
        changed = expect(client, "POST", f"/entries/{correction['id']}/request-correction", 200, reviewer, json={"comments": "Correct the vendor name."}).json()
        assert changed["status"] == "changes_requested" and changed["reviewComments"] == "Correct the vendor name."
        denied = expect(client, "POST", f"/entries/{rejected['id']}/reject", 200, approver, json={"comments": "Duplicate invoice."}).json()
        assert denied["status"] == "rejected"
        expect(client, "POST", f"/entries/{approved['id']}/mark-reviewed", 200, approver, json={"comments": "Reviewed."})
        approved_result = expect(client, "POST", f"/entries/{approved['id']}/approve", 200, approver, json={"comments": "Approved for posting."}).json()
        assert approved_result["status"] == "approved"

        current_entries = expect(client, "GET", "/entries", 200, auditor).json()
        statuses = {item["sourceFile"]: item["status"] for item in current_entries}
        assert statuses == {
            "correction-invoice.txt": "changes_requested",
            "rejected-invoice.txt": "rejected",
            "approved-invoice.txt": "approved",
        }
        history = expect(client, "GET", "/review/history", 200, auditor).json()
        decisions = {item["decision"] for item in history}
        assert {"changes_requested", "rejected", "approved"}.issubset(decisions)
        assert any(item.get("comments") == "Correct the vendor name." for item in history)
        expect(client, "POST", f"/entries/{approved['id']}/approve", 403, auditor, json={"comments": "Forbidden"})

        # Only approved + valid entries become SAP posting candidates.
        postings = expect(client, "GET", "/posting/sap", 200, sap_poster).json()
        assert len(postings) == 1 and postings[0]["entryId"] == approved["id"]
        posting_id = postings[0]["id"]
        blocked = expect(client, "POST", f"/posting/sap/{posting_id}/execute", 422, sap_poster)
        assert "Configure SAP" in blocked.json()["detail"]

        sap_settings = expect(client, "GET", "/integrations/sap/settings", 200, integrations).json()
        sap_settings.update({"systemName": "DEV SAP", "baseUrl": "mock://sap-development", "companyCode": "1000"})
        expect(client, "PUT", "/integrations/sap/settings", 200, integrations, json=sap_settings)
        test_result = expect(client, "POST", "/integrations/sap/test", 200, integrations, json=sap_settings).json()
        assert test_result["status"] == "success"
        posted = expect(client, "POST", f"/posting/sap/{posting_id}/execute", 200, sap_poster).json()
        assert posted["sapStatus"] == "posted"

        # SAP and Tally appear in the provider catalog; Tally creates real content.
        providers = expect(client, "GET", "/integrations/providers", 200, integrations).json()
        provider_codes = {provider["code"] for provider in providers}
        assert {"sap_s4hana", "tallyprime"}.issubset(provider_codes)
        tally = expect(client, "POST", "/integrations/tallyprime/exports", 201, integrations, json={"format": "xml", "voucherTypes": ["Journal"]}).json()
        metadata = expect(client, "GET", f"/integrations/tallyprime/exports/{tally['id']}/download", 200, integrations).json()
        tally_file = expect(client, "GET", metadata["downloadUrl"], 200, integrations)
        assert b"<ENVELOPE>" in tally_file.content

        # A failed cloud fallback becomes visible in Processing Logs and Error Center.
        cloud_failure = expect(client, "POST", f"/files/{files[0]['id']}/ocr/cloud-fallback", 422, finance)
        assert "credentials" in cloud_failure.json()["detail"].lower()
        errors = expect(client, "GET", "/monitoring/errors", 200, auditor).json()
        assert any(item["code"] == "CLOUD_OCR_NOT_CONFIGURED" for item in errors)
        error_id = next(item["id"] for item in errors if item["code"] == "CLOUD_OCR_NOT_CONFIGURED")
        assert expect(client, "POST", f"/monitoring/errors/{error_id}/retry", 200, auditor).json()["status"] == "queued"

        audit = expect(client, "GET", "/audit/logs", 200, auditor).json()
        processing_logs = expect(client, "GET", "/monitoring/processing-logs", 200, auditor).json()
        assert audit and processing_logs
        actions = {item["action"] for item in audit}
        assert {"FILE_UPLOADED", "REVIEW_APPROVE", "TALLY_EXPORT_CREATED", "SAP_POSTED"}.issubset(actions)

        analytics = expect(client, "GET", "/analytics/enterprise", 200, auditor).json()
        metrics = metric_map(analytics)
        assert metrics["files"] == "3" and metrics["entries"] == "3"
        assert metrics["approved"] == "1" and metrics["errors"] == "1"
        assert analytics["trend"] and float(metrics["confidence"].rstrip("%")) > 0

        # Admin deletion removes its linked entry/task/posting while preserving other files.
        expect(client, "DELETE", f"/files/{files[0]['id']}", 204, admin)
        remaining_files = expect(client, "GET", "/files", 200, admin).json()
        remaining_entries = expect(client, "GET", "/entries", 200, admin).json()
        assert len(remaining_files) == 2 and all(item["id"] != files[0]["id"] for item in remaining_files)
        assert len(remaining_entries) == 2 and all(item["fileId"] != files[0]["id"] for item in remaining_entries)

    # New clients/sessions still see persisted database state.
    with TestClient(app) as client:
        admin, _ = login(client, "admin@translatrix.example.com")
        assert len(expect(client, "GET", "/files", 200, admin).json()) == 2
        assert expect(client, "GET", "/settings/company", 200, admin).json()["phone"] == "+91-9000000000"

        # Enabling privileged-role MFA creates a real TOTP setup challenge and
        # only issues a session after the six-digit code is verified.
        security = expect(client, "GET", "/settings/security", 200, admin).json()
        security["mfaRequiredForPrivilegedRoles"] = True
        expect(client, "PUT", "/settings/security", 200, admin, json=security)
        challenge_response = client.post(f"{BASE}/auth/login", json={"email": "admin@translatrix.example.com", "password": PASSWORD})
        assert challenge_response.status_code == 200
        challenge = challenge_response.json()
        assert challenge["mfaRequired"] is True and challenge["mfaSetupRequired"] is True and challenge.get("secret")
        verified = expect(client, "POST", "/auth/mfa/verify", 200, json={"challengeToken": challenge["challengeToken"], "code": totp_code(challenge["secret"])}).json()
        assert verified["user"]["mfaEnabled"] is True and verified.get("accessToken")

    print("PASS full local integration smoke test")


if __name__ == "__main__":
    main()
