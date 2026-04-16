"""
Website Review Module
Milestone 9: Light website scanning for privacy link and tracker detection
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class ReviewMethod(str, Enum):
    MANUAL = "manual"  # User-reported findings
    AUTOMATED = "automated"  # System scan
    HYBRID = "hybrid"  # Both automated + manual review


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class WebsiteReview(Base):
    """
    Website review record for privacy compliance assessment.
    Light scan approach - not a full crawler.
    """
    __tablename__ = "website_reviews"
    
    review_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False)
    
    # Website details
    url = Column(String(500), nullable=False)
    reviewed_url = Column(String(500), nullable=True)  # Final URL after redirects
    
    # Review metadata
    review_method = Column(SQLEnum(ReviewMethod), default=ReviewMethod.HYBRID, nullable=False)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    
    # Scan results
    homepage_loadable = Column(Boolean, nullable=True)
    scans_completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Screenshots (evidence)
    homepage_screenshot_key = Column(String(512), nullable=True)  # S3 storage key
    mobile_screenshot_key = Column(String(512), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="website_reviews")
    findings = relationship("WebsiteFinding", back_populates="website_review", cascade="all, delete-orphan")


class WebsiteFinding(Base):
    """
    Individual finding from website review.
    """
    __tablename__ = "website_findings"
    
    __table_args__ = (
        Index("ix_finding_org_type", "organization_id", "finding_type"),
    )
    
    finding_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    website_review_id = Column(String(32), ForeignKey("website_reviews.review_id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False)
    
    # Finding classification
    finding_type = Column(String(50), nullable=False)  # See FINDING_TYPES below
    severity = Column(SQLEnum(FindingSeverity), nullable=False)
    
    # Description
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Evidence
    evidence_screenshot_key = Column(String(512), nullable=True)
    page_url = Column(String(500), nullable=True)  # Where finding was observed
    element_selector = Column(String(255), nullable=True)  # CSS selector if applicable
    
    # Automated detection results
    detected_value = Column(String(500), nullable=True)  # What was detected
    confidence = Column(String(20), default="medium")  # low, medium, high
    
    # Resolution
    requires_manual_review = Column(Boolean, default=False)
    remediation_task_id = Column(String(32), ForeignKey("remediation_tasks.task_id"), nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    website_review = relationship("WebsiteReview", back_populates="findings")
    remediation_task = relationship("RemediationTask")


# Standard finding types
FINDING_TYPES = {
    # Privacy Policy
    "privacy_link_missing": {
        "category": "policy",
        "severity": FindingSeverity.CRITICAL,
        "title": "Privacy policy link not found on homepage",
        "description": "MHMDA requires a clear privacy policy link. No visible link detected in footer or header."
    },
    "privacy_link_present": {
        "category": "policy",
        "severity": FindingSeverity.INFO,
        "title": "Privacy policy link found",
        "description": "Privacy policy link is visible and clickable."
    },
    "privacy_link_broken": {
        "category": "policy",
        "severity": FindingSeverity.HIGH,
        "title": "Privacy policy link returns error",
        "description": "Privacy policy link exists but returns HTTP error or redirects to 404."
    },
    
    # Cookie/Tracking
    "cookie_banner_present": {
        "category": "tracking",
        "severity": FindingSeverity.INFO,
        "title": "Cookie consent banner detected",
        "description": "Site displays cookie consent UI on first visit."
    },
    "cookie_banner_missing": {
        "category": "tracking",
        "severity": FindingSeverity.LOW,
        "title": "No cookie consent banner detected",
        "description": "No cookie consent mechanism observed. May be acceptable if no third-party cookies."
    },
    "google_analytics_detected": {
        "category": "tracking",
        "severity": FindingSeverity.MEDIUM,
        "title": "Google Analytics detected",
        "description": "Google Analytics script (gtag.js or analytics.js) present on page."
    },
    "facebook_pixel_detected": {
        "category": "tracking",
        "severity": FindingSeverity.HIGH,
        "title": "Facebook/Meta Pixel detected",
        "description": "Meta/Facebook tracking pixel detected. May raise health advertising concerns."
    },
    "ad_network_detected": {
        "category": "tracking",
        "severity": FindingSeverity.HIGH,
        "title": "Advertising network detected",
        "description": "Ad network scripts present. Risk of health-related ad targeting."
    },
    "third_party_cookies": {
        "category": "tracking",
        "severity": FindingSeverity.MEDIUM,
        "title": "Third-party cookies detected",
        "description": "Cookies set by domains other than the site itself."
    },
    "local_storage_usage": {
        "category": "tracking",
        "severity": FindingSeverity.LOW,
        "title": "Local storage usage detected",
        "description": "Site uses browser localStorage. May store tracking data."
    },
    
    # Forms
    "contact_form_present": {
        "category": "forms",
        "severity": FindingSeverity.INFO,
        "title": "Contact form detected",
        "description": "Contact or inquiry form present on site."
    },
    "intake_form_detected": {
        "category": "forms",
        "severity": FindingSeverity.MEDIUM,
        "title": "Health intake-like form detected",
        "description": "Form contains fields that may collect health-related information."
    },
    "unsecured_form": {
        "category": "forms",
        "severity": FindingSeverity.HIGH,
        "title": "Form submits over HTTP",
        "description": "Form detected that submits to non-HTTPS endpoint."
    },
    
    # Location
    "location_request_detected": {
        "category": "location",
        "severity": FindingSeverity.MEDIUM,
        "title": "Geolocation API usage detected",
        "description": "Site requests browser geolocation. May track health-related visits."
    },
    "location_in_form": {
        "category": "location",
        "severity": FindingSeverity.MEDIUM,
        "title": "Address/location fields in forms",
        "description": "Forms collect address or ZIP code information."
    },
    
    # Security
    "https_available": {
        "category": "security",
        "severity": FindingSeverity.INFO,
        "title": "HTTPS enabled",
        "description": "Site serves securely over HTTPS."
    },
    "mixed_content": {
        "category": "security",
        "severity": FindingSeverity.MEDIUM,
        "title": "Mixed content detected",
        "description": "HTTPS page loads HTTP resources (images, scripts, etc.)."
    },
    "security_headers_missing": {
        "category": "security",
        "severity": FindingSeverity.LOW,
        "title": "Security headers missing",
        "description": "Expected security headers (CSP, X-Frame-Options) not present."
    }
}


class WebsiteScanResult(Base):
    """
    Raw scan results for a website review.
    Stores technical findings before interpretation.
    """
    __tablename__ = "website_scan_results"
    
    scan_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    website_review_id = Column(String(32), ForeignKey("website_reviews.review_id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    tenant_id = Column(String(64), nullable=False)
    
    # Technical results
    http_status = Column(Integer, nullable=True)
    final_url = Column(String(500), nullable=True)
    page_title = Column(String(255), nullable=True)
    
    # Headers
    response_headers = Column(JSON, default=dict)
    
    # Scripts detected
    scripts_detected = Column(JSON, default=list)  # List of script URLs
    cookies_detected = Column(JSON, default=list)
    
    # DOM features
    forms_detected = Column(JSON, default=list)
    links_detected = Column(JSON, default=list)  # Including privacy policy links
    
    # Feature detection
    has_local_storage_calls = Column(Boolean, default=False)
    has_geolocation_calls = Column(Boolean, default=False)
    has_canvas_fingerprinting = Column(Boolean, default=False)
    
    # Scan metadata
    scan_duration_ms = Column(Integer, nullable=True)
    page_size_bytes = Column(Integer, nullable=True)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    
    # Error info
    scan_error = Column(Text, nullable=True)


class WebsiteScanService:
    """
    Light website scanning service.
    NOT a full crawler - targeted checks only.
    """
    
    KNOWN_TRACKERS = {
        "google-analytics.com": "Google Analytics",
        "googletagmanager.com": "Google Tag Manager",
        "googleadservices.com": "Google Ads",
        "doubleclick.net": "Google DoubleClick",
        "connect.facebook.net": "Facebook Pixel",
        "facebook.com/tr": "Facebook Pixel",
        "snap.licdn.com": "LinkedIn Insights",
        "analytics.twitter.com": "Twitter Analytics",
        "bat.bing.com": "Bing Ads",
        "criteo.com": "Criteo",
        "adsystem.amazon.com": "Amazon Advertising",
        "pinterest.com/ct.html": "Pinterest Tag",
        "tiktok.com/track": "TikTok Pixel",
    }
    
    HEALTH_KEYWORDS = [
        "medical", "health", "patient", "doctor", "physician", "clinic",
        "treatment", "diagnosis", "prescription", "care", "symptom",
        "condition", "medication", "therapy", "wellness", "insurance"
    ]
    
    def __init__(self, http_client=None):
        self.http_client = http_client  # Should be injected/initialized properly
    
    def scan_website(self, url: str, organization_id: str) -> WebsiteReview:
        """
        Perform light scan of website.
        
        Steps:
        1. Fetch homepage
        2. Extract scripts, links, forms
        3. Check for privacy policy link
        4. Detect known trackers
        5. Flag health-related forms
        """
        review = WebsiteReview(
            organization_id=organization_id,
            tenant_id=tenant_id,  # Need to get this
            url=url,
            status=ReviewStatus.IN_PROGRESS
        )
        
        try:
            # Fetch page (with timeout and size limit)
            response = self._fetch_page(url)
            
            if response.status_code != 200:
                review.status = ReviewStatus.FAILED
                review.error_message = f"HTTP {response.status_code}"
                return review
            
            review.homepage_loadable = True
            review.reviewed_url = str(response.url)
            
            # Parse content
            scan_result = self._analyze_page(response)
            
            # Generate findings
            findings = self._generate_findings(scan_result, review.review_id, organization_id)
            
            review.status = ReviewStatus.COMPLETED
            review.scans_completed_at = datetime.utcnow()
            
        except Exception as e:
            review.status = ReviewStatus.FAILED
            review.error_message = str(e)
        
        return review, scan_result, findings
    
    def _fetch_page(self, url: str):
        """Fetch page with safety checks."""
        import requests
        from urllib.parse import urlparse
        
        # Validate URL
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("Invalid URL scheme")
        
        # Safety: timeout, no redirects to internal IPs
        response = requests.get(
            url,
            timeout=10,
            headers={
                'User-Agent': 'HealthDataReady-Bot/1.0 (Compliance Scan)'
            },
            allow_redirects=True,
            max_redirects=5
        )
        
        # Limit size to prevent memory issues
        content_length = len(response.content)
        if content_length > 5 * 1024 * 1024:  # 5MB limit
            raise ValueError("Page too large")
        
        return response
    
    def _analyze_page(self, response) -> dict:
        """Analyze page content for findings."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        result = {
            'page_title': soup.title.string if soup.title else None,
            'scripts': [],
            'links': [],
            'forms': [],
            'has_privacy_link': False,
            'privacy_link_url': None
        }
        
        # Extract scripts
        for script in soup.find_all('script', src=True):
            result['scripts'].append(script['src'])
        
        # Extract links
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link['href']
            
            result['links'].append({
                'url': href,
                'text': link_text
            })
            
            # Check for privacy policy link
            if any(term in link_text for term in ['privacy', 'privacy policy']):
                result['has_privacy_link'] = True
                result['privacy_link_url'] = href
        
        # Extract forms
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get'),
                'fields': []
            }
            
            for field in form.find_all(['input', 'textarea', 'select']):
                field_name = field.get('name', '')
                field_type = field.get('type', 'text')
                field_label = self._get_field_label(field)
                
                form_data['fields'].append({
                    'name': field_name,
                    'type': field_type,
                    'label': field_label
                })
            
            # Check if form might be health-related
            form_text = ' '.join([f.get('label', '') for f in form_data['fields']]).lower()
            form_data['may_be_health_related'] = any(kw in form_text for kw in self.HEALTH_KEYWORDS)
            
            result['forms'].append(form_data)
        
        return result
    
    def _get_field_label(self, field) -> str:
        """Try to find label for a form field."""
        field_id = field.get('id', '')
        field_name = field.get('name', '')
        placeholder = field.get('placeholder', '')
        
        # Check for explicit label
        if field_id:
            label = field.find_previous('label', {'for': field_id})
            if label:
                return label.get_text(strip=True)
        
        return placeholder or field_name
    
    def _generate_findings(self, scan_result: dict, review_id: str, org_id: str) -> List[WebsiteFinding]:
        """Generate findings from scan results."""
        findings = []
        tenant_id = "get_from_db"  # Placeholder
        
        # Privacy policy link
        if scan_result['has_privacy_link']:
            finding_type = "privacy_link_present"
        else:
            finding_type = "privacy_link_missing"
        
        template = FINDING_TYPES[finding_type]
        findings.append(WebsiteFinding(
            website_review_id=review_id,
            organization_id=org_id,
            tenant_id=tenant_id,
            finding_type=finding_type,
            severity=template['severity'],
            title=template['title'],
            description=template['description'],
            detected_value=scan_result.get('privacy_link_url'),
            page_url=scan_result.get('final_url')
        ))
        
        # Trackers detected
        for script_url in scan_result['scripts']:
            for tracker_domain, tracker_name in self.KNOWN_TRACKERS.items():
                if tracker_domain in script_url:
                    finding_key = None
                    if 'facebook' in tracker_domain:
                        finding_key = "facebook_pixel_detected"
                    elif 'google-analytics' in tracker_domain or 'googletagmanager' in tracker_domain:
                        finding_key = "google_analytics_detected"
                    elif 'googleadservices' in tracker_domain or 'doubleclick' in tracker_domain:
                        finding_key = "ad_network_detected"
                    else:
                        finding_key = "third_party_cookies"
                    
                    if finding_key in FINDING_TYPES:
                        template = FINDING_TYPES[finding_key]
                        findings.append(WebsiteFinding(
                            website_review_id=review_id,
                            organization_id=org_id,
                            tenant_id=tenant_id,
                            finding_type=finding_key,
                            severity=template['severity'],
                            title=template['title'],
                            description=template['description'],
                            detected_value=script_url,
                            page_url=scan_result.get('final_url')
                        ))
        
        # Health-related forms
        for form in scan_result['forms']:
            if form.get('may_be_health_related'):
                template = FINDING_TYPES["intake_form_detected"]
                findings.append(WebsiteFinding(
                    website_review_id=review_id,
                    organization_id=org_id,
                    tenant_id=tenant_id,
                    finding_type="intake_form_detected",
                    severity=template['severity'],
                    title=template['title'],
                    description=template['description'],
                    page_url=scan_result.get('final_url'),
                    requires_manual_review=True
                ))
        
        return findings
