"""
MHMDA Rights Request Timeline Engine
RCW 19.373.040 - 45 day response requirement
"""

from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import holidays


class TimelineStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    EXTENDED = "extended"
    DUE_SOON = "due_soon"  # < 7 days
    OVERDUE = "overdue"
    COMPLETED = "completed"


class ExtensionReason(str, Enum):
    VERIFICATION_REQUIRED = "verification_required"
    HIGH_VOLUME = "high_volume"
    TECHNICAL_DIFFICULTY = "technical_difficulty"
    LEGAL_REVIEW = "legal_review"


class RightsTimelineEngine:
    """Calculate MHMDA-mandated response deadlines."""
    
    BASE_DAYS = 45
    EXTENSION_DAYS = 45
    WARNING_THRESHOLD_DAYS = 7
    
    def __init__(self):
        # Washington State holidays
        self.wa_holidays = holidays.US(state='WA', years=range(2024, 2030))
    
    def calculate_deadline(
        self, 
        request_date: datetime,
        extension_granted: bool = False,
        extension_reason: Optional[ExtensionReason] = None,
        extension_date: Optional[datetime] = None
    ) -> dict:
        """
        Calculate response deadline per RCW 19.373.040.
        Returns full timeline details.
        """
        base_deadline = self._add_business_days(request_date, self.BASE_DAYS)
        
        result = {
            'request_date': request_date.isoformat(),
            'base_deadline': base_deadline.isoformat(),
            'days_remaining': self._business_days_between(datetime.now(), base_deadline),
            'extension_granted': extension_granted,
            'extension_reason': extension_reason.value if extension_reason else None,
            'extended_deadline': None,
            'total_days_allowed': self.BASE_DAYS,
            'is_overdue': False,
            'is_due_soon': False,
            'timeline_status': TimelineStatus.PENDING.value
        }
        
        if extension_granted and extension_date:
            extended_deadline = self._add_business_days(extension_date, self.EXTENSION_DAYS)
            result['extended_deadline'] = extended_deadline.isoformat()
            result['total_days_allowed'] = self.BASE_DAYS + self.EXTENSION_DAYS
            effective_deadline = extended_deadline
        else:
            effective_deadline = base_deadline
        
        # Status calculation
        now = datetime.now()
        days_to_deadline = self._business_days_between(now, effective_deadline)
        
        if days_to_deadline < 0:
            result['is_overdue'] = True
            result['timeline_status'] = TimelineStatus.OVERDUE.value
            result['days_overdue'] = abs(days_to_deadline)
        elif days_to_deadline <= self.WARNING_THRESHOLD_DAYS:
            result['is_due_soon'] = True
            result['timeline_status'] = TimelineStatus.DUE_SOON.value
            result['days_remaining'] = days_to_deadline
        else:
            result['days_remaining'] = days_to_deadline
            result['timeline_status'] = TimelineStatus.IN_PROGRESS.value
        
        return result
    
    def _add_business_days(self, start_date: datetime, days: int) -> datetime:
        """Add business days excluding weekends and WA holidays."""
        current = start_date
        business_days_added = 0
        
        while business_days_added < days:
            current += timedelta(days=1)
            if self._is_business_day(current):
                business_days_added += 1
        
        return current
    
    def _business_days_between(self, start: datetime, end: datetime) -> int:
        """Count business days between dates (can be negative)."""
        if start > end:
            return -self._business_days_between(end, start)
        
        days = 0
        current = start
        while current.date() < end.date():
            current += timedelta(days=1)
            if self._is_business_day(current):
                days += 1
        
        return days
    
    def _is_business_day(self, date: datetime) -> bool:
        """Check if date is a business day."""
        return (
            date.weekday() < 5  # Mon-Fri
            and date.date() not in self.wa_holidays
        )
    
    def validate_extension_request(
        self, 
        request_date: datetime,
        proposed_reason: ExtensionReason,
        current_day: int
    ) -> dict:
        """Validate if extension request meets MHMDA requirements."""
        # Extensions must be requested before base deadline
        base_deadline = self._add_business_days(request_date, self.BASE_DAYS)
        can_extend = current_day <= self.BASE_DAYS
        
        valid_reasons = [
            ExtensionReason.VERIFICATION_REQUIRED,
            ExtensionReason.HIGH_VOLUME,
            ExtensionReason.TECHNICAL_DIFFICULTY,
            ExtensionReason.LEGAL_REVIEW
        ]
        
        return {
            'can_extend': can_extend,
            'base_deadline_passed': current_day > self.BASE_DAYS,
            'reason_valid': proposed_reason in valid_reasons,
            'requires_consumer_notice': True,  # Must notify consumer of extension
            'notice_must_include': [
                'Reason for delay',
                'New expected completion date',
                'Consumer rights under MHMDA'
            ]
        }
    
    def get_milestones(self, request_date: datetime) -> list:
        """Get key timeline milestones for a request."""
        milestones = [
            {'day': 0, 'event': 'Request received', 'deadline': request_date.isoformat()},
            {'day': 7, 'event': 'Acknowledgment due', 'action': 'Send confirmation to consumer'},
            {'day': 30, 'event': 'Progress check', 'action': 'Verify collection/processing status'},
            {'day': 45, 'event': 'Final response due', 'deadline': self._add_business_days(request_date, 45).isoformat()},
        ]
        
        extended_start = self._add_business_days(request_date, 45)
        milestones.extend([
            {'day': 52, 'event': 'Extension acknowledgment', 'action': 'Notify consumer of extension'},
            {'day': 75, 'event': 'Extended progress check', 'action': 'Verify near completion'},
            {'day': 90, 'event': 'Extended deadline', 'deadline': self._add_business_days(request_date, 90).isoformat(), 'note': 'Maximum allowed under MHMDA'},
        ])
        
        return milestones
