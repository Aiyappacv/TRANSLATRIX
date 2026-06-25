"""Classification Service"""
from typing import Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from app.modules.classification.models import FinancialClassification, ClassificationMethod
from app.modules.classification.classifiers.rule_based import RuleBasedClassifier
from app.modules.classification.classifiers.ai_based import AIBasedClassifier
from app.modules.entries.models import FinancialEntry

logger = structlog.get_logger(__name__)


class ClassificationService:
    """Classification orchestration service"""

    def __init__(self, config: Optional[Dict] = None):
        self.rule_classifier = RuleBasedClassifier()
        self.ai_classifier = AIBasedClassifier(config or {})

    async def classify_entry(
        self, db: Session, entry_id: UUID, use_ai_fallback: bool = True
    ) -> FinancialClassification:
        """Classify a financial entry"""
        # Get entry
        entry = db.query(FinancialEntry).filter(FinancialEntry.id == entry_id).first()
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        # Try rule-based first
        rule_result = self.rule_classifier.classify(
            entry.translated_description or entry.original_description,
            float(entry.amount) if entry.amount else None,
        )

        # Use AI if rule confidence is low
        final_result = rule_result
        if rule_result["confidence"] < 0.7 and use_ai_fallback:
            logger.info("using_ai_fallback", entry_id=entry_id, rule_confidence=rule_result["confidence"])
            ai_result = await self.ai_classifier.classify(
                entry.translated_description or entry.original_description,
                float(entry.amount) if entry.amount else None,
            )
            if ai_result["confidence"] > rule_result["confidence"]:
                final_result = ai_result

        # Create or update classification
        classification = db.query(FinancialClassification).filter(
            FinancialClassification.entry_id == entry_id
        ).first()

        method_enum = ClassificationMethod.RULE_BASED
        if final_result["method"] == "ai_based":
            method_enum = ClassificationMethod.AI_BASED
        elif rule_result["confidence"] > 0 and final_result["method"] == "ai_based":
            method_enum = ClassificationMethod.HYBRID

        if classification:
            classification.category = final_result["category"]
            classification.confidence = final_result["confidence"]
            classification.reason = final_result["reason"]
            classification.classification_method = method_enum
        else:
            classification = FinancialClassification(
                entry_id=entry_id,
                category=final_result["category"] or "expenses",
                confidence=final_result["confidence"],
                reason=final_result["reason"],
                classification_method=method_enum,
            )
            db.add(classification)

        db.commit()
        db.refresh(classification)

        # Update entry
        entry.category = final_result["category"]
        entry.classification_confidence = final_result["confidence"]
        db.commit()

        logger.info("classification_complete", entry_id=entry_id, category=final_result["category"])
        return classification
