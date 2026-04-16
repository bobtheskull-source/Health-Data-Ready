# Health Data Ready - Rewired Phase 1 Cards

---

## HDR-RW-001 | Engagement Shell
**Type:** Feature | **Priority:** Critical | **Platform:** All
**Size:** Small | **Dependencies:** None

### Description
Create engagement with client name, consultant name, start date, reference number. Engagement header persists across all document views.

### Acceptance Criteria
- [ ] Create new engagement form with fields: client name, consultant name, start date, reference number
- [ ] Persist engagement data to IndexedDB (local-first)
- [ ] Engagement header displays on all document views (sticky top bar)
- [ ] List saved engagements in consultant workspace (home screen)
- [ ] Resume engagement from last active document
- [ ] Mobile-optimized form layout (single column)
- [ ] Edit engagement metadata anytime

### Notes
Foundation card. Must complete before any documents can be created.

---

## HDR-RW-002 | Document Data Model
**Type:** Architecture | **Priority:** Critical | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-001

### Description
Define core data schema: Engagement → Documents → Sections → RowEntries. Enables relational persistence and cross-document data sharing.

### Acceptance Criteria
- [ ] Engagement model: id, clientName, consultantName, startDate, referenceNumber, createdAt, updatedAt
- [ ] Document model: type (enum of 10 docs), engagementId, status (draft/completed/locked), progress, sections
- [ ] Section model: title, fields (key-value), isComplete, lastEdited
- [ ] RowEntry model: type (device/vendor/finding/staff/incident/remediation), parentDocumentId, data (JSON)
- [ ] IndexedDB schema with proper indexes
- [ ] Data access layer (DAL) with CRUD operations
- [ ] Migration path for future schema changes

### Notes
Required before building any documents. Schema must support all 10 document types.

---

## HDR-RW-003 | Row-Table Engine
**Type:** Component | **Priority:** Critical | **Platform:** All
**Size:** Medium | **Dependencies:** HDR-RW-002

### Description
Reusable row-table component system for all repeated-entry tables across documents. Core interaction pattern.

### Acceptance Criteria
- [ ] Generic row-table component accepts column config array
- [ ] Row types supported: Device, Vendor, Finding, Staff, Incident, Remediation
- [ ] Add row button opens form modal or inline inputs
- [ ] Edit row inline or in modal
- [ ] Delete row with confirmation
- [ ] Duplicate row functionality (copy existing)
- [ ] Mobile: swipe to delete/edit OR action buttons
- [ ] Empty state message
- [ ] Sort by column headers
- [ ] Search/filter within table

### Schema per Row Type
- Device: name, category, os/version, purpose, healthData (bool), lastUpdated
- Vendor: name, service, dataShared (bool), baaSigned (bool), notes
- Finding: description, severity (critical/high/medium/low), source, remediationRef
- Staff: name, role, trainingDate, acknowledgmentSigned
- Incident: date, description, dataInvolved, notificationRequired, resolved
- Remediation: item, priority, dueDate, assignedTo, status, sourceFinding

### Notes
Most reused component. Build once, use everywhere.

---

## HDR-RW-004 | Device Inventory Document
**Type:** Feature | **Priority:** High | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-003

### Description
Structured form documenting all systems, devices, and software processing health data.

### Acceptance Criteria
- [ ] Section: Overview (health data systems purpose)
- [ ] Section: Device Table using Row-Table Engine
- [ ] Section: Cloud Services (row table)
- [ ] Section: Mobile/IoT Devices (row table)
- [ ] Section: Software/Applications (row table)
- [ ] Smart defaults: suggest device categories (desktop, laptop, phone, tablet, server)
- [ ] Flag health-data systems visually
- [ ] Percent complete calculation
- [ ] Autosave per field

### Notes
First document to test row-table engine.

---

## HDR-RW-005 | Vulnerability Assessment Document
**Type:** Feature | **Priority:** High | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-003

### Description
Document identifying security weaknesses, risks, and required controls.

### Acceptance Criteria
- [ ] Section: Assessment Methodology (notes)
- [ ] Section: Findings Table using Row-Table Engine
- [ ] Severity selector: Critical / High / Medium / Low
- [ ] Status: Open / In Progress / Closed
- [ ] Link finding to specific device (from Device Inventory)
- [ ] Suggest remediation template based on finding type
- [ ] Risk score calculation (count by severity)
- [ ] Generate remediation suggestions automatically

### Notes
Findings feed into Remediation Plan automatically.

---

## HDR-RW-006 | MHMD Compliance Document
**Type:** Feature | **Priority:** High | **Platform:** All
**Size:** Medium | **Dependencies:** HDR-RW-001

### Description
Washington My Health My Data Act checklist assessment with gap identification.

### Acceptance Criteria
- [ ] Section: Applicability Determination (5 questions with logic)
- [ ] Section: Data Collection Practices Checklist
- [ ] Section: Consumer Rights Process
- [ ] Section: Consent Mechanisms
- [ ] Section: Data Sharing Disclosures
- [ ] Section: Security Measures Checklist
- [ ] Gap detection: flag incomplete items
- [ ] Applicability result: Applicable / Not Applicable / Needs Review
- [ ] Auto-generate gaps list
- [ ] Reference RCW citations inline

