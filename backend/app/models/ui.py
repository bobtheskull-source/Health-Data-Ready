"""
Web App UI Shell Models
FastAPI endpoints for web frontend serving.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class UIComponentType(str, Enum):
    DASHBOARD = "dashboard"
    DATA_INVENTORY = "data_inventory"
    VENDOR_MANAGEMENT = "vendor_management"
    RIGHTS_REQUESTS = "rights_requests"
    POLICY_CENTER = "policy_center"
    COMPLIANCE_REPORTS = "compliance_reports"
    AUDIT_LOG = "audit_log"
    SETTINGS = "settings"


class UserPreference(Base):
    """User-specific UI preferences and settings."""
    __tablename__ = "user_preferences"
    
    preference_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False, unique=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # UI Settings
    theme = Column(String(20), default="system")  # light, dark, system
    sidebar_collapsed = Column(Boolean, default=False)
    default_page = Column(String(50), default="dashboard")
    items_per_page = Column(Integer, default=25)
    timezone = Column(String(50), default="America/Los_Angeles")
    date_format = Column(String(20), default="YYYY-MM-DD")
    
    # Dashboard layout (JSON widget positions)
    dashboard_layout = Column(String(2048), default="{}")
    
    # Notifications
    email_notifications = Column(Boolean, default=True)
    digest_frequency = Column(String(20), default="daily")  # off, daily, weekly
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("WorkspaceUser", back_populates="preferences")


class PageView(Base):
    """Analytics tracking for UI usage."""
    __tablename__ = "page_views"
    
    view_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    page = Column(String(100), nullable=False)
    route = Column(String(255), nullable=False)
    referrer = Column(String(500), nullable=True)
    
    view_started_at = Column(DateTime, default=datetime.utcnow)
    view_ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    user_agent_hash = Column(String(64), nullable=True)  # Privacy-hashed
    session_id = Column(String(64), nullable=True, index=True)


class Notification(Base):
    """In-app notifications for users."""
    __tablename__ = "notifications"
    
    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    type = Column(String(50), nullable=False)  # request_assigned, deadline_approaching, etc.
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    link_route = Column(String(255), nullable=True)  # Click action
    link_params = Column(String(500), nullable=True)  # JSON params
    
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    dismissed = Column(Boolean, default=False)


class FeatureFlag(Base):
    """Feature flags for progressive rollout."""
    __tablename__ = "feature_flags"
    
    flag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_key = Column(String(100), unique=True, nullable=False)
    feature_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rollout settings
    enabled_globally = Column(Boolean, default=False)
    enabled_for_orgs = Column(String(2048), default="[]")  # JSON list of org IDs
    enabled_for_users = Column(String(2048), default="[]")  # JSON list of user IDs
    rollout_percentage = Column(Integer, default=0)  # 0-100
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)


class UIHelpArticle(Base):
    """In-app help documentation."""
    __tablename__ = "ui_help_articles"
    
    article_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    category = Column(String(50), nullable=False)  # getting-started, data-inventory, etc.
    related_features = Column(String(500), default="[]")  # JSON list of feature keys
    
    published = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
