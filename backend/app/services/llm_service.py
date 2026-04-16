"""
LLM Integration Layer
Abstracted LLM calls for classification assistance, NOT legal generation.
MHMDA compliance: LLM assists categorization; final determinations are deterministic.
"""

import os
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
import json
import asyncio

import openai
from anthropic import AsyncAnthropic


@dataclass
class ClassificationResult:
    """Structured output from LLM-assisted classification."""
    field_name: str
    suggested_category: str
    confidence: float  # 0.0 - 1.0
    health_signal: bool
    reasoning: str
    requires_human_review: bool
    alternative_categories: List[str]


@dataclass
class LLMResponse:
    """Generic LLM response wrapper."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class LLMService:
    """
    Unified interface for LLM providers with MHMDA-compliant constraints.
    
    RULES:
    1. LLM assists with categorization suggestions ONLY
    2. Final classification determined by deterministic rules
    3. LLM NEVER generates legal text for policies/consent
    4. All LLM outputs logged to audit trail
    """
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        self.provider = provider.lower()
        self.model = model or self._default_model()
        
        if self.provider == "openai":
            self.client = openai.AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _default_model(self) -> str:
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307"
        }
        return defaults.get(self.provider, "gpt-4o-mini")
    
    async def classify_data_field(
        self,
        field_name: str,
        field_type: str,
        sample_values: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Suggest classification for a data field.
        Uses LLM for semantic understanding; rules engine makes final call.
        """
        system_prompt = """You are a data classification assistant for healthcare-adjacent businesses.
Your task: analyze a data field name and suggest which MHMDA category it likely belongs to.

CATEGORIES (select ONE primary):
- consumer_profile: name, email, address, contact
- identification: SSN, driver_license, ID numbers
- financial: payment cards, banking, billing
- health_biometric: diagnoses, conditions, biometric data
- health_reproductive: pregnancy, fertility, sexual health
- health_precise_geo: precise location tracking (health-related visits)
- health_inferred: inferred health conditions (search history, purchases)
- behavior_online: browsing, clicks, session data
- behavior_cross_site: tracking across domains
- commercial: purchase history, transaction records
- device_tech: IP, device ID, browser fingerprint
- social: social media data, connections

Respond in JSON:
{
  "primary_category": "category_name",
  "health_signal": true/false (does this indicate health info?),
  "confidence": 0.00-1.00,
  "reasoning": "brief explanation",
  "requires_human_review": true/false,
  "alternative_categories": ["cat1", "cat2"]
}

IMPORTANT: This is ASSISTANCE only. Final categorization uses deterministic rules."""

        user_content = f"Field name: {field_name}\nField type: {field_type}"
        if sample_values:
            user_content += f"\nSample values: {', '.join(sample_values[:3])}"
        if context:
            user_content += f"\nContext: {context}"
        
        response = await self._complete(
            system=system_prompt,
            user=user_content,
            json_mode=True,
            max_tokens=500
        )
        
        try:
            result = json.loads(response.content)
            return ClassificationResult(
                field_name=field_name,
                suggested_category=result.get("primary_category", "other"),
                confidence=result.get("confidence", 0.5),
                health_signal=result.get("health_signal", False),
                reasoning=result.get("reasoning", ""),
                requires_human_review=result.get("requires_human_review", True),
                alternative_categories=result.get("alternative_categories", [])
            )
        except json.JSONDecodeError:
            # Fallback: mark for human review
            return ClassificationResult(
                field_name=field_name,
                suggested_category="other",
                confidence=0.0,
                health_signal=False,
                reasoning="LLM response parsing failed",
                requires_human_review=True,
                alternative_categories=[]
            )
    
    async def classify_fields_batch(
        self,
        fields: List[Dict[str, str]],
        max_concurrent: int = 5
    ) -> List[ClassificationResult]:
        """Classify multiple fields with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def classify_with_limit(field):
            async with semaphore:
                return await self.classify_data_field(
                    field_name=field["name"],
                    field_type=field.get("type", "string"),
                    sample_values=field.get("samples"),
                    context=field.get("context")
                )
        
        tasks = [classify_with_limit(f) for f in fields]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def summarize_vendor_description(
        self,
        vendor_name: str,
        description: str,
        website: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Extract structured vendor metadata from free-text description.
        Used for initial vendor enrichment, NOT compliance determination.
        """
        system_prompt = """Extract vendor metadata from description.
Respond ONLY in JSON:
{
  "services": ["list", "of", "services"],
  "data_types_handled": ["pii", "health", "payment", etc.],
  "likely_processes_health_data": true/false,
  "is_ad_tech": true/false,
  "is_analytics": true/false,
  "data_storage_region": "US" or "EU" or "Unknown",
  "confidence": 0.0-1.0
}"""

        user_content = f"Vendor: {vendor_name}\nDescription: {description}"
        if website:
            user_content += f"\nWebsite: {website}"
        
        response = await self._complete(
            system=system_prompt,
            user=user_content,
            json_mode=True,
            max_tokens=300
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "services": [],
                "data_types_handled": [],
                "likely_processes_health_data": False,
                "is_ad_tech": False,
                "is_analytics": False,
                "confidence": 0.0,
                "parsing_failed": True
            }
    
    async def _complete(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        max_tokens: int = 500,
        temperature: float = 0.3  # Low temp for consistency
    ) -> LLMResponse:
        """Provider-agnostic completion wrapper."""
        
        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"} if json_mode else None
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=response.choices[0].finish_reason
            )
        
        elif self.provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            
            content = response.content[0].text
            # Anthropic doesn't have native JSON mode, wrap if requested
            if json_mode:
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    # Attempt to extract JSON from text
                    content = self._extract_json(content)
            
            return LLMResponse(
                content=content,
                model=self.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                finish_reason=response.stop_reason
            )
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that might have markdown or extra content."""
        # Look for JSON code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        
        # Look for curly braces
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        
        return text


class LLMClassificationPipeline:
    """
    Pipeline that combines LLM suggestions with deterministic rules.
    Ensures MHMDA compliance: LLM assists, rules decide.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()
        # Import rules engine
        from .field_classifier import FieldClassifier
        self.classifier = FieldClassifier()
    
    async def classify_with_override(
        self,
        field_name: str,
        field_type: str,
        use_llm_suggestion: bool = True
    ) -> Dict:
        """
        Two-stage classification:
        1. Run deterministic rules
        2. Optionally get LLM suggestion
        3. Return both; rules output is authoritative
        """
        # Stage 1: Deterministic classification (authoritative)
        rules_result = self.classifier.classify_field(field_name, field_type)
        
        # Stage 2: LLM suggestion (advisory only)
        llm_result = None
        confidence_boost = 0.0
        
        if use_llm_suggestion and os.getenv("LLM_CLASSIFICATION_ENABLED", "true").lower() == "true":
            llm_result = await self.llm.classify_data_field(field_name, field_type)
            
            # If LLM strongly agrees with rules, boost confidence
            if llm_result.suggested_category == rules_result['mhmda_category']:
                confidence_boost = llm_result.confidence * 0.1  # Max 10% boost
        
        final_result = {
            'field_name': field_name,
            'field_type': field_type,
            # AUTHORITATIVE (from rules)
            'category': rules_result['mhmda_category'],
            'health_signal': rules_result['health_signal'],
            'confidence': min(rules_result['confidence'] + confidence_boost, 1.0),
            'match_type': rules_result['match_type'],
            # ADVISORY (from LLM, logged only)
            'llm_suggestion': llm_result.suggested_category if llm_result else None,
            'llm_confidence': llm_result.confidence if llm_result else None,
            'llm_reasoning': llm_result.reasoning if llm_result else None,
            'requires_human_review': (
                rules_result['match_type'] in ['pattern', 'none'] or
                (llm_result.requires_human_review if llm_result else False)
            ),
            'classification_method': 'rules_with_llm_assist' if llm_result else 'rules_only'
        }
        
        return final_result
