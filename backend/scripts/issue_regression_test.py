"""Regression coverage for the consolidated role-wise correction register.

This suite exercises the real FastAPI application with a temporary SQLite database.
It covers multilingual translation, structured financial extraction, validation,
review RBAC, correction resubmission, SAP safeguards, dashboard aggregation,
monitoring aggregation, and the supplied scanned invoice samples.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB_PATH = Path("/tmp/translatrix_issue_regression.db")
UPLOAD_PATH = Path("/tmp/translatrix_issue_regression_uploads")
for path in (DB_PATH,):
    if path.exists():
        path.unlink()
for path in (UPLOAD_PATH,):
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
    "DEV_SEED_PASSWORD": "DevOnly!2026",
})

from fastapi.testclient import TestClient

from app.main import app
from scripts.seed_development import main as seed_development

BASE = "/api/v1/frontend"
PASSWORD = "DevOnly!2026"
FIXTURES = ROOT / "tests" / "fixtures" / "issue_invoices"


def login(client: TestClient, email: str) -> tuple[dict[str, str], dict]:
    response = client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, (email, response.status_code, response.text)
    payload = response.json()
    return {"Authorization": f"Bearer {payload['accessToken']}"}, payload


def expect(client: TestClient, method: str, path: str, expected: int, headers=None, **kwargs):
    response = client.request(method, f"{BASE}{path}", headers=headers, **kwargs)
    assert response.status_code == expected, (method, path, expected, response.status_code, response.text)
    return response


def upload_bytes(client: TestClient, headers: dict[str, str], name: str, body: bytes, mime: str) -> dict:
    return expect(client, "POST", "/files/upload", 201, headers, files={"file": (name, body, mime)}).json()


def issue_codes(item: dict) -> set[str]:
    return {str(issue.get("code")) for issue in item.get("issues", item.get("validationIssues", []))}


def assert_balanced(entry: dict) -> None:
    accounting = entry["accountingEntry"]
    debit = round(sum(float(line.get("amount") or 0) for line in accounting["debitLines"]), 2)
    credit = round(sum(float(line.get("amount") or 0) for line in accounting["creditLines"]), 2)
    assert debit == credit == round(float(entry["amount"]), 2), (debit, credit, entry["amount"])


def main() -> None:
    seed_development()
    with TestClient(app) as client:
        admin, _ = login(client, "admin@translatrix.example.com")
        finance, finance_session = login(client, "finance.user@translatrix.example.com")
        reviewer, reviewer_session = login(client, "reviewer@translatrix.example.com")
        approver, _ = login(client, "approver@translatrix.example.com")
        sap_poster, _ = login(client, "sap.poster@translatrix.example.com")
        integrations, _ = login(client, "integrations@translatrix.example.com")
        auditor, _ = login(client, "auditor@translatrix.example.com")
        super_admin, _ = login(client, "super.admin@translatrix.example.com")

        # Pending tenant registration -> Super Admin approval -> Company Admin activation.
        registration_payload = {
            "legalName": "Regression Registration Ltd",
            "tradingName": "Regression Registration",
            "country": "India",
            "industry": "Professional Services",
            "registrationNumber": "REG-2026-001",
            "taxId": "27ABCDE1234F1Z5",
            "primaryContactName": "Regression Admin",
            "primaryContactEmail": "registration.admin@regression.example.com",
            "phoneNumber": "+91-9000000000",
            "website": "https://regression.example.com",
            "defaultCurrency": "INR",
            "defaultLanguage": "en",
            "timezone": "Asia/Kolkata",
            "preferredAccountingSystem": "Manual JSON export",
        }
        registered = expect(client, "POST", "/register", 201, json=registration_payload).json()
        assert registered["status"] == "pending"
        expect(client, "POST", "/auth/login", 401, json={"email": registration_payload["primaryContactEmail"], "password": PASSWORD})
        pending_requests = expect(client, "GET", "/super-admin/registration-requests", 200, super_admin).json()
        pending_request = next(item for item in pending_requests if item["companyId"] == registered["id"])
        assert pending_request["status"] == "pending"
        platform_companies = expect(client, "GET", "/super-admin/companies", 200, super_admin).json()
        pending_company = next(item for item in platform_companies if item["id"] == registered["id"])
        assert pending_company["status"] == "pending"
        activation = expect(client, "POST", f"/super-admin/registration-requests/{pending_request['id']}/approve", 200, super_admin).json()
        assert activation["request"]["status"] == "approved"
        assert activation["company"]["status"] == "active"
        activation_token = activation["activationPath"].split("token=", 1)[1]
        expect(client, "POST", "/auth/reset-password", 200, json={"token": activation_token, "password": PASSWORD})
        activated_admin, activated_session = login(client, registration_payload["primaryContactEmail"])
        assert activated_session["user"]["roles"] == ["company_admin"]
        assert activated_session.get("mfaRequired") is False
        expect(client, "GET", "/users", 200, activated_admin)
        invited = expect(client, "POST", "/users/invitations", 201, activated_admin, json={
            "email": "registration.finance@regression.example.com",
            "name": "Registration Finance",
            "role": "finance_user",
            "department": "Finance",
        }).json()
        assert invited["status"] == "invited"
        submitted = expect(client, "POST", "/onboarding/submit", 200, activated_admin, json={"companyProfile": registration_payload}).json()
        assert submitted["status"] == "submitted"
        assert expect(client, "GET", "/onboarding", 200, activated_admin).json()["completion"] == 100

        # Role contracts: no final approval for Reviewer/Finance User and no global
        # integrations permission for roles that triggered the repeated 403 popup.
        assert "review:approve" not in reviewer_session["user"]["permissions"]
        assert "review:approve" not in finance_session["user"]["permissions"]
        for role_headers in (finance, reviewer, approver):
            expect(client, "GET", "/integrations/providers", 403, role_headers)

        spanish = """FACTURA DE COMPRA
