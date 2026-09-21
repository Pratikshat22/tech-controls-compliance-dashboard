# Technology Controls & Compliance Monitoring

An IT Audit / GRC project I built to go with my resume — control testing, access certification, segregation-of-duties conflicts, and third-party vendor risk, worked through in Power BI over a dataset I generated myself.

**[Live preview →](https://pratikshat22.github.io/tech-controls-compliance-dashboard/)** — I built this as a quick prototype to check my analysis actually made sense visually before committing to the full Power BI build. The real work is in the findings below and in the DAX logic, not the webpage itself.

## Why I built it this way

Most of the portfolio projects I looked at before starting this used a sales dataset or an HR attrition dataset — the same ones everyone uses. I wanted something closer to what I'd actually be doing in an IT Audit / GRC role, so I picked four things auditors genuinely track:

- Are controls actually operating effectively, or are exceptions piling up somewhere?
- Are access reviews happening on time, and are there segregation-of-duties conflicts sitting undetected?
- Are our vendors being reassessed on schedule, based on how risky they actually are?
- If leadership wants to tighten a compliance deadline, what does that actually do to the backlog — before anyone commits to the policy?

I didn't have access to a real company's GRC data (obviously), so I generated a synthetic dataset in Python with realistic, non-random patterns built in — some systems and control categories are deliberately weaker than others, the way they would be in a real environment. That part is documented in [`scripts/generate_dataset.py`](scripts/generate_dataset.py) if you want to see how.

## What I found

I'm listing these roughly in order of how confident I am in them — some findings here rest on a lot more test data than others, which matters (more on that at the bottom).

**Change Management is the weakest control category by a wide margin** — 22.8% of tests came back as an exception or failure, against 13.1% company-wide, and that's across 250 tests so it's not a fluke of small sample size. What stood out more to me than the rate itself was the aging: open Change Management exceptions have been sitting for 85 days on average, one as long as 216 days, while every other category clears its open items in about 4 days on average. My read on this is that Change Management is a process control, not a technical one — nobody's forcing it closed the way a system might auto-remediate a technical gap. If I were advising on this, I'd put a hard 30-day SLA on Critical/High Change Management findings specifically, because right now nothing is.

**Legacy on-prem systems run almost double the exception rate of cloud systems** — 19.9% vs. 9.8%, and again the sample sizes are big enough (396 vs. 792 tests) that I trust this isn't noise. Makes sense when you think about it: cloud platforms tend to bake in things like enforced MFA and automated patching, so a control test passes almost by default, whereas the on-prem systems here depend on someone manually keeping configuration correct.

**Orphaned accounts are basically a two-system problem.** 22 people ended up with active access after their termination date, and 78% of those cases were on two systems — SAP ERP and the Oracle production database — both of which rely on a manual deprovisioning ticket instead of an automated trigger. Cloud systems in this dataset barely show any orphan cases at all, because offboarding there is automated. If I were writing this up as a real finding, I'd push for extending whatever automated offboarding trigger already exists for the cloud systems to cover these two as well, rather than treating it as "add more manual review."

**Segregation-of-duties conflicts showed up exclusively in the two Finance systems** — SAP ERP and the Treasury portal — which is exactly where you'd expect them, since that's where someone could plausibly both create and approve a payment. 13 people had a conflict at some point. The thing I'd flag here is that these were all caught during quarterly access review, meaning a conflict could sit live for up to three months before anyone catches it. That's a detective control filling in for what should really be a preventive one — the provisioning system itself should refuse to grant a second, conflicting role in the first place.

**Tightening the access-review SLA from 30 to 15 days looked like an easy win until I actually ran the numbers.** On-time completion right now, at 30 days, is 77.8%. If you just move the deadline to 15 days without changing anything else about how reviews get done, that number falls to 46.3% — and roughly 2,550 additional reviews (about a third of all of them) instantly become "late." The part that made me actually stop and reconsider the whole idea: on-prem systems are already only 56.5% on-time under the *current* 30-day policy. Tightening the deadline there wouldn't make access any safer, it would just make the metric look worse. I modeled this with a Power BI What-If Parameter so you can move the slider yourself and watch it happen — details in [`docs/DAX_MEASURES.md`](docs/DAX_MEASURES.md#section-5--what-if-parameter-access-review-sla-30--15-days).

**Third-party risk oversight has a gap right where it matters most.** 5 of 25 vendors are overdue for reassessment, and every single one of them is in the highest risk tier — the tier that's supposed to be checked most often. Payroll-processing vendors specifically have the highest average number of open findings of any category, which is a little uncomfortable given that's the category handling direct banking and personal data.

Full write-up with root cause and recommendation for each of these: [`docs/FINDINGS.md`](docs/FINDINGS.md).

## A caveat I want to be upfront about

Not every number here carries the same weight. The single highest exception rate anywhere in the dataset — 44% — is on a Salesforce/SoD combination, but it's based on only 9 tests, because that control category only gets tested quarterly. A one- or two-result swing moves that number by ten points. I think it's worth mentioning because I've seen dashboards (and reports) present a number like that with the same confidence as something backed by 250 data points, and that's a mistake I didn't want to make here.

## How the data model is put together

Three fact tables — control tests, access reviews, and vendor assessments — sharing a common set of dimensions (system, date, control owner) rather than being crammed into one flat table. I went this route because the three processes genuinely happen at different grains: a control test happens per control per test date, an access review happens per user per system per quarter, and a vendor assessment happens per vendor per assessment event. Trying to force those into a single fact table would mean a lot of empty columns and would break simple row counts.

- Full schema, table grains, and relationships: [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- Every DAX measure, with my reasoning for why it's written the way it is (not just the syntax): [`docs/DAX_MEASURES.md`](docs/DAX_MEASURES.md)
- Concepts I'd want to be able to explain out loud if asked — SoD, remediation aging vs. cycle time, inherent vs. residual risk: [`docs/INTERVIEW_NOTES.md`](docs/INTERVIEW_NOTES.md)
- What I simplified and why, stated plainly rather than left for someone to find: [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md)

## Repo layout
