"""
Consent Template Generator
Template-based consent text for collection and sharing.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ConsentTemplate:
    template_type: str  # "collection" or "sharing"
    name: str
    title: str
    body: str
    required_elements: List[str]
    optional_clauses: List[str]

class ConsentTemplateGenerator:
    """Generate consent templates for health data operations."""
    
    COLLECTION_TEMPLATE = """
<h2>Consent to Collect Consumer Health Data</h2>

<p>By providing the information below, you consent to {business_name} collecting and processing your consumer health data as described in our Consumer Health Data Privacy Policy.</p>

<h3>Data We Will Collect</h3>
<ul>
{data_categories_list}
</ul>

<h3>Purposes of Collection</h3>
<p>We collect this health data for the following purposes:</p>
<ul>
{purposes_list}
</ul>

<h3>Your Rights</h3>
<p>You have the right to:</p>
<ul>
<li>Access your health data</li>
<li>Request deletion of your health data</li>
<li>Withdraw this consent at any time</li>
<li>Appeal any decision regarding your data rights</li>
</ul>

<p>To exercise these rights, contact us at: {contact_email}</p>

<p><label><input type="checkbox" name="consent_given" required> 
I consent to the collection and processing of my consumer health data as described above.</label></p>

<p><small>You may withdraw your consent at any time by contacting us. Withdrawing consent will not affect the lawfulness of processing before the withdrawal.</small></p>
""".strip()
    
    SHARING_TEMPLATE = """
<h2>Consent to Share Consumer Health Data</h2>

<p>{business_name} would like your explicit consent to share your consumer health data with the following third parties:</p>

<h3>Categories of Recipients</h3>
<ul>
{recipient_categories}
</ul>

<h3>Specific Third Parties</h3>
<ul>
{specific_vendors}
</ul>

<h3>Data Categories to be Shared</h3>
<ul>
{data_shared_list}
</ul>

<h3>Purposes of Sharing</h3>
<ul>
{sharing_purposes}
</ul>

<p><strong>Note:</strong> These third parties will be required to handle your data in accordance with applicable law and our agreements with them.</p>

<p><label><input type="checkbox" name="sharing_consent_given" required> 
I consent to sharing my consumer health data with the third parties listed above for the stated purposes.</label></p>

<p><small>You may withdraw this consent at any time. Please note that withdrawing consent may affect our ability to provide certain services to you.</small></p>
""".strip()
    
    def generate_collection_consent(
        self,
        business_name: str,
        data_categories: List[str],
        purposes: List[str],
        contact_email: str
    ) -> ConsentTemplate:
        """Generate collection consent template."""
        
        data_list = "\n".join([f"<li>{cat}</li>" for cat in data_categories])
        purposes_list = "\n".join([f"<li>{p}</li>" for p in purposes])
        
        body = self.COLLECTION_TEMPLATE.format(
            business_name=business_name,
            data_categories_list=data_list,
            purposes_list=purposes_list,
            contact_email=contact_email
        )
        
        return ConsentTemplate(
            template_type="collection",
            name="consumer_health_data_collection",
            title="Consent to Collect Consumer Health Data",
            body=body,
            required_elements=[
                "purpose_specification",
                "data_categories",
                "rights_notification",
                "withdrawal_method"
            ],
            optional_clauses=["retention_period", "automated_decisioning"]
        )
    
    def generate_sharing_consent(
        self,
        business_name: str,
        vendor_list: List[Dict],
        data_categories: List[str],
        purposes: List[str]
    ) -> ConsentTemplate:
        """Generate sharing consent template."""
        
        # Group vendors by category
        categories = {}
        specific_vendors = []
        for v in vendor_list:
            cat = v.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(v.get("name", "Unknown"))
            specific_vendors.append(f"<li>{v.get('name', 'Unknown')} - {v.get('purpose', 'Service provider')}</li>")
        
        category_list = "\n".join([f"<li>{k}: {', '.join(v)}</li>" for k, v in categories.items()])
        data_list = "\n".join([f"<li>{d}</li>" for d in data_categories])
        purposes_list = "\n".join([f"<li>{p}</li>" for p in purposes])
        
        body = self.SHARING_TEMPLATE.format(
            business_name=business_name,
            recipient_categories=category_list or "<li>Service providers</li>",
            specific_vendors="\n".join(specific_vendors) or "<li>Not specified</li>",
            data_shared_list=data_list,
            sharing_purposes=purposes_list
        )
        
        return ConsentTemplate(
            template_type="sharing",
            name="consumer_health_data_sharing",
            title="Consent to Share Consumer Health Data",
            body=body,
            required_elements=[
                "recipient_identification",
                "data_categories",
                "purposes",
                "withdrawal_method"
            ],
            optional_clauses=["contractual_safeguards", "international_transfer"]
        )
    
    def validate_consent(
        self,
        template: ConsentTemplate,
        provided_elements: List[str]
    ) -> Dict:
        """Validate that consent template has all required elements."""
        
        missing = [e for e in template.required_elements if e not in provided_elements]
        
        return {
            "valid": len(missing) == 0,
            "missing_elements": missing,
            "template_type": template.template_type,
            "has_required_structure": True
        }
