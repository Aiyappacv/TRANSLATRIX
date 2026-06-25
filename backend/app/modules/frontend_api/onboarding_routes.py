from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.store import get_state, scope_for_user, set_state
from app.modules.frontend_api.utils import now_iso

router = APIRouter()

STEPS = [
    ("company-profile", "Company profile", "Company identity and contact details"),
    ("finance-config", "Finance configuration", "Company code, currency, fiscal year, and approval policy"),
    ("users-invited", "User invitations", "Invite finance, review, posting, and audit roles"),
    ("integration-selection", "Integration selection", "Select SAP and accounting connectors"),
    ("security-settings", "Security settings", "MFA, SSO, and IP access controls"),
    ("review-submit", "Review and submit", "Confirm the onboarding configuration"),
]


def state_for(draft, submitted=False):
    completed = 6 if submitted else (1 if draft else 0)
    current = min(completed, 5)
    return {
        "currentStep": STEPS[current][0],
        "completion": round((completed / len(STEPS)) * 100),
        "steps": [
            {"id": sid, "title": title, "description": desc, "status": "completed" if i < completed else "current" if i == current else "pending"}
            for i, (sid, title, desc) in enumerate(STEPS)
        ],
    }


@router.get("/onboarding", dependencies=[Depends(require_frontend_permission("onboarding:manage"))])
def get_onboarding(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    draft = get_state(db, scope, "onboarding_draft", None)
    submitted = bool(get_state(db, scope, "onboarding_submitted", False))
    return state_for(draft, submitted)


@router.get("/onboarding/draft", dependencies=[Depends(require_frontend_permission("onboarding:manage"))])
def get_draft(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "onboarding_draft", None)


@router.put("/onboarding/draft", dependencies=[Depends(require_frontend_permission("onboarding:manage"))])
def save_draft(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    set_state(db, scope_for_user(current_user), "onboarding_draft", payload)
    return {"status": "saved", "savedAt": now_iso(), "payload": payload}


@router.post("/onboarding/submit", dependencies=[Depends(require_frontend_permission("onboarding:manage"))])
def submit(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    set_state(db, scope, "onboarding_draft", payload)
    set_state(db, scope, "onboarding_submitted", True)
    return {"status": "submitted", "company": {"id": str(current_user.company_id or "platform"), "name": getattr(getattr(current_user, "company", None), "legal_name", "Platform"), "tenantId": str(current_user.tenant_id or "platform")}, "payload": payload}


@router.post("/onboarding/complete-step", dependencies=[Depends(require_frontend_permission("onboarding:manage"))])
def complete_step(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    steps = get_state(db, scope_for_user(current_user), "onboarding_completed_steps", [])
    step_id = str(payload.get("stepId") or "")
    if step_id and step_id not in steps:
        steps.append(step_id)
        set_state(db, scope_for_user(current_user), "onboarding_completed_steps", steps)
    return {"stepId": step_id, "status": "completed"}
