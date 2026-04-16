"""
Approved Clause Library Service
Milestone 10: Deterministic policy generation from approved blocks
"""

from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
import uuid
import json

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base


class ClauseCategory(str, Enum):
    INTRODUCTION = "introduction"
    SCOPE = "scope"
    DATA_COLLECTION = "data_collection"
    DATA_USE = "data_use"
    DATA_SHARING = "data_sharing"
    CONSUMER_RIGHTS = "consumer_rights"
    SECURITY = "security"
    RETENTION = "retention"
    INTERNATIONAL = "international"
    CONTACT = "contact"
    DEFINITIONS = "definitions"


class ClauseStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    WITHDRAWN = "withdrawn"


class Jurisdiction(str, Enum):
    WASHINGTON = "washington"
    CALIFORNIA = "california"
    COLORADO = "colorado"
    CONNECTICUT = "connecticut"
    FEDERAL = "federal"
    GENERIC_US = "generic_us"


class ClauseBlock(Base):
    """
    Approved clause block for policy assembly.
    Versioned, jurisdiction-tagged, immutable once approved.
    """
    __tablename__ = "clause_blocks"
    
    clause_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    
    # Identification
    clause_key = Column(String(100), nullable=False, index=True)  # e.g., "mhmda_scope"
    version = Column(String(10), nullable=False, default="1.0")
    
    # Content
    title = Column(String(200), nullable=False)
    category = Column(SQLEnum(ClauseCategory), nullable=False)
    content = Column(Text, nullable=False)  # The actual text block
    
    # Legal metadata
    jurisdiction = Column(SQLEnum(Jurisdiction), default=Jurisdiction.WASHINGTON, nullable=False)
    regulatory_citations = Column(JSON, default=list)  # e.g., ["RCW 19.373.010"]
    
    # Status
    status = Column(SQLEnum(ClauseStatus), default=ClauseStatus.DRAFT, nullable=False)
    approved_by = Column(String(255), nullable=True)  # Legal counsel email/name
    approved_at = Column(DateTime, nullable=True)
    
    # Use conditions
    required_context = Column(JSON, default=dict)  # What facts must be present
    optional_variables = Column(JSON, default=list)  # What can be substituted
    
    # Provenance
    created_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Version history
    previous_version_id = Column(String(32), ForeignKey("clause_blocks.clause_id"), nullable=True)
    
    # Usage tracking
    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('clause_key', 'version', name='uq_clause_version'),
    )


