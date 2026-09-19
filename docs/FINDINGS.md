# Findings & Recommendations

Six findings, each tied to a specific query result against the fact tables — ordered roughly by materiality (test volume × severity), not by category name. Every number here reproduces exactly from [`powerbi/GRC_Tech_Controls_Dataset.xlsx`](../powerbi/GRC_Tech_Controls_Dataset.xlsx) or by running [`scripts/analyze_findings.py`](../scripts/analyze_findings.py) against [`data/`](../data).

## Finding 1
### Change Management is the weakest control category, and its exceptions go stale

**Observation.** Change Management tests fail or except at **22.8%** (57 of 250 tests) — the highest of all 8 categories and nearly double the 13.1% company-wide rate. Its currently open exceptions have been sitting unresolved for **85 days on average** (worst case: 216 days), versus 4 days average for every other category's open items. Of its 9 currently open exceptions, 5 (55.6%) are already past the 60-day aging threshold.

**Likely root cause.** Change Management is a preventive, process-heavy control (deployment approvals, emergency-change reviews) that depends on people following a workflow consistently, rather than a technical control that can be automated end to end. Once an exception is opened, there is no severity-driven urgency forcing it to close — the data shows items simply accumulate rather than resolve.

**Why it matters.** Change Management failures are a direct pathway to unauthorized or untested changes reaching production — the control an auditor tests first because it underpins the integrity of every other system-level control.

> **Recommendation:** cap Change Management remediation at a 30-day SLA for High/Critical findings (mirroring the severity-based due dates already used elsewhere in the model) and require the control owner to submit a written remediation plan by day 15 for anything not yet closed. Add a standing "Change Management aging" exception report to the monthly control-owner meeting rather than relying on the quarterly test cycle to surface it.

## Finding 2
### Legacy on-prem systems carry roughly double the exception rate of cloud-native systems

**Observation.** On-prem systems (SAP ERP, Oracle Production DB, Active Directory) test at a **19.9%** exception rate (79 of 396 tests) versus **9.8%** for cloud-native systems (78 of 792 tests) — a gap that holds across a large enough sample (n=396 vs. n=792) to be a real signal. Hybrid systems (Treasury & Banking Portal) sit in between at 12.1%.

**Likely root cause.** Cloud-native systems more often ship built-in, vendor-managed controls (automated patching, enforced MFA, managed backup) that satisfy a control test by design. Legacy on-prem systems depend on manual configuration and manual evidence-gathering, which is where process drift accumulates.

**Why it matters.** This is a portfolio-level signal, not a single-system problem — it says control effectiveness is materially a function of hosting architecture, directly relevant to any technology-modernization business case.

> **Recommendation:** when evaluating modernization/cloud-migration business cases for SAP ERP, Oracle Production DB, or Active Directory, include the ~10-point exception-rate gap as a quantified control-risk-reduction benefit, not just a cost/licensing argument. In the interim, require compensating manual evidence review for on-prem Change Management and Access Management tests specifically — the two categories where the on-prem gap is widest.

## Finding 3
### Orphaned accounts are concentrated almost entirely in two manually-deprovisioned systems

**Observation.** 22 distinct users carry an orphaned account (active access after termination). **78%** of the flagged review instances (28 of 36) are on **SAP ERP** (18) and **Oracle Production DB** (10) — both on-prem systems with manual, ticket-driven deprovisioning. Cloud systems account for 3 combined — essentially the noise floor.

**Likely root cause.** Cloud systems in this environment deprovision automatically within days of a termination event (a Workday-triggered offboarding workflow). SAP ERP and Oracle Production DB have no such trigger — deprovisioning depends on a manual ticket, which the data shows taking anywhere from weeks to several months.

**Why it matters.** An orphaned account on a Finance ERP or a production database is a live path for a terminated employee — or anyone who obtains their still-active credentials — to access financial or production data with no legitimate business justification. This is one of the most commonly cited findings in a real SOX or ITGC audit.

> **Recommendation:** extend the existing Joiner-Mover-Leaver (JML) automation that already deprovisions cloud accounts to trigger a same-day access-suspension ticket (not just eventual removal) for SAP ERP and Oracle Production DB the moment a termination is recorded in the HR system of record. Until that automation exists, add a **weekly** (not quarterly) reconciliation between the HR termination list and active-access lists for these two systems specifically.

## Finding 4
### Segregation-of-duties conflicts are fully concentrated in the two Finance transaction systems

