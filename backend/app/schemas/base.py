# Application schemas
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models import Role

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: Role = Role.READ_ONLY_REVIEWER

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[Role] = None

class UserResponse(UserBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    email_verified: bool
    mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Organization schemas
class OrganizationBase(BaseModel):
    name: str
    slug: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: UUID
    tenant_id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class TokenData(BaseModel):
    user_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# Audit schemas
class AuditEventResponse(BaseModel):
    id: UUID
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    user_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuditEventDetail(AuditEventResponse):
    before_state: Optional[dict]
    after_state: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
