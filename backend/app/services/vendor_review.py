"""
Vendor Review and Processor Agreement Tracking
Enhanced vendor workflows with review cadence and agreement status
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class AgreementStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    NOT_STARTED = "not_started"
    IN_NEGOTIATION = "in_negotiation"
    EXECUTED = "executed"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class ReviewCadence(str, Enum):
    ANNUAL = "annual"
    BI_ANNUAL = "bi_annual"
    QUARTERLY = "quarterly"
    ADHOC = "adhoc"


class VendorRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VendorReview(Base):
    """
    Periodic review record for a vendor.
    Tracks review cadence and findings.
    """
    __tablename__ = "vendor_reviews"
    
    review_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    vendor_id = Column(String(32), ForeignKey("system_vendors.vendor_id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    tenant_id = Column(String(64), nullable=False)
    
    # Review scheduling
    review_number = Column(Integer, nullable=False)  # 1 = first review
    scheduled_date = Column(Date, nullable=False)
    completed_date = Column(Date, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    
    # Review content
    risk_level = Column(SQLEnum(VendorRiskLevel), nullable=True)
    review_notes = Column(Text, nullable=True)
    findings = Column(JSON, default=list)  # List of findings from review
    
    # Status
    is_completed = Column(Boolean, default=False)
    requires_follow_up = Column(Boolean, default=False)
    follow_up_task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    vendor = relationship("SystemVendor", back_populates="reviews")


class ProcessorAgreement(Base):
    """
    Data Processing Agreement (DPA) tracking for vendors.
    """
    __tablename__ = "processor_agreements"
    
    agreement_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    vendor_id = Column(String(32), ForeignKey("system_vendors.vendor_id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    tenant_id = Column(String(64), nullable=False)
    
    # Agreement details
    agreement_type = Column(String(50), default="dpa")  # dpa, baa, dsa
    status = Column(SQLEnum(AgreementStatus), default=AgreementStatus.NOT_STARTED, nullable=False)
    
    # Dates
    requested_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=True)
    executed_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)
    
    # Document storage
    draft_document_key = Column(String(512), nullable=True)
    executed_document_key = Column(String(512), nullable=True)
    
    # Terms
    covers_hipaa = Column(Boolean, default=False)
    covers_mhmda = Column(Boolean, default=False)
    allows_subprocessors = Column(Boolean, nullable=True)
    data_retention_terms = Column(Text, nullable=True)
    data_deletion_terms = Column(Text, nullable=True)
    
    # Reminders
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    # Notes
    negotiation_notes = Column(Text, nullable=True)
    legal_review_required = Column(Boolean, default=False)
    legal_review_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vendor = relationship("SystemVendor", back_populates="agreements")


class VendorSubprocessor(Base):
    """
    Subprocessors disclosed by a vendor.
    """
    __tablename__ = "vendor_subprocessors"
    
    subprocessor_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    vendor_id = Column(String(32), ForeignKey("system_vendors.vendor_id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Subprocessor details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    purpose = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    disclosed_at = Column(DateTime, default=datetime.utcnow)
    
    # Data handling
    data_categories = Column(JSON, default=list)


class VendorDataCategory(Base):
    """
    Data categories shared with each vendor.
    Many-to-many relationship with detailed tracking.
    """
    __tablename__ = "vendor_data_categories"
    
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    vendor_id = Column(String(32), ForeignKey("system_vendors.vendor_id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Data category
    category_name = Column(String(100), nullable=False)
    category_description = Column(Text, nullable=True)
    
    # Purpose
    sharing_purpose = Column(Text, nullable=False)
    legal_basis = Column(String(100), nullable=True)  # consent, contract, legitimate_interest, etc.
    
    # Transfers
    is_transferred_internationally = Column(Boolean, default=False)
    transfer_mechanism = Column(String(100), nullable=True)  # SCCs, adequacy decision, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)


class VendorReminderSchedule(Base):
    """
    Reminder schedule for vendor-related tasks.
    """
    __tablename__ = "vendor_reminder_schedules"
    
    vendor_id = Column(String(32), ForeignKey("system_vendors.vendor_id"), primary_key=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Review cadence
    review_cadence = Column(SQLEnum(ReviewCadence), default=ReviewCadence.ANNUAL)
    next_review_date = Column(Date, nullable=True)
    
    # Agreement reminders
    agreement_renewal_reminder_days = Column(Integer, default=90)  # Days before expiration
    
    # Notification settings
    notify_roles = Column(JSON, default=list)  # ['owner', 'staff_editor']
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorReviewService:
    """
    Service for managing vendor reviews and agreement tracking.
    """
    
    def __init__(self, db):
        self.db = db
    
    def schedule_review(self, vendor_id: str, organization_id: str, scheduled_date: date) -> VendorReview:
        """Schedule a new vendor review."""
        # Get next review number
        last_review = self.db.query(VendorReview).filter_by(
            vendor_id=vendor_id
        ).order_by(VendorReview.review_number.desc()).first()
        
        review_number = (last_review.review_number + 1) if last_review else 1
        
        review = VendorReview(
            vendor_id=vendor_id,
            organization_id=organization_id,
            tenant_id=self._get_tenant_id(organization_id),
            review_number=review_number,
            scheduled_date=scheduled_date
        )
        
        self.db.add(review)
        self.db.commit()
        
        return review
    
    def complete_review(
        self,
        review_id: str,
        reviewed_by: str,
        risk_level: VendorRiskLevel,
        notes: str,
        findings: List[dict]
    ) -> VendorReview:
        """Mark a review as completed."""
        review = self.db.query(VendorReview).filter_by(review_id=review_id).first()
        
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        review.is_completed = True
        review.completed_date = datetime.utcnow().date()
        review.reviewed_by = reviewed_by
        review.risk_level = risk_level
        review.review_notes = notes
        review.findings = findings
        
        # Schedule next review based on cadence
        self._schedule_next_review(review.vendor_id, review.organization_id)
        
        self.db.commit()
        return review
    
    def check_agreement_status(self, vendor_id: str) -> dict:
        """Check processor agreement status for a vendor."""
        vendor = self.db.query(SystemVendor).filter_by(vendor_id=vendor_id).first()
        
        if not vendor:
            raise ValueError(f"Vendor {vendor_id} not found")
        
        # Check if agreement is required
        if not vendor.processes_health_data:
            return {
                "agreement_required": False,
                "reason": "Vendor does not process health data"
            }
        
        # Get latest agreement
        latest_agreement = self.db.query(ProcessorAgreement).filter_by(
            vendor_id=vendor_id
        ).order_by(ProcessorAgreement.created_at.desc()).first()
        
        if not latest_agreement:
            return {
                "agreement_required": True,
                "status": "not_started",
                "action_needed": "Request DPA from vendor"
            }
        
        # Check expiration
        if latest_agreement.expiration_date:
            days_until_expiry = (latest_agreement.expiration_date - datetime.utcnow().date()).days
            
            if days_until_expiry < 0:
                return {
                    "agreement_required": True,
                    "status": "expired",
                    "action_needed": "Renew expired agreement",
                    "days_overdue": abs(days_until_expiry)
                }
            elif days_until_expiry < 90:
                return {
                    "agreement_required": True,
                    "status": "expiring_soon",
                    "action_needed": f"Renew in {days_until_expiry} days",
                    "days_remaining": days_until_expiry
                }
        
        return {
            "agreement_required": True,
            "status": latest_agreement.status.value,
            "covers_hipaa": latest_agreement.covers_hipaa,
            "covers_mhmda": latest_agreement.covers_mhmda
        }
    
    def _schedule_next_review(self, vendor_id: str, organization_id: str):
        """Schedule next review based on cadence."""
        schedule = self.db.query(VendorReminderSchedule).filter_by(
            vendor_id=vendor_id
        ).first()
        
        if not schedule:
            return
        
        # Calculate next review date
        today = datetime.utcnow().date()
        
        if schedule.review_cadence == ReviewCadence.ANNUAL:
            next_date = today + timedelta(days=365)
        elif schedule.review_cadence == ReviewCadence.BI_ANNUAL:
            next_date = today + timedelta(days=180)
        elif schedule.review_cadence == ReviewCadence.QUARTERLY:
            next_date = today + timedelta(days=90)
        else:
            return  # No auto-schedule for adhoc
        
        schedule.next_review_date = next_date
        self.db.commit()
    
    def get_overdue_reviews(self, organization_id: str) -> List[VendorReview]:
        """Get all overdue vendor reviews for an organization."""
        today = datetime.utcnow().date()
        
        return self.db.query(VendorReview).filter(
            VendorReview.organization_id == organization_id,
            VendorReview.is_completed == False,
            VendorReview.scheduled_date < today
        ).all()
    
    def get_vendors_needing_agreements(self, organization_id: str) -> List[SystemVendor]:
        """Get vendors that need processor agreements but don't have them."""
        # Get all vendors that process health data
        health_vendors = self.db.query(SystemVendor).filter(
            SystemVendor.organization_id == organization_id,
            SystemVendor.processes_health_data == True
        ).all()
        
        needing_agreements = []
        
        for vendor in health_vendors:
            # Check for active agreement
            active_agreement = self.db.query(ProcessorAgreement).filter(
                ProcessorAgreement.vendor_id == vendor.vendor_id,
                ProcessorAgreement.status.in_([AgreementStatus.EXECUTED, AgreementStatus.IN_NEGOTIATION])
            ).first()
            
            if not active_agreement:
                needing_agreements.append(vendor)
        
        return needing_agreements
    
    def _get_tenant_id(self, organization_id: str) -> str:
        """Get tenant ID from organization."""
        org = self.db.query(Organization).filter_by(id=organization_id).first()
        return org.tenant_id if org else None
