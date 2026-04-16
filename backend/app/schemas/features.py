from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.vendors import VendorRole, ContractStatus

# Vendor schemas
class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=500)
    role: VendorRole = VendorRole.UNKNOWN
    contract_status: ContractStatus = ContractStatus.NONE
    location_country: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)

class VendorCreate(VendorBase):
    adtech_flag: bool = False
    location_flag: bool = False
    shares_health_data: bool = False
    has_subprocessors: bool = False
    privacy_contact_email: Optional[str] = None

class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=500)
    role: Optional[VendorRole] = None
    contract_status: Optional[ContractStatus] = None
    location_country: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)
    adtech_flag: Optional[bool] = None
    location_flag: Optional[bool] = None
    shares_health_data: Optional[bool] = None
    has_subprocessors: Optional[bool] = None
    privacy_contact_email: Optional[str] = None
    is_active: Optional[bool] = None

class VendorResponse(VendorBase):
    id: UUID
    organization_id: UUID
    adtech_flag: bool
    location_flag: bool
    deletion_notice_required: bool
    shares_health_data: bool
    has_subprocessors: bool
    privacy_contact_email: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class VendorListResponse(BaseModel):
    total: int
    items: List[VendorResponse]

# Questionnaire schemas
from app.models.questionnaire import BusinessType, QuestionnaireStatus

class QuestionnaireBase(BaseModel):
    business_type: Optional[BusinessType] = None
    business_type_other: Optional[str] = None
    business_name: Optional[str] = Field(None, max_length=255)
    services_offered: List[str] = []

class QuestionnaireStep1(QuestionnaireBase):
    pass

class QuestionnaireStep2(BaseModel):
    has_website: bool = False
    website_url: Optional[str] = Field(None, max_length=500)
    website_features: List[str] = []
    uses_third_party_booking: bool = False
    third_party_booking_provider: Optional[str] = Field(None, max_length=255)

class QuestionnaireStep3(BaseModel):
    collects_health_data: bool = False
    health_data_types: List[str] = []
    collects_insurance_info: bool = False
    collects_medical_history: bool = False
    collects_fitness_data: bool = False
    collects_nutrition_data: bool = False
    collects_mental_health_notes: bool = False

class QuestionnaireStep4(BaseModel):
    makes_health_inferences: bool = False
    inference_types: List[str] = []

class QuestionnaireStep5(BaseModel):
    vendor_list: List[dict] = []

class QuestionnaireStep6(BaseModel):
    uses_location_based_marketing: bool = False
    uses_advertising_pixels: bool = False
    advertising_platforms: List[str] = []

class QuestionnaireStep7(BaseModel):
    shares_health_data: bool = False
    sharing_recipients: List[str] = []
    has_processor_contracts: bool = False

class QuestionnaireCreate(BaseModel):
    pass

class QuestionnaireResponse(BaseModel):
    id: UUID
    organization_id: UUID
    current_step: str
    status: QuestionnaireStatus
    progress_percent: str
    
    # Step data
    business_type: Optional[BusinessType]
    business_name: Optional[str]
    services_offered: List[str]
    has_website: bool
    website_url: Optional[str]
    collects_health_data: bool
    health_data_types: List[str]
    uses_location_based_marketing: bool
    uses_advertising_pixels: bool
    advertising_platforms: List[str]
    shares_health_data: bool
    
    # Metadata
    started_at: datetime
    last_saved_at: datetime
    submitted_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class QuestionnaireSaveResponse(BaseModel):
    success: bool
    questionnaire_id: UUID
    current_step: str
    progress_percent: str
    next_step: Optional[str] = None

# Applicability result schemas
class ApplicabilityResultResponse(BaseModel):
    id: UUID
    status: str
    confidence_score: str
    mhmda_signals: List[str]
    hipaa_triage_status: Optional[str]
    escalation_triggers: List[str]
    required_actions: List[str]
    requires_human_review: bool
    review_reason: Optional[str]
    generated_at: datetime
    rule_version: str
    acknowledged_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ApplicabilityResultAcknowledge(BaseModel):
    acknowledge: bool
    notes: Optional[str] = None
