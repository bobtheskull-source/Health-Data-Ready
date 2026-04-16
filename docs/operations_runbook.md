# Health Data Ready - Operations Documentation

## Quick Start (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/bobtheskull-source/Health-Data-Ready.git
cd Health-Data-Ready

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit: DATABASE_URL, SECRET_KEY, S3_BUCKET

# 3. Start services
docker-compose up -d

# 4. Run migrations
docker-compose exec api alembic upgrade head

# 5. Create admin user
docker-compose exec api python scripts/create_admin.py

# Access: http://localhost:8000/docs
```

---

## System Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Web Frontend  │────▶│  FastAPI API │────▶│  PostgreSQL │
│   (GitHub Pages)│     │              │     │  (Data)     │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   S3/MinIO   │
                        │(Evidence Vault)│
                        └──────────────┘
```

### Component Responsibilities

| Component | Purpose | Scaling |
|-----------|---------|---------|
| GitHub Pages | Static UI delivery | CDN-backed |
| FastAPI Workers | API request handling | Horizontal (K8s) |
| PostgreSQL | Transactional data | Read replicas |
| S3/MinIO | Immutable audit evidence | Unlimited |

---

## Daily Operations

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/health/db

# Full system check
curl http://localhost:8000/health/complete
```

### Log Monitoring

```bash
# View API logs
docker-compose logs -f api

# View error rate (last hour)
docker-compose exec api python scripts/log_analysis.py --errors --since=1h

# Audit log query
docker-compose exec db psql -U postgres -d healthdata -c \
  "SELECT action, COUNT(*) FROM audit_events WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY action;"
```

### Backup Procedures

```bash
# Database backup
pg_dump $DATABASE_URL | gzip > backup-$(date +%Y%m%d).sql.gz

# Evidence vault sync
aws s3 sync s3://health-data-ready-evidence/ /backups/evidence/

# Automated daily backup (cron)
0 2 * * * cd /opt/health-data-ready && ./scripts/backup.sh >> /var/log/hdr-backup.log 2>&1
```

---

## Incident Response

### Severity Levels

| Level | Examples | Response Time |
|-------|----------|---------------|
| P1 | Data breach, system down | 15 min |
| P2 | Partial outage, data loss risk | 1 hour |
| P3 | Performance degradation | 4 hours |
| P4 | Non-critical bugs | 24 hours |

### P1 Incident Response

1. **Immediate (0-15 min)**
   ```bash
   # Notify team
   # Switch to maintenance mode if needed
   curl -X POST http://localhost:8000/admin/maintenance-mode \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"enabled": true}'
   ```

2. **Assessment (15-45 min)**
   - Review audit logs for scope
   - Check evidence vault integrity: `python scripts/verify_evidence_chain.py`
   - Determine if consumer notification required (72 hours under MHMDA)

3. **Containment (45-90 min)**
   - Revoke compromised tokens
   - Isolate affected tenant(s)
   - Preserve evidence per RCW 19.373.060

4. **Recovery (90+ min)**
   - Restore from verified backup
   - Verify system integrity
   - Document actions taken

### Contact Escalation

| Order | Role | Contact | When |
|-------|------|---------|------|
| 1 | On-call Engineer | PagerDuty | All incidents |
| 2 | Security Lead | security@example.com | P1-P2 |
| 3 | Legal Counsel | counsel@lawfirm.com | Data breach |
| 4 | PR/Communications | pr@example.com | External disclosure needed |

---

## Compliance Procedures

### MHMDA Response SLA Monitoring

```bash
# Check overdue requests
docker-compose exec db psql -U postgres -d healthdata -c "
  SELECT request_id, type, received_at, deadline, NOW() - deadline as overdue_by
  FROM rights_requests
  WHERE status != 'completed' AND deadline < NOW() + INTERVAL '7 days';
"

# Weekly compliance report
docker-compose exec api python scripts/compliance_report.py --week
```

### Evidence Retention

| Evidence Type | Retention Period | Destruction After |
|---------------|------------------|-------------------|
| Identity verification | 7 years | Manual review required |
| Processing logs | 7 years | Auto-delete after retention |
| Consumer communications | 7 years | Manual review required |
| Deletion certificates | Permanent | Never |

### Regulatory Export

```bash
# Generate audit bundle for AG inspection
python scripts/generate_audit_bundle.py \
  --organization-id $ORG_ID \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --output /exports/ag-inspection-2024.zip

