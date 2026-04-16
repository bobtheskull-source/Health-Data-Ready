"""
Rights Request Timeline Calculator
MHMDA deadline calculations per RCW 19.373.040
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from enum import Enum

class RequestType(str, Enum):
    ACCESS = "access"
    DELETION = "deletion"
    WITHDRAW_CONSENT = "withdraw_consent"
    APPEAL = "appeal"

class TimelineCalculator:
    """
    Calculate deadlines for MHMDA rights requests.
    
    Per RCW 19.373.040:
    - Controller must respond within 45 days of receipt
    - One 45-day extension allowed with notice to consumer
    - Extension must include reason and new deadline
    """
    
    BASE_RESPONSE_DAYS = 45
    EXTENSION_DAYS = 45
    APPEAL_RESPONSE_DAYS = 45
    
    @classmethod
    def calculate_deadline(
        cls,
        received_at: datetime,
        request_type: RequestType,
        extension_used: bool = False
    ) -> datetime:
        """
        Calculate the response deadline for a rights request.
        
        Args:
            received_at: When the request was received
            request_type: Type of rights request
            extension_used: Whether extension has been invoked
        
        Returns:
            The deadline datetime
        """
        # Ensure received_at is timezone-aware
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=timezone.utc)
        
        # Calculate base deadline (45 days)
        deadline = received_at + timedelta(days=cls.BASE_RESPONSE_DAYS)
        
        # If extension used, add another 45 days
        if extension_used:
            deadline = deadline + timedelta(days=cls.EXTENSION_DAYS)
        
        return deadline
    
    @classmethod
    def can_use_extension(
        cls,
        received_at: datetime,
        current_status: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if extension can still be requested.
        
        Extension must be requested before the original deadline.
        
        Returns:
            (can_extend, reason_if_not)
        """
        now = datetime.now(timezone.utc)
        original_deadline = received_at + timedelta(days=cls.BASE_RESPONSE_DAYS)
        
        if now > original_deadline:
            return False, "Original deadline has passed"
        
        if current_status in ["fulfilled", "denied", "closed"]:
            return False, "Request is already resolved"
        
        return True, None
    
    @classmethod
    def get_timeline_summary(
        cls,
        received_at: datetime,
        extension_used: bool,
        extension_requested_at: Optional[datetime] = None
    ) -> dict:
        """Get a full timeline summary for a request."""
        
        now = datetime.now(timezone.utc)
        base_deadline = received_at + timedelta(days=cls.BASE_RESPONSE_DAYS)
        
        summary = {
            "received_at": received_at.isoformat(),
            "base_deadline": base_deadline.isoformat(),
            "extension_used": extension_used,
            "days_remaining": None,
            "deadline_status": None
        }
        
        if extension_used and extension_requested_at:
            final_deadline = base_deadline + timedelta(days=cls.EXTENSION_DAYS)
            summary["extension_requested_at"] = extension_requested_at.isoformat()
            summary["final_deadline"] = final_deadline.isoformat()
            
            days_remaining = (final_deadline - now).days
            summary["days_remaining"] = max(0, days_remaining)
            
            if now > final_deadline:
                summary["deadline_status"] = "overdue"
            elif days_remaining <= 7:
                summary["deadline_status"] = "urgent"
            elif days_remaining <= 14:
                summary["deadline_status"] = "approaching"
            else:
                summary["deadline_status"] = "on_track"
        else:
            days_remaining = (base_deadline - now).days
            summary["days_remaining"] = max(0, days_remaining)
            summary["final_deadline"] = base_deadline.isoformat()
            
            if now > base_deadline:
                summary["deadline_status"] = "overdue"
            elif days_remaining <= 7:
                summary["deadline_status"] = "approaching"
            else:
                summary["deadline_status"] = "on_track"
        
        return summary
    
    @classmethod
    def calculate_appeal_deadline(
        cls,
        denial_date: datetime
    ) -> datetime:
        """
        Calculate the appeal submission deadline.
        
        Note: MHMDA doesn't specify appeal deadline, but reasonable
        timeframes are typically 30-60 days. Using 45 days for consistency.
        """
        return denial_date + timedelta(days=cls.APPEAL_RESPONSE_DAYS)
    
    @classmethod
    def is_duplicate_request(
        cls,
        existing_request_date: datetime,
        new_request_date: datetime,
        same_consumer: bool
    ) -> bool:
        """
        Check if a new request might be a duplicate.
        
        Duplicate detection within 30 days for same consumer.
        """
        if not same_consumer:
            return False
        
        time_diff = new_request_date - existing_request_date
        return abs(time_diff.days) <= 30
