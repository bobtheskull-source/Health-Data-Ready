"""
Partner Workspace Models
Milestone 8: Multi-client partner/consultant support
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class PartnerTier(str, Enum):
    BASIC = "basic"  # Single consultant
    PROFESSIONAL = "professional"  # Small firm, up to 10 clients
    ENTERPRISE = "enterprise"  # Large MSP/consulting firm


class PartnerRole(str, Enum):
    PARTNER_ADMIN = "partner_admin"  # Full admin access to partner org
    PARTNER_MANAGER = "partner_manager"  # Can manage clients, assign staff
    PARTNER_ANALYST = "partner_analyst"  # Can view and work on assigned clients
    PARTNER_READONLY = "partner_readonly"  # View only, no modifications


class ClientAccessLevel(str, Enum):
    FULL = "full"  # Complete workspace access
    ANALYSIS = "analysis"  # Can modify data, cannot export/admin
    READONLY = "readonly"  # View only
    AUDIT = "audit"  # Audit logs and exports only


class PartnerOrganization(Base):
    """
    Partner/consultant firm that manages multiple client organizations.
    """
    __tablename__ = "partner_organizations"
    
    partner_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Contact
    primary_email = Column(String(255), nullable=False)
    billing_email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Tier and limits
    tier = Column(SQLEnum(PartnerTier), default=PartnerTier.BASIC, nullable=False)
    max_clients = Column(Integer, default=5)
    current_client_count = Column(Integer, default=0)
    
    # Branding
    brand_name = Column(String(255), nullable=True)  # For co-branded exports
    logo_storage_key = Column(String(512), nullable=True)
    
    # Settings
    settings = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email/domain verified
    verified_at = Column(DateTime, nullable=True)
    
    # Billing
    subscription_starts_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("PartnerUser", back_populates="partner_org")
    client_assignments = relationship("PartnerClientAssignment", back_populates="partner_org")


class PartnerUser(Base):
    """
    User account within a partner organization.
    Separate from WorkspaceUser - partner users may access multiple clients.
    """
    __tablename__ = "partner_users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.partner_id"), nullable=False, index=True)
    
    # Identity
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    title = Column(String(100), nullable=True)
    
    # Auth
    hashed_password = Column(String(255), nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Role within partner org
    partner_role = Column(SQLEnum(PartnerRole), default=PartnerRole.PARTNER_ANALYST, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Settings
    default_client_view = Column(String(50), default="list")  # 'list', 'dashboard'
    notification_preferences = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    partner_org = relationship("PartnerOrganization", back_populates="users")
    client_access = relationship("PartnerClientAccess", back_populates="partner_user")
    activity_log = relationship("PartnerActivityLog", back_populates="partner_user")


class PartnerClientAssignment(Base):
    """
    Links a client organization to a partner for management.
    """
    __tablename__ = "partner_client_assignments"
    
    assignment_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.partner_id"), nullable=False, index=True)
    client_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True)
    
    # Assignment details
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=True)
    
    # Service scope
    service_type = Column(String(100), nullable=True)  # 'compliance_review', 'ongoing_support', 'adhoc'
    
    # Status
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivation_reason = Column(Text, nullable=True)
    
    # Settings override
    custom_settings = Column(JSON, default=dict)
    
    # Relationships
    partner_org = relationship("PartnerOrganization", back_populates="client_assignments")
    client_org = relationship("Organization")
    user_access = relationship("PartnerClientAccess", back_populates="assignment")


class PartnerClientAccess(Base):
    """
    Scoped access for a partner user to a specific client.
    Critical for tenant isolation enforcement.
    """
    __tablename__ = "partner_client_access"
    
    access_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    partner_user_id = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=False, index=True)
    assignment_id = Column(String(32), ForeignKey("partner_client_assignments.assignment_id"), nullable=False, index=True)
    
    # Access scope
    access_level = Column(SQLEnum(ClientAccessLevel), default=ClientAccessLevel.ANALYSIS, nullable=False)
    
    # Specific permissions (override defaults for level)
    can_export = Column(Boolean, default=False)
    can_invite_users = Column(Boolean, default=False)
    can_delete_data = Column(Boolean, default=False)
    can_manage_vendors = Column(Boolean, default=True)
    can_manage_policy = Column(Boolean, default=True)
    
    # Time bounds
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional time limit
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=True)
    revoke_reason = Column(Text, nullable=True)
    
    # Relationships
    partner_user = relationship("PartnerUser", back_populates="client_access")
    assignment = relationship("PartnerClientAssignment", back_populates="user_access")


class PartnerNote(Base):
    """
    Notes created by partners about clients.
    Strict visibility controls: internal vs client-visible.
    """
    __tablename__ = "partner_notes"
    
    note_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.partner_id"), nullable=False, index=True)
    client_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Content
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # Visibility - CRITICAL for data separation
    visibility = Column(String(20), default="internal", nullable=False)  # 'internal', 'client_visible'
    
    # If client-visible: when did client see it?
    client_visible_at = Column(DateTime, nullable=True)
    client_acknowledged_at = Column(DateTime, nullable=True)
    
    # Categorization
    category = Column(String(50), nullable=True)  # 'observation', 'recommendation', 'risk', 'approval'
    tags = Column(JSON, default=list)
    
    # Author
    created_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_edited_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=True)
    
    # Link to specific entity
    related_entity_type = Column(String(50), nullable=True)  # 'vendor', 'policy', 'task', null for general
    related_entity_id = Column(String(32), nullable=True)
    
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=True)


class PartnerTemplate(Base):
    """
    Reusable templates created by partners for use across their clients.
    """
    __tablename__ = "partner_templates"
    
    template_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.partner_id"), nullable=False, index=True)
    
    # Template info
    name = Column(String(200), nullable=False)
    template_type = Column(String(50), nullable=False)  # 'remediation', 'vendor_review', 'policy_clause', 'report'
    description = Column(Text, nullable=True)
    
    # Content (varies by type)
    content = Column(JSON, nullable=False)
    
    # Usage
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_shared = Column(Boolean, default=False)  # Share with other partners?
    
    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PartnerActivityLog(Base):
    """
    Audit log for partner actions across clients.
    Complete traceability for security and compliance.
    """
    __tablename__ = "partner_activity_logs"
    
    __table_args__ = (
        Index("ix_partner_activity_org_time", "client_organization_id", "created_at"),
        Index("ix_partner_activity_user", "partner_user_id", "created_at"),
    )
    
    log_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.partner_id"), nullable=False, index=True)
    partner_user_id = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=False, index=True)
    client_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Action details
    action = Column(String(50), nullable=False)  # 'view', 'create', 'update', 'delete', 'export', 'switch_context'
    entity_type = Column(String(50), nullable=True)  # 'data_element', 'vendor', 'policy', etc.
    entity_id = Column(String(32), nullable=True)
    
    # Context
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)  # Privacy-hashed
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    partner_user = relationship("PartnerUser", back_populates="activity_log")


class PartnerExportConfig(Base):
    """
    Partner-specific export branding and configuration.
    """
    __tablename__ = "partner_export_configs"
    
    config_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.partner_id"), nullable=False, unique=True)
    
    # Branding
    header_text = Column(Text, nullable=True)
    footer_text = Column(Text, nullable=True)
    include_partner_logo = Column(Boolean, default=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    
    # Document settings
    default_format = Column(String(10), default="pdf")  # 'pdf', 'docx'
    include_disclaimer = Column(Boolean, default=True)
    custom_disclaimer = Column(Text, nullable=True)
    
    # Page elements
    show_partner_contact = Column(Boolean, default=True)
    show_page_numbers = Column(Boolean, default=True)
    show_toc = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("partner_users.user_id"), nullable=True)