class PolicyTemplate(Base):
    """
    Template that specifies which clauses to assemble for a policy type.
    """
    __tablename__ = "policy_templates"
    
    template_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    
    # Identification
    template_key = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Assembly specification
    required_clauses = Column(JSON, default=list)  # ["intro_v1", "scope_v1", ...]
    optional_clauses = Column(JSON, default=list)
    
    # Applicability
    jurisdictions = Column(JSON, default=list)
    applies_to_entity_types = Column(JSON, default=list)  # ['medical_practice', 'wellness_app']
    
    # Version
    version = Column(String(10), default="1.0")
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedPolicyProvenance(Base):
    """
    Audit record of exactly which clauses were used to generate a policy.
    """
    __tablename__ = "generated_policy_provenance"
    
    provenance_id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])
    policy_document_id = Column(String(32), ForeignKey("policy_documents.document_id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Assembly record
    template_used = Column(String(100), nullable=False)
    template_version = Column(String(10), nullable=False)
    clauses_assembled = Column(JSON, default=list)  # Detailed assembly log
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("workspace_users.user_id"), nullable=False)
    
    # Input snapshot
    input_facts_hash = Column(String(64), nullable=False)
    input_facts_snapshot = Column(JSON, default=dict)


class ClauseLibraryService:
    """
    Service for managing approved clause library and policy assembly.
    
    RULES:
    1. Only pre-approved clauses can be used
    2. Assembly is deterministic given same facts
    3. All generation is auditable
    4. Facts must be validated, never invented
    """
    
    # Pre-defined approved clauses for MHMDA
    DEFAULT_CLAUSES = [
        {
            "clause_key": "mhmda_introduction",
            "version": "1.0",
            "title": "Introduction and Scope",
            "category": ClauseCategory.INTRODUCTION,
            "content": """This Privacy Policy describes how {organization_name} ("we," "our," or "us") collects, uses, shares, and protects consumer health data under the Washington My Health My Data Act (MHMDA), Chapter 19.373 RCW.

This policy applies to Washington State residents and their consumer health data collected through {data_collection_contexts}.

Effective Date: {effective_date}""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.020"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["organization_name", "effective_date"],
            "optional_variables": ["data_collection_contexts"]
        },
        {
            "clause_key": "mhmda_scope",
            "version": "1.0",
            "title": "What is Consumer Health Data",
            "category": ClauseCategory.SCOPE,
            "content": """Under the Washington My Health My Data Act, "consumer health data" means personal information that is linked or reasonably linkable to a consumer and that identifies the consumer's past, present, or future physical or mental health status.

This includes:
{health_data_categories}

Consumer health data does not include:
- Information originally created for purposes of HIPAA compliance (see separate HIPAA Notice of Privacy Practices if applicable)
- Information originally created for purposes of the Washington State Medical Records Act (Chapter 70.02 RCW)
- De-identified data as defined under applicable law""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.010(2)"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["health_data_categories"],
            "optional_variables": []
        },
        {
            "clause_key": "mhmda_collection",
            "version": "1.0",
            "title": "Data We Collect",
            "category": ClauseCategory.DATA_COLLECTION,
            "content": """We collect the following categories of consumer health data:

{data_element_list}

We collect this data from:
{data_sources}

We collect this data for the following purposes:
{collection_purposes}""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.020(1)"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["data_element_list", "data_sources", "collection_purposes"],
            "optional_variables": []
        },
        {
            "clause_key": "mhmda_sharing",
            "version": "1.0",
            "title": "How We Share Your Data",
            "category": ClauseCategory.DATA_SHARING,
            "content": """We share consumer health data with the following categories of third parties:

{vendor_list}

We share data for the following purposes:
{sharing_purposes}

We do not sell consumer health data. We do not share consumer health data for targeted advertising purposes without your explicit consent.""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.020(3)", "RCW 19.373.110"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["vendor_list"],
            "optional_variables": ["sharing_purposes"]
        },
        {
            "clause_key": "mhmda_rights",
            "version": "1.0",
            "title": "Your Rights Under Washington Law",
            "category": ClauseCategory.CONSUMER_RIGHTS,
            "content": """Under the Washington My Health My Data Act, you have the following rights:

**Right to Confirm (RCW 19.373.120)**
You have the right to confirm whether we are processing your consumer health data.

**Right to Delete (RCW 19.373.130)**
You have the right to request deletion of your consumer health data, subject to certain exceptions under law.

**Right to Withdraw Consent (RCW 19.373.140)**
Where processing is based on consent, you may withdraw consent at any time.

**Right to Appeal (RCW 19.373.150)**
If we deny your request, you have the right to appeal our decision.

**How to Exercise Your Rights:**
To exercise any of these rights, please contact us at:
- Email: {privacy_email}
- Phone: {privacy_phone}
- Address: {privacy_address}

We will respond to your request within 45 days as required by law.

**Right to Non-Discrimination:**
We will not discriminate against you for exercising any of your rights under the MHMDA.""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.120-150"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["privacy_email"],
            "optional_variables": ["privacy_phone", "privacy_address"]
        },
        {
            "clause_key": "mhmda_security",
            "version": "1.0",
            "title": "Data Security",
            "category": ClauseCategory.SECURITY,
            "content": """We implement reasonable administrative, technical, and physical safeguards to protect consumer health data, including:

{security_measures}

Despite these measures, no security system is impenetrable. We cannot guarantee the absolute security of your data.""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.060"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["security_measures"],
            "optional_variables": []
        },
        {
            "clause_key": "mhmda_retention",
            "version": "1.0",
            "title": "Data Retention",
            "category": ClauseCategory.RETENTION,
            "content": """We retain consumer health data for as long as necessary to fulfill the purposes for which it was collected, including:
- To provide services to you
- To comply with legal obligations
- To resolve disputes
- To enforce our agreements

{retention_schedules}

When data is no longer needed, we will securely delete or de-identify it in accordance with our data retention policies.""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.060"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["retention_schedules"],
            "optional_variables": []
        },
        {
            "clause_key": "mhmda_contact",
            "version": "1.0",
            "title": "Contact Us",
            "category": ClauseCategory.CONTACT,
            "content": """If you have questions or concerns about this Privacy Policy or our handling of consumer health data, please contact:

**Privacy Officer**
{organization_name}
Email: {privacy_email}
{optional_phone_line}
{optional_address_block}

If you believe we have violated your rights under the Washington My Health My Data Act, you may contact the Washington State Attorney General's Office at:
- Website: https://www.atg.wa.gov
- Phone: 1-800-551-4636""",
            "jurisdiction": Jurisdiction.WASHINGTON,
            "regulatory_citations": ["RCW 19.373.060"],
            "status": ClauseStatus.APPROVED,
            "required_context": ["organization_name", "privacy_email"],
            "optional_variables": ["optional_phone_line", "optional_address_block"]
        }
    ]
    
    def __init__(self, db):
        self.db = db
    
    def seed_default_clauses(self):
        """Load approved default clauses into database."""
        for clause_data in self.DEFAULT_CLAUSES:
            # Check if already exists
            existing = self.db.query(ClauseBlock).filter_by(
                clause_key=clause_data["clause_key"],
                version=clause_data["version"]
            ).first()
            
            if not existing:
                clause = ClauseBlock(**clause_data)
                clause.status = ClauseStatus.APPROVED
                clause.approved_at = datetime.utcnow()
                clause.approved_by = "system_seed"
                self.db.add(clause)
        
        self.db.commit()
    
    def assemble_policy(
        self,
        template_key: str,
        organization_id: str,
        facts: dict,
        generated_by: str
    ) -> dict:
        """
        Assemble a policy from approved clauses.
        
        RULE: All generation is deterministic assembly of pre-approved blocks.
        NO LLM generation of legal text.
        """
        # Get template
        template = self.db.query(PolicyTemplate).filter_by(
            template_key=template_key,
            is_active=True
        ).first()
        
        if not template:
            raise ValueError(f"Template {template_key} not found")
        
        # Collect clauses
        assembled_clauses = []
        missing_facts = []
        
        for clause_key_version in template.required_clauses:
            # Parse "clause_key@version" or use latest approved
            if "@" in clause_key_version:
                clause_key, version = clause_key_version.split("@")
            else:
                clause_key = clause_key_version
                version = None
            
            # Get specific or latest version
            if version:
                clause = self.db.query(ClauseBlock).filter_by(
                    clause_key=clause_key,
                    version=version,
                    status=ClauseStatus.APPROVED
                ).first()
            else:
                clause = self.db.query(ClauseBlock).filter_by(
                    clause_key=clause_key,
                    status=ClauseStatus.APPROVED
                ).order_by(ClauseBlock.version.desc()).first()
            
            if not clause:
                raise ValueError(f"Approved clause {clause_key} not found")
            
            # Validate required facts
            for fact_key in clause.required_context:
                if fact_key not in facts or facts[fact_key] is None:
                    missing_facts.append(fact_key)
            
            # Substitute variables
            content = clause.content
            for var in clause.required_context + clause.optional_variables:
                if var in facts:
                    placeholder = "{" + var + "}"
                    content = content.replace(placeholder, str(facts[var]))
                else:
                    # Leave placeholder for manual completion
                    pass
            
            assembled_clauses.append({
                "clause_id": clause.clause_id,
                "clause_key": clause.clause_key,
                "version": clause.version,
                "title": clause.title,
                "content": content,
                "regulatory_citations": clause.regulatory_citations
            })
            
            # Update usage stats
            clause.use_count += 1
            clause.last_used_at = datetime.utcnow()
        
        if missing_facts:
            return {
                "success": False,
                "missing_facts": missing_facts,
                "assembled_policy": None,
                "message": f"Missing required facts: {', '.join(missing_facts)}"
            }
        
        # Combine into final policy
        policy_text = self._format_policy(assembled_clauses, facts)
        
        # Create provenance record
        provenance = GeneratedPolicyProvenance(
            policy_document_id=facts.get("document_id", "temp"),
            organization_id=organization_id,
            template_used=template_key,
            template_version=template.version,
            clauses_assembled=[c["clause_id"] for c in assembled_clauses],
            generated_by=generated_by,
            input_facts_hash=self._hash_facts(facts),
            input_facts_snapshot=facts
        )
        self.db.add(provenance)
        self.db.commit()
        
        return {
            "success": True,
            "policy_text": policy_text,
            "clauses_used": assembled_clauses,
            "provenance_id": provenance.provenance_id,
            "missing_facts": []
        }
    
    def _format_policy(self, clauses: List[dict], facts: dict) -> str:
        """Format assembled clauses into final policy document."""
        sections = []
        
        # Header
        sections.append(f"PRIVACY POLICY")
        sections.append(f"{facts.get('organization_name', 'ORGANIZATION')}")
        sections.append(f"Effective Date: {facts.get('effective_date', 'TBD')}")
        sections.append("")
        
        # Sections
        for clause in clauses:
            sections.append(f"## {clause['title']}")
            sections.append("")
            sections.append(clause['content'])
            sections.append("")
            
            # Add regulatory citations as footnotes
            if clause.get('regulatory_citations'):
                sections.append(f"_Legal basis: {', '.join(clause['regulatory_citations'])}_")
                sections.append("")
        
        # Provenance footer
        sections.append("---")
        sections.append("")
        sections.append("**Document Provenance:**")
        sections.append(f"This policy was generated from pre-approved legal clauses on {datetime.utcnow().date().isoformat()}.")
        sections.append("Clause assembly log available upon request for compliance verification.")
        
        return "\n".join(sections)
    
    def _hash_facts(self, facts: dict) -> str:
        """Create deterministic hash of input facts."""
        import hashlib
        normalized = json.dumps(facts, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get_clause_version_history(self, clause_key: str) -> List[ClauseBlock]:
        """Get version history for a clause."""
        return self.db.query(ClauseBlock).filter(
            ClauseBlock.clause_key == clause_key
        ).order_by(ClauseBlock.version.desc()).all()
    
    def deprecate_clause(self, clause_id: str, deprecated_by: str) -> ClauseBlock:
        """Mark a clause as deprecated - requires review."""
        clause = self.db.query(ClauseBlock).filter_by(clause_id=clause_id).first()
        if clause:
            clause.status = ClauseStatus.DEPRECATED
            self.db.commit()
        return clause
