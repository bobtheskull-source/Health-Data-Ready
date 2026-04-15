from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import timedelta, datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, 
    create_access_token, create_refresh_token
)
from app.core.config import settings
from app.models import WorkspaceUser, Organization, Role, AuditEvent
from app.schemas import LoginRequest, Token, UserCreate, UserResponse
from app.dependencies.auth import require_auth
from app.dependencies.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=Token)
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens."""
    user = db.query(WorkspaceUser).filter(
        WorkspaceUser.email == login_data.email
    ).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        # Log failed login attempt
        log_audit_event(
            db=db,
            action="login_failed",
            organization_id=user.organization_id if user else uuid.uuid4(),  # Dummy for logging
            tenant_id=user.tenant_id if user else "unknown",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    # Log successful login
    log_audit_event(
        db=db,
        action="login",
        organization_id=user.organization_id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/register")
def register(
    request: Request,
    org_data: dict,  # OrganizationCreate + UserCreate combined
    db: Session = Depends(get_db)
):
    """Register new organization with owner user."""
    # This would create organization + owner user
    # Implementation simplified for MVP
    pass

@router.get("/me", response_model=UserResponse)
def get_current_user(current_user: WorkspaceUser = Depends(require_auth)):
    """Get current authenticated user."""
    return current_user
