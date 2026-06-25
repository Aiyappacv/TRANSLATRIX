"""SAP Mapping Service"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from app.modules.sap.models import SAPTCodeMapping, GLAccountMapping

logger = structlog.get_logger(__name__)


class SAPMappingService:
    """SAP mapping lookup and suggestion service"""

    def suggest_tcode(
        self, db: Session, tenant_id: UUID, description: str, category: Optional[str] = None
    ) -> Optional[str]:
        """Suggest SAP T-Code based on description and category"""
        query = db.query(SAPTCodeMapping).filter(
            SAPTCodeMapping.tenant_id == tenant_id,
            SAPTCodeMapping.is_active == True,
        )

        if category:
            query = query.filter(SAPTCodeMapping.category == category)

        mappings = query.order_by(SAPTCodeMapping.priority.desc()).all()

        # Simple keyword matching
        desc_lower = description.lower()
        for mapping in mappings:
            if mapping.keywords:
                if any(kw.lower() in desc_lower for kw in mapping.keywords):
                    logger.info("tcode_matched", tcode=mapping.tcode, description=description)
                    return mapping.tcode

        return None

    def suggest_gl_accounts(
        self, db: Session, tenant_id: UUID, category: str, amount: float
    ) -> List[dict]:
        """Suggest GL accounts for debit and credit"""
        mappings = db.query(GLAccountMapping).filter(
            GLAccountMapping.tenant_id == tenant_id,
            GLAccountMapping.category == category,
            GLAccountMapping.is_active == True,
        ).order_by(GLAccountMapping.priority.desc()).all()

        suggestions = []
        for mapping in mappings[:2]:  # Return top 2
            suggestions.append({
                "gl_account": mapping.gl_account,
                "account_name": mapping.account_name,
                "account_type": mapping.account_type,
            })

        return suggestions
