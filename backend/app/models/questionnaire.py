from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, JSON, Index, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base

class BusinessType(str, enum.Enum):
    WELLNESS_CENTER = "wellness_center"
    PHYSICAL_THERAPY = "physical_therapy"
    MEDICAL_SPA = "medical_spa"
    HEALTH_COACHING = "health_coaching"
    FITNESS_STUDIO = "fitness_studio"
    NUTRITION_PRACTICE = "nutrition_practice"
    MENTAL_HEALTH = "mental_health"
    OTHER = "other"

class QuestionnaireStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"

class QuestionnaireResponse(Base):
    """Stores MHMDA applicability questionnaire responses with save/resume support."""
    
    __tablename__ = "questionnaire_responses"
    __table_args__ = (
        Index("ix_questionnaire_org_status", "organization_id", "status"),
        Index("ix_questionnaire_current_step", "current_step"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    # Save/Resume tracking
    current_step = Column(String(50), default="business_info", nullable=False)
    status = Column(Enum(QuestionnaireStatus), default=QuestionnaireStatus.DRAFT, nullable=False, index=True)
    progress_percent = Column(String(10), default="0%")
    
    # Core business info (Step 1)
    business_type = Column(Enum(BusinessType), nullable=True)
    business_type_other = Column(Text, nullable=True)
    business_name = Column(String(255), nullable=True)
    services_offered = Column(JSON, default=list)  # List of service strings
    
    # Website/Online presence (Step 2)
    has_website = Column(Boolean, default=False)
    website_url = Column(String(500), nullable=True)
    website_features = Column(JSON, default=list)  # ["booking", "payment", "contact_form", etc]
    uses_third_party_booking = Column(Boolean, default=False)
    third_party_booking_provider = Column(String(255), nullable=True)
    
    # Data collection (Step 3)
    collects_health_data = Column(Boolean, default=False)
    health_data_types = Column(JSON, default=list)  # Types of health data collected
    collects_insurance_info = Column(Boolean, default=False)
    collects_medical_history = Column(Boolean, default=False)
    collects_fitness_data = Column(Boolean, default=False)
    collects_nutrition_data = Column(Boolean, default=False)
    collects_mental_health_notes = Column(Boolean, default=False)
    
    # Inferred data (Step 4)
    makes_health_inferences = Column(Boolean, default=False)
    inference_types = Column(JSON, default=list)  # Types of inferences made
    
    # Vendor/Processor inventory (Step 5)
    vendor_list = Column(JSON, default=list)  # [{"name": "Stripe", "purpose": "payment"}]
    
    # Location/CDP/Adtech (Step 6)
    uses_location_based_marketing = Column(Boolean, default=False)
    uses_advertising_pixels = Column(Boolean, default=False)
    advertising_platforms = Column(JSON, default=list)  # ["Facebook", "Google", etc]
    
    # Data sharing (Step 7)
    shares_health_data = Column(Boolean, default=False)
    sharing_recipients = Column(JSON, default=list)  # Who data is shared with
    has_processor_contracts = Column(Boolean, default=False)
    
    # Metadata
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_saved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Version control for edits
    version = Column(String(10), default="1.0")
    
    # Relationships
    organization = relationship("Organization", back_populates="questionnaires")
    applicability_result = relationship("ApplicabilityResult", back_populates="questionnaire", uselist=False)

class ApplicabilityResult(Base):
    """Stores MHMDA applicability assessment results."""
    
    __tablename__ = "applicability_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False)
    questionnaire_id = Column(UUID(as_uuid=True), ForeignKey("questionnaire_responses.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Assessment result
    status = Column(String(20), nullable=False)  # in_scope, out_of_scope, unclear
    confidence_score = Column(String(10), default="high")  # high, medium, low
    
    # Detailed breakdown
    mhmda_signals = Column(JSON, default=list)  # Signals indicating MHMDA applicability
    hipaa_triage_status = Column(String(50), nullable=True)  # If HIPAA overlap detected
    
    # Escalation and actions
    escalation_triggers = Column(JSON, default=list)  # Reasons for escalation
    required_actions = Column(JSON, default=list)  # List of actions required
    
    # Human review flag
    requires_human_review = Column(Boolean, default=False)
    review_reason = Column(Text, nullable=True)
    
    # Generation metadata
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    rule_version = Column(String(20), default="1.0.0")
    
    # Acknowledgment
    acknowledged_by_user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    questionnaire = relationship("QuestionnaireResponse", back_populates="applicability_result")
