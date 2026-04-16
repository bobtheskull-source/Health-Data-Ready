"""
Evidence Vault Models
"""

from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class EvidenceType(str, Enum):
    REQUEST_RECEIPT = "request_receipt"
    IDENTITY_VERIFICATION = "identity_verification"
    DATA_INVENTORY_SNAPSHOT = "data_inventory_snapshot"
    PROCESSING_LOG = "processing_log"
    CONSUMER_COMMUNICATION = "consumer_communication"
    THIRD_PARTY_DISCLOSURE = "third_party_disclosure"
    DELETION_CERTIFICATE = "deletion_certificate"
    EXTENSION_NOTICE = "extension_notice"
    LEGAL_REVIEW = "legal_review"
    APPEAL_RECORD = "appeal_record"


class EvidenceFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
    EMAIL_RFC2822 = "email_rfc2822"
    IMAGE_JPEG = "image_jpeg"
    IMAGE_PNG = "image_png"
    HASH_SHA256 = "hash_sha256"
    DIGITAL_SIGNATURE = "digital_signature"


class EvidenceRecord(Base):
    """Immutable audit evidence with integrity chain."""
    __tablename__ = "evidence_records"
    
    evidence_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    rights_request_id = Column(String(32), ForeignKey("rights_requests.request_id"), nullable=True, index=True)
    
    evidence_type = Column(SQLEnum(EvidenceType), nullable=False)
    evidence_format = Column(SQLEnum(EvidenceFormat), nullable=False)
    
    content_hash = Column(String(64), nullable=False, index=True)
    content_size_bytes = Column(Integer, nullable=False)
    storage_key = Column(String(512), nullable=False)  # S3 or file path
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    retention_until = Column(DateTime, nullable=True)
    
    # Chain integrity
    previous_hash = Column(String(64), nullable=True)
    chain_hash = Column(String(64), nullable=False, index=True)
    
    # Searchable metadata
    tags = Column(JSON, default=dict)
    description = Column(Text, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="evidence_records")
    rights_request = relationship("RightsRequest", back_populates="evidence_records")
    uploader = relationship("WorkspaceUser")


class EvidenceChainHead(Base):
    """Tracks latest chain hash per organization for tamper detection."""
    __tablename__ = "evidence_chain_heads"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True)
    last_chain_hash = Column(String(64), nullable=False)
    last_evidence_id = Column(String(32), ForeignKey("evidence_records.evidence_id"), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvidenceVerificationLog(Base):
    """Log of integrity verification checks."""
    __tablename__ = "evidence_verification_logs"
    
    verification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(String(32), ForeignKey("evidence_records.evidence_id"), nullable=False, index=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verification_result = Column(String(20), nullable=False)  # 'passed', 'failed', 'unavailable'
    stored_hash = Column(String(64), nullable=False)
    computed_hash = Column(String(64), nullable=False)
    chain_intact = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
