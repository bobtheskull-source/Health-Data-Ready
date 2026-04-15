from fastapi import Request
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime, timezone

from app.models import AuditEvent

def sanitize_for_audit(data: Optional[dict]) -> Optional[dict]:
    """Remove sensitive fields before logging."""
    if not data:
        return None
    
    sensitive_keywords = ['password', 'secret', 'token', 'api_key', 'credit_card', 'ssn', 'auth']
    sanitized = {}
    
    for key, value in data.items():
        if any(keyword in key.lower() for keyword in sensitive_keywords):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_audit(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_for_audit(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized

def log_audit_event(
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
    """Create audit event with automatic sanitization."""
    event = AuditEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        organization_id=organization_id,
        tenant_id=tenant_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        before_state=sanitize_for_audit(before_state),
        after_state=sanitize_for_audit(after_state),
        ip_address=ip_address[:45] if ip_address else None,
        user_agent=user_agent[:1000] if user_agent else None,
        request_id=request_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
