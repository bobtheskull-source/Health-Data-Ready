"""
Annual Review Scheduler and Workflow
Milestone 6: Recurring compliance workflows
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class ReviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ReviewTrigger(str, Enum):
    SCHEDULED = "scheduled"  # Annual recurrence
    MANUAL = "manual"  # User-initiated
    MATERIAL_CHANGE = "material_change"  # Triggered by significant change
    VENDOR_CHANGE = "vendor_change"
    POLICY_CHANGE = "policy_change"


class AnnualReview(Base):
    """
    Annual compliance review run for an organization.
    Captures state at review start and tracks progress.
    """
    __tablename__ = "annual_reviews"
    
    review_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False)
    
    # Review scheduling
    review_number = Column(Integer, nullable=False)  # 1 = first review, 2 = second, etc.
    scheduled_date = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=False)  # 90 days from scheduled
    
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.SCHEDULED, nullable=False)
    trigger = Column(SQLEnum(ReviewTrigger), default=ReviewTrigger.SCHEDULED, nullable=False)
    
    # Snapshot references
    baseline_snapshot_id = Column(String(32), ForeignKey("compliance_snapshots.snapshot_id"), nullable=True)
    current_snapshot_id = Column(String(32), ForeignKey("compliance_snapshots.snapshot_id"), nullable=True)
    
    # Review metadata
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    # Results
    changes_detected = Column(JSON, default=dict)  # Summary of what changed
    follow_up_tasks_created = Column(Integer, default=0)
    policy_regenerated = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="annual_reviews")
    baseline_snapshot = relationship("ComplianceSnapshot", foreign_keys=[baseline_snapshot_id])
    current_snapshot = relationship("ComplianceSnapshot", foreign_keys=[current_snapshot_id])
    assignee = relationship("WorkspaceUser")
    change_events = relationship("ChangeEvent", back_populates="annual_review")
    review_checklists = relationship("ReviewChecklist", back_populates="annual_review")


class ComplianceSnapshot(Base):
    """
    Immutable point-in-time capture of compliance state.
    Used for before/after comparison.
    """
    __tablename__ = "compliance_snapshots"
    
    snapshot_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False)
    
    # Snapshot content
    snapshot_type = Column(String(50), nullable=False)  # 'annual_review', 'material_change', 'manual'
    questionnaire_responses = Column(JSON, default=dict)
    data_elements_summary = Column(JSON, default=dict)  # Count by category
    vendors_summary = Column(JSON, default=dict)  # List of vendor IDs and names
    policy_inputs_hash = Column(String(64), nullable=True)  # Hash of policy inputs
    
    # Metadata
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    captured_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    
    # Change detection flag
    has_material_changes = Column(Boolean, default=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="compliance_snapshots")


class ChangeEvent(Base):
    """
    Individual change detected during review comparison.
    """
    __tablename__ = "change_events"
    
    change_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False)
    annual_review_id = Column(String(32), ForeignKey("annual_reviews.review_id"), nullable=True, index=True)
    
    # What changed
    entity_type = Column(String(50), nullable=False)  # 'questionnaire', 'data_element', 'vendor', 'policy_input'
    entity_id = Column(String(64), nullable=True)  # Optional reference to specific entity
    field_name = Column(String(100), nullable=True)  # Specific field that changed
    
    # Change details
    change_type = Column(String(20), nullable=False)  # 'added', 'removed', 'modified'
    previous_value = Column(JSON, nullable=True)
    current_value = Column(JSON, nullable=True)
    
    # Classification
    is_material = Column(Boolean, default=False)  # Does this require policy update?
    requires_follow_up = Column(Boolean, default=False)
    follow_up_task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=True)
    
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    annual_review = relationship("AnnualReview", back_populates="change_events")
    remediation_task = relationship("RemediationTask")


class ReviewChecklist(Base):
    """
    Checklist items for completing an annual review.
    """
    __tablename__ = "review_checklists"
    
    checklist_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    annual_review_id = Column(String(32), ForeignKey("annual_reviews.review_id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Checklist item
    category = Column(String(50), nullable=False)  # 'questionnaire', 'vendors', 'data_elements', 'policy'
    item_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    is_required = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    
    # Evidence
    evidence_attached = Column(Boolean, default=False)
    evidence_snapshot_id = Column(String(32), ForeignKey("compliance_snapshots.snapshot_id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    annual_review = relationship("AnnualReview", back_populates="review_checklists")


class AnnualReviewSchedule(Base):
    """
    Configuration for automatic review scheduling per organization.
    """
    __tablename__ = "annual_review_schedules"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True)
    tenant_id = Column(String(64), nullable=False)
    
    # Schedule configuration
    is_enabled = Column(Boolean, default=True)
    recurrence_months = Column(Integer, default=12)  # 12 = annual
    reminder_days_before = Column(Integer, default=30)
    
    # Last/next scheduled
    last_review_date = Column(DateTime, nullable=True)
    next_review_date = Column(DateTime, nullable=True, index=True)
    
    # Notifications
    notify_roles = Column(JSON, default=list)  # ['owner', 'staff_editor']
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    configured_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
