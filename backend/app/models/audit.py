from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Index, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base

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

class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.id"), nullable=True, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False, index=True)
    
    # Action details
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(255), nullable=True, index=True)
    
    # Data (redact sensitive fields)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationship
    user = relationship("WorkspaceUser", back_populates="audit_events")

def create_audit_event(
    db: Session,
    action: str,
    organization_id: uuid.UUID,
    tenant_id: str,
    user_id: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None
) -> AuditEvent:
    """Create and persist an audit event. Sensitive data should be redacted before calling."""
    event = AuditEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        organization_id=organization_id,
        tenant_id=tenant_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        before_state=_redact_sensitive(before_state),
        after_state=_redact_sensitive(after_state),
        ip_address=ip_address,
        user_agent=user_agent[:1000] if user_agent else None,  # Limit size
        request_id=request_id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def _redact_sensitive(data: Optional[dict]) -> Optional[dict]:
    """Redact sensitive fields from audit data."""
    if data is None:
        return None
    
    sensitive_keys = {
        "password", "hashed_password", "token", "secret", "api_key",
        "mfa_secret", "credit_card", "ssn", "auth_code"
    }
    
    redacted = {}
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_keys):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive(value)
        else:
            redacted[key] = value
    
    return redacted