Número de factura: ES-2026-104
Fecha de factura: 21/06/2026
Fecha de vencimiento: 21/07/2026
Proveedor: Servicios Iberia SL
NIF: B12345678
Referencia: PO-99999999
Moneda: EUR
Descripción: Servicios de consultoría financiera
Base imponible: EUR 1000.00
IVA 21%: EUR 210.00
Importe total: EUR 1210.00
1 Servicio de consultoría 1000.00
""".encode("utf-8")
        translated_file = upload_bytes(client, finance, "factura-espanola.txt", spanish, "text/plain")
        assert translated_file["sourceLanguage"] == "Spanish"
        translation = translated_file["translation"]
        assert translation["status"] in {"completed", "needs_review"}
        assert translation["englishText"].strip()
        assert translation["englishText"].strip() != translation["originalText"].strip()
        assert "invoice" in translation["englishText"].lower()
        fields = translated_file["structuredFields"]
        assert fields["invoiceNumber"] == "ES-2026-104"
        assert fields["vendor"] == "Servicios Iberia SL"
        assert fields["gstVatNumber"] == "B12345678"
        assert fields["invoiceDate"] == "2026-06-21"
        assert fields["dueDate"] == "2026-07-21"
        assert fields["currency"] == "EUR"
        assert fields["subtotal"] == 1000.0
        assert fields["taxAmount"] == 210.0
        assert fields["total"] == 1210.0
        assert fields["referenceNumber"] == "PO-99999999"
        assert translated_file["amount"] == 1210.0

        entries = expect(client, "GET", "/entries", 200, finance).json()
        translated_entry = next(item for item in entries if item["sourceFile"] == "factura-espanola.txt")
        assert translated_entry["validationStatus"] == "valid", translated_entry["issues"]
        assert translated_entry["amount"] == 1210.0
        assert translated_entry["taxAmount"] == 210.0
        assert any(line["accountName"] == "Input tax" and line["amount"] == 210.0 for line in translated_entry["accountingEntry"]["debitLines"])
        assert_balanced(translated_entry)

        # Largest-number regression: a PO/reference must not replace the labelled total.
        incomplete = """FACTURA