# Verify bundle integrity
python scripts/verify_bundle.py --bundle /exports/ag-inspection-2024.zip
```

---

## Deployment

### Environments

| Environment | URL | Database |
|-------------|-----|----------|
| Local | http://localhost:8000 | Docker PostgreSQL |
| Staging | https://staging.hdr.example.com | RDS staging |
| Production | https://api.hdr.example.com | RDS production |

### Deployment Checklist

```bash
# Pre-deployment
git checkout main
git pull origin main
./scripts/run_tests.sh
./scripts/security_scan.sh

# Deployment
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3

# Post-deployment
./scripts/smoke_tests.sh https://api.hdr.example.com
./scripts/verify_health.sh https://api.hdr.example.com
```

### Database Migrations

```bash
# Dry run
alembic upgrade head --sql

# Execute with backup
./scripts/migrate_with_backup.sh

# Rollback (if needed)
alembic downgrade -1
```

---

## Troubleshooting

### Common Issues

**Issue:** API returns 500 errors
```bash
# Check logs
docker-compose logs api | tail -100

# Check database connection
docker-compose exec api python -c "from app.database import engine; print(engine.connect())"

# Restart service
docker-compose restart api
```

**Issue:** Evidence vault verification fails
```bash
# Check chain integrity
python scripts/verify_chain.py --organization-id $ORG_ID

# Repair (if chain broken)
python scripts/rebuilding_chain.py --organization-id $ORG_ID --from-date 2024-01-01
```

**Issue:** Consumer request overdue
```bash
# Extend deadline (with required notice)
curl -X POST http://localhost:8000/api/v1/rights-requests/$REQ_ID/extend \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "reason": "verification_required",
    "consumer_notice": {
      "method": "email",
      "reason": "Identity verification documents incomplete"
    }
  }'
```

### Performance Tuning

```bash
# Database slow query analysis
docker-compose exec db psql -U postgres -c "
  SELECT query, mean_time, calls
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# API response time metrics
curl http://localhost:8000/metrics | grep http_request_duration
```

---

## Security Operations

### Certificate Rotation

```bash
# TLS certificate renewal (Let's Encrypt)
certbot renew --nginx

# JWT secret rotation (requires logout-all)
python scripts/rotate_jwt_secret.py --notify-users
```

### Access Review

```bash
# Quarterly access review
python scripts/access_review.py --format csv > access_review_$(date +%YQ%q).csv

# Disabled users report
python scripts/list_disabled_users.py

# Orphaned evidence check
python scripts/find_orphaned_evidence.py
```

---

## API Reference

### Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Response: {"access_token": "jwt-token", "token_type": "bearer"}

# Use token
curl http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer jwt-token"
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/applicability/assess` | POST | Run MHMDA applicability check |
| `/api/v1/data-elements` | GET/POST | Data inventory management |
| `/api/v1/vendors` | GET/POST | Vendor register |
| `/api/v1/rights-requests` | GET/POST | Consumer rights requests |
| `/api/v1/policy/generate` | POST | Generate privacy policy |
| `/api/v1/export/bundle` | POST | Create compliance export |

---

## Glossary

| Term | Definition |
|------|------------|
| MHMDA | Washington My Health My Data Act (RCW 19.373) |
| Consumer | Individual whose data is processed (not "patient" per MHMDA) |
| Health Data | Consumer health data as defined by RCW 19.373.010(2) |
| Precise Geolocation | Location data within 1,750 feet radius |
| Ad-Tech | Advertising technology vendors (high scrutiny under MHMDA) |
| Consumer Rights | Access, deletion, correction, portability under MHMDA |
| Evidence Vault | Tamper-evident audit trail storage |

---

## Support

- **Technical Issues**: Create GitHub issue at https://github.com/bobtheskull-source/Health-Data-Ready/issues
- **Security Reports**: security@example.com (PGP key available)
- **Compliance Questions**: legal@example.com

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Review Schedule**: Quarterly
