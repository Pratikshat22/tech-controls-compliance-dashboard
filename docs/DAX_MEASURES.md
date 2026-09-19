# DAX Measure Library

The plain-text, copy-paste-into-Power-BI version of this file is [`powerbi/DAX_Measures.dax.txt`](../powerbi/DAX_Measures.dax.txt). This page is the same content formatted for reading, with the reasoning up front — you should be able to explain *why* each measure is written this way, not just recite the syntax.

## Section 0 — Calculated columns (build these first)

`Fact_ControlTest` carries **three** distinct remediation dates, but only `TestDateKey` has an active relationship to `Dim_Date` (see [DATA_MODEL.md](DATA_MODEL.md#why-three-date-roles-on-fact_controltest-are-not-three-relationships) for why). The other three become calculated Date columns via `LOOKUPVALUE`:

```dax
Fact_ControlTest[RemediationOpenDate] =
LOOKUPVALUE(Dim_Date[Date], Dim_Date[DateKey], Fact_ControlTest[RemediationOpenDateKey])

Fact_ControlTest[RemediationDueDate] =
LOOKUPVALUE(Dim_Date[Date], Dim_Date[DateKey], Fact_ControlTest[RemediationDueDateKey])

Fact_ControlTest[RemediationCloseDate] =
LOOKUPVALUE(Dim_Date[Date], Dim_Date[DateKey], Fact_ControlTest[RemediationCloseDateKey])
```

A blank `RemediationOpenDateKey` (i.e. a `Pass` row) simply produces a blank date — exactly what's wanted, since Pass rows should never enter an aging calculation.

## Section 1 — Base counts

```dax
Total Control Tests = COUNTROWS(Fact_ControlTest)
Total Access Reviews = COUNTROWS(Fact_AccessReview)
Total Vendor Assessments = COUNTROWS(Fact_VendorAssessment)
```

Every ratio measure below divides by one of these three.

## Section 2 — Control exception rate (the core testing metric)

```dax
Control Exceptions =
CALCULATE(COUNTROWS(Fact_ControlTest), Fact_ControlTest[TestResult] = "Exception")

Control Failures =
CALCULATE(COUNTROWS(Fact_ControlTest), Fact_ControlTest[TestResult] = "Fail")

Non-Effective Tests = [Control Exceptions] + [Control Failures]

Control Exception Rate % =
DIVIDE([Non-Effective Tests], [Total Control Tests])
```

`CALCULATE()` is doing real work here even though the filter is on the fact table's own column: it establishes a fresh filter context that combines with **AND** against whatever System/Category slicers a visual already applies — which is exactly what lets one generic measure recolor every cell of the System × Category heat map correctly. `DIVIDE()` (never a bare `/`) matters concretely on this dataset — several System × Category cells have as few as 4–9 tests because Encryption and Logical Security are tested semi-annually/quarterly, so a zero-test cell is a real possibility, not a hypothetical.

```dax
% of Total Non-Effective Tests (Pareto share) =
DIVIDE(
    [Non-Effective Tests],
    CALCULATE([Non-Effective Tests], ALL(Dim_ControlCategory), ALL(Dim_System))
)
```

`ALL()` strips the Category and System filters *only inside this CALCULATE*, so the denominator is always the grand total of non-effective tests across the whole model, regardless of which matrix cell, slicer, or drill-down path the numerator is evaluated under — this is what makes a Pareto chart ("Change Management alone accounts for 43% of all control exceptions company-wide") behave correctly instead of re-basing to 100% inside every filtered subview.

## Section 3 — Remediation aging: two different questions, two different measures

```dax
Open Remediation Items =
CALCULATE(COUNTROWS(Fact_ControlTest), Fact_ControlTest[RemediationStatus] IN {"Open", "In Progress"})

Avg Remediation Aging (Days Open) =
AVERAGEX(
    FILTER(Fact_ControlTest, Fact_ControlTest[RemediationStatus] IN {"Open", "In Progress"}),
    DATEDIFF(Fact_ControlTest[RemediationOpenDate], TODAY(), DAY)
)

Avg Days to Remediate (Closed) =
AVERAGEX(
    FILTER(Fact_ControlTest, Fact_ControlTest[RemediationStatus] = "Closed"),
    DATEDIFF(Fact_ControlTest[RemediationOpenDate], Fact_ControlTest[RemediationCloseDate], DAY)
)
```

These are **not** the same measure with a different filter — conflating them is the single most common mistake in audit dashboards that report "average remediation time." `Avg Remediation Aging (Days Open)` is a *snapshot*: how stale is today's backlog, measured against `TODAY()` — it changes every day the report is opened, by design. `Avg Days to Remediate (Closed)` is a *cycle-time* metric: once someone starts fixing something, how long does it actually take — useful for capacity planning, not for describing current risk exposure.

```dax
Aged Exceptions (60+ Days Open) =
CALCULATE(
    COUNTROWS(Fact_ControlTest),
    Fact_ControlTest[RemediationStatus] IN {"Open", "In Progress"},
    FILTER(Fact_ControlTest, DATEDIFF(Fact_ControlTest[RemediationOpenDate], TODAY(), DAY) > 60)
)

Aged Exception Rate % (of Open Backlog) =
DIVIDE([Aged Exceptions (60+ Days Open)], [Open Remediation Items])

Remediation Past Due Date (Severity-Based SLA Breach) =
CALCULATE(
    COUNTROWS(Fact_ControlTest),
    Fact_ControlTest[RemediationStatus] IN {"Open", "In Progress"},
    Fact_ControlTest[RemediationDueDate] < TODAY()
)
```

`CALCULATE` takes two filter arguments in the first measure: a plain column predicate (status) and a table `FILTER` (needed because "days open > 60" is a calculated expression, not a bare column comparison). The severity-based breach measure sits deliberately alongside the blunt 60-day tripwire — a Critical finding open 20 days is *already* breached there but wouldn't show up in the 60-day measure. Reporting only one hides risk in one direction or the other.

## Section 4 — On-time %, without survivorship bias

```dax
% Access Reviews Completed On Time (30-Day SLA) =
VAR CompletedOnTime =
    CALCULATE(COUNTROWS(Fact_AccessReview), Fact_AccessReview[DaysOutstanding] <= 30)
RETURN
    DIVIDE(CompletedOnTime, [Total Access Reviews])
```

`DaysOutstanding` is populated for **both** completed reviews (actual days taken) and still-open reviews (elapsed days as of today) — so a review that has sat untouched for 90 days counts against on-time performance immediately, instead of being excluded because it has no completion date yet. Excluding incomplete reviews is a classic survivorship-bias mistake that makes on-time % look best exactly when the backlog is worst.

```dax
Orphaned Accounts (Distinct Users) =
CALCULATE(DISTINCTCOUNT(Fact_AccessReview[UserKey]), Fact_AccessReview[IsOrphanedAccount] = TRUE())

Orphaned Account Rate % =
DIVIDE([Orphaned Accounts (Distinct Users)], DISTINCTCOUNT(Fact_AccessReview[UserKey]))

SoD Conflicts (Distinct Users) =
CALCULATE(DISTINCTCOUNT(Fact_AccessReview[UserKey]), Fact_AccessReview[HasSoDConflict] = TRUE())

SoD Conflict Rate % (of Reviewed Users) =
DIVIDE([SoD Conflicts (Distinct Users)], DISTINCTCOUNT(Fact_AccessReview[UserKey]))
```

`DISTINCTCOUNT`, deliberately not `COUNTROWS`: the same terminated employee can appear flagged across more than one quarterly cycle before the account is finally deprovisioned. Counting rows would count that person 2–3 times and overstate the finding — auditors report orphaned **accounts**, not orphan-detection **events**.

## Section 5 — What-If Parameter: Access Review SLA (30 → 15 days)

**Build steps (Power BI Desktop UI):**
1. Modeling ribbon → New Parameter → Numeric range.
2. Name: `Access Review SLA (Days)`. Data type: Whole number. Min 10, Max 45, Increment 5, Default 30.
3. Power BI auto-creates a **disconnected** table with a generated measure:
   ```dax
   Access Review SLA (Days) Value =
   SELECTEDVALUE('Access Review SLA (Days)'[Access Review SLA (Days)], 30)
   ```
4. Add a Slicer bound to this field — that's the control a GRC manager actually drags on the report page.

**Why a disconnected table, specifically:** the parameter table has *no relationship* to `Fact_AccessReview` or any other table. `SELECTEDVALUE()` reads whatever the slicer is set to and returns it as a plain **scalar** — a number used inside a formula, not a filter propagating through the model. If the parameter table were connected instead, moving the slider to "15" would try to filter `Fact_AccessReview` to rows where some column equals 15, which is not the question being asked at all.

```dax
On-Time % (Dynamic SLA) =
VAR SelectedSLA = [Access Review SLA (Days) Value]
VAR OnTimeCount =
    CALCULATE(COUNTROWS(Fact_AccessReview), Fact_AccessReview[DaysOutstanding] <= SelectedSLA)
RETURN
    DIVIDE(OnTimeCount, [Total Access Reviews])

Backlog Count (Dynamic SLA) =
VAR SelectedSLA = [Access Review SLA (Days) Value]
RETURN
    CALCULATE(COUNTROWS(Fact_AccessReview), Fact_AccessReview[DaysOutstanding] > SelectedSLA)

Incremental Backlog vs Current 30-Day SLA =
VAR SelectedSLA    = [Access Review SLA (Days) Value]
VAR BreachSelected = CALCULATE(COUNTROWS(Fact_AccessReview), Fact_AccessReview[DaysOutstanding] > SelectedSLA)
VAR BreachAt30     = CALCULATE(COUNTROWS(Fact_AccessReview), Fact_AccessReview[DaysOutstanding] > 30)
RETURN
    BreachSelected - BreachAt30
```

**The mechanic, in one sentence:** this measure holds every reviewer's actual, historical completion time fixed (`DaysOutstanding` does not change when the slider moves) and asks only how many of those same reviews would now be classified as breaching, under a stricter policy line drawn through the same data. That's the honest, first-order answer to "what happens if we tighten the SLA" — before anyone has added headcount, automated a system, or changed a process.

**On this dataset:** moving the slider from 30 → 15 takes on-time performance from **77.8% to 46.3%** and adds roughly **2,550 reviews (~31% of the population)** to the backlog overnight, with no change in reviewer capacity. Full numbers in [FINDINGS.md](FINDINGS.md#finding-5).

## Section 6 — Third-party / vendor risk

```dax
Vendors Overdue for Reassessment =
CALCULATE(
    DISTINCTCOUNT(Fact_VendorAssessment[VendorKey]),
    Fact_VendorAssessment[IsLatestAssessment] = TRUE(),
    Fact_VendorAssessment[OverdueForReassessment] = TRUE()
)

% Vendors Overdue for Reassessment =
DIVIDE([Vendors Overdue for Reassessment], DISTINCTCOUNT(Dim_Vendor[VendorKey]))

Avg Open Findings per Vendor (Latest Assessment) =
CALCULATE(AVERAGE(Fact_VendorAssessment[OpenFindingsCount]), Fact_VendorAssessment[IsLatestAssessment] = TRUE())
```

Filtered to `IsLatestAssessment = TRUE()` deliberately: a vendor with three historical assessments on file should be judged "overdue" only against its **most recent** record. Without this filter, a vendor properly reassessed last quarter could still get flagged because an assessment from two years ago looks overdue relative to its own, long-superseded due date.

## Section 7 — Risk heat map (System × Control Category)

1. Insert a **Matrix** visual. Rows = `Dim_ControlCategory[CategoryName]`. Columns = `Dim_System[SystemName]`. Values = `[Control Exception Rate %]`.
2. Format → Cell elements → new rule → **Color scale**: min = green (~0%), mid = amber (~15%), max = red (~30%+). These thresholds come from the dataset itself — amber sits at "above the 13.1% company average," red at "worse than the worst category on record (22.8%)."
3. Add `[Total Control Tests]` as a tooltip field, so a viewer sees sample size before over-reading a small-n cell (several cells have only 8–9 tests, since some categories are tested quarterly/semi-annually).

No new measure is required — `[Control Exception Rate %]` recolors correctly at every Row × Column intersection because each cell simply supplies a different combination of `Dim_ControlCategory` and `Dim_System` to the filter context the measure already respects.
