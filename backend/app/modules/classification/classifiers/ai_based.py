"""AI-based Classifier using LLM"""
from typing import Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class AIBasedClassifier:
    """LLM-based financial entry classifier"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self.config.get("openai_api_key")
        self.model = self.config.get("model", "gpt-3.5-turbo")

    async def classify(self, description: str, amount: Optional[float] = None) -> Dict:
        """
        Classify using AI

        Returns:
            {category: str, confidence: float, reason: str, method: str}
        """
        try:
            from openai import AsyncOpenAI

            if not self.api_key:
                logger.warning("openai_api_key_not_configured")
                return {"category": None, "confidence": 0.0, "reason": "AI not configured", "method": "ai_based"}

            client = AsyncOpenAI(api_key=self.api_key)

            prompt = f"""Classify this financial entry into ONE of these categories: expenses, income, assets, liabilities.

Description: {description}
Amount: {amount if amount else 'N/A'}

Respond in JSON format:
{{"category": "<category>", "confidence": <0.0-1.0>, "reason": "<brief reason>"}}"""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial classification expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            import json
            result = json.loads(result_text)

            logger.info("ai_classification", category=result.get("category"), confidence=result.get("confidence"))

            return {
                "category": result.get("category"),
                "confidence": result.get("confidence", 0.9),
                "reason": result.get("reason", "AI classified"),
                "method": "ai_based",
            }

        except Exception as e:
            logger.error("ai_classification_error", error=str(e))
            return {"category": None, "confidence": 0.0, "reason": f"AI error: {str(e)}", "method": "ai_based"}
