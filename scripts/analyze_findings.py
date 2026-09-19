import os
import pandas as pd
import numpy as np
import json
from datetime import date

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
TODAY = date(2026, 9, 19)

dim_system = pd.read_csv(f"{D}/Dim_System.csv")
dim_category = pd.read_csv(f"{D}/Dim_ControlCategory.csv")
dim_owner = pd.read_csv(f"{D}/Dim_ControlOwner.csv")
dim_control = pd.read_csv(f"{D}/Dim_Control.csv")
dim_user = pd.read_csv(f"{D}/Dim_User.csv")
dim_vendor = pd.read_csv(f"{D}/Dim_Vendor.csv")
fact_test = pd.read_csv(f"{D}/Fact_ControlTest.csv")
fact_access = pd.read_csv(f"{D}/Fact_AccessReview.csv")
fact_vendor = pd.read_csv(f"{D}/Fact_VendorAssessment.csv")

findings = {}

# --- join helpers ---
ft = fact_test.merge(dim_category, on="ControlCategoryKey").merge(dim_system, on="SystemKey")
ft["NonPass"] = ft["TestResult"].isin(["Fail", "Exception"])

# 1. Exception rate by control category (overall)
by_cat = ft.groupby("CategoryName").agg(
    Tests=("TestResult", "size"),
    NonPass=("NonPass", "sum"),
).reset_index()
by_cat["ExceptionRatePct"] = (by_cat["NonPass"] / by_cat["Tests"] * 100).round(1)
by_cat = by_cat.sort_values("ExceptionRatePct", ascending=False)
findings["exception_rate_by_category"] = by_cat.to_dict("records")

# 2. Aging: avg days open for currently OPEN/IN PROGRESS exceptions, by category
open_items = ft[ft["RemediationStatus"].isin(["Open", "In Progress"])].copy()
open_items["DaysOpen"] = (pd.Timestamp(TODAY) -
                           pd.to_datetime(open_items["RemediationOpenDateKey"], format="%Y%m%d")).dt.days
aging_by_cat = open_items.groupby("CategoryName").agg(
    OpenExceptions=("DaysOpen", "size"),
    AvgDaysOpen=("DaysOpen", "mean"),
    MaxDaysOpen=("DaysOpen", "max"),
).reset_index()
aging_by_cat["AvgDaysOpen"] = aging_by_cat["AvgDaysOpen"].round(0)
aging_by_cat = aging_by_cat.sort_values("AvgDaysOpen", ascending=False)
findings["aging_by_category"] = aging_by_cat.to_dict("records")

# aged exceptions (>60 days open) rate by category
open_items["Aged60"] = open_items["DaysOpen"] > 60
aged_by_cat = open_items.groupby("CategoryName")["Aged60"].agg(["sum", "count"]).reset_index()
aged_by_cat["AgedRatePctOfOpen"] = (aged_by_cat["sum"] / aged_by_cat["count"] * 100).round(1)
findings["aged_over_60d_by_category"] = aged_by_cat.sort_values(
    "AgedRatePctOfOpen", ascending=False).to_dict("records")

# 3. Legacy on-prem vs cloud comparison
by_env = ft.groupby("Environment").agg(
    Tests=("TestResult", "size"), NonPass=("NonPass", "sum")
).reset_index()
by_env["ExceptionRatePct"] = (by_env["NonPass"] / by_env["Tests"] * 100).round(1)
findings["exception_rate_by_environment"] = by_env.to_dict("records")

# 4. System x Category heat-map matrix (exception rate %)
heat = ft.groupby(["SystemName", "CategoryName"]).agg(
    Tests=("TestResult", "size"), NonPass=("NonPass", "sum")
).reset_index()
heat["ExceptionRatePct"] = (heat["NonPass"] / heat["Tests"] * 100).round(1)
findings["heatmap_system_category"] = heat.to_dict("records")

# 5. Overall KPIs
findings["overall_control_exception_rate_pct"] = round(ft["NonPass"].sum() / len(ft) * 100, 1)
findings["overall_fail_rate_pct"] = round((ft["TestResult"] == "Fail").sum() / len(ft) * 100, 1)
findings["total_control_tests"] = int(len(ft))
findings["open_exceptions_count"] = int(len(open_items))
findings["avg_days_open_overall"] = round(open_items["DaysOpen"].mean(), 0)

# worst single system-category cell
worst_cell = heat.sort_values("ExceptionRatePct", ascending=False).iloc[0]
findings["worst_cell"] = worst_cell.to_dict()