**Observation.** 13 distinct users hold an SoD conflict during at least one certification cycle — **100%** of them on SAP ERP (29 flagged review instances) or the Treasury & Banking Portal (24 flagged review instances). No conflicts were detected on any other system.

**Likely root cause.** Conflicts are detected during quarterly access certification — after the fact — rather than being prevented at the point a role is assigned. A conflicting pair of roles can be live and usable for up to a full quarter before a reviewer catches it.

**Why it matters.** SoD conflicts on payment initiation/approval and GL entry/approval are precisely the pattern control frameworks (and external auditors) look for as a fraud-risk indicator: one person able to both create and approve a financial transaction end to end.

> **Recommendation:** this is a detective control doing a preventive control's job. Implement a role-conflict rule directly in the SAP ERP and Treasury provisioning workflow (a hard block, or a required compensating approval when a conflicting second role is requested), and reserve the quarterly access review for confirming the rule held — not for being the first line of defense that finds it three months later.

## Finding 5
### Tightening the access-review SLA from 30 to 15 days would create a compliance cliff, not an improvement, without added capacity

**Observation.** At the current 30-day SLA, **77.8%** of access reviews complete on time. Simulating a 15-day SLA against the same historical completion behavior drops on-time performance to **46.3%** and adds roughly **2,550 reviews (31.5% of the population)** to the backlog — with no change in who is doing the reviewing. On-prem systems are already the constraint: only **56.5%** on-time at the *current* 30-day policy, versus 88.3% for cloud systems.

| Environment | On-time % @ 30 days (current) | On-time % @ 15 days (proposed) | Point drop |
|---|---|---|---|
| Cloud | 88.3% | 56.8% | -31.6 pts |
| Hybrid | 69.9% | 35.9% | -34.0 pts |
| On-Prem | 56.5% | 25.7% | -30.8 pts |

**Likely root cause.** Legacy on-prem review workflows take longer to complete (manual evidence pulls, spreadsheet-based sign-off) than cloud-native, workflow-driven certifications. The completion-time distribution for on-prem reviews is simply shifted right — tightening the deadline doesn't change that distribution, it only reclassifies more of it as "late."

**Why it matters.** A policy change that immediately turns a majority-compliant program into a majority-non-compliant one, with no operational change, is a credibility problem for the GRC function and a real audit finding waiting to happen.

> **Recommendation:** do not blanket-adopt a 15-day SLA. Either **(a)** phase it — apply 15 days to cloud-native systems first, where the drop is smaller and the base rate is higher, and hold on-prem systems at 30 days pending automation — or **(b)** invest in automating the on-prem review workflow before tightening any deadline. Full mechanics: [DAX_MEASURES.md, Section 5](DAX_MEASURES.md#section-5--what-if-parameter-access-review-sla-30--15-days).

## Finding 6
### Third-party oversight gaps concentrate in the highest-risk vendor tier

**Observation.** **5 of 25 vendors** are overdue for reassessment against their own required cadence — and **all 5 are High inherent-risk-tier**, the exact tier with the shortest (12-month) required cadence. Payroll Processing vendors carry the highest average open-findings count of any service category (4.33 per vendor, versus 1.0 for Cloud Hosting and 0.0 for Legal/Compliance), and 2 of the 3 Payroll Processing vendors are among the overdue group.

**Likely root cause.** Higher-risk vendors are assessed more frequently by design, which mechanically creates more opportunities to fall behind schedule if the reassessment process isn't calendar-driven — a 12-month cadence is easier to miss than a 24-month one simply because it recurs more often.

**Why it matters.** Payroll and payment-processing vendors handle direct banking and PII data; an overdue reassessment on exactly this population is the highest-consequence version of this gap, not a paperwork technicality.

> **Recommendation:** put automated reassessment-due alerts (60/30/7-days-out) on every High-tier vendor in whatever GRC or vendor-management tool is authoritative, and prioritize closing the two overdue Payroll Processing vendor assessments this quarter given both the elevated findings count and the sensitivity of the data they process.

---

## A note on statistical confidence

Not every number in this dataset carries equal weight, and a defensible analysis says so explicitly. The single highest exception-rate cell in the full heat map — **Salesforce CRM × Segregation of Duties at 44.4%** — is built on only 9 tests (4 non-pass), because SoD is tested quarterly over a 24-month window. That's a real result, not an error, but it's a **watch item** requiring more test cycles before being reported with the same confidence as Change Management's 22.8% rate, which rests on 250 tests. The heat map's tooltip surfaces test count (n) for exactly this reason.
