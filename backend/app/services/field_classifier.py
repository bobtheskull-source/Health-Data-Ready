"""
Intake Field Classifier
Rules-based classification of form fields for health data detection.
Template-first approach, no LLM required for standard cases.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class FieldConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ClassificationResult:
    field_name: str
    display_name: str
    category: str
    is_health_data: bool
    is_inferred: bool
    confidence: FieldConfidence
    reasoning: str
    requires_review: bool

# Health data taxonomy - exact matches and patterns
HEALTH_DATA_PATTERNS = {
    "identifiers": {
        "patterns": [r"name", r"email", r"phone", r"address", r"patient[_\s]?id", r"member[_\s]?id"],
        "confidence": FieldConfidence.HIGH
    },
    "health_status": {
        "patterns": [
            r"condition", r"diagnosis", r"disease", r"symptom", r"illness",
            r"injury", r"disorder", r"syndrome", r"health[_\s]?status",
            r"medical[_\s]?condition", r"current[_\s]?health"
        ],
        "confidence": FieldConfidence.HIGH
    },
    "medical_history": {
        "patterns": [
            r"history", r"past[_\s]?medical", r"previous[_\s]?condition",
            r"surgery", r"hospitalization", r"medication[_\s]?history",
            r"family[_\s]?history", r"allergies", r"immunization"
        ],
        "confidence": FieldConfidence.HIGH
    },
    "mental_health": {
        "patterns": [
            r"mental[_\s]?health", r"psychiatric", r"psychological",
            r"depression", r"anxiety", r"therapy", r"counseling",
            r"mood", r"stress", r"emotional[_\s]?wellness"
        ],
        "confidence": FieldConfidence.HIGH
    },
    "fitness": {
        "patterns": [
            r"exercise", r"workout", r"fitness", r"activity[_\s]?level",
            r"steps", r"heart[_\s]?rate", r"calories[_\s]?burned"
        ],
        "confidence": FieldConfidence.MEDIUM
    },
    "nutrition": {
        "patterns": [
            r"diet", r"nutrition", r"food", r"eating[_\s]?habits",
            r"weight", r"bmi", r"body[_\s]?mass", r"calories[_\s]?consumed"
        ],
        "confidence": FieldConfidence.MEDIUM
    },
    "biometric": {
        "patterns": [
            r"blood[_\s]?pressure", r"glucose", r"cholesterol", r"heart[_\s]?rate",
            r"sleep", r"temperature", r"oxygen", r"biometric"
        ],
        "confidence": FieldConfidence.HIGH
    },
    "insurance": {
        "patterns": [
            r"insurance", r"policy[_\s]?number", r"carrier", r"group[_\s]?number",
            r"subscriber", r"medicaid", r"medicare"
        ],
        "confidence": FieldConfidence.HIGH
    },
    "inferred": {
        "patterns": [
            r"predict", r"risk[_\s]?score", r"health[_\s]?score",
            r"assessment", r"recommendation", r"personalized[_\s]?plan"
        ],
        "confidence": FieldConfidence.MEDIUM
    }
}

# Fields that are definitely NOT health data
NON_HEALTH_PATTERNS = [
    r"^date$", r"^timestamp$", r"^created[_\s]?at$", r"^updated[_\s]?at$",
    r"status$", r"^id$", r"_id$", r"^uuid$", r"^referral[_\s]?code$",
    r"^marketing", r"^survey", r"^feedback$"
]

def classify_field(field_name: str, field_context: Optional[str] = None) -> ClassificationResult:
    """
    Classify a single field from an intake form.
    
    Args:
        field_name: The field name/key from the form
        field_context: Optional context (label, placeholder, etc)
    
    Returns:
        ClassificationResult with category, confidence, and reasoning
    """
    field_lower = field_name.lower()
    context_lower = (field_context or "").lower()
    combined = f"{field_lower} {context_lower}"
    
    # Check non-health patterns first
    for pattern in NON_HEALTH_PATTERNS:
        if re.search(pattern, field_lower):
            return ClassificationResult(
                field_name=field_name,
                display_name=_format_display_name(field_name),
                category="operational",
                is_health_data=False,
                is_inferred=False,
                confidence=FieldConfidence.HIGH,
                reasoning="Standard operational field, not health-related",
                requires_review=False
            )
    
    # Check health data patterns
    for category, config in HEALTH_DATA_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, combined):
                is_inferred = category == "inferred"
                return ClassificationResult(
                    field_name=field_name,
                    display_name=_format_display_name(field_name),
                    category=category,
                    is_health_data=True,
                    is_inferred=is_inferred,
                    confidence=config["confidence"],
                    reasoning=f"Matched pattern '{pattern}' in {category} category",
                    requires_review=config["confidence"] != FieldConfidence.HIGH
                )
    
    # Ambiguous - flag for review
    return ClassificationResult(
        field_name=field_name,
        display_name=_format_display_name(field_name),
        category="uncategorized",
        is_health_data=False,
        is_inferred=False,
        confidence=FieldConfidence.LOW,
        reasoning="No clear pattern match - manual categorization recommended",
        requires_review=True
    )

def classify_form_fields(fields: List[Dict[str, str]]) -> List[ClassificationResult]:
    """
    Classify multiple fields from a form.
    
    Args:
        fields: List of dicts with 'name' and optionally 'label' keys
    
    Returns:
        List of ClassificationResult for each field
    """
    results = []
    for field in fields:
        result = classify_field(
            field_name=field.get("name", ""),
            field_context=field.get("label") or field.get("placeholder")
        )
        results.append(result)
    return results

def generate_data_inventory(results: List[ClassificationResult]) -> Dict:
    """
    Generate a summary data inventory from classification results.
    """
    health_fields = [r for r in results if r.is_health_data]
    inferred_fields = [r for r in results if r.is_inferred]
    review_needed = [r for r in results if r.requires_review]
    
    return {
        "total_fields": len(results),
        "health_data_fields": len(health_fields),
        "inferred_health_fields": len(inferred_fields),
        "requires_manual_review": len(review_needed),
        "high_confidence": len([r for r in results if r.confidence == FieldConfidence.HIGH]),
        "categories": _group_by_category(results),
        "fields_requiring_review": [
            {"name": r.field_name, "reason": r.reasoning}
            for r in review_needed
        ]
    }

def _format_display_name(field_name: str) -> str:
    """Convert snake_case or camelCase to readable display name."""
    # Replace underscores and dashes with spaces
    name = re.sub(r'[_\-]', ' ', field_name)
    # Insert space before camelCase capitals
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    # Capitalize each word
    return name.title()

def _group_by_category(results: List[ClassificationResult]) -> Dict[str, int]:
    """Group classification results by category."""
    categories = {}
    for result in results:
        categories[result.category] = categories.get(result.category, 0) + 1
    return categories

def process_csv_headers(headers: List[str]) -> List[ClassificationResult]:
    """Process CSV column headers for data inventory."""
    fields = [{"name": h, "label": h} for h in headers]
    return classify_form_fields(fields)
