from datetime import datetime
from sqlalchemy import Column, DateTime, JSON, String
from app.database import Base


class FrontendState(Base):
    """Tenant/company scoped JSON state used by the frontend-facing API.

    The existing domain tables remain authoritative for users and companies. This
    table persists UI-facing workflow/configuration data whose richer frontend
    contract is not yet represented by a dedicated domain model.
    """

    __tablename__ = "frontend_state"

    scope_key = Column(String(180), primary_key=True)
    namespace = Column(String(100), primary_key=True)
    payload = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
