# Health Data Ready - Developer Documentation

## Project Overview

Washington MHMDA compliance platform for medical-adjacent small businesses. FastAPI backend with deterministic compliance logic.

## Directory Structure

```
backend/
├── app/
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── __init__.py      # Organization, WorkspaceUser, AuditEvent
│   │   ├── questionnaire.py # Applicability assessment
│   │   ├── vendors.py       # Vendor register
│   │   ├── data_elements.py # Data inventory
│   │   ├── rights_requests.py # Consumer rights workflow
│   │   ├── evidence.py      # Audit evidence vault
│   │   └── ui.py            # Web app UI models
│   ├── services/         # Business logic
│   │   ├── applicability_engine.py  # MHMDA trigger detection
│   │   ├── field_classifier.py      # Data categorization
│   │   ├── policy_generator.py      # Template-based policy generation
│   │   ├── rights_timeline.py       # Deadline calculation
│   │   ├── evidence_vault.py        # Immutable audit storage
│   │   ├── bundle_generator.py      # Export packaging
│   │   └── llm_service.py           # LLM abstraction (assist only)
│   ├── routers/          # API endpoints
│   ├── core/             # Auth, config, middleware, database
│   └── main.py           # Application entry
├── tests/                # Pytest suite
│   ├── test_security.py     # Penetration test fixtures
│   └── uat_fixtures.py      # UAT scenarios
└── docs/                 # Documentation
    └── operations_runbook.md
```

## Key Design Decisions

### 1. Rules-First, Deterministic Legal Logic

```python
# CORRECT: Deterministic rules engine
final_category = rules_engine.classify(field_name)

# INCORRECT: LLM generates legal conclusion
category = llm.generate("What category is this field?")  # NEVER DO THIS
```

LLM is used ONLY for:
- Semantic field name suggestions
- Vendor description parsing
- Confidence boost when rules and LLM agree

### 2. Tenant Isolation

Every table includes `tenant_id` (string) and `organization_id` (UUID):

```python
class DataElement(Base):
    organization_id = Column(ForeignKey("organizations.id"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("organizations.tenant_id"), nullable=False)
```

Enforced at dependency injection layer in `auth.py`.

### 3. Audit Trail Requirements

Every state change creates `AuditEvent`:

```python
audit_event = AuditEvent(
    action=ActionType.CREATE,
    entity_type="data_element",
    entity_id=str(element.id),
    before_state=None,
    after_state=element.to_dict(),
    # ... metadata
)
```

Evidence Vault adds tamper-evident hashing for compliance documents.

### 4. Password Handling

Watch for this in copy-pasted configs:

```python
# WRONG (often in template comments):
# SECRET_KEY = "change-me-in-production"

# RIGHT (active configuration):
SECRET_KEY = os.getenv("SECRET_KEY")  # Never commit secrets
```

## Development Workflow

### Setting Up

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit: DATABASE_URL, SECRET_KEY (generate: openssl rand -hex 32)

# Database setup
alembic upgrade head

# Run dev server
uvicorn app.main:app --reload
```

### Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Security tests
pytest tests/test_security.py -v

# Integration tests (requires test DB)
pytest tests/integration/ --integration

# UAT scenario validation
python -c "from tests.uat_fixtures import export_uat_data; export_uat_data()"
```

### Code Style

```bash
# Format
black app/ tests/

# Lint
flake8 app/ tests/

# Type check
mypy app/
```

## MHMDA Compliance Logic

### Applicability Engine

See `services/applicability_engine.py`:

```python
engine = ApplicabilityEngine()
result = engine.assess(questionnaire_responses)

# Returns:
# - mhmda_applies: bool
# - confidence: "high" | "medium" | "low"
# - reasoning: list of trigger factors
# - exemption_factors: list of potential exemptions
```

### Rights Request Timeline

See `services/rights_timeline.py`:

```python
timeline = RightsTimelineEngine()
deadline = timeline.calculate_deadline(
    request_date=datetime.now(),
    extension_granted=False
)
# Returns: deadline, days_remaining, status flags
```

### Evidence Vault

See `services/evidence_vault.py`:

```python
vault = EvidenceVault()
record = vault.store(
    content=bytes,
    evidence_type=EvidenceType.DELETION_CERTIFICATE,
    # ... metadata
)
# record includes: content_hash, chain_hash, storage_key
```

## API Patterns

### Standard Response Format

```python
{
    "success": true,
    "data": { ... },
    "meta": {
        "request_id": "uuid",
        "timestamp": "iso8601"
    }
}
```

### Error Format

```python
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "...",
        "details": { ... }
    },
    "meta": { ... }
}
```

### Tenant Isolation Pattern

```python
@router.get("/data-elements")
async def list_elements(
    current_user = Depends(get_current_user),
    tenant_id = Depends(get_tenant_id)  # Enforced by auth
):
    return db.query(DataElement).filter(
        DataElement.tenant_id == tenant_id
    ).all()
```

## Adding New Features

### 1. Model Layer

```python
# backend/app/models/new_feature.py
class NewFeature(Base):
    __tablename__ = "new_features"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id = Column(ForeignKey("organizations.id"), nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    # ... fields
```

### 2. Service Layer

```python
# backend/app/services/new_feature_service.py
class NewFeatureService:
    def __init__(self, db, tenant_id):
        self.db = db
        self.tenant_id = tenant_id
    
    def create(self, data: dict) -> NewFeature:
        # Business logic
        pass
```

### 3. Router

```python
# backend/app/routers/new_feature.py
@router.post("/", status_code=201)
async def create(
    data: NewFeatureCreate,
    service: NewFeatureService = Depends(get_service),
    user = Depends(require_role(Role.STAFF_EDITOR))
):
    return service.create(data)
```

### 4. Migration

```bash
alembic revision --autogenerate -m "Add new_feature table"
alembic upgrade head
```

### 5. Tests

```python
# backend/tests/test_new_feature.py
def test_create_feature(client, auth_headers):
    response = client.post("/api/v1/new-features", json={...})
    assert response.status_code == 201
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing key (32+ bytes) |
| `OPENAI_API_KEY` | No | For LLM classification assist |
| `ANTHROPIC_API_KEY` | No | Alternative LLM provider |
| `S3_BUCKET` | No | Evidence vault storage |
| `AWS_ACCESS_KEY_ID` | No | S3 credentials |
| `LLM_CLASSIFICATION_ENABLED` | No | Default: true |

## Common Issues

### Import Errors
```bash
# Ensure PYTHONPATH includes backend/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

### Database Connection
```bash
# Check connection
psql $DATABASE_URL -c "SELECT version();"
```

### Migration Conflicts
```bash
# Reset to baseline (dev only!)
alembic downgrade base
alembic upgrade head
```

## Contributing

1. Create feature branch: `git checkout -b feature/HDR-XXX`
2. Write tests first
3. Implement feature
4. Run full test suite
5. Submit PR with compliance impact notes

## Resources

- **MHMDA Text**: RCW Chapter 19.373
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy**: https://docs.sqlalchemy.org
