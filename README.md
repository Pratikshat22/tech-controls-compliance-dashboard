# Technology Controls & Compliance Monitoring

**An IT Audit / GRC analytics project** — control testing, access certification, segregation-of-duties conflicts, and third-party risk, analyzed over a simulated enterprise dataset and built out in Power BI.

**[Live preview →](https://pratikshat22.github.io/tech-controls-compliance-dashboard/)** — a prototype used to validate the analysis before the Power BI build. The audit work is the findings below, not the webpage.

---

## What this project is

Most portfolio dashboards use a sales or HR dataset. This one is built around what an **IT Audit / GRC analyst** actually reviews between formal audit cycles:

- Are our controls operating effectively, and where is the exception backlog going stale?
- Are we current on quarterly access recertification, and free of segregation-of-duties conflicts?
- Are our third-party vendors being reassessed on schedule, proportional to their risk?
- If we tightened a compliance SLA, what would actually happen to the backlog — before we change the policy?

Every finding below is tied to a specific number pulled from the dataset, with a root cause and a recommendation — the way a finding would be written in a real audit workpaper, not a vague "compliance is low."

## Findings

| # | Finding | Number |
|---|---|---|
| 1 | **Change Management** is the weakest control category | 22.8% exception rate (n=250) — nearly 2× the 13.1% overall rate; open items aged **85 days** on average vs. 4 days elsewhere |
| 2 | Legacy **on-prem** systems underperform cloud-native systems | 19.9% vs. 9.8% exception rate (n=396 vs. n=792) |
| 3 | **Orphaned accounts** cluster in manually-deprovisioned systems | 78% of exposure (28 of 36 instances) sits in 2 of 10 systems |
| 4 | **SoD conflicts** are 100% concentrated in Finance systems | 13 distinct users, entirely on SAP ERP + Treasury |
| 5 | Tightening the access-review SLA 30→15 days would spike the backlog | On-time completion drops 77.8% → 46.3%; +2,550 reviews (31%) added overnight |
| 6 | Third-party oversight gaps concentrate in the highest-risk tier | 5 of 25 vendors overdue for reassessment — **all 5** are High-tier |

Full root-cause analysis and recommendations for each: [`docs/FINDINGS.md`](docs/FINDINGS.md).

## Audit concepts this project applies

- **Segregation of Duties (SoD):** modeled as two distinct lenses — a raw population risk indicator (who currently holds a conflicting role pair) vs. whether the SoD *monitoring process itself* is operating effectively. Explained in [`docs/INTERVIEW_NOTES.md`](docs/INTERVIEW_NOTES.md#segregation-of-duties-sod).
- **Remediation aging vs. cycle time:** "days open" (a snapshot of today's backlog) and "time to remediate" (how long closed items actually took) are deliberately kept as separate measures — conflating them is a common mistake in audit reporting. See [`docs/INTERVIEW_NOTES.md`](docs/INTERVIEW_NOTES.md#remediation-aging-days-open-vs-time-to-remediate).
- **Inherent vs. residual risk (vendor tiering):** assessment cadence follows inherent risk tier; remediation prioritization follows residual risk tier, which escalates when assessment evidence finds critical issues.
- **Statistical confidence in findings:** the highest single number in the dataset (a 44% exception rate on one system/category pair) is called out as a *watch item*, not a headline finding, because it rests on only 9 tests — a defensible audit finding states its own sample size.

Anticipated interview questions and full answers: [`docs/INTERVIEW_NOTES.md`](docs/INTERVIEW_NOTES.md).

## The data model (supporting layer)

A star/galaxy schema — three fact tables (control tests, access reviews, vendor assessments) sharing conformed dimensions — built in Power BI with 20+ DAX measures. This is the technical layer that makes the findings above reproducible and auditable, not the point of the project on its own.

- Schema, grains, and relationships: [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- Every DAX measure with the reasoning behind it: [`docs/DAX_MEASURES.md`](docs/DAX_MEASURES.md)
- The Power BI What-If Parameter behind Finding #5 (SLA policy modeling): [`docs/DAX_MEASURES.md`](docs/DAX_MEASURES.md#section-5--what-if-parameter-access-review-sla-30--15-days)

## Repo structure
