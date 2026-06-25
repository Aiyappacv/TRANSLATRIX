"""Rule-based Classifier"""
import re
from typing import Dict, Optional, List
import structlog

logger = structlog.get_logger(__name__)


class RuleBasedClassifier:
    """Rule-based financial entry classifier"""

    def __init__(self):
        self.rules = self._initialize_rules()

    def _initialize_rules(self) -> Dict[str, List[Dict]]:
        """Initialize classification rules"""
        return {
            "expenses": [
                {"keywords": ["invoice", "bill", "payment", "expense", "cost", "purchase"], "weight": 0.9},
                {"keywords": ["vendor", "supplier", "payable"], "weight": 0.85},
                {"keywords": ["utilities", "rent", "salary", "office"], "weight": 0.8},
            ],
            "income": [
                {"keywords": ["revenue", "sales", "income", "receipt"], "weight": 0.9},
                {"keywords": ["customer", "receivable", "payment received"], "weight": 0.85},
            ],
            "assets": [
                {"keywords": ["asset", "equipment", "property", "inventory"], "weight": 0.9},
                {"keywords": ["purchase of", "acquisition"], "weight": 0.8},
            ],
            "liabilities": [
                {"keywords": ["loan", "debt", "payable", "liability"], "weight": 0.9},
                {"keywords": ["borrowed", "financing"], "weight": 0.8},
            ],
        }

    def classify(self, description: str, amount: Optional[float] = None) -> Dict:
        """
        Classify financial entry using rules

        Returns:
            {category: str, confidence: float, reason: str, method: str}
        """
        if not description:
            return {"category": None, "confidence": 0.0, "reason": "No description", "method": "rule_based"}

        description_lower = description.lower()
        scores = {}

        # Score each category
        for category, rules in self.rules.items():
            score = 0.0
            matched_keywords = []

            for rule in rules:
                for keyword in rule["keywords"]:
                    if keyword in description_lower:
                        score += rule["weight"]
                        matched_keywords.append(keyword)

            scores[category] = score

        # Get best match
        if not scores or max(scores.values()) == 0:
            return {"category": None, "confidence": 0.0, "reason": "No rules matched", "method": "rule_based"}

        best_category = max(scores, key=scores.get)
        max_score = scores[best_category]

        # Normalize confidence to 0-1
        confidence = min(max_score / 2.0, 1.0)  # Divide by 2 as multiple keywords could match

        logger.info(
            "rule_based_classification",
            category=best_category,
            confidence=confidence,
            scores=scores,
        )

        return {
            "category": best_category,
            "confidence": round(confidence, 2),
            "reason": f"Matched category '{best_category}' based on keywords",
            "method": "rule_based",
        }
