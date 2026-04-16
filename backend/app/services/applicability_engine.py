"""
MHMDA Applicability Rules Engine
Deterministic rule-based assessment for MHMDA applicability.
No LLM dependency - rules first as per spec.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class ScopeStatus(str, Enum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    UNCLEAR = "unclear"

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ApplicabilityAssessment:
    status: ScopeStatus
    confidence: Confidence
    signals: List[str]
    escalation_triggers: List[str]
    required_actions: List[str]
    hipaa_triage: str
    requires_human_review: bool
    review_reasons: List[str]

def assess_applicability(questionnaire: dict) -> ApplicabilityAssessment:
    """
    Main entry point for applicability assessment.
    Takes questionnaire response dict, returns assessment.
    """
    signals = []
    escalation_triggers = []
    required_actions = []
    review_reasons = []
    
    # Extract key fields
    business_type = questionnaire.get("business_type")
    collects_health_data = questionnaire.get("collects_health_data", False)
    health_data_types = questionnaire.get("health_data_types", [])
    collects_medical_history = questionnaire.get("collects_medical_history", False)
    collects_mental_health_notes = questionnaire.get("collects_mental_health_notes", False)
    makes_health_inferences = questionnaire.get("makes_health_inferences", False)
    uses_location_marketing = questionnaire.get("uses_location_based_marketing", False)
    uses_advertising_pixels = questionnaire.get("uses_advertising_pixels", False)
    shares_health_data = questionnaire.get("shares_health_data", False)
    services_offered = [s.lower() for s in questionnaire.get("services_offered", [])]
    
    # RULE 1: Definite triggers (almost certainly in scope)
    definite_triggers = []
    
    if collects_medical_history:
        definite_triggers.append("Collects medical history/diagnoses")
    if collects_mental_health_notes:
        definite_triggers.append("Collects mental health information")
    if makes_health_inferences:
        definite_triggers.append("Makes inferences about health status")
    if any("medical" in s or "clinical" in s or "diagnosis" in s for s in services_offered):
        definite_triggers.append("Services include medical/clinical terminology")
    if "insurance" in [ht.lower() for ht in health_data_types]:
        definite_triggers.append("Collects insurance/claims information")
    
    # RULE 2: Strong indicators of likely in-scope
    strong_indicators = []
    
    health_adjacent_businesses = [
        "physical_therapy", "medical_spa", "mental_health"
    ]
    if business_type in health_adjacent_businesses:
        strong_indicators.append(f"Business type: {business_type}")
    
    if collects_health_data and len(health_data_types) >= 3:
        strong_indicators.append("Multiple types of health data collected")
    
    # RULE 3: Adtech/location red flags (automatic escalation)
    if uses_location_marketing:
        escalation_triggers.append("Uses location-based marketing (geofencing concern)")
        required_actions.append("Review geofencing compliance - MHMDA Section 5 restriction")
        signals.append("Location-based marketing detected")
    
    if uses_advertising_pixels:
        escalation_triggers.append("Uses advertising pixels/trackers on website")
        required_actions.append("Review adtech data sharing - potential inferred data concern")
        signals.append("Advertising tracking detected")
    
    if shares_health_data:
        signals.append("Shares consumer health data with third parties")
        required_actions.append("Map all data flows and verify processor contracts")
    
    # RULE 4: HIPAA overlap check
    hipaa_triage = check_hipaa_overlap(questionnaire)
    if hipaa_triage == "likely_hipaa_covered":
        escalation_triggers.append("Possible HIPAA-covered entity")
        review_reasons.append("Business may be HIPAA-covered; MHMDA applies to non-HIPAA consumer health data")
        signals.append("Potential HIPAA overlap - requires verification")
    elif hipaa_triage == "hybrid":
        required_actions.append("Identify HIPAA vs non-HIPAA data flows")
        signals.append("Potential hybrid entity - separate flows required")
    
    # RULE 5: Out-of-scope indicators
    out_of_scope_indicators = []
    
    if not collects_health_data and not makes_health_inferences:
        out_of_scope_indicators.append("No health data or inferences collected")
    
    if business_type == "fitness_studio" and not collects_medical_history:
        out_of_scope_indicators.append("Pure fitness without health data collection")
    
    # RULE 6: Unclear/ambiguous cases
    if business_type == "other" and not questionnaire.get("business_type_other"):
        review_reasons.append("Business type marked 'other' without description")
        escalation_triggers.append("Unclear business classification")
    
    if collects_health_data and business_type == "wellness_center":
        review_reasons.append("Wellness centers have variable scope - fact-dependent")
        required_actions.append("Detailed analysis of exact data types and uses required")
    
    # DETERMINE OUTCOME
    requires_human_review = False
    status = ScopeStatus.UNCLEAR
    confidence = Confidence.LOW
    
    # In-scope determination
    if definite_triggers:
        status = ScopeStatus.IN_SCOPE
        confidence = Confidence.HIGH
        signals.extend(definite_triggers)
    elif strong_indicators:
        status = ScopeStatus.IN_SCOPE
        confidence = Confidence.MEDIUM
        signals.extend(strong_indicators)
    # Out-of-scope determination
    elif out_of_scope_indicators and not signals:
        status = ScopeStatus.OUT_OF_SCOPE
        confidence = Confidence.MEDIUM
    
    # Escalation overrides
    if escalation_triggers:
        requires_human_review = True
        if len(review_reasons) >= 2 or "Possible HIPAA-covered entity" in escalation_triggers:
            confidence = Confidence.LOW  # High complexity = lower confidence in automated assessment
    
    # Edge case: Consumer health data inferences only
    if makes_health_inferences and not collects_health_data:
        signals.append("Inferred health data only - Section 3(1)(a)(ii) may apply")
        required_actions.append("Review inferred data collection practices")
        status = ScopeStatus.IN_SCOPE
        confidence = Confidence.MEDIUM
        requires_human_review = True
    
    # Ensure required actions list
    if status == ScopeStatus.IN_SCOPE and not required_actions:
        required_actions.append("Draft and post MHMDA consumer health data privacy policy")
        required_actions.append("Establish consumer rights request workflow")
        required_actions.append("Map and document data inventory")
    
    return ApplicabilityAssessment(
        status=status,
        confidence=confidence,
        signals=signals,
        escalation_triggers=escalation_triggers,
        required_actions=required_actions,
        hipaa_triage=hipaa_triage,
        requires_human_review=requires_human_review,
        review_reasons=review_reasons
    )

def check_hipaa_overlap(questionnaire: dict) -> str:
    """
    Simple triage for HIPAA overlap.
    Returns: 'likely_hipaa_covered', 'hybrid', 'likely_not_covered', or 'unclear'
    """
    health_data_types = [ht.lower() for ht in questionnaire.get("health_data_types", [])]
    services = [s.lower() for s in questionnaire.get("services_offered", [])]
    
    # Indicators of HIPAA coverage
    hipaa_indicators = [
        "medical records", "ehr", "electronic health", "phi", "protected health",
        "billing", "insurance claims", "medicare", "medicaid"
    ]
    
    direct_care_indicators = [
        "diagnose", "treat", "prescribe", "clinical", "medical doctor",
        "physician", "nurse practitioner", "licensed therapist"
    ]
    
    hipaa_score = sum(1 for ind in hipaa_indicators if any(ind in ht for ht in health_data_types))
    direct_care_score = sum(1 for ind in direct_care_indicators if any(ind in s for s in services))
    
    if hipaa_score >= 2 or direct_care_score >= 1:
        return "likely_hipaa_covered"
    elif hipaa_score == 1:
        return "hybrid"
    else:
        return "likely_not_covered"

def get_step_data(step: int, questionnaire: dict) -> dict:
    """Extract step-specific data for partial save/resume."""
    step_fields = {
        1: ["business_type", "business_type_other", "business_name", "services_offered"],
        2: ["has_website", "website_url", "website_features", "uses_third_party_booking", "third_party_booking_provider"],
        3: ["collects_health_data", "health_data_types", "collects_insurance_info", "collects_medical_history", "collects_fitness_data", "collects_nutrition_data", "collects_mental_health_notes"],
        4: ["makes_health_inferences", "inference_types"],
        5: ["vendor_list"],
        6: ["uses_location_based_marketing", "uses_advertising_pixels", "advertising_platforms"],
        7: ["shares_health_data", "sharing_recipients", "has_processor_contracts"]
    }
    
    return {field: questionnaire.get(field) for field in step_fields.get(step, [])}

def calculate_progress(current_step: int) -> str:
    """Calculate progress percentage based on step."""
    total_steps = 7
    pct = min(int((current_step / total_steps) * 100), 99)
    if current_step == total_steps:
        pct = 100
    return f"{pct}%"