# 6. Access review / SoD / orphan stats
findings["total_access_reviews"] = int(len(fact_access))
findings["distinct_orphan_users"] = int(fact_access[fact_access["IsOrphanedAccount"]]["UserKey"].nunique())
findings["orphan_rows"] = int(fact_access["IsOrphanedAccount"].sum())
orphan_by_sys = fact_access[fact_access["IsOrphanedAccount"]].merge(
    dim_system, on="SystemKey").groupby("SystemName").size().reset_index(name="OrphanCount")
findings["orphan_by_system"] = orphan_by_sys.sort_values("OrphanCount", ascending=False).to_dict("records")

findings["distinct_sod_users"] = int(fact_access[fact_access["HasSoDConflict"]]["UserKey"].nunique())
findings["sod_rows"] = int(fact_access["HasSoDConflict"].sum())
sod_by_sys = fact_access[fact_access["HasSoDConflict"]].merge(
    dim_system, on="SystemKey").groupby("SystemName").size().reset_index(name="SoDCount")
findings["sod_by_system"] = sod_by_sys.to_dict("records")

# 7. On-time % at current 30-day SLA and simulated 15-day SLA + backlog delta
for sla in [15, 20, 25, 30, 35, 40, 45]:
    on_time = (fact_access["DaysOutstanding"] <= sla).sum()
    pct = round(on_time / len(fact_access) * 100, 1)
    findings.setdefault("sla_scenarios", []).append({
        "SLA_Days": sla, "OnTimePct": pct, "BreachCount": int(len(fact_access) - on_time)
    })

breach_30 = (fact_access["DaysOutstanding"] > 30).sum()
breach_15 = (fact_access["DaysOutstanding"] > 15).sum()
findings["sla_tighten_30_to_15"] = {
    "breach_count_at_30": int(breach_30),
    "breach_count_at_15": int(breach_15),
    "incremental_backlog": int(breach_15 - breach_30),
    "incremental_backlog_pct_of_total": round((breach_15 - breach_30) / len(fact_access) * 100, 1),
}

# distribution export for the interactive HTML what-if slider (rounded to keep payload small)
findings["days_outstanding_distribution"] = fact_access["DaysOutstanding"].clip(upper=130).astype(int).tolist()

# 8. Vendor risk stats
latest = fact_vendor[fact_vendor["IsLatestAssessment"]]
findings["total_vendors"] = int(len(dim_vendor))
findings["vendors_overdue_reassessment"] = int(latest["OverdueForReassessment"].sum())
findings["high_tier_vendors"] = int((dim_vendor["InherentRiskTier"] == "High").sum())
high_latest = latest.merge(dim_vendor, on="VendorKey")
findings["high_tier_overdue"] = int(
    high_latest[(high_latest["InherentRiskTier_x"] == "High")]["OverdueForReassessment"].sum()
    if "InherentRiskTier_x" in high_latest.columns else
    high_latest[(high_latest["InherentRiskTier"] == "High")]["OverdueForReassessment"].sum()
)
findings["vendors_with_open_findings"] = int((latest["OpenFindingsCount"] > 0).sum())
findings["vendors_with_critical_findings"] = int((latest["CriticalFindingsCount"] > 0).sum())
by_vendor_cat = latest.merge(dim_vendor, on="VendorKey").groupby("ServiceCategory").agg(
    Vendors=("VendorKey", "nunique"),
    AvgOpenFindings=("OpenFindingsCount", "mean"),
    OverdueCount=("OverdueForReassessment", "sum"),
).reset_index()
by_vendor_cat["AvgOpenFindings"] = by_vendor_cat["AvgOpenFindings"].round(2)
findings["vendor_by_category"] = by_vendor_cat.sort_values("AvgOpenFindings", ascending=False).to_dict("records")

# 7b. SLA what-if segmented by system environment (drives the actionable recommendation)
fa_env = fact_access.merge(dim_system, on="SystemKey")
seg_rows = []
for env, grp in fa_env.groupby("Environment"):
    on30 = (grp["DaysOutstanding"] <= 30).sum() / len(grp) * 100
    on15 = (grp["DaysOutstanding"] <= 15).sum() / len(grp) * 100
    seg_rows.append({
        "Environment": env, "N": int(len(grp)),
        "OnTimePct_at30": round(on30, 1), "OnTimePct_at15": round(on15, 1),
        "PtDropIfTightenedTo15": round(on30 - on15, 1),
    })
findings["sla_by_environment"] = seg_rows

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "findings_stats.json")
with open(OUT_JSON, "w") as f:
    json.dump(findings, f, indent=2, default=str)

print(json.dumps({k: v for k, v in findings.items() if k != "days_outstanding_distribution"}, indent=2, default=str))
