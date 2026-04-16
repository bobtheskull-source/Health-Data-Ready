"""
Remediation Queue and Task Management
Milestone 7: Convert findings into actionable tasks
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class TaskSeverity(str, Enum):
    CRITICAL = "critical"  # Blocking compliance, immediate action required
    HIGH = "high"  # Significant risk, address within 30 days
    MEDIUM = "medium"  # Moderate risk, address within 90 days
    LOW = "low"  # Minor issue, address when convenient


class TaskStatus(str, Enum):
    PENDING = "pending"  # Created, not yet assigned
    ASSIGNED = "assigned"  # Has owner, not started
    IN_PROGRESS = "in_progress"
    COMPLETED_UNVERIFIED = "completed_unverified"  # Marked done, needs verification
    VERIFIED = "verified"  # Completed and verified
    CLOSED_OVERRIDE = "closed_override"  # Closed without full completion (requires justification)
    CANCELLED = "cancelled"


class TaskBlockingLevel(str, Enum):
    BLOCKING = "blocking"  # Prevents policy generation/export
    NON_BLOCKING = "non_blocking"  # Warning only


class RemediationTask(Base):
    """
    Individual remediation task from gap analysis.
    Tracks from creation through verification.
    """
    __tablename__ = "remediation_tasks"
    
    task_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False)
    
    # Task identification
    task_number = Column(Integer, nullable=False)  # Sequential within org
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Task templates provide standard gaps
    template_key = Column(String(100), nullable=True)  # e.g., 'missing_privacy_link'
    
    # Classification
    severity = Column(SQLEnum(TaskSeverity), nullable=False)
    blocking_level = Column(SQLEnum(TaskBlockingLevel), default=TaskBlockingLevel.NON_BLOCKING, nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    
    # Ownership
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Due dates
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Reasoning for due date
    due_date_reason = Column(Text, nullable=True)
    
    # Closure evidence
    requires_evidence = Column(Boolean, default=True)
    evidence_attached = Column(Boolean, default=False)
    evidence_snapshot_id = Column(String(32), ForeignKey("compliance_snapshots.snapshot_id"), nullable=True)
    
    # Verification
    verified_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Override (if closing without completion)
    override_justification = Column(Text, nullable=True)
    override_approved_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    override_approved_at = Column(DateTime, nullable=True)
    
    # Source tracking
    source_type = Column(String(50), nullable=True)  # 'annual_review', 'gap_analysis', 'manual'
    source_id = Column(String(32), nullable=True)  # e.g., annual_review_id
    change_event_id = Column(String(32), ForeignKey("change_events.change_id"), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="remediation_tasks")
    assignee = relationship("WorkspaceUser", foreign_keys=[assigned_to])
    status_history = relationship("TaskStatusHistory", back_populates="task", order_by="TaskStatusHistory.changed_at")
    notes = relationship("TaskNote", back_populates="task")


class TaskStatusHistory(Base):
    """Immutable audit trail of task status changes."""
    __tablename__ = "task_status_history"
    
    history_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=False, index=True)
    
    from_status = Column(SQLEnum(TaskStatus), nullable=True)
    to_status = Column(SQLEnum(TaskStatus), nullable=False)
    
    changed_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    change_reason = Column(Text, nullable=True)
    
    # Relationships
    task = relationship("RemediationTask", back_populates="status_history")


class TaskNote(Base):
    """Notes on remediation tasks - internal vs client-visible."""
    __tablename__ = "task_notes"
    
    note_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    visibility = Column(String(20), default="internal", nullable=False)  # 'internal', 'client_visible'
    
    # Author
    created_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    task = relationship("RemediationTask", back_populates="notes")


class TaskTemplate(Base):
    """Reusable task templates for common remediation scenarios."""
    __tablename__ = "task_templates"
    
    template_key = Column(String(100), primary_key=True)
    
    # Content
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(TaskSeverity), nullable=False)
    blocking_level = Column(SQLEnum(TaskBlockingLevel), nullable=False)
    
    # Default settings
    default_due_days = Column(Integer, default=30)
    requires_evidence = Column(Boolean, default=True)
    
    # Categorization
    category = Column(String(50), nullable=False)  # 'policy', 'vendor', 'web', 'process'
    tags = Column(JSON, default=list)
    
    # Helpful guidance
    remediation_steps = Column(JSON, default=list)  # Ordered list of steps
    evidence_requirements = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RemediationQueue(Base):
    """Queue state tracking for organization remediation backlog."""
    __tablename__ = "remediation_queues"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True)
    tenant_id = Column(String(64), nullable=False)
    
    # Counts
    total_open = Column(Integer, default=0)
    critical_open = Column(Integer, default=0)
    high_open = Column(Integer, default=0)
    medium_open = Column(Integer, default=0)
    low_open = Column(Integer, default=0)
    
    blocking_tasks = Column(Integer, default=0)
    overdue_tasks = Column(Integer, default=0)
    unverified_completions = Column(Integer, default=0)
    
    # Scoring
    health_score = Column(Integer, default=100)  # 0-100
    last_calculated_at = Column(DateTime, default=datetime.utcnow)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Common task templates
DEFAULT_TASK_TEMPLATES = [
    {
        "template_key": "missing_privacy_link",
        "title": "Add privacy policy link to homepage",
        "description": "MHMDA requires a clear privacy policy link on the homepage footer. Verify link is visible and functional.",
        "severity": TaskSeverity.HIGH,
        "blocking_level": TaskBlockingLevel.BLOCKING,
        "category": "web",
        "default_due_days": 14,
        "remediation_steps": [
            "Add privacy policy link to website footer",
            "Verify link is clickable from homepage",
            "Test link on mobile view",
            "Take screenshot as evidence"
        ]
    },
    {
        "template_key": "unclear_request_channel",
        "title": "Clarify consumer rights request intake channel",
        "description": "Consumer must have a clear channel to submit access/deletion requests under MHMDA (RCW 19.373.120-130).",
        "severity": TaskSeverity.CRITICAL,
        "blocking_level": TaskBlockingLevel.BLOCKING,
        "category": "process",
        "default_due_days": 7,
        "remediation_steps": [
            "Document current request intake method",
            "Create dedicated email (e.g., privacy@company.com) or web form",
            "Add intake instructions to privacy policy",
            "Train staff on recognizing and routing requests"
        ]
    },
    {
        "template_key": "missing_processor_agreement",
        "title": "Obtain or document processor agreement with vendor",
        "description": "Vendors processing health data should have written agreements covering data handling obligations.",
        "severity": TaskSeverity.MEDIUM,
        "blocking_level": TaskBlockingLevel.NON_BLOCKING,
        "category": "vendor",
        "default_due_days": 45,
        "remediation_steps": [
            "Request Data Processing Agreement from vendor",
            "Review agreement for MHMDA compliance terms",
            "Execute agreement",
            "Upload executed agreement to Evidence Vault"
        ]
    },
    {
        "template_key": "ad_pixel_review_needed",
        "title": "Review advertising pixels for health context",
        "description": "Ad tech on health-related pages may trigger HIPAA or MHMDA obligations. Review pixel deployment.",
        "severity": TaskSeverity.HIGH,
        "blocking_level": TaskBlockingLevel.BLOCKING,
        "category": "web",
        "default_due_days": 21,
        "remediation_steps": [
            "Inventory all advertising/analytics pixels",
            "Identify which pages have health context",
            "Remove or restrict pixels on sensitive pages",
            "Document remaining pixel usage in policy"
        ]
    },
    {
        "template_key": "location_marketing_review",
        "title": "Review location-based marketing for health context",
        "description": "Location tracking that reveals health-related visits (clinics, pharmacies) is consumer health data under MHMDA.",
        "severity": TaskSeverity.HIGH,
        "blocking_level": TaskBlockingLevel.NON_BLOCKING,
        "category": "process",
        "default_due_days": 30,
        "remediation_steps": [
            "Audit location data collection practices",
            "Identify health-related location patterns",
            "Review consent language for location use",
            "Document business justification for any health-related tracking"
        ]
    },
    {
        "template_key": "unclear_vendor_role",
        "title": "Clarify vendor data handling role",
        "description": "Unable to determine if vendor processes health data. This affects policy disclosure obligations.",
        "severity": TaskSeverity.MEDIUM,
        "blocking_level": TaskBlockingLevel.NON_BLOCKING,
        "category": "vendor",
        "default_due_days": 30,
        "remediation_steps": [
            "Contact vendor for clarification on data types processed",
            "Obtain vendor service description",
            "Classify vendor role in register",
            "Update policy with accurate vendor disclosures"
        ]
    },
    {
        "template_key": "incomplete_deletion_workflow",
        "title": "Complete data deletion workflow",
        "description": "MHMDA requires deletion request handling within 45 days. Ensure workflow is defined and documented.",
        "severity": TaskSeverity.CRITICAL,
        "blocking_level": TaskBlockingLevel.BLOCKING,
        "category": "process",
        "default_due_days": 14,
        "remediation_steps": [
            "Document data deletion process",
            "Identify systems holding consumer data",
            "Create deletion request tracking log",
            "Define notification procedure when deletion is complete"
        ]
    },
    {
        "template_key": "missing_sharing_disclosure",
        "title": "Add missing sharing/purpose disclosure to policy",
        "description": "Policy must clearly identify third parties who receive consumer health data and purposes of sharing.",
        "severity": TaskSeverity.HIGH,
        "blocking_level": TaskBlockingLevel.BLOCKING,
        "category": "policy",
        "default_due_days": 14,
        "remediation_steps": [
            "Update vendor register",
            "Generate updated policy",
            "Legal review of sharing disclosures",
            "Publish updated policy and record version"
        ]
    },
    {
        "template_key": "consent_language_mismatch",
        "title": "Align consent language with actual data practices",
        "description": "Consent language does not match actual data collection/sharing documented in inventory.",
        "severity": TaskSeverity.HIGH,
        "blocking_level": TaskBlockingLevel.BLOCKING,
        "category": "policy",
        "default_due_days": 21,
        "remediation_steps": [
            "Compare consent language with data inventory",
            "Update consent where practices differ",
            "Document consent version and effective date",
            "Archive previous consent language"
        ]
    },
    {
        "template_key": "undocumented_staff_access",
        "title": "Document staff data access controls",
        "description": "Access to consumer health data by staff must be documented with role-based limitations.",
        "severity": TaskSeverity.MEDIUM,
        "blocking_level": TaskBlockingLevel.NON_BLOCKING,
        "category": "process",
        "default_due_days": 60,
        "remediation_steps": [
            "Inventory staff roles",
            "Document data access per role",
            "Create access granting/revocation procedure",
            "Schedule access review every 6 months"
        ]
    }
]
