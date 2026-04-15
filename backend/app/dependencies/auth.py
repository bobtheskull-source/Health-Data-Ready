from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.models import WorkspaceUser, Organization, Role

security = HTTPBearer(auto_error=False)

def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> WorkspaceUser:
    """Dependency to require authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id, token_type = decode_token(credentials.credentials)
    
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    
    user = db.query(WorkspaceUser).filter(
        and_(
            WorkspaceUser.id == uuid.UUID(user_id),
            WorkspaceUser.is_active == True
        )
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    return user

def require_role(*roles: Role):
    """Dependency factory to require specific roles."""
    def role_checker(current_user: WorkspaceUser = Depends(require_auth)) -> WorkspaceUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {[r.value for r in roles]}",
            )
        return current_user
    return role_checker

def require_owner_or_staff(current_user: WorkspaceUser = Depends(require_auth)) -> WorkspaceUser:
    """Require owner or staff editor role."""
    if current_user.role not in [Role.OWNER, Role.STAFF_EDITOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires owner or staff editor role",
        )
    return current_user

def require_owner(current_user: WorkspaceUser = Depends(require_auth)) -> WorkspaceUser:
    """Require owner role only."""
    if current_user.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires owner role",
        )
    return current_user
