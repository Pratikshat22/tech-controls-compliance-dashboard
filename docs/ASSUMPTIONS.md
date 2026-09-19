# Assumptions & Limitations

Stated plainly, because a good analyst names their assumptions rather than letting a reader discover them.

- The dataset is **simulated** with a fixed random seed (`42`) and deliberately embedded patterns (Change Management weaker, legacy on-prem weaker, orphans concentrated in manual-deprovisioning systems, etc.) so the model has genuine signal to analyze. It is not drawn from any real organization. Running [`scripts/generate_dataset.py`](../scripts/generate_dataset.py) reproduces it byte-for-byte.
- Aging and overdue measures use `TODAY()` and are therefore **point-in-time** — every number in this repo reflects a snapshot taken **September 19, 2026**. Re-running the scripts or reopening the workbook on a later date will shift aging/overdue figures, which is expected behavior for a snapshot metric, not a data issue.
- Access review cadence is modeled as strictly quarterly with a single reviewer role (Identity & Access Manager) owning all systems. A real environment typically has system-specific reviewers and sometimes annual (not quarterly) cycles for lower-risk systems — simplified here to keep the fact table's grain consistent and legible.
- Remediation due dates are derived purely from a severity-to-SLA mapping (Critical = 15 / High = 30 / Medium = 60 / Low = 90 days) applied uniformly across all control categories. A real GRC program often sets category-specific SLAs — this model uses one severity-based rule for simplicity and transparency.
- Several System × Category combinations in the heat map have small sample sizes (as few as 4–9 tests) because those categories are tested quarterly or semi-annually over a 24-month window. These cells are directionally useful but shouldn't be treated with the same statistical confidence as high-volume cells — flagged explicitly in [FINDINGS.md](FINDINGS.md#a-note-on-statistical-confidence).
- Vendor risk tiering (inherent and residual) is a simplified two-factor model (service category sets inherent tier; critical findings escalate residual tier by one level) for illustration. Real third-party risk programs typically weigh data sensitivity, business criticality, and geographic/regulatory exposure as separate inputs.

## Why there's no `.pbix` file in this repo

Power BI Desktop is a Windows application and wasn't available in the environment this project was built in. Everything needed to reproduce the report natively **is** here — it's a mechanical, fully-specified build:

1. Import [`powerbi/GRC_Tech_Controls_Dataset.xlsx`](../powerbi/GRC_Tech_Controls_Dataset.xlsx) (Get Data → Excel workbook; the workbook's own README sheet repeats the steps below).
2. Build the relationships in [DATA_MODEL.md](DATA_MODEL.md#relationships-to-build-in-power-bi-model-view). Mark `Dim_Date` as a Date Table.
3. Add the calculated columns and every measure from [`powerbi/DAX_Measures.dax.txt`](../powerbi/DAX_Measures.dax.txt) (or the annotated version, [DAX_MEASURES.md](DAX_MEASURES.md)), in order — later measures reference earlier ones.
4. Build the report pages: an executive KPI page, the System × Category heat map (Matrix + conditional formatting), a remediation-aging bar chart, the What-If SLA page (Numeric range parameter + slicer), an identity-risk page, and a vendor-risk page.
5. Validate: every number in [FINDINGS.md](FINDINGS.md) should reproduce exactly, because it was computed with the same logic the DAX measures implement (see [`scripts/analyze_findings.py`](../scripts/analyze_findings.py)).

The [live interactive preview](https://claude.ai/artifact/71M4HZGNHiZwK43xD1iqGx) reproduces the same numbers client-side against the real `Fact_AccessReview` data — moving its SLA slider from 30 to 15 gives the identical 77.8% → 46.3% on-time result and +2,550 backlog figure documented in FINDINGS.md. That agreement is a correctness check on the whole pipeline: dataset, DAX design, and prototype all reduce to the same numbers.
