from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Enum, JSON, Index, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base

class DataCategory(str, enum.Enum):
    IDENTIFIERS = "identifiers"
    CONTACT = "contact"
    DEMOGRAPHIC = "demographic"
    HEALTH_STATUS = "health_status"
    MEDICAL_HISTORY = "medical_history"
    MENTAL_HEALTH = "mental_health"
    FITNESS = "fitness"
    NUTRITION = "nutrition"
    BIOMETRIC = "biometric"
    GENETIC = "genetic"
    INSURANCE = "insurance"
    PAYMENT = "payment"
    LOCATION = "location"
    DEVICE = "device"
    INFERRED = "inferred"
    OTHER = "other"

class HealthSignalType(str, enum.Enum):
    DIRECT = "direct"  # Explicitly provided health info
    INFERRED_HEALTH = "inferred_health"  # Algorithmically inferred
    LINKABLE = "linkable"  # Can be combined to identify health status
    NOT_HEALTH = "not_health"  # Not health data

class RetentionStatus(str, enum.Enum):
    ACTIVE = "active"
    SCHEDULED_FOR_DELETION = "scheduled_for_deletion"
    ARCHIVED = "archived"
    DELETED = "deleted"

class StorageType(str, enum.Enum):
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CLOUD_STORAGE = "cloud_storage"
    THIRD_PARTY = "third_party"
    ANALYTICS = "analytics"
    BACKUP = "backup"

class DataElement(Base):
    """Individual data element in the inventory - the core of data mapping."""
    
    __tablename__ = "data_elements"
    __table_args__ = (
        Index("ix_dataelement_org_category", "organization_id", "category"),
        Index("ix_dataelement_health_signal", "health_signal"),
        Index("ix_dataelement_vendor", "source_vendor_id"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    # Field identification
    field_name = Column(String(255), nullable=False)
    display_name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification per MHMDA
    category = Column(Enum(DataCategory), nullable=False)
    health_signal = Column(Enum(HealthSignalType), default=HealthSignalType.NOT_HEALTH, nullable=False)
    is_inferred = Column(Boolean, default=False)
    inference_method = Column(String(500), nullable=True)  # How it was inferred
    identifier_linkability = Column(String(50), default="low")  # high/medium/low
    
    # Source tracking
    source_system = Column(String(255), nullable=False)  # "intake_form", "crm", "analytics"
    source_form = Column(String(255), nullable=True)  # Specific form name if applicable
    source_vendor_id = Column(UUID(as_uuid=True), ForeignKey("system_vendors.id"), nullable=True)
    
    # Storage
    storage_locations = Column(JSON, default=list)  # ["postgres_db", "s3_backup", "salesforce"]
    storage_type = Column(Enum(StorageType), default=StorageType.DATABASE)
    
    # Sharing
    shared_internally = Column(Boolean, default=False)
    shared_externally = Column(Boolean, default=False)
    shared_with_vendor_ids = Column(JSON, default=list)  # UUIDs of vendors
    sharing_purposes = Column(JSON, default=list)  # ["payment_processing", "analytics"]
    
    # Retention
    retention_period_days = Column(Integer, nullable=True)
    retention_basis = Column(String(500), nullable=True)  # "legal_requirement", "business_need"
    retention_status = Column(Enum(RetentionStatus), default=RetentionStatus.ACTIVE)
    deletion_due_date = Column(DateTime(timezone=True), nullable=True)
    
    # MHMDA specific
    collected_from_consumer = Column(Boolean, default=True)
    collection_method = Column(String(100), nullable=True)  # "direct_input", "observed", "inferred"
    purpose_of_collection = Column(JSON, default=list)
    consumer_consent_obtained = Column(Boolean, default=False)
    
    # Internal
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.id"), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="data_elements")
    source_vendor = relationship("SystemVendor", backref="data_elements")
    created_by = relationship("WorkspaceUser")
