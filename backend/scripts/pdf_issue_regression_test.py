"""Focused regression test for the three supplied scanned invoice samples."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DB_PATH = Path("/tmp/translatrix_pdf_issue_regression.db")
UPLOAD_PATH = Path("/tmp/translatrix_pdf_issue_regression_uploads")
if DB_PATH.exists():
    DB_PATH.unlink()
if UPLOAD_PATH.exists():
    shutil.rmtree(UPLOAD_PATH)

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
FIXTURES = Path(os.getenv("SUPPLIED_PDF_DIR", str(ROOT / "tests" / "fixtures" / "issue_invoices")))


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, (email, response.status_code, response.text)
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def request(client: TestClient, method: str, path: str, expected: int, headers=None, **kwargs):
    response = client.request(method, f"{BASE}{path}", headers=headers, **kwargs)
    assert response.status_code == expected, (method, path, expected, response.status_code, response.text)
    return response


def issue_codes(item: dict) -> set[str]:
    return {str(issue.get("code")) for issue in item.get("issues", item.get("validationIssues", []))}


def main() -> None:
    seed_development()
    with TestClient(app) as client:
        admin = login(client, "admin@translatrix.example.com")
        finance = login(client, "finance.user@translatrix.example.com")
        approver = login(client, "approver@translatrix.example.com")
        auditor = login(client, "auditor@translatrix.example.com")

        ocr = request(client, "GET", "/settings/ocr", 200, admin).json()
        ocr["maxPagesPerFile"] = 1
        request(client, "PUT", "/settings/ocr", 200, admin, json=ocr)

        results: dict[str, dict] = {}
        for path in sorted(FIXTURES.glob("*.pdf")):
            print(f"Processing {path.name}", flush=True)
            response = request(
                client,
                "POST",
                "/files/upload",
                201,
                finance,
                files={"file": (path.name, path.read_bytes(), "application/pdf")},
            )
            results[path.name] = response.json()

        ravi_key = next(name for name in results if name.startswith("11(3)"))
        amar_key = next(name for name in results if name.startswith("12(3)"))
        modern_key = next(name for name in results if name.startswith("13(3)"))

        for name, item in results.items():
            print(
                f"RESULT {name}: invoice={item.get('invoiceNumber')} date={item.get('invoiceDate')} "
                f"amount={item.get('amount')} status={item.get('status')} issues={sorted(issue_codes(item))}",
                flush=True,
            )

        ravi = results[ravi_key]
        assert ravi["ocrStatus"] == "completed" and ravi["extractionStatus"] == "completed"
        assert ravi["invoiceNumber"] == "S/39106"
        assert ravi["amount"] == 2195.54 and ravi["amount"] < 100000
        assert ravi["status"] == "validation_failed"

        amar = results[amar_key]
        assert amar["ocrStatus"] == "completed"
        assert amar["amount"] < 100000
        assert "TOTAL_MISSING" in issue_codes(amar)

        modern = results[modern_key]
        assert modern["ocrStatus"] == "completed"
        assert modern["invoiceNumber"] == "CREDIT-41497/19"
        assert modern["invoiceDate"] == "2019-11-28"
        assert modern["amount"] < 100000
        assert "TOTAL_MISSING" in issue_codes(modern)

        for role_headers in (approver, auditor):
            request(client, "GET", f"/files/{ravi['id']}", 200, role_headers)
            downloaded = request(client, "GET", f"/files/{ravi['id']}/download", 200, role_headers)
            assert downloaded.content
            request(client, "DELETE", f"/files/{ravi['id']}", 403, role_headers)

    print("PASS supplied-PDF processing regression test")


if __name__ == "__main__":
    main()