### Applicability Questions
1. Washington business or targeting WA consumers?
2. Collecting consumer health data?
3. Exempt under RCW 19.373.090?
4. Data shared with third parties?
5. Precise geolocation collected?

### Notes
Can reuse assessment questions from HDR-UI-004.

---

## HDR-RW-007 | Remediation Plan Document
**Type:** Feature | **Priority:** High | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-005

### Description
Actionable task list addressing findings from other documents.

### Acceptance Criteria
- [ ] Section: Open Items Table using Row-Table Engine
- [ ] Auto-import findings from Vulnerability Assessment (optional)
- [ ] Auto-import gaps from MHMD Compliance (optional)
- [ ] Columns: item description, priority, due date, assigned to, status
- [ ] Status dropdown: Not Started / In Progress / Deferred / Complete
- [ ] Link each remediation back to source finding
- [ ] Progress bar: % complete
- [ ] Filter by status
- [ ] Overdue warnings

### Notes
Auto-linking from findings is a Phase 2 feature (RW-015).

---

## HDR-RW-008 | HIPAA Attestation Document
**Type:** Feature | **Priority:** Medium | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-001

### Description
Determine HIPAA covered entity status and document privacy/security safeguards.

### Acceptance Criteria
- [ ] Section: Entity Type Determination
  - [ ] Question: Are you a healthcare provider? (yes/no)
  - [ ] Question: Do you transmit health info electronically? (yes/no)
  - [ ] Question: Are you a health plan or clearinghouse? (yes/no)
  - [ ] Result: Covered Entity / Business Associate / Neither / Needs Review
- [ ] Section: Triage Flow - if unclear, escalation questions
- [ ] Section: Privacy Safeguards Checklist
- [ ] Section: Security Safeguards Checklist
- [ ] Section: Breach Notification Procedures
- [ ] Final attestation signature (checkbox + date)

### Notes
Keep simple: triage, not full HIPAA audit.

---

## HDR-RW-009 | Data Inventory & Flow Map
**Type:** Feature | **Priority:** High | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-003

### Description
Track what health data is collected, where it flows, and which vendors handle it.

### Acceptance Criteria
- [ ] Section: Data Categories (checkboxes)
  - [ ] Contact info, medical records, biometrics, genetics, mental health, prescriptions, insurance, device data, behavioral, location
- [ ] Section: Data Sources Table (row-table)
- [ ] Section: Data Recipients Table (row-table)
- [ ] Section: Cross-Border Transfers
- [ ] Section: Retention Schedule
- [ ] Visual: simple flow diagram (boxes and arrows)
- [ ] Health data sensitivity flag per row
- [ ] Link to Device Inventory systems

### Notes
Replaces HDR-UI-005. Can keep some existing logic.

---

## HDR-RW-010 | Incident Response Log
**Type:** Feature | **Priority:** Medium | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-003

### Description
Log of security incidents, breaches, and privacy events.

### Acceptance Criteria
- [ ] Section: Incident Table using Row-Table Engine
- [ ] Columns: date, description, data types involved, records affected, notification required, notification sent, status
- [ ] Notification calculator: was this a reportable breach?
  - [ ] Based on: records count, data sensitivity, harm assessment
- [ ] 60-day notification deadline tracker
- [ ] Status: Open / Under Investigation / Resolved / Closed
- [ ] Link to remediation items if action required

### Notes
Simple logging tool. Keep complexity low.

---

## HDR-RW-011 | Staff Awareness Document
**Type:** Feature | **Priority:** Medium | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-003

### Description
Training roster, policy acknowledgments, and awareness verification.

### Acceptance Criteria
- [ ] Section: Staff Roster Table using Row-Table Engine
- [ ] Columns: name, role, hire date, training completed, acknowledgment signed, date
- [ ] Section: Training Topics (checklist)
  - [ ] Privacy policies, security procedures, incident reporting, device handling, PHI access rules
- [ ] Section: Policy Acknowledgment Tracking
- [ ] Flag incomplete training
- [ ] Reminder for annual refresher

### Notes
HR-style document. Keep fields minimal.

---

## HDR-RW-012 | Annual Compliance Summary
**Type:** Feature | **Priority:** Critical | **Platform:** All
**Size:** Medium | **Dependencies:** HDR-RW-004 to RW-011

### Description
Executive summary auto-generated from all completed documents.

### Acceptance Criteria
- [ ] Section: Engagement Metadata (client, consultant, date, reference)
- [ ] Section: Documents Completed (checklist with completion %)
- [ ] Section: Compliance Posture Summary
  - [ ] Device count, finding count by severity, MHMD applicability, HIPAA status
- [ ] Section: Open Remediation Items (count and age)
- [ ] Section: Key Risks Identified
- [ ] Section: Carry-Forward Items for Next Year
- [ ] Section: Recommendations (auto-generated from gaps)
- [ ] Year-over-year comparison fields (placeholder)
- [ ] Export integrates this as cover section of package

