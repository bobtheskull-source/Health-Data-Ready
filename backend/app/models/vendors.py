from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, JSON, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base

class VendorRole(str, enum.Enum):
    CONTROLLER_LIKE = "controller_like"
    PROCESSOR = "processor"
    THIRD_PARTY = "third_party"
    UNKNOWN = "unknown"

class ContractStatus(str, enum.Enum):
    NONE = "none"
    VERBAL = "verbal"
    WRITTEN = "written"
    SIGNED_MHMDA = "signed_mhmda"

class SystemVendor(Base):
    """Vendor/processor register for data mapping."""
    
    __tablename__ = "system_vendors"
    __table_args__ = (
        Index("ix_vendor_org_name", "organization_id", "name"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    # Core info
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    website = Column(String(500), nullable=True)
    
    # MHMDA classification
    role = Column(Enum(VendorRole), default=VendorRole.UNKNOWN, nullable=False)
    contract_status = Column(Enum(ContractStatus), default=ContractStatus.NONE, nullable=False)
    
    # Location (for deletion jurisdiction)
    location_country = Column(String(100), nullable=True)
    location_state = Column(String(100), nullable=True)
    
    # Red flags per MHMDA
    adtech_flag = Column(Boolean, default=False)  # Ad pixel, tracking SDK
    location_flag = Column(Boolean, default=False)  # Geofencing/location data
    deletion_notice_required = Column(Boolean, default=False)
    
    # Data handling
    data_types_handled = Column(JSON, default=list)  # ["payment", "scheduling", "analytics"]
    shares_health_data = Column(Boolean, default=False)
    has_subprocessors = Column(Boolean, default=False)
    
    # Contact for rights requests
    privacy_contact_email = Column(String(255), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", back_populates="vendors")
