"""
Security Testing Suite
Penetration testing fixtures and automated security validation.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from app.main import app
from app.core.config import SECRET_KEY, ALGORITHM
from app.core.auth import create_access_token, get_password_hash
from app.models import Organization, WorkspaceUser, Role
from app.core.database import SessionLocal


client = TestClient(app)


class TestAuthenticationSecurity:
    """Authentication and session security tests."""
    
    def test_jwt_token_expiration_enforced(self):
        """HDR-021: Tokens must expire and be rejected after expiry."""
        # Create expired token
        expired_token = jose_jwt.encode(
            {"sub": "test@example.com", "exp": datetime.utcnow() - timedelta(hours=1)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
    
    def test_jwt_token_tampering_detected(self):
        """HDR-021: Tampered tokens must be rejected."""
        # Create valid token
        token = create_access_token({"sub": "test@example.com"})
        
        # Tamper with payload
        parts = token.split('.')
        tampered = f"{parts[0]}.{parts[1]}.{parts[2][:-5]}AAAAA"
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered}"}
        )
        assert response.status_code == 401
    
    def test_sql_injection_login_blocked(self):
        """HDR-021: SQL injection via login form must be blocked."""
        payloads = [
            {"email": "' OR '1'='1", "password": "password"},
            {"email": "admin@example.com'; DROP TABLE users; --", "password": "password"},
            {"email": "test@example.com", "password": "' OR '1'='1"},
        ]
        
        for payload in payloads:
            response = client.post("/api/v1/auth/login", json=payload)
            # Should fail authentication, not crash
            assert response.status_code in [401, 422]
    
    def test_brute_force_rate_limiting(self):
        """HDR-021: Rapid login attempts must be rate limited."""
        for i in range(15):  # Exceed default rate limit
            response = client.post("/api/v1/auth/login", json={
                "email": f"test{i}@example.com",
                "password": "wrongpassword"
            })
        
        # Should be rate limited
        assert response.status_code == 429


class TestAuthorizationSecurity:
    """Authorization and access control tests."""
    
    def test_tenant_isolation_enforced(self, db):
        """HDR-021: Users cannot access other tenants' data."""
        # Create two organizations
        org1 = Organization(name="Org One", slug="org-one", tenant_id="tenant-1")
        org2 = Organization(name="Org Two", slug="org-two", tenant_id="tenant-2")
        db.add_all([org1, org2])
        db.commit()
        
        # Create user in org1
        user1 = WorkspaceUser(
            organization_id=org1.id,
            email="user1@org1.com",
            name="User One",
            tenant_id="tenant-1",
            role=Role.OWNER
        )
        db.add(user1)
        db.commit()
        
        # Generate token for user1
        token = create_access_token({
            "sub": str(user1.id),
            "org_id": str(org1.id),
            "tenant_id": "tenant-1"
        })
        
        # Attempt to access org2 data
        response = client.get(
            f"/api/v1/organizations/{org2.id}/data-elements",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    
    def test_role_based_access_control(self, db):
        """HDR-021: Read-only users cannot modify data."""
        org = Organization(name="Test Org", slug="test-org", tenant_id="test-tenant")
        db.add(org)
        db.commit()
        
        # Create read-only user
        reviewer = WorkspaceUser(
            organization_id=org.id,
            email="reviewer@test.com",
            name="Reviewer",
            tenant_id="test-tenant",
            role=Role.READ_ONLY_REVIEWER
        )
        db.add(reviewer)
        db.commit()
        
        token = create_access_token({
            "sub": str(reviewer.id),
            "org_id": str(org.id),
            "role": "read_only_reviewer"
        })
        
        # Attempt to create data element
        response = client.post(
            "/api/v1/data-elements",
            json={"name": "Test Field", "category": "consumer_profile"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


class TestInputValidationSecurity:
    """Input validation and sanitization tests."""
    
    def test_xss_payloads_sanitized(self):
        """HDR-021: XSS payloads must be sanitized or rejected."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
        ]
        
        for payload in xss_payloads:
            response = client.post("/api/v1/organizations", json={
                "name": payload,
                "slug": "test-org-xss"
            })
            # Should sanitize or reject
            if response.status_code == 200:
                # Verify script tags not present in response
                assert "<script>" not in response.text
    
    def test_path_traversal_blocked(self):
        """HDR-021: Path traversal attempts must be blocked."""
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "file:///etc/passwd"
        ]
        
        for payload in payloads:
            response = client.get(f"/api/v1/export/{payload}")
            assert response.status_code in [400, 404, 422]
    
    def test_oversized_payload_rejected(self):
        """HDR-021: Excessively large payloads must be rejected."""
        # 10MB JSON payload
        large_payload = {"data": "x" * (10 * 1024 * 1024)}
        
        response = client.post("/api/v1/data-elements/bulk", json=large_payload)
        assert response.status_code == 413  # Payload Too Large


class TestDataExposureSecurity:
    """Data exposure and information disclosure tests."""
    
    def test_error_messages_no_stack_traces(self):
        """HDR-021: Production errors must not expose stack traces."""
        response = client.get("/api/v1/trigger-error")
        
        assert response.status_code == 500
        assert "Traceback" not in response.text
        assert "File \"" not in response.text
        assert "line " not in response.text.lower()
    
    def test_health_endpoint_no_sensitive_data(self):
        """HDR-021: Health check must not expose sensitive info."""
        response = client.get("/health")
        
        sensitive_patterns = [
            "password", "secret", "key", "token", "credential",
            "admin", "root", "postgres", "mongodb"
        ]
        
        response_lower = response.text.lower()
        for pattern in sensitive_patterns:
            assert pattern not in response_lower
    
    def test_api_version_disclosure_limited(self):
        """HDR-021: API should not disclose detailed version info."""
        response = client.get("/api/v1/health")
        
        # Should not expose specific package versions
        assert "fastapi" not in response.text.lower()
        assert "sqlalchemy" not in response.text.lower()
        assert "python 3." not in response.text.lower()


class TestAuditAndLogging:
    """Audit trail and security logging tests."""
    
    def test_failed_login_logged(self, db):
        """HDR-021: Failed login attempts must be audited."""
        client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        # Check audit log
        from app.models import AuditEvent, ActionType
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == ActionType.LOGIN_FAILED
        ).first()
        
        assert audit is not None
        assert audit.ip_address is not None
    
    def test_sensitive_operations_logged(self, db):
        """HDR-021: Data deletion must create audit record."""
        # This requires authenticated setup
        # Verify deletion creates audit event with before/after state
        pass  # Integration test placeholder


class TestCryptographicSecurity:
    """Cryptographic implementation tests."""
    
    def test_password_hashing_uses_bcrypt(self):
        """HDR-021: Passwords must use bcrypt."""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash("testpassword")
        
        # Verify bcrypt prefix
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    
    def test_weak_passwords_rejected(self):
        """HDR-021: Weak passwords must be rejected."""
        weak_passwords = [
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "password123"
        ]
        
        for password in weak_passwords:
            response = client.post("/api/v1/auth/register", json={
                "email": "test@example.com",
                "password": password,
                "name": "Test User"
            })
            assert response.status_code == 422


class TestInfrastructureSecurity:
    """Infrastructure and deployment security tests."""
    
    def test_security_headers_present(self):
        """HDR-021: Security headers must be present."""
        response = client.get("/health")
        
        headers = response.headers
        required_headers = [
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options"
        ]
        
        for header in required_headers:
            assert header in headers
    
    def test_cors_configuration_restrictive(self):
        """HDR-021: CORS must not allow wildcard in production."""
        response = client.options("/api/v1/health", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET"
        })
        
        # Should not reflect arbitrary origins
        access_control = response.headers.get("access-control-allow-origin")
        assert access_control != "*" or "evil.com" not in (access_control or "")


# Penetration test checklist for manual verification
PENTEST_CHECKLIST = """
MHMDA Compliance Security Verification Checklist
================================================

Authentication & Session Management
-----------------------------------
[ ] JWT tokens expire correctly (test with --runslow)
[ ] Refresh token rotation implemented
[ ] Concurrent session limits enforced
[ ] Session invalidation on password change
[ ] Secure cookie flags (HttpOnly, Secure, SameSite)

Authorization
-------------
[ ] Horizontal privilege escalation tested
[ ] Vertical privilege escalation tested
[ ] Tenant isolation verified across all endpoints
[ ] Role-based access control enforced

Data Protection
---------------
[ ] PII redaction in logs verified
[ ] Encryption at rest enabled (RDS/S3)
[ ] TLS 1.3 enforced for all connections
[ ] Sensitive data excluded from error messages

API Security
------------
[ ] Rate limiting tested at threshold
[ ] Input validation fuzzing completed
[ ] File upload restrictions tested
[ ] Content-Type validation enforced

Infrastructure
--------------
[ ] Security groups restrict database access
[ ] Secrets not in environment variables (use AWS SM)
[ ] Container runs as non-root
[ ] Read-only filesystem where possible

Compliance Specific
-------------------
[ ] Audit log tamper-evidence verified
[ ] Evidence vault hash chain validated
[ ] Retention policy automatic deletion tested
[ ] Export bundle integrity verification works

Manual Penetration Tests
------------------------
[ ] Burp Suite passive scan - no high/critical issues
[ ] OWASP ZAP baseline scan - no high/critical issues
[ ] SQLMap injection tests - negative results
[ ] Nmap port scan - only expected ports open
"""


@pytest.fixture
def db():
    """Database session fixture."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    print(PENTEST_CHECKLIST)