Referencia: PO-987654321
Total a pagar: EUR 500.00
""".encode("utf-8")
        incomplete_file = upload_bytes(client, finance, "factura-incompleta.txt", incomplete, "text/plain")
        assert incomplete_file["amount"] == 500.0
        assert incomplete_file["amount"] != 987654321
        assert {"INVOICE_NUMBER_MISSING", "VENDOR_MISSING", "INVOICE_DATE_MISSING"}.issubset(issue_codes(incomplete_file))
        incomplete_entry = next(item for item in expect(client, "GET", "/entries", 200, finance).json() if item["sourceFile"] == "factura-incompleta.txt")
        assert incomplete_entry["validationStatus"] == "failed"
        assert {"INVOICE_NUMBER_MISSING", "VENDOR_MISSING", "INVOICE_DATE_MISSING"}.issubset(issue_codes(incomplete_entry))

        # Review task generation is idempotent; the Reviewer cannot perform final approval.
        tasks_first = expect(client, "GET", "/review/tasks", 200, reviewer).json()
        tasks_second = expect(client, "GET", "/review/tasks", 200, reviewer).json()
        assert len(tasks_first) == len(tasks_second)
        assert len({task["entry"]["id"] for task in tasks_second}) == len(tasks_second)
        translated_task = next(task for task in tasks_second if task["entry"]["id"] == translated_entry["id"])
        expect(client, "POST", f"/review/tasks/{translated_task['id']}/approve", 403, reviewer, json={"comments": "Reviewer must not approve."})

        # Reviewer -> correction -> Finance User resubmission -> Approver workflow.
        corrected = expect(client, "POST", f"/entries/{translated_entry['id']}/request-correction", 200, reviewer, json={"comments": "Confirm the reference."}).json()
        assert corrected["status"] == "changes_requested"
        expect(client, "POST", f"/entries/{translated_entry['id']}/approve", 403, finance, json={"comments": "Not allowed"})
        resubmitted = expect(client, "POST", f"/entries/{translated_entry['id']}/resubmit", 200, finance, json={"comments": "Reference confirmed."}).json()
        assert resubmitted["status"] == "needs_review"
        reviewed = expect(client, "POST", f"/entries/{translated_entry['id']}/mark-reviewed", 200, reviewer, json={"comments": "Review complete."}).json()
        assert reviewed["status"] == "ready_for_approval"
        approved = expect(client, "POST", f"/entries/{translated_entry['id']}/approve", 200, approver, json={"comments": "Approved."}).json()
        assert approved["status"] == "approved"
        assert_balanced(approved)

        # Dashboard count derives from the live queue and never from the old 137 fallback.
        live_tasks = expect(client, "GET", "/review/tasks", 200, reviewer).json()
        pending = sum(1 for task in live_tasks if task["status"] not in {"approved", "rejected"})
        dashboard = expect(client, "GET", "/dashboards/reviewer", 200, reviewer).json()
        dashboard_kpis = {item["key"]: item["value"] for item in dashboard["kpis"]}
        assert int(dashboard_kpis["reviews"]) == pending
        assert int(dashboard_kpis["reviews"]) != 137
        assert dashboard["categoryBreakdown"]

        # SAP records include only approved+valid entries and execution is blocked until configured.
        postings = expect(client, "GET", "/posting/sap", 200, sap_poster).json()
        assert [record["entryId"] for record in postings] == [translated_entry["id"]]
        sap_configuration = expect(client, "GET", "/posting/sap/configuration-status", 200, sap_poster).json()
        assert sap_configuration["canPost"] is False and "disabled" in sap_configuration["message"].lower()
        blocked = expect(client, "POST", f"/posting/sap/{postings[0]['id']}/execute", 422, sap_poster)
        assert "Configure SAP" in blocked.json()["detail"]
        sap_dashboard = expect(client, "GET", "/dashboards/sap_poster", 200, sap_poster).json()
        sap_keys = {item["key"] for item in sap_dashboard["kpis"]}
        assert {"ready", "posted", "failed", "success"}.issubset(sap_keys)
        assert {item["label"] for item in sap_dashboard["sapPosting"]}.issuperset({"Ready to post", "Posted", "Retryable failures", "Non-retryable failures", "Last SAP connection"})

        # Failed integration probes create company-scoped audit/error records.
        failure = expect(client, "POST", "/integrations/sap/test", 200, integrations, json={"baseUrl": ""}).json()
        assert failure["status"] == "failed"
        company_errors = expect(client, "GET", "/monitoring/errors", 200, auditor).json()
        assert any(item["code"] == "SAP_CONNECTION_TEST_FAILED" for item in company_errors)
        company_audit = expect(client, "GET", "/audit/logs", 200, auditor).json()
        assert any(item["action"] == "INTEGRATION_TESTED" for item in company_audit)

        # Auditor read-only contract.
        assert expect(client, "GET", "/entries", 200, auditor).json()
        assert expect(client, "GET", f"/files/{translated_file['id']}", 200, auditor).json()["id"] == translated_file["id"]
        assert expect(client, "GET", "/review/history", 200, auditor).json()
        expect(client, "PATCH", f"/entries/{translated_entry['id']}", 403, auditor, json={"category": "Income"})
        expect(client, "POST", "/files/upload", 403, auditor, files={"file": ("forbidden.txt", b"x", "text/plain")})
        expect(client, "PUT", "/integrations/sap/settings", 403, auditor, json={"baseUrl": "mock://blocked"})
        expect(client, "POST", f"/posting/sap/{postings[0]['id']}/execute", 403, auditor)

        # Super Admin health/usage/provider truthfulness and tenant aggregation.
        provider_cards = expect(client, "GET", "/super-admin/integrations", 200, super_admin).json()
        assert provider_cards and all(card["status"] in {"not_configured", "unknown", "degraded", "outage", "operational"} for card in provider_cards)
        unconfigured = next(card for card in provider_cards if card["status"] == "not_configured")
        assert unconfigured["uptimePercent"] is None and unconfigured["successRate"] is None and unconfigured["latencyMs"] is None
        expect(client, "POST", f"/super-admin/integrations/{unconfigured['code']}/test", 200, super_admin)
        refreshed = expect(client, "GET", "/super-admin/integrations", 200, super_admin).json()
        tested = next(card for card in refreshed if card["code"] == unconfigured["code"])
        assert tested["status"] == "not_configured" and "no live health claim" in tested["message"].lower()

        health = expect(client, "GET", "/super-admin/system-health", 200, super_admin).json()
        assert {service["id"] for service in health} == {"api", "database", "redis", "worker"}
        assert all("message" in service for service in health)
        usage = expect(client, "GET", "/super-admin/dashboard", 200, super_admin).json()
        usage_kpis = {item["key"]: item["value"] for item in usage["kpis"]}
        assert usage_kpis["files_processed"] >= 2 and usage_kpis["entries_processed"] >= 2
        assert usage["usageTrend"]
        platform_errors = expect(client, "GET", "/super-admin/error-center", 200, super_admin).json()
        assert any(item["code"] == "SAP_CONNECTION_TEST_FAILED" for item in platform_errors)
        platform_audit = expect(client, "GET", "/super-admin/audit-logs", 200, super_admin).json()
        assert any(item["action"] == "FILE_UPLOADED" for item in platform_audit)
        assert any(item["action"] == "INTEGRATION_TESTED" for item in platform_audit)

        if os.getenv("SKIP_PDF_REGRESSION") != "1":
            # Supplied scanned invoice samples: process the actual first pages. A readable
            # labelled total is extracted where OCR evidence supports it; difficult scans
            # remain validation_failed rather than receiving a false valid status.
            ocr = expect(client, "GET", "/settings/ocr", 200, admin).json()
            ocr["maxPagesPerFile"] = 1
            expect(client, "PUT", "/settings/ocr", 200, admin, json=ocr)
            scanned_results: dict[str, dict] = {}
            for path in sorted(FIXTURES.glob("*.pdf")):
                scanned_results[path.name] = upload_bytes(client, finance, path.name, path.read_bytes(), "application/pdf")

            ravi = scanned_results["11(3)_page1.pdf"]
            assert ravi["ocrStatus"] == "completed" and ravi["extractionStatus"] == "completed"
            assert ravi["invoiceNumber"] == "S/39106"
            assert ravi["amount"] == 2195.54
            assert ravi["amount"] < 100000
            assert ravi["status"] == "validation_failed"  # Missing/uncertain date/tax must be surfaced.

            amar = scanned_results["12(3)_page1.pdf"]
            assert amar["ocrStatus"] == "completed"
            assert amar["amount"] < 100000
            assert "TOTAL_MISSING" in issue_codes(amar)

            modern = scanned_results["13(3)_page1.pdf"]
            assert modern["ocrStatus"] == "completed"
            assert modern["invoiceNumber"] == "CREDIT-41497/19"
            assert modern["invoiceDate"] == "2019-11-28"
            assert modern["amount"] < 100000
            assert "TOTAL_MISSING" in issue_codes(modern)

            # Source file read/download is available to Approver and Auditor but upload/delete is not.
            for role_headers in (approver, auditor):
                expect(client, "GET", f"/files/{ravi['id']}", 200, role_headers)
                downloaded = expect(client, "GET", f"/files/{ravi['id']}/download", 200, role_headers)
                assert downloaded.content
                expect(client, "DELETE", f"/files/{ravi['id']}", 403, role_headers)

    print("PASS consolidated issue regression test")


if __name__ == "__main__":
    main()
