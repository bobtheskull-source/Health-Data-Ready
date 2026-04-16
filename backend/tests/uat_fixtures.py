"""
UAT Test Fixtures and Scenarios
End-to-end user acceptance test data and scenarios.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List
import uuid


class UATScenarios:
    """
    Predefined UAT scenarios for MHMDA compliance validation.
    Each scenario represents a realistic business situation.
    """
    
    # Scenario 1: Small Medical Practice
    SMALL_MEDICAL_PRACTICE = {
        "name": "Small Medical Practice",
        "description": "Family medicine practice with 3 providers, EHR system, patient portal",
        "business_type": "medical_practice",
        "employee_count": 15,
        "data_volume_estimate": "10,000 patient records",
        
        "applicability_answers": {
            "collects_health_data": True,
            "processes_wa_residents": True,
            "health_data_sources": ["patient_forms", "ehr", "lab_results", "billing"],
            "consumer_facing": True,
            "revenue_threshold": "under_25m"
        },
        
        "data_elements": [
            {"name": "patient_name", "category": "consumer_profile", "source": "intake_form"},
            {"name": "date_of_birth", "category": "consumer_profile", "source": "intake_form"},
            {"name": "ssn", "category": "identification", "source": "insurance_verification"},
            {"name": "diagnosis_codes", "category": "health_biometric", "source": "ehr"},
            {"name": "prescriptions", "category": "health_biometric", "source": "ehr"},
            {"name": "insurance_id", "category": "financial", "source": "billing"},
            {"name": "payment_card", "category": "financial", "source": "billing"},
            {"name": "email", "category": "consumer_profile", "source": "portal_registration"},
            {"name": "phone", "category": "consumer_profile", "source": "intake_form"},
            {"name": "emergency_contact", "category": "consumer_profile", "source": "intake_form"},
        ],
        
        "vendors": [
            {
                "name": "Epic Systems",
                "purpose": "EHR hosting",
                "processes_health_data": True,
                "data_types": ["phi", "diagnoses", "medications"],
                "location": "US-WA"
            },
            {
                "name": "Square Payments",
                "purpose": "Payment processing",
                "processes_health_data": False,
                "data_types": ["payment_cards", "billing_addresses"],
                "location": "US"
            },
            {
                "name": "Mailchimp",
                "purpose": "Newsletter marketing",
                "processes_health_data": False,
                "is_ad_tech": False,
                "data_types": ["email", "names"],
                "consent_required": True
            }
        ],
        
        "rights_request_scenarios": [
            {
                "type": "access_request",
                "consumer_name": "Jane Doe",
                "request_date": datetime.now() - timedelta(days=10),
                "expected_deadline": datetime.now() + timedelta(days=35),
                "status": "in_progress"
            },
            {
                "type": "deletion_request",
                "consumer_name": "John Smith",
                "request_date": datetime.now() - timedelta(days=50),
                "extended": True,
                "extension_reason": "verification_required",
                "expected_deadline": datetime.now() + timedelta(days=40),
                "status": "extended"
            }
        ]
    }
    
    # Scenario 2: Wellness/Fitness App
    WELLNESS_APP = {
        "name": "Wellness Tracking App",
        "description": "Mobile app for fitness tracking, nutrition logging, menstrual cycle tracking",
        "business_type": "consumer_app",
        "employee_count": 8,
        "data_volume_estimate": "50,000 active users",
        
        "applicability_answers": {
            "collects_health_data": True,
            "processes_wa_residents": True,
            "health_data_sources": ["user_input", "device_sensors", "third_party_apis"],
            "consumer_facing": True,
            "revenue_threshold": "under_25m"
        },
        
        "data_elements": [
            {"name": "weight", "category": "health_biometric", "source": "user_input"},
            {"name": "heart_rate", "category": "health_biometric", "source": "device_sensor"},
            {"name": "menstrual_cycle", "category": "health_reproductive", "source": "user_input"},
            {"name": "sleep_data", "category": "health_biometric", "source": "device_sensor"},
            {"name": "location_workout", "category": "health_precise_geo", "source": "gps"},
            {"name": "food_log", "category": "behavior_online", "source": "user_input"},
            {"name": "email", "category": "consumer_profile", "source": "registration"},
            {"name": "device_id", "category": "device_tech", "source": "app_install"},
            {"name": "advertising_id", "category": "behavior_cross_site", "source": "third_party_sdk"},
        ],
        
        "vendors": [
            {
                "name": "Firebase Analytics",
                "purpose": "App analytics",
                "processes_health_data": True,
                "is_ad_tech": False,
                "is_analytics": True,
                "data_types": ["usage_patterns", "device_id"]
            },
            {
                "name": "Facebook SDK",
                "purpose": "Social sharing",
                "processes_health_data": False,
                "is_ad_tech": True,
                "is_analytics": True,
                "data_types": ["advertising_id", "app_events"],
                "consent_required": True,
                "mhmda_risk": "High - ad tech with health context"
            },
            {
                "name": "AWS S3",
                "purpose": "Data storage",
                "processes_health_data": True,
                "data_types": ["all_user_data"],
                "location": "US-WA"
            }
        ],
        
        "compliance_challenges": [
            "Precise geolocation tied to health activities (gyms, clinics)",
            "Reproductive health data requires enhanced protection",
            "Advertising SDK may infer health status from app usage",
            "Device ID linkage to health data"
        ]
    }
    
    # Scenario 3: Pharmacy Chain (Multi-location)
    PHARMACY_CHAIN = {
        "name": "Regional Pharmacy Chain",
        "description": "12-location pharmacy chain with online prescription refills",
        "business_type": "pharmacy",
        "employee_count": 120,
        "data_volume_estimate": "200,000 active patients",
        "mhmda_exempt": False,  # HIPAA-covered but MHMDA still applies to non-HIPAA activities
        
        "hipaa_activities": [
            "Prescription processing",
            "Insurance billing",
            "Patient counseling records"
        ],
        
        "mhmda_covered_activities": [
            "Loyalty program enrollment",
            "Marketing email campaigns",
            "Website analytics",
            "Third-party advertising",
            "Mobile app usage tracking"
        ],
        
        "data_elements": [
            {"name": "prescription_history", "category": "hipaa_exempt", "note": "Covered by HIPAA"},
            {"name": "loyalty_id", "category": "consumer_profile", "note": "MHMDA applies"},
            {"name": "purchase_history", "category": "commercial", "note": "OTC purchases may indicate health"},
            {"name": "website_visits", "category": "behavior_online", "note": "MHMDA applies"},
            {"name": "marketing_preferences", "category": "consumer_profile", "note": "MHMDA applies"},
        ]
    }
    
    # Scenario 4: Mental Health Platform
    MENTAL_HEALTH_PLATFORM = {
        "name": "Mental Health Teletherapy Platform",
        "description": "Video therapy platform with booking, messaging, and notes",
        "business_type": "mental_health_service",
        "employee_count": 25,
        
        "sensitive_data_categories": [
            "mental_health_diagnoses",
            "therapy_session_notes",
            "medication_adherence",
            "crisis_intervention_logs"
        ],
        
        "high_risk_vendors": [
            {
                "name": "Zoom",
                "purpose": "Video sessions",
                "risk": "Recording features, data residency"
            },
            {
                "name": "Intercom",
                "purpose": "Customer support chat",
                "risk": "Chat content may include health disclosures"
            }
        ],
        
        "rights_request_scenarios": [
            {
                "type": "access_request_complex",
                "description": "Patient requests all data including session transcripts",
                "challenge": "Need to balance access with provider notes protection"
            },
            {
                "type": "emergency_hold",
                "description": "Deletion requested during active safety concern",
                "challenge": "MHMDA allows retention if required for safety"
            }
        ]
    }


class TestDataGenerator:
    """Generate realistic test data for UAT."""
    
    @staticmethod
    def generate_organization(org_type: str = "medical_practice") -> Dict:
        """Generate a complete test organization with all entities."""
        scenario = UATScenarios.SMALL_MEDICAL_PRACTICE
        
        return {
            "organization_id": str(uuid.uuid4()),
            "tenant_id": f"tenant-{uuid.uuid4().hex[:8]}",
            "name": scenario["name"],
            "slug": f"test-{org_type}-{uuid.uuid4().hex[:6]}",
            "business_type": scenario["business_type"],
            "applicability": scenario["applicability_answers"],
            "data_elements": [
                {**de, "element_id": str(uuid.uuid4())[:8]}
                for de in scenario["data_elements"]
            ],
            "vendors": [
                {**v, "vendor_id": str(uuid.uuid4())[:8]}
                for v in scenario["vendors"]
            ],
            "rights_requests": scenario.get("rights_request_scenarios", [])
        }
    
    @staticmethod
    def generate_consumer_request(request_type: str = "access") -> Dict:
        """Generate a realistic consumer rights request."""
        request_types = ["access", "deletion", "correction", "portability"]
        
        return {
            "request_id": f"REQ-{uuid.uuid4().hex[:12].upper()}",
            "type": request_type if request_type in request_types else "access",
            "consumer_email": f"consumer{uuid.uuid4().hex[:6]}@example.com",
            "consumer_name": "Test Consumer",
            "received_at": datetime.now().isoformat(),
            "status": "pending",
            "verification_status": "unverified",
            "data_categories_requested": "all"
        }
    
    @staticmethod
    def generate_audit_trail(days: int = 30) -> List[Dict]:
        """Generate realistic audit events."""
        events = []
        base_date = datetime.now() - timedelta(days=days)
        
        action_types = [
            "login", "logout", "data_element_create", "data_element_update",
            "vendor_add", "rights_request_received", "rights_request_completed",
            "policy_generated", "consent_given", "consent_withdrawn"
        ]
        
        for day in range(days):
            for _ in range(5):  # 5 events per day
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "action": action_types[hash(str(day + _)) % len(action_types)],
                    "timestamp": (base_date + timedelta(days=day, hours=hash(str(_)) % 24)).isoformat(),
                    "user_id": f"user-{hash(str(day)) % 5}",
                    "entity_type": "data_element" if "data" in action_types[0] else "user"
                })
        
        return events
    
    @staticmethod
    def generate_policy_versions() -> List[Dict]:
        """Generate policy version history for testing."""
        return [
            {
                "version": "1.0",
                "effective_date": "2024-01-01",
                "changes": "Initial MHMDA compliance policy",
                "reviewed_by": "legal@example.com"
            },
            {
                "version": "1.1",
                "effective_date": "2024-06-15",
                "changes": "Added new vendor disclosure requirements",
                "reviewed_by": "legal@example.com"
            },
            {
                "version": "2.0",
                "effective_date": "2024-12-01",
                "changes": "Comprehensive rewrite for regulatory changes",
                "reviewed_by": "external-counsel@lawfirm.com"
            }
        ]


# UAT Test Scripts
UAT_TEST_SCRIPTS = {
    "onboarding_flow": """
    Onboarding Acceptance Test
    ==========================
    
    1. Create new organization
       - Navigate to /signup
       - Enter valid business details
       - Expected: Organization created, tenant isolated
    
    2. Complete Applicability Assessment
       - Answer all 10 applicability questions
       - Expected: Score calculated, exemption status clear
    
    3. Review Applicability Report
       - Verify summary shows MHMDA applies
       - Verify risk areas highlighted
       - Expected: Actionable next steps displayed
    
    4. Invite Team Members
       - Add 2 staff editors
       - Add 1 read-only reviewer
       - Expected: Invitations sent, roles assigned
    
    Success Criteria: Organization fully configured in < 15 minutes
    """,
    
    "data_inventory_workflow": """
    Data Inventory Acceptance Test
    ==============================
    
    1. Upload CSV with 50 data fields
       - Format: field_name,field_type,sample_value
       - Expected: All fields parsed, classifications suggested
    
    2. Review Auto-classifications
       - Verify confidence scores displayed
       - Expected: High confidence > 0.8 marked auto-approved
    
    3. Manual Correction
       - Find 5 incorrectly classified fields
       - Apply correct categories
       - Expected: Changes saved, confidence updated
    
    4. Export Inventory
       - Generate PDF report
       - Verify MHMDA categories correct
       - Expected: Professional output suitable for legal review
    
    Success Criteria: 50 fields processed in < 10 minutes
    """,
    
    "rights_request_workflow": """
    Rights Request Acceptance Test
    ==============================
    
    1. Receive Access Request
       - Consumer emails privacy@org.com
       - Staff creates request in system
       - Expected: Deadline calculated (45 days)
    
    2. Verify Identity
       - Request ID verification
       - Upload verification document
       - Expected: Status changes to identity_verified
    
    3. Generate Data Export
       - Run data inventory query
       - Generate consumer disclosure bundle
       - Expected: ZIP created with JSON + PDF
    
    4. Send Response
       - Log communication
       - Mark request complete
       - Expected: Audit trail complete, deadline met
    
    Success Criteria: Request processed within 45-day deadline
    """
}


def export_uat_data(output_path: str = "uat_test_data.json"):
    """Export all UAT data to JSON file."""
    data = {
        "scenarios": {
            "small_medical_practice": UATScenarios.SMALL_MEDICAL_PRACTICE,
            "wellness_app": UATScenarios.WELLNESS_APP,
            "pharmacy_chain": UATScenarios.PHARMACY_CHAIN,
            "mental_health_platform": UATScenarios.MENTAL_HEALTH_PLATFORM
        },
        "test_scripts": UAT_TEST_SCRIPTS,
        "generated_fixtures": {
            "organization": TestDataGenerator.generate_organization(),
            "consumer_request": TestDataGenerator.generate_consumer_request(),
            "audit_trail_sample": TestDataGenerator.generate_audit_trail(days=7),
            "policy_versions": TestDataGenerator.generate_policy_versions()
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return output_path


if __name__ == "__main__":
    path = export_uat_data()
    print(f"UAT test data exported to: {path}")
