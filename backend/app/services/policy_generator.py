"""
MHMDA Privacy Policy Generator
Template-based generation from structured facts.
Deterministic assembly - no LLM required.
"""

from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from string import Template

@dataclass
class PolicyFacts:
    """Structured facts required for policy generation."""
    business_name: str
    business_type: str
    website_url: Optional[str]
    
    # Data collection
    collects_health_data: bool
    health_data_categories: List[str]
    data_sources: List[str]
    
    # Purposes
    collection_purposes: List[str]
    
    # Sharing
    shares_data: bool
    sharing_categories: List[Dict]  # [{"category": "payment_processors", "description": "..."}]
    third_party_categories: List[str]
    affiliates: List[str]
    
    # Consumer rights
    rights_contact_email: str
    rights_contact_phone: Optional[str]
    rights_contact_address: Optional[str]
    
    # Required disclosures per RCW 19.373.020
    has_consumer_health_data_privacy_policy: bool = True
    homepage_link_verified: bool = False
    
    # Effective date
    effective_date: str = ""

class PolicyGenerator:
    """Generate MHMDA-compliant privacy policies from structured facts."""
    
    REQUIRED_FIELDS = [
        "business_name",
        "health_data_categories",
        "collection_purposes",
        "rights_contact_email"
    ]
    
    POLICY_TEMPLATE = '''
<h1>Consumer Health Data Privacy Policy</h1>
<p><strong>${business_name}</strong></p>
<p>Effective Date: ${effective_date}</p>

<div class="legal-notice">
<p><strong>Not Legal Advice:</strong> This policy was generated based on information you provided about your business practices. 
It should be reviewed by qualified legal counsel before use.</p>
</div>

<h2>1. Introduction</h2>
<p>${business_name} ("we," "us," or "our") respects your privacy and is committed to protecting your consumer health data. 
This Consumer Health Data Privacy Policy explains how we collect, use, disclose, and protect your personal health information 
under Washington State's My Health My Data Act (Chapter 19.373 RCW).</p>

$if{has_website}<p>This policy is available at: <a href="${website_url}/privacy">${website_url}/privacy</a></p>$endif

<h2>2. Categories of Consumer Health Data We Collect</h2>
<p>We collect the following categories of consumer health data:</p>
<ul>
${health_data_list}
</ul>

<h2>3. Sources of Consumer Health Data</h2>
<p>We collect consumer health data from the following sources:</p>
<ul>
${data_sources_list}
</ul>

<h2>4. Purposes for Collecting Consumer Health Data</h2>
<p>We collect and use your consumer health data for the following purposes:</p>
<ul>
${purposes_list}
</ul>

<h2>5. Categories of Consumer Health Data We Share</h2>
$if{shares_data}
<p>We may share the following categories of consumer health data:</p>
<ul>
${sharing_list}
</ul>

<h3>5.1 Categories of Third Parties</h3>
<p>We may share consumer health data with the following categories of third parties:</p>
<ul>
${third_party_list}
</ul>

$if{has_affiliates}
<h3>5.2 Affiliates</h3>
<p>We may share consumer health data with the following affiliates:</p>
<ul>
${affiliates_list}
</ul>
$endif

$else
<p>We do not share your consumer health data with third parties, except as required by law or with your explicit consent.</p>
$endif

<h2>6. Your Rights Under Washington Law</h2>
<p>Under the Washington My Health My Data Act, you have the following rights regarding your consumer health data:</p>

<h3>6.1 Right to Access</h3>
<p>You have the right to request confirmation of whether we are processing your consumer health data and to access such data.</p>

<h3>6.2 Right to Withdraw Consent</h3>
<p>You have the right to withdraw your consent for our collection and sharing of your consumer health data at any time.</p>

<h3>6.3 Right to Deletion</h3>
<p>You have the right to request that we delete your consumer health data, subject to certain exceptions permitted by law.</p>

<h3>6.4 Right to Appeal</h3>
<p>If we decline to take action on your request, you have the right to appeal our decision within a reasonable period.</p>

<h2>7. How to Exercise Your Rights</h2>
<p>To exercise your rights, please contact us using one of the following methods:</p>
<ul>
<li>Email: ${rights_contact_email}</li>
$if{has_phone}<li>Phone: ${rights_contact_phone}</li>$endif
$if{has_address}<li>Mail: ${rights_contact_address}</li>$endif
</ul>

<p>We will respond to your request within the timeframe required by Washington law. We may need to verify your identity before processing your request.</p>

<h2>8. Data Security</h2>
<p>We implement appropriate technical and organizational measures to protect your consumer health data from unauthorized access, disclosure, alteration, or destruction.</p>

<h2>9. Changes to This Policy</h2>
<p>We may update this Consumer Health Data Privacy Policy from time to time. The updated version will be indicated by an updated "Effective Date" at the top of this policy.</p>

<h2>10. Contact Information</h2>
<p>If you have questions or concerns about this policy or our data practices, please contact:</p>
<p>
${business_name}<br>
Email: ${rights_contact_email}<br>
$if{has_phone}Phone: ${rights_contact_phone}<br>$endif
$if{has_address}${rights_contact_address}<br>$endif
</p>

<hr>
<p><small>This policy was generated on ${generation_date} and is based on your business practices as reported to Health Data Ready.</small></p>
'''.strip()
    
    def validate_facts(self, facts: PolicyFacts) -> List[str]:
        """Validate that all required facts are present."""
        missing = []
        
        if not facts.business_name:
            missing.append("business_name")
        if not facts.health_data_categories:
            missing.append("health_data_categories")
        if not facts.collection_purposes:
            missing.append("collection_purposes")
        if not facts.rights_contact_email:
            missing.append("rights_contact_email")
            
        return missing
    
    def generate(self, facts: PolicyFacts) -> Dict:
        """
        Generate privacy policy from structured facts.
        
        Returns:
            Dict with 'html', 'missing_fields', 'warnings'
        """
        # Validate required fields
        missing = self.validate_facts(facts)
        if missing:
            return {
                "html": None,
                "missing_fields": missing,
                "warnings": [f"Missing required field: {f}" for f in missing],
                "can_generate": False
            }
        
        warnings = []
        
        # Build lists
        health_data_list = self._build_list(facts.health_data_categories)
        data_sources_list = self._build_list(facts.data_sources or ["Directly from you"])
        purposes_list = self._build_list(facts.collection_purposes)
        
        # Sharing section
        if facts.shares_data and facts.sharing_categories:
            sharing_list = self._build_sharing_list(facts.sharing_categories)
            third_party_list = self._build_list(facts.third_party_categories)
        else:
            sharing_list = ""
            third_party_list = ""
        
        affiliates_list = self._build_list(facts.affiliates) if facts.affiliates else ""
        
        # Check for potential issues
        if facts.shares_data and not facts.sharing_categories:
            warnings.append("Data sharing indicated but no sharing categories specified")
        
        # Substitute into template
        template = Template(self.POLICY_TEMPLATE)
        
        html = template.substitute(
            business_name=facts.business_name,
            effective_date=facts.effective_date or datetime.now().strftime("%B %d, %Y"),
            generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            has_website=bool(facts.website_url),
            website_url=facts.website_url or "",
            health_data_list=health_data_list,
            data_sources_list=data_sources_list,
            purposes_list=purposes_list,
            shares_data=facts.shares_data,
            sharing_list=sharing_list,
            third_party_list=third_party_list,
            has_affiliates=bool(facts.affiliates),
            affiliates_list=affiliates_list,
            rights_contact_email=facts.rights_contact_email,
            has_phone=bool(facts.rights_contact_phone),
            rights_contact_phone=facts.rights_contact_phone or "",
            has_address=bool(facts.rights_contact_address),
            rights_contact_address=facts.rights_contact_address or ""
        )
        
        # Clean up conditional blocks
        html = self._process_conditionals(html)
        
        return {
            "html": html,
            "missing_fields": [],
            "warnings": warnings,
            "can_generate": True,
            "homepage_link_required": True,
            "legal_review_banner": True
        }
    
    def _build_list(self, items: List[str]) -> str:
        """Build HTML list from items."""
        return "\n".join([f"<li>{item}</li>" for item in items])
    
    def _build_sharing_list(self, categories: List[Dict]) -> str:
        """Build sharing categories list."""
        items = []
        for cat in categories:
            name = cat.get("category", "").replace("_", " ").title()
            desc = cat.get("description", "")
            items.append(f"<li><strong>{name}:</strong> {desc}</li>")
        return "\n".join(items)
    
    def _process_conditionals(self, html: str) -> str:
        """Process $if{condition}...$endif blocks."""
        import re
        
        # Simple conditional processing
        def replace_conditional(match):
            condition = match.group(1)
            content = match.group(2)
            # If condition is truthy, return content, else return empty
            if condition in ["True", "true", "1"]:
                return content
            return ""
        
        pattern = r'\$if\{([^}]+)\}(.*?)\$endif'
        return re.sub(pattern, replace_conditional, html, flags=re.DOTALL)
