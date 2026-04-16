"""
Remediation Verification Workflow
Task completion verification with evidence requirements
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class VerificationStatus(str, Enum):
    PENDING = "pending"  # Task marked complete, awaiting verification
    UNDER_REVIEW = "under_review"  # Verification in progress
    VERIFIED = "verified"  # Confirmed complete
    REJECTED = "rejected"  # Evidence insufficient, returned to assignee
    OVERRIDE_APPROVED = "override_approved"  # Closed without full completion (with justification)


class VerificationMethod(str, Enum):
    EVIDENCE_REVIEW = "evidence_review"  # Review attached screenshot/document
    SAMPLER_CHECK = "sampler_check"  # Quick sampling verification
    FULL_AUDIT = "full_audit"  # Comprehensive verification
    DELEGATED = "delegated"  # Assigned to another reviewer
    AUTOMATED = "automated"  # Passed automated checks


class RemediationVerification(Base):
    """
    Verification record for completed remediation tasks.
    Ensures tasks are actually complete, not just marked complete.
    """
    __tablename__ = "remediation_verifications"
    
    verification_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=False, unique=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False)
    
    # Status
    status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False)
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Verification execution
    verified_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    verification_method = Column(SQLEnum(VerificationMethod), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Evidence reviewed
    evidence_reviewed = Column(JSON, default=list)  # List of evidence IDs examined
    evidence_sufficient = Column(Boolean, nullable=True)
    
    # Verification notes
    verification_notes = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)  # What was found during verification
    
    # Rejection (if applicable)
    rejection_reason = Column(Text, nullable=True)
    returned_at = Column(DateTime, nullable=True)
    
    # Override (if applicable)
    override_justification = Column(Text, nullable=True)
    override_risk_accepted = Column(Boolean, default=False)
    override_approved_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    override_approved_at = Column(DateTime, nullable=True)
    
    # Timeline
    created_at = Column(DateTime, default=datetime.utcnow)
    pending_since = Column(DateTime, default=datetime.utcnow)  # Track SLA
    review_started_at = Column(DateTime, nullable=True)
    
    # SLA tracking
    sla_hours = Column(Integer, default=72)  # 3 business days default
    sla_breached = Column(Boolean, default=False)
    
    # Relationships
    task = relationship("RemediationTask", back_populates="verification")
    reviewer = relationship("WorkspaceUser", foreign_keys=[verified_by])


class VerificationChecklist(Base):
    """Checklist items for verifying specific task types."""
    __tablename__ = "verification_checklists"
    
    checklist_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    verification_id = Column(String(32), ForeignKey("remediation_verifications.verification_id"), nullable=False)
    
    # Checklist item
    item_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    is_required = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    evidence_reference = Column(String(64), nullable=True)  # Evidence ID
    
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationEvidenceRequirement(Base):
    """
    Defines what evidence is required for different task types.
    Used to validate incoming verification attempts.
    """
    __tablename__ = "verification_evidence_requirements"
    
    task_template_key = Column(String(100), primary_key=True)
    
    # Requirements
    required_evidence_types = Column(JSON, default=list)  # ['screenshot', 'policy_version', 'contract']
    min_evidence_count = Column(Integer, default=1)
    
    # Optional evidence
    optional_evidence_types = Column(JSON, default=list)
    
    # Specific checks
    requires_url_verification = Column(Boolean, default=False)
    requires_date_proof = Column(Boolean, default=False)
    requires_version_number = Column(Boolean, default=False)
    requires_signature = Column(Boolean, default=False)
    
    # Validation rules
    validation_rules = Column(JSON, default=dict)  # e.g., {'url_must_be_https': True}
    
    is_active = Column(Boolean, default=True)


class EvidenceAttachment(Base):
    """Evidence attached to remediation tasks."""
    __tablename__ = "evidence_attachments"
    
    attachment_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Content
    evidence_type = Column(String(50), nullable=False)  # 'screenshot', 'policy_version', 'contract', 'log', 'other'
    evidence_format = Column(String(20), nullable=False)  # 'png', 'pdf', 'txt', 'json'
    
    # Storage
    storage_key = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    
    # Context
    description = Column(Text, nullable=True)
    captured_url = Column(String(500), nullable=True)  # For screenshots
    captured_at = Column(DateTime, nullable=True)
    
    # Verification status
    verified_in_task = Column(Boolean, default=False)
    verification_notes = Column(Text, nullable=True)
    
    # Audit
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Link to Evidence Vault
    evidence_record_id = Column(String(32), ForeignKey("evidence_records.evidence_id"), nullable=True)


class VerificationService:
    """
    Service for managing remediation verification workflows.
    """
    
    REQUIRED_EVIDENCE_RULES = {
        "missing_privacy_link": {
            "required_types": ["screenshot"],
            "requires_url_verification": True,
            "validation_rules": {"url_must_be_https": True}
        },
        "unclear_request_channel": {
            "required_types": ["policy_version", "log"],
            "requires_url_verification": False
        },
        "missing_processor_agreement": {
            "required_types": ["contract"],
            "requires_signature": True
        },
        "ad_pixel_review_needed": {
            "required_types": ["screenshot", "log"],
            "min_count": 2
        },
        "location_marketing_review": {
            "required_types": ["policy_version", "log"]
        },
        "incomplete_deletion_workflow": {
            "required_types": ["policy_version", "log"]
        },
        "missing_sharing_disclosure": {
            "required_types": ["policy_version"],
            "requires_version_number": True
        },
        "consent_language_mismatch": {
            "required_types": ["policy_version", "screenshot"],
            "requires_date_proof": True
        }
    }
    
    def __init__(self, db, evidence_vault):
        self.db = db
        self.evidence_vault = evidence_vault
    
    def submit_for_verification(self, task_id: str, submitted_by: str) -> RemediationVerification:
        """Submit completed task for verification."""
        from .remediation import RemediationTask, TaskStatus
        
        task = self.db.query(RemediationTask).filter_by(task_id=task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status != TaskStatus.COMPLETED_UNVERIFIED:
            raise ValueError(f"Task must be in completed_unverified status")
        
        # Check evidence requirements
        evidence = self.db.query(EvidenceAttachment).filter_by(task_id=task_id).all()
        required_evidence = self._get_required_evidence(task.template_key)
        
        if len(evidence) < required_evidence.get("min_count", 1):
            raise ValueError(f"Insufficient evidence: {len(evidence)} attached, {required_evidence.get('min_count', 1)} required")
        
        # Create verification record
        verification = RemediationVerification(
            task_id=task_id,
            organization_id=task.organization_id,
            tenant_id=task.tenant_id,
            status=VerificationStatus.PENDING,
            sla_hours=72  # 3 business days
        )
        
        self.db.add(verification)
        self.db.commit()
        
        return verification
    
    def verify_task(
        self,
        verification_id: str,
        verified_by: str,
        method: VerificationMethod,
        notes: str,
        findings: Optional[str] = None
    ) -> RemediationVerification:
        """Complete verification of a task."""
        verification = self.db.query(RemediationVerification).filter_by(
            verification_id=verification_id
        ).first()
        
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        verification.status = VerificationStatus.VERIFIED
        verification.verified_by = verified_by
        verification.verification_method = method
        verification.verified_at = datetime.utcnow()
        verification.verification_notes = notes
        verification.findings = findings
        verification.evidence_sufficient = True
        
        # Update task status
        from .remediation import TaskStatus
        verification.task.status = TaskStatus.VERIFIED
        verification.task.verified_at = datetime.utcnow()
        verification.task.verified_by = verified_by
        
        self.db.commit()
        return verification
    
    def reject_verification(
        self,
        verification_id: str,
        rejected_by: str,
        reason: str
    ) -> RemediationVerification:
        """Reject verification - returns task to assigned for more work."""
        verification = self.db.query(RemediationVerification).filter_by(
            verification_id=verification_id
        ).first()
        
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        verification.status = VerificationStatus.REJECTED
        verification.rejection_reason = reason
        verification.returned_at = datetime.utcnow()
        
        # Return task to assigned state
        from .remediation import TaskStatus
        verification.task.status = TaskStatus.ASSIGNED
        verification.task.completed_at = None
        
        self.db.commit()
        return verification
    
    def approve_override(
        self,
        verification_id: str,
        approved_by: str,
        justification: str,
        risk_accepted: bool
    ) -> RemediationVerification:
        """Approve closing task without full completion (with override)."""
        verification = self.db.query(RemediationVerification).filter_by(
            verification_id=verification_id
        ).first()
        
        if not verification:
            raise ValueError(f"Verification {verification_id} not found")
        
        verification.status = VerificationStatus.OVERRIDE_APPROVED
        verification.override_justification = justification
        verification.override_risk_accepted = risk_accepted
        verification.override_approved_by = approved_by
        verification.override_approved_at = datetime.utcnow()
        verification.verified_at = datetime.utcnow()
        verification.evidence_sufficient = False
        
        # Update task with override
        from .remediation import TaskStatus
        verification.task.status = TaskStatus.CLOSED_OVERRIDE
        verification.task.override_justification = justification
        verification.task.override_approved_by = approved_by
        verification.task.override_approved_at = datetime.utcnow()
        
        self.db.commit()
        return verification
    
    def check_sla_breach(self) -> List[RemediationVerification]:
        """Find verifications approaching or past SLA."""
        cutoff = datetime.utcnow() - timedelta(hours=72)
        
        pending = self.db.query(RemediationVerification).filter(
            RemediationVerification.status == VerificationStatus.PENDING,
            RemediationVerification.pending_since < cutoff
        ).all()
        
        for v in pending:
            v.sla_breached = True
        
        self.db.commit()
        return pending
    
    def _get_required_evidence(self, template_key: Optional[str]) -> dict:
        """Get evidence requirements for a task template."""
        if template_key and template_key in self.REQUIRED_EVIDENCE_RULES:
            return self.REQUIRED_EVIDENCE_RULES[template_key]
        return {"min_count": 1, "required_types": []}
