# Interview Defense Notes

Concept primers for the three control ideas this project is built around, written the way you should be able to explain them out loud — in your own words — followed by a short anticipated Q&A.

## Segregation of Duties (SoD)

SoD is the principle that no single person should be able to both **execute** and **approve/control** the same end-to-end transaction, because that combination removes the independent check that catches errors or intentional fraud. The classic finance example, and the one modeled here, is a user holding both a transaction-entry role (AP Processor, GL Preparer, Payment Initiator) and its matching approval role (AP Approver, GL Approver, Payment Approver) — that person could create a fraudulent payment and approve it themselves.

This model deliberately separates two different lenses on SoD, and explaining *why* they're different is itself a good interview answer:

- **`Fact_AccessReview[HasSoDConflict]`** is a raw population risk indicator — does this user currently hold a conflicting role pair, detected during quarterly access certification. It answers *"who is exposed right now."*
- **The Segregation of Duties control category in `Fact_ControlTest`** tests whether the SoD monitoring/review *process itself* is operating effectively — are conflict reviews happening on schedule, are findings escalated. It answers *"is our detection mechanism working."*

A real SoD conflict list from the access-review fact would typically get escalated **into** a formal `Fact_ControlTest` exception if unresolved promptly — the two tables are related in practice even though they're kept as separate fact grains here, because they answer different audit questions and mixing them would blur "we have a conflict" with "our process for catching conflicts is broken."

## Remediation aging: "days open" vs. "time to remediate"

These sound like the same metric and are not. **"Days open"** (aging) is a snapshot metric: for exceptions still open today, how long has each been sitting, measured against `TODAY()`. It answers *"how stale is our current backlog,"* and by definition changes every day the report is refreshed with no new data at all — expected and correct for a backlog metric, not a bug. **"Time to remediate"** (cycle time) is measured only on **closed** items: open-date to close-date. It answers *"how long does it actually take us to fix something once we start"* — the number you'd use to set a realistic SLA or measure whether a process-improvement initiative worked.

Reporting only one hides information a CISO needs: a category could have excellent average cycle time on the items it closes while still carrying a terrible aging backlog, if a subset of exceptions simply never gets worked. That's close to the actual pattern in this dataset's Change Management category — a bad exception rate on its own (22.8%), plus a distinctly more urgent fact: 85-day average aging and a 216-day maximum on its still-open items.

## Risk tiering: inherent vs. residual risk (vendor model)

**Inherent risk** is the risk a vendor relationship carries by its nature, before considering how well it's actually being managed — `InherentRiskTier` is set once, from the vendor's service category (Payment Processing and Payroll Processing are High by nature; Facilities and Legal are Low). **Residual risk** is what's left after accounting for actual assessment results — `ResidualRiskTier` escalates a vendor's tier upward when an assessment turns up critical findings, regardless of the original classification.

Why the distinction matters operationally: assessment **cadence** (12/18/24 months) is set by inherent tier, because you can't know how often to check on something before you've checked on it once — but remediation **prioritization** and CISO reporting should follow residual tier, because that's the number reflecting what assessment evidence actually found.

---

## Anticipated interview questions

**Q: Why a galaxy schema with three fact tables instead of one wide fact table?**
Control testing, access review, and vendor assessment happen at genuinely different grains (per control-test event, per user-per-system-per-quarter, per vendor-assessment event) and different cadences. Forcing them into one fact table would pad every row with nulls for columns that don't apply, and it would break simple counts — `COUNTROWS` would no longer mean "number of control tests" because access-review rows would be mixed in. A galaxy schema keeps each fact table's grain honest while still sharing `Dim_System`, `Dim_Date`, and `Dim_ControlOwner` so cross-process questions stay answerable with a single filter.

**Q: Why `DISTINCTCOUNT` instead of `COUNTROWS` for orphaned accounts and SoD conflicts?**
Because the fact table's grain is per-review-*cycle*, not per-person. A terminated user can be flagged as orphaned across two or three consecutive quarterly cycles before deprovisioning finally happens. `COUNTROWS` would count that one person multiple times and overstate the finding; auditors report how many distinct accounts/people are exposed, not how many detection events occurred.

**Q: Walk me through what happens, mechanically, when someone moves the SLA slider from 30 to 15.**
The slider is bound to a disconnected What-If parameter table with no relationship to the model. Moving it changes what `SELECTEDVALUE()` returns — a plain number, not a filter. That number gets pulled into a `VAR` in the downstream measures and compared against `Fact_AccessReview[DaysOutstanding]` for every row via `CALCULATE(COUNTROWS(...), DaysOutstanding > SelectedSLA)`. No row is added or removed from the model; the same 8,096 rows are just re-classified as on-time or breaching against a different threshold. That's why it's a legitimate what-if: it isolates the effect of the *policy line* from any change in actual behavior.

**Q: Why not just hardcode a 15-vs-30 comparison instead of building a parameter?**
Two static measures would answer this one comparison and nothing else. A parameter lets a GRC manager explore the whole curve — what does 20 days look like, 25 — interactively, which is what a real policy conversation needs. It's also the correct Power BI-native pattern for this class of problem.

**Q: The heat map shows a 44% exception rate for Salesforce CRM SoD — isn't that your worst finding?**
It's the highest single number, but not the most defensible finding, and saying so is the point. That cell has only 9 tests behind it, so a swing of even one or two results moves the rate by more than 10 points. Change Management's 22.8% rate on 250 tests is a far more statistically solid signal, which is why it's Finding #1 and the Salesforce cell is called out separately as a watch item.

**Q: How would this change with real production data instead of simulated data?**
The schema, relationships, and every DAX measure are unchanged — they operate on `TestResult`, `RemediationStatus`, `DaysOutstanding`, and the other columns regardless of where the rows came from. What would change: (1) dates would come from an actual GRC/ITSM system export instead of a generator, (2) `DaysOutstanding` for access reviews would need a real source system that timestamps cycle assignment and completion (most IGA tools like SailPoint or Saviynt expose this), and (3) the specific numeric thresholds in the heat map's conditional formatting and the SLA scenario range would get recalibrated to the organization's own historical baseline.
