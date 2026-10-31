import json
import logging
from typing import Dict, Any, Optional
from groq import Groq
from src.config import settings

logger = logging.getLogger(__name__)

class GroqMedicalAgent:
    """
    AI-powered clinical reasoning and medical terminology normalization
    using Groq's high-speed inference with Qwen models (e.g. qwen-2.5-32b).
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.client: Optional[Groq] = None
        if self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"):
            try:
                # Official Groq SDK handles the internal /openai/v1 endpoint automatically
                self.client = Groq(api_key=self.api_key, base_url="https://api.groq.com")
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def normalize_clinical_line_item(
        self, description: str, category: str, primary_diagnosis: str
    ) -> Dict[str, Any]:
        """
        Uses Qwen 2.5 on Groq to parse ambiguous line items, identifying:
        - standard clinical concept (SNOMED / ICD)
        - whether it is an excluded consumable / luxury item
        - clinical justification
        """
        if not self.is_available:
            return {
                "concept": description,
                "is_excluded": False,
                "reasoning": "Offline mode: AI evaluation skipped (Groq API key not set)",
                "ai_assisted": False,
            }

        prompt = f"""You are an expert AI Insurance Medical Auditor.
Analyze the following hospital invoice line item:
Item Description: "{description}"
Category Tag: "{category}"
Primary Diagnosis: "{primary_diagnosis}"

Determine:
1. Standardized clinical/medical terminology concept.
2. Whether this item is typically considered an EXCLUDED NON-PAYABLE CONSUMABLE / LUXURY / ADMINISTRATIVE item under standard health insurance policies.
3. Brief clinical reason.

Respond ONLY with valid JSON in this exact structure:
{{
  "concept": "<standardized term>",
  "is_excluded": <true|false>,
  "reasoning": "<concise explanation>"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a specialized medical claims auditor returning strict JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            parsed["ai_assisted"] = True
            return parsed
        except Exception as e:
            logger.warning(f"Groq Qwen API call failed: {e}. Falling back to deterministic rules.")
            return {
                "concept": description,
                "is_excluded": False,
                "reasoning": f"Groq fallback: {str(e)}",
                "ai_assisted": False,
            }

groq_agent = GroqMedicalAgent()

