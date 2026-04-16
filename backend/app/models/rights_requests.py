from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Enum, JSON, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base

class RequestType(str, enum.Enum):
    ACCESS = "access"
    DELETION = "deletion"
    WITHDRAW_CONSENT = "withdraw_consent"
    APPEAL = "appeal"

class RequestStatus(str, enum.Enum):
    RECEIVED = "received"
    IDENTITY_VERIFICATION_PENDING = "identity_verification_pending"
    UNDER_REVIEW = "under_review"
    EXTENSION_REQUESTED = "extension_requested"
    FULFILLED = "fulfilled"
    DENIED = "denied"
    APPEAL_UNDER_REVIEW = "appeal_under_review"
    CLOSED = "closed"

class RightsRequest(Base):
    """Consumer rights request under MHMDA."""
    
    __tablename__ = "rights_requests"
    __table_args__ = (
        Index("ix_rights_org_status", "organization_id", "status"),
        Index("ix_rights_due_date", "due_date"),
        Index("ix_rights_consumer_email", "consumer_email"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    # Request identification
    request_number = Column(String(50), unique=True, nullable=False, index=True)
    request_type = Column(Enum(RequestType), nullable=False)
    
    # Consumer info
    consumer_email = Column(String(255), nullable=False, index=True)
    consumer_name = Column(String(255), nullable=True)
    consumer_verified = Column(Boolean, default=False)
    verification_method = Column(String(100), nullable=True)
    
    # Request details
    description = Column(Text, nullable=True)
    request_scope = Column(JSON, default=list)  # ["all_data", "specific_categories"]
    specific_categories = Column(JSON, default=list)
    
    # Timeline
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    extension_used = Column(Boolean, default=False)
    extension_reason = Column(Text, nullable=True)
    extension_requested_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status workflow
    status = Column(Enum(RequestStatus), default=RequestStatus.RECEIVED, nullable=False, index=True)
    status_history = Column(JSON, default=list)  # [{"status": "x", "timestamp": "...", "note": "..."}]
    
    # Downstream notifications (MHMDA requires notifying processors)
    processors_notified = Column(Boolean, default=False)
    processors_notification_date = Column(DateTime(timezone=True), nullable=True)
    processors_notification_list = Column(JSON, default=list)  # Vendor IDs notified
    
    # Response
    response_summary = Column(Text, nullable=True)
    response_data_format = Column(String(50), nullable=True)  # "pdf", "csv", "api"
    response_data_location = Column(String(500), nullable=True)  # Secure download URL
    denial_reason = Column(Text, nullable=True)
    appeal_deadline = Column(DateTime(timezone=True), nullable=True)
    
    # Evidence
    evidence_item_ids = Column(JSON, default=list)
    completion_notes = Column(Text, nullable=True)
    
    # Internal tracking
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.id"), nullable=True)
    priority = Column(String(20), default="normal")  # normal, high, urgent
    internal_notes = Column(Text, nullable=True)  # Not shared with consumer
    
    # Metadata
    source = Column(String(50), default="web_form")  # web_form, email, phone, mail
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = relationship("Organization", backref="rights_requests")
    assigned_to = relationship("WorkspaceUser")
