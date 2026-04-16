import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Enum, JSON, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base

# Enums
class Role(str, enum.Enum):
    OWNER = "owner"
    STAFF_EDITOR = "staff_editor"
    READ_ONLY_REVIEWER = "read_only_reviewer"

class ActionType(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    ROLE_CHANGE = "role_change"

# Models
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(64), unique=True, nullable=False, index=True)
    
    users = relationship("WorkspaceUser", back_populates="organization", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="organization")
    questionnaires = relationship("QuestionnaireResponse", back_populates="organization", cascade="all, delete-orphan")
    vendors = relationship("SystemVendor", back_populates="organization", cascade="all, delete-orphan")

class WorkspaceUser(Base):
    __tablename__ = "workspace_users"
    __table_args__ = (
        Index("ix_workspace_org_user", "organization_id", "email", unique=True),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(Enum(Role), nullable=False, default=Role.READ_ONLY_REVIEWER)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    organization = relationship("Organization", back_populates="users")
    audit_events = relationship("AuditEvent", back_populates="user")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.id"), nullable=True, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(255), nullable=True, index=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    user = relationship("WorkspaceUser", back_populates="audit_events")
    organization = relationship("Organization", back_populates="audit_events")
