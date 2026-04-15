from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text, Enum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base
import enum

class Role(str, enum.Enum):
    OWNER = "owner"
    STAFF_EDITOR = "staff_editor"
    READ_ONLY_REVIEWER = "read_only_reviewer"

class TokenType(str, enum.Enum):
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    MFA_SETUP = "mfa_setup"

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Tenant isolation helper
    tenant_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # Relationships
    users = relationship("WorkspaceUser", back_populates="organization", cascade="all, delete-orphan")

class WorkspaceUser(Base):
    __tablename__ = "workspace_users"
    __table_args__ = (
        Index("ix_workspace_org_user", "organization_id", "email", unique=True),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for SSO future
    
    role = Column(Enum(Role), nullable=False, default=Role.READ_ONLY_REVIEWER)
    
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted MFA secret
    
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Tenant isolation - ensures all queries filter by tenant
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    audit_events = relationship("AuditEvent", back_populates="user")

class TokenBlacklist(Base):
    """JWT token blacklist for logout/revocation."""
    __tablename__ = "token_blacklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(Enum(TokenType), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Index for cleanup of expired tokens
    __table_args__ = (
        Index("ix_token_blacklist_expires", "expires_at"),
    )