### Auto-Generated Metrics
- Total devices inventoried
- Critical/High findings count
- Days since last incident
- % remediation complete
- Training completion rate

### Notes
Last document to implement. Needs all others first.

---

## HDR-RW-013 | Autosave & Draft Persistence
**Type:** Infrastructure | **Priority:** Critical | **Platform:** All
**Size:** Medium | **Dependencies:** HDR-RW-002

### Description
Per-field autosave with conflict detection. No explicit save button.

### Acceptance Criteria
- [ ] Autosave triggers on: field blur, 2-second debounce on typing, navigation attempt
- [ ] Save to IndexedDB immediately
- [ ] Visual indicator: "Saved" / "Saving..." / "Unsaved changes"
- [ ] Handle offline: queue saves, retry on reconnect
- [ ] Conflict detection: if document edited elsewhere, show diff
- [ ] Unsaved changes prompt before navigation
- [ ] Document-level lastEdit timestamp
- [ ] Per-field edit history (optional v1)

### Notes
Critical UX feature. Must be reliable before any document work.

---

## HDR-RW-014 | Export Package Builder
**Type:** Feature | **Priority:** Critical | **Platform:** All
**Size:** Medium | **Dependencies:** HDR-RW-012

### Description
Select documents, compile into polished printable/PDF annual package.

### Acceptance Criteria
- [ ] Export screen with checklist: select which docs to include
- [ ] Mark incomplete docs visually (warning icon)
- [ ] Generate cover page with engagement metadata
- [ ] Table of contents with page references
- [ ] Assemble documents in canonical order
- [ ] Branded header/footer per consultant
- [ ] PDF generation (client-side or server)
- [ ] Digital signature placeholders
- [ ] Export version ID and timestamp
- [ ] Download or print output
- [ ] Save export history (list of prior exports)

### Export Order
1. Cover + Engagement Info
2. Annual Compliance Summary
3. Device Inventory
4. Vulnerability Assessment
5. MHMD Compliance
6. Remediation Plan
7. HIPAA Attestation
8. Data Inventory & Flow Map
9. Incident Response Log
10. Staff Awareness

### Notes
First-class feature. Not an afterthought.

---

## HDR-RW-015 | Cross-Document Data Propagation
**Type:** Feature | **Priority:** Medium | **Platform:** All
**Size:** Medium | **Dependencies:** HDR-RW-004 to RW-011

### Description
Enter data once, use everywhere. Shared facts across documents.

### Acceptance Criteria
- [ ] Global engagement facts: client name appears in all docs automatically
- [ ] Shared vendor list: enter in Data Inventory, available in MHMD, Remediation
- [ ] Shared device inventory: devices selectable in Vulnerability, Incident
- [ ] Shared findings: Vulnerability findings link to Remediation items
- [ ] Edit in one place, update references (or mark out of sync)
- [ ] Visual indicator: "linked from Data Inventory"
- [ ] Conflict resolution when source changes

### Propagation Map
- Device Inventory → Vulnerability, Incident
- Vendors → MHMD, Remediation, Data Inventory
- Findings → Remediation
- Incidents → Annual Summary
- Training → Annual Summary

### Notes
Phase 2 feature. Can implement basic linking in Phase 1.

---

## HDR-RW-016 | Document Completion Scoring
**Type:** Feature | **Priority:** Medium | **Platform:** All
**Size:** Small | **Dependencies:** HDR-RW-004 to RW-011

### Description
Progress indicators, validation, and "ready for export" state.

### Acceptance Criteria
- [ ] Sidebar shows completion % per document
- [ ] Required field indicators (red asterisk)
- [ ] Validation on field blur: highlight invalid
- [ ] Section-level progress bars
- [ ] Document states: Draft / In Progress / Complete / Needs Review
- [ ] "Ready for Export" flag when 100% complete
- [ ] Warning for empty required sections
- [ ] Missing field list (what's left to complete)

### Completion Rules
- Required fields must have values
- Row tables must have at least one entry
- Attestation documents require signature checkbox
- Findings with Critical/High severity require remediation link

### Notes
Enables quality gates before export.

---

# Sizing Summary

| Card | Size | Complexity |
|------|------|------------|
| HDR-RW-001 | Small | Foundation |
| HDR-RW-002 | Small | Architecture |
| HDR-RW-003 | Medium | Component reuse |
| HDR-RW-004 | Small | Uses RW-003 |
| HDR-RW-005 | Small | Uses RW-003 |
| HDR-RW-006 | Medium | Logic-heavy |
| HDR-RW-007 | Small | Uses RW-003 |
| HDR-RW-008 | Small | Decision tree |
| HDR-RW-009 | Small | Uses RW-003 |
| HDR-RW-010 | Small | Uses RW-003 |
| HDR-RW-011 | Small | Uses RW-003 |
| HDR-RW-012 | Medium | Aggregation |
| HDR-RW-013 | Medium | Async/reliable |
| HDR-RW-014 | Medium | PDF/export |
| HDR-RW-015 | Medium | Data linking |
| HDR-RW-016 | Small | Validation |

**Phase 1 Work: 16 cards**
**Dependencies: RW-001 → RW-002 → RW-003 → Documents**
