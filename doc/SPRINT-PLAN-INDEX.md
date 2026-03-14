# SAP-Facture Sprint Plan - Quick Navigation

**Document**: `SPRINT-PLAN.md` (1,681 lines)

## Quick Links

### Executive Summary
Start here for overview:
- Scope: 69 story points across 2 sprints (10 days)
- Team: 1-2 developers
- Timeline: 2 weeks compressed

### Sprint Plans (JUMP HERE FOR ACTION)

**Sprint 1 (Days 1-5)**: Infrastructure + URSSAF Integration
- 28 points, focus: database + API integration + security
- Location: Line ~500
- Key deliverable: URSSAF sandbox working

**Sprint 2 (Days 6-10)**: Web UI + Deployment  
- 41 points, focus: web forms + PDF + deployment
- Location: Line ~700
- Key deliverable: MVP ready for production

### Epic Breakdown (JUMP HERE FOR FEATURES)

| Epic | Points | Priority | Status |
|------|--------|----------|--------|
| 1. Infrastructure & Security | 13 | P0 | Critical foundation |
| 2. URSSAF API Integration | 16 | P0 | Core feature |
| 3. Invoice Management | 12 | P0 | Core feature |
| 4. Dashboard & Tracking | 8 | P0 | User-facing |
| 5. CLI Automation | 5 | P1 | Nice-to-have |
| 6. Testing & Deployment | 6 | P0 | Quality gate |

### User Stories by Epic

**Epic 1: Infrastructure** (Lines 80-200)
- STORY-101: Setup + Docker
- STORY-102: Database schema
- STORY-103: Security + encryption

**Epic 2: URSSAF Integration** (Lines 200-350)
- STORY-201: OAuth 2.0
- STORY-202: Submit invoice
- STORY-203: Status polling
- STORY-204: Error handling

**Epic 3: Invoice Management** (Lines 350-550)
- STORY-301: Client CRUD
- STORY-302: Invoice form
- STORY-303: PDF generation
- STORY-304: Submit button

**Epic 4: Dashboard** (Lines 550-700)
- STORY-401: Invoice list
- STORY-402: Invoice detail
- STORY-403: CSV export

**Epic 5: CLI** (Lines 700-800)
- STORY-501: CLI commands

**Epic 6: Testing & Deployment** (Lines 800-950)
- STORY-601: Unit tests
- STORY-602: Docker + VPS
- STORY-603: Sandbox validation

### Critical Information

**Definition of Done**
- Sprint 1: Lines ~1100
- Sprint 2: Lines ~1200

**Risk Register**
- Location: Line ~1400

**Dependencies & Critical Path**
- Location: Line ~1300

**Next Steps (Pre-Sprint Kickoff)**
- Location: Line ~1600

## How to Use This Plan

### For Developers

1. Read "Résumé Exécutif" (lines 10-50)
2. Find your assigned stories (Ctrl+F "STORY-XXX")
3. Read acceptance criteria + tasks
4. Check dependencies before starting
5. Track progress against burndown expectations

### For Product Owner

1. Review "Epic Breakdown" (lines 55-150)
2. Check "Sprint Plan" section (lines 500-750)
3. Daily monitor: "Plan Sprint" section for burndown
4. Review "Definition of Done" (lines 1100-1250)

### For Project Manager

1. Start with "Résumé Exécutif" + key metrics
2. Track "Burndown Expectations" (lines ~1250)
3. Monitor risks in "Risk Register" (lines ~1400)
4. Use "Next Steps" checklist (line 1600)

### For DevOps/QA

1. Find "Testing & Deployment" epic (lines 750-950)
2. Review STORY-601 (testing strategy)
3. Review STORY-602 (Docker + deployment)
4. Check "Definition of Done - Sprint 2" (lines 1200+)

## Key Metrics at a Glance

- **Total Points**: 69
- **Sprint 1**: 28 points / 5 days = 5.6 pts/day
- **Sprint 2**: 41 points / 5 days = 8.2 pts/day (aggressive)
- **Expected Velocity**: 60-65 points (86-94% completion)
- **Team Size**: 1-2 developers
- **Success Criteria**: All P0 stories done, >70% test coverage, Docker deployed

## Burndown Quick Reference

```
Sprint 1 Ideal Pace: 28 points ÷ 5 days = 5.6 pts/day

Day 1: 28 → 24 (setup + schema)
Day 2: 24 → 19 (schema + encryption)  
Day 3: 19 → 14 (encryption + OAuth)
Day 4: 14 → 9  (OAuth + submit API)
Day 5: 9 → 0   (polling + sandbox + error handling)

Sprint 2 Ideal Pace: 41 points ÷ 5 days = 8.2 pts/day

Day 6: 41 → 35 (clients + invoice model)
Day 7: 35 → 30 (invoice form + PDF)
Day 8: 30 → 22 (PDF + dashboard)
Day 9: 22 → 12 (detail + CLI + export)
Day 10: 12 → 0 (tests + deployment)
```

## Pre-Sprint Checklist

Before Sprint 1 starts:

- [ ] URSSAF sandbox credentials received from Jules
- [ ] VPS access (SSH) provided
- [ ] Git repo initialized + shared
- [ ] Docker installed locally + tested
- [ ] Python 3.11+ available
- [ ] Team aligned on 10-day aggressive timeline
- [ ] Daily standup scheduled (9 AM)

## Risk Mitigation Quick Reference

Top 3 Risks & Fixes:

1. **URSSAF API format surprise** → Sandbox test DAY 2, not day 5
2. **PDF rendering issues** → POC day 3, HTML fallback ready
3. **Time overrun** → Daily standup, deprioritize P1 if needed

## Document Version

- Version: 1.0
- Date: 14 mars 2026
- Author: BMAD Scrum Master (Automated)
- Status: Ready for Sprint 1 kickoff

---

**Next**: Open SPRINT-PLAN.md and search for your assigned story by ID (e.g., STORY-101)
