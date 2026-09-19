"""
Generate a realistic Technology Controls & Compliance Monitoring dataset
for a Power BI portfolio project (IT Audit / Tech Risk / GRC).

Star-schema (galaxy schema — 3 fact tables share conformed dimensions):

FACTS
  Fact_ControlTest     -> control testing results (pass/fail/exception + remediation)
  Fact_AccessReview    -> user access certification events (orphans, SoD flags, on-time)
  Fact_VendorAssessment-> third-party risk assessments (tier, findings, overdue)

DIMENSIONS (conformed where applicable)
  Dim_Date, Dim_System, Dim_ControlCategory, Dim_ControlOwner, Dim_Control,
  Dim_User, Dim_Vendor

Design choices are intentionally NOT random noise — specific categories/systems
are biased to under- or over-perform so the resulting dataset supports genuine,
defensible audit findings (e.g., Change Management is the weakest category;
legacy on-prem systems lag cloud-native systems; SoD conflicts concentrate in
Finance systems; orphaned accounts concentrate in manually-deprovisioned legacy
systems; a subset of high-risk vendors is overdue for reassessment).
"""

import os
import numpy as np
import pandas as pd
from datetime import date, timedelta
import json

rng = np.random.default_rng(42)

TODAY = date(2026, 9, 19)          # "as of" date used for aging / overdue logic
WINDOW_START = date(2024, 9, 1)    # ~24.5 months of history ending today
CAL_END = date(2027, 3, 31)        # calendar extends a bit past today for due dates

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# ---------------------------------------------------------------------------
# 1. DIM_DATE
# ---------------------------------------------------------------------------
def build_dim_date():
    dates = pd.date_range(date(2024, 1, 1), CAL_END, freq="D")
    d = pd.DataFrame({"Date": dates})
    d["DateKey"] = d["Date"].dt.strftime("%Y%m%d").astype(int)
    d["Year"] = d["Date"].dt.year
    d["MonthNum"] = d["Date"].dt.month
    d["MonthName"] = d["Date"].dt.strftime("%b")
    d["YearMonth"] = d["Date"].dt.strftime("%Y-%m")
    d["Quarter"] = "Q" + d["Date"].dt.quarter.astype(str)
    d["YearQuarter"] = d["Year"].astype(str) + "-" + d["Quarter"]
    # Fiscal year = calendar year here (no FY offset) -- documented assumption
    d["FiscalYear"] = d["Year"]
    d["DayOfWeek"] = d["Date"].dt.day_name()
    d["IsWeekend"] = d["Date"].dt.dayofweek >= 5
    d["Date"] = d["Date"].dt.strftime("%Y-%m-%d")
    return d

dim_date = build_dim_date()
dim_date.to_csv(f"{OUT}/Dim_Date.csv", index=False)


def to_key(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def days_between(d1, d2):
    return (d2 - d1).days


# ---------------------------------------------------------------------------
# 2. DIM_SYSTEM
# ---------------------------------------------------------------------------
systems = [
    # SystemName, BusinessUnit, Criticality, Environment, LegacyFlag
    ("SAP ERP (Finance)",               "Finance",           "Critical", "On-Prem", True),
    ("Oracle Production DB",            "IT",                "Critical", "On-Prem", True),
    ("Active Directory / IAM",          "IT Security",       "Critical", "On-Prem", True),
    ("AWS Cloud Infrastructure",        "IT",                "Critical", "Cloud",   False),
    ("Treasury & Banking Portal",       "Finance",           "Critical", "Hybrid",  False),
    ("Workday HCM",                     "Human Resources",   "High",     "Cloud",   False),
    ("Salesforce CRM",                  "Sales",             "High",     "Cloud",   False),
    ("Enterprise Data Warehouse",       "Data & Analytics",  "High",     "Cloud",   False),
    ("ServiceNow ITSM",                 "IT",                "Medium",   "Cloud",   False),
    ("Payroll System (ADP)",            "Human Resources",   "High",     "Cloud",   False),
]
dim_system = pd.DataFrame(systems, columns=[
    "SystemName", "BusinessUnit", "Criticality", "Environment", "LegacyOnPrem"
])
dim_system.insert(0, "SystemKey", range(1, len(dim_system) + 1))
dim_system.to_csv(f"{OUT}/Dim_System.csv", index=False)

# ---------------------------------------------------------------------------
# 3. DIM_CONTROLCATEGORY  (+ NIST CSF function mapping, base risk parameters)
# ---------------------------------------------------------------------------
categories = [
    # CategoryName, NISTFunction, TestFrequency, ControlType, BaseExceptionRate, AvgRemediationDaysHealthy
    ("Access Management",                 "Protect", "Monthly",     "Preventive", 0.12, 25),
    ("Segregation of Duties",             "Protect", "Quarterly",   "Detective",  0.15, 35),
    ("Change Management",                 "Protect", "Monthly",     "Preventive", 0.22, 70),
    ("Logical Security & Authentication", "Protect", "Quarterly",   "Preventive", 0.08, 20),
    ("Backup & Recovery",                 "Recover", "Monthly",     "Detective",  0.05, 15),
    ("Encryption & Data Protection",      "Protect", "Semi-Annual", "Preventive", 0.06, 30),
    ("Vendor & Third-Party Oversight",    "Identify","Quarterly",   "Detective",  0.10, 45),
    ("Incident Response & Monitoring",    "Detect",  "Monthly",     "Detective",  0.10, 10),
]
dim_category = pd.DataFrame(categories, columns=[
    "CategoryName", "NISTFunction", "TestFrequency", "ControlType",
    "BaseExceptionRate", "AvgRemediationDaysHealthy"
])
dim_category.insert(0, "ControlCategoryKey", range(1, len(dim_category) + 1))
dim_category.to_csv(f"{OUT}/Dim_ControlCategory.csv", index=False)

# ---------------------------------------------------------------------------
# 4. DIM_CONTROLOWNER
# ---------------------------------------------------------------------------
owners = [
    ("IT Security - Identity & Access Manager", "IT Security"),
    ("Compliance Manager - SoD Governance",      "Compliance"),
    ("IT Operations - Change Manager",           "IT Operations"),
    ("Network Security Engineer",                "IT Security"),
    ("Infrastructure Lead - Backup & DR",        "Infrastructure"),
    ("Security Engineer - Data Protection",      "IT Security"),
    ("Procurement / Vendor Risk Manager",        "Procurement"),
    ("SOC Manager - Security Monitoring",        "IT Security"),
]
dim_owner = pd.DataFrame(owners, columns=["OwnerName", "Department"])
dim_owner.insert(0, "OwnerKey", range(1, len(dim_owner) + 1))
dim_owner.to_csv(f"{OUT}/Dim_ControlOwner.csv", index=False)
# category -> owner mapping (1:1 by design; realistic in practice)
category_owner_map = {i + 1: i + 1 for i in range(len(categories))}

print("Dims (System/Category/Owner/Date) written.")

# ---------------------------------------------------------------------------
# 5. DIM_CONTROL  (one control per System x Category = 80 controls)
# ---------------------------------------------------------------------------
control_rows = []
control_id_counter = 1
for _, sysr in dim_system.iterrows():
    for _, catr in dim_category.iterrows():
        prefix = "".join([w[0] for w in catr["CategoryName"].split()[:3]]).upper()
        control_id = f"{prefix}-{sysr['SystemKey']:02d}{catr['ControlCategoryKey']:02d}"
        control_name = f"{catr['CategoryName']} Control - {sysr['SystemName']}"
        control_rows.append({
            "ControlKey": control_id_counter,
            "ControlID": control_id,
            "ControlName": control_name,
            "SystemKey": sysr["SystemKey"],
            "ControlCategoryKey": catr["ControlCategoryKey"],
            "OwnerKey": category_owner_map[catr["ControlCategoryKey"]],
            "TestFrequency": catr["TestFrequency"],
            "ControlType": catr["ControlType"],
        })
        control_id_counter += 1
dim_control = pd.DataFrame(control_rows)
dim_control.to_csv(f"{OUT}/Dim_Control.csv", index=False)

# ---------------------------------------------------------------------------
# 6. FACT_CONTROLTEST
# ---------------------------------------------------------------------------
FREQ_MONTHS = {"Monthly": 1, "Quarterly": 3, "Semi-Annual": 6, "Annual": 12}


def test_dates_for(freq):
    """Return list of test dates from WINDOW_START through TODAY at the given cadence,
    landing on the ~15th of the applicable month for realism."""
    step = FREQ_MONTHS[freq]
    dates = []
    cur = date(WINDOW_START.year, WINDOW_START.month, 15)
    while cur <= TODAY:
        dates.append(cur)
        m = cur.month + step
        y = cur.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        cur = date(y, m, 15)
    return dates


sys_lookup = dim_system.set_index("SystemKey")
cat_lookup = dim_category.set_index("ControlCategoryKey")

test_rows = []
test_id = 1
for _, ctrl in dim_control.iterrows():
    sysinfo = sys_lookup.loc[ctrl["SystemKey"]]
    catinfo = cat_lookup.loc[ctrl["ControlCategoryKey"]]
    base_rate = catinfo["BaseExceptionRate"]
    # legacy on-prem systems carry higher exception risk; hybrid a bit; cloud a touch lower
    if sysinfo["Environment"] == "On-Prem":
        env_adj = 0.08
    elif sysinfo["Environment"] == "Hybrid":
        env_adj = 0.03
    else:
        env_adj = -0.015
    non_pass_rate = min(max(base_rate + env_adj, 0.01), 0.60)

    dates = test_dates_for(ctrl["TestFrequency"])
    for td in dates:
        roll = rng.random()
        if roll > non_pass_rate:
            result = "Pass"
        else:
            # split non-pass into Exception (lower severity) vs Fail (control breakdown)
            fail_share = 0.45 if catinfo["CategoryName"] == "Change Management" else 0.25
            result = "Fail" if rng.random() < fail_share else "Exception"

        severity = None
        remediation_status = "N/A"
        open_dt = None
        due_dt = None
        close_dt = None
        days_open_at_close = None

        if result in ("Fail", "Exception"):
            # severity skews higher for Change Mgmt / Access Mgmt, lower for Backup/Encryption
            sev_weights = {
                "Change Management": [0.35, 0.35, 0.22, 0.08],
                "Access Management": [0.20, 0.35, 0.30, 0.15],
                "Segregation of Duties": [0.25, 0.35, 0.28, 0.12],
            }.get(catinfo["CategoryName"], [0.08, 0.22, 0.40, 0.30])
            severity = rng.choice(["Critical", "High", "Medium", "Low"], p=sev_weights)

            open_dt = td
            sla_days = {"Critical": 15, "High": 30, "Medium": 60, "Low": 90}[severity]
            due_dt = open_dt + timedelta(days=sla_days)

            # expected close time: category healthy-average, inflated for Fail vs Exception,
            # and a "chronic backlog" tail injected for Change Management specifically
            base_days = catinfo["AvgRemediationDaysHealthy"] * (1.3 if result == "Fail" else 1.0)
            noise_days = rng.gamma(shape=2.0, scale=base_days / 2.0)
            if catinfo["CategoryName"] == "Change Management" and rng.random() < 0.22:
                noise_days += rng.uniform(90, 220)  # chronic backlog tail
            close_after = int(round(noise_days))

            candidate_close = open_dt + timedelta(days=close_after)
            if candidate_close <= TODAY:
                close_dt = candidate_close
                remediation_status = "Closed"
                days_open_at_close = close_after
            else:
                close_dt = None
                days_since_open = days_between(open_dt, TODAY)
                remediation_status = "In Progress" if days_since_open < close_after * 0.6 else "Open"

        test_rows.append({
            "TestKey": test_id,
            "ControlKey": ctrl["ControlKey"],
            "SystemKey": ctrl["SystemKey"],
            "ControlCategoryKey": ctrl["ControlCategoryKey"],
            "OwnerKey": ctrl["OwnerKey"],
            "TestDateKey": to_key(td),
            "TestResult": result,
            "ExceptionSeverity": severity if severity else "N/A",
            "RemediationStatus": remediation_status,
            "RemediationOpenDateKey": to_key(open_dt) if open_dt else None,
            "RemediationDueDateKey": to_key(due_dt) if due_dt else None,
            "RemediationCloseDateKey": to_key(close_dt) if close_dt else None,
        })
        test_id += 1

fact_control_test = pd.DataFrame(test_rows)
fact_control_test.to_csv(f"{OUT}/Fact_ControlTest.csv", index=False)
print(f"Fact_ControlTest rows: {len(fact_control_test)}")
print(fact_control_test["TestResult"].value_counts())

# ---------------------------------------------------------------------------
# 7. DIM_USER
# ---------------------------------------------------------------------------
FIRST_NAMES = ["James","Maria","Robert","Linda","Michael","Susan","David","Karen",
               "John","Patricia","Daniel","Jennifer","Thomas","Elizabeth","Mark","Lisa",
               "Paul","Nancy","Steven","Betty","Kevin","Sandra","Brian","Ashley","Jason",
               "Emily","Ryan","Kimberly","Jacob","Michelle","Gary","Amanda","Nathan","Laura",
               "Adam","Rachel","Eric","Samantha","Stephen","Rebecca","Jonathan","Stephanie",
               "Larry","Nicole","Justin","Christina","Scott","Melissa","Brandon","Amy"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
              "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
              "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White",
              "Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker","Young",
              "Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores","Green"]

DEPARTMENTS = ["Finance", "Human Resources", "Sales", "IT", "Data & Analytics",
               "Operations", "Executive"]
DEPT_WEIGHTS = [0.18, 0.10, 0.20, 0.22, 0.10, 0.16, 0.04]

DEPT_TITLES = {
    "Finance": ["AP Processor", "AP Approver", "GL Preparer", "GL Approver",
                "Payment Initiator", "Payment Approver", "Financial Analyst"],
    "Human Resources": ["HR Generalist", "HRIS Analyst", "Payroll Specialist", "HR Manager"],
    "Sales": ["Account Executive", "Sales Manager", "Sales Ops Analyst"],
    "IT": ["System Administrator", "Database Administrator", "Cloud Engineer",
           "Help Desk Analyst", "IT Manager"],
    "Data & Analytics": ["Data Analyst", "Data Engineer", "BI Developer"],
    "Operations": ["Operations Analyst", "Operations Manager", "Supply Chain Analyst"],
    "Executive": ["VP", "Director", "Chief of Staff"],
}

DEPT_SYSTEMS = {
    "Finance": ["SAP ERP (Finance)", "Treasury & Banking Portal", "Enterprise Data Warehouse"],
    "Human Resources": ["Workday HCM", "Payroll System (ADP)"],
    "Sales": ["Salesforce CRM", "Enterprise Data Warehouse"],
    "IT": ["Active Directory / IAM", "AWS Cloud Infrastructure", "Oracle Production DB",
           "ServiceNow ITSM", "Enterprise Data Warehouse"],
    "Data & Analytics": ["Enterprise Data Warehouse", "Oracle Production DB",
                          "AWS Cloud Infrastructure"],
    "Operations": ["ServiceNow ITSM", "SAP ERP (Finance)"],
    "Executive": ["SAP ERP (Finance)", "Salesforce CRM", "Enterprise Data Warehouse"],
}

N_USERS = 500
sys_name_to_key = dim_system.set_index("SystemName")["SystemKey"].to_dict()

user_rows = []
user_system_assign = []   # (UserKey, SystemKey, ConflictFlag)
for uid in range(1, N_USERS + 1):
    dept = rng.choice(DEPARTMENTS, p=DEPT_WEIGHTS)
    title = rng.choice(DEPT_TITLES[dept])
    fname, lname = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    hire_offset = int(rng.integers(30, 2500))
    hire_date = TODAY - timedelta(days=hire_offset)
    is_terminated = rng.random() < 0.11
    term_date = None
    if is_terminated:
        term_offset = int(rng.integers(20, days_between(WINDOW_START, TODAY) - 10))
        term_date = WINDOW_START + timedelta(days=term_offset)

    user_rows.append({
        "UserKey": uid,
        "UserName": f"{fname} {lname}",
        "Department": dept,
        "JobTitle": title,
        "EmploymentStatus": "Terminated" if is_terminated else "Active",
        "HireDateKey": to_key(hire_date),
        "TerminationDateKey": to_key(term_date) if term_date else None,
    })

    eligible = DEPT_SYSTEMS[dept]
    n_sys = min(len(eligible), int(rng.integers(1, 4)))
    chosen = list(rng.choice(eligible, size=n_sys, replace=False))
    # SoD-sensitive conflicting duties: only meaningful for Finance users on
    # SAP ERP / Treasury who hold two conflicting transactional roles
    conflict_flag = False
    if dept == "Finance" and title in ("AP Processor", "AP Approver", "GL Preparer",
                                        "GL Approver", "Payment Initiator", "Payment Approver"):
        if rng.random() < 0.14:
            conflict_flag = True
    for s in chosen:
        user_system_assign.append((uid, sys_name_to_key[s], conflict_flag and s in
                                    ("SAP ERP (Finance)", "Treasury & Banking Portal")))

dim_user = pd.DataFrame(user_rows)
dim_user.to_csv(f"{OUT}/Dim_User.csv", index=False)
print(f"Dim_User rows: {len(dim_user)}  (terminated: {dim_user['EmploymentStatus'].eq('Terminated').sum()})")

# ---------------------------------------------------------------------------
# 8. FACT_ACCESSREVIEW  (quarterly certification cycles)
# ---------------------------------------------------------------------------
def quarter_starts(start, end):
    qs = []
    y, m = start.year, ((start.month - 1) // 3) * 3 + 1
    cur = date(y, m, 1)
    while cur <= end:
        qs.append(cur)
        m2 = m + 3
        y2 = y + (m2 - 1) // 12
        m2 = (m2 - 1) % 12 + 1
        y, m = y2, m2
        cur = date(y, m, 1)
    return qs

CYCLES = quarter_starts(WINDOW_START, TODAY)  # ~8 cycles
BASELINE_SLA = 30

owner_by_system = {
    "SAP ERP (Finance)": 1, "Treasury & Banking Portal": 1, "Oracle Production DB": 1,
    "Active Directory / IAM": 1, "Workday HCM": 1, "Payroll System (ADP)": 1,
    "Salesforce CRM": 1, "Enterprise Data Warehouse": 1, "AWS Cloud Infrastructure": 1,
    "ServiceNow ITSM": 1,
}  # all access reviews owned by Identity & Access Manager (OwnerKey=1), realistic single-owner process

sys_key_to_env = dim_system.set_index("SystemKey")["Environment"].to_dict()
sys_key_to_name = dim_system.set_index("SystemKey")["SystemName"].to_dict()

access_rows = []
review_id = 1
# pre-compute per terminated user-system a "deprovisioned after N days" value
deprov_delay = {}
for uid, skey, _ in user_system_assign:
    env = sys_key_to_env[skey]
    if env == "Cloud":
        delay = int(rng.integers(1, 10))       # auto-deprovisioning workflows
    elif env == "Hybrid":
        delay = int(rng.integers(10, 60))
    else:  # On-Prem: manual ticket-driven deprovisioning -> slow & risky
        delay = int(rng.integers(20, 220))
    deprov_delay[(uid, skey)] = delay

# conflict duration: how many consecutive cycles an SoD conflict persists before remediated
conflict_duration_cycles = {}

user_term = dim_user.set_index("UserKey")["TerminationDateKey"].to_dict()

for uid, skey, conflict_flag in user_system_assign:
    term_key = user_term[uid]
    term_date = None
    if term_key is not None and not (isinstance(term_key, float) and pd.isna(term_key)):
        term_date = pd.to_datetime(str(int(term_key)), format="%Y%m%d").date()
    dep_delay = deprov_delay[(uid, skey)]
    deprovisioned_date = term_date + timedelta(days=dep_delay) if term_date else None

    if conflict_flag:
        conflict_duration_cycles[(uid, skey)] = int(rng.integers(2, 5))
    cycles_flagged = 0

    for cyc in CYCLES:
        # stop generating reviews once user has left AND access has been fully deprovisioned
        if term_date and deprovisioned_date and cyc > deprovisioned_date:
            continue
        # skip cycles before the user was even hired (rough: skip if cycle before WINDOW_START, n/a here)

        is_orphan = bool(term_date and cyc >= term_date and (deprovisioned_date is None or cyc < deprovisioned_date))

        env = sys_key_to_env[skey]
        mean_days = {"On-Prem": 32, "Hybrid": 26, "Cloud": 16}[env]
        assigned = cyc
        raw_days = rng.gamma(shape=2.0, scale=mean_days / 2.0)
        days_to_complete = int(np.clip(round(raw_days), 1, 130))
        completed_date = assigned + timedelta(days=days_to_complete)

        # most recent 1-2 cycles: some legitimately still in progress if not yet due
        if completed_date <= TODAY:
            status = "Completed"
            completed_key = to_key(completed_date)
            days_outstanding = days_to_complete
        else:
            elapsed = days_between(assigned, TODAY)
            completed_key = None
            days_outstanding = elapsed
            status = "Overdue" if elapsed > BASELINE_SLA else "In Progress"

        has_sod = False
        if conflict_flag and (uid, skey) in conflict_duration_cycles:
            if cycles_flagged < conflict_duration_cycles[(uid, skey)]:
                has_sod = True
                cycles_flagged += 1

        access_rows.append({
            "ReviewKey": review_id,
            "UserKey": uid,
            "SystemKey": skey,
            "OwnerKey": owner_by_system[sys_key_to_name[skey]],
            "CycleDateKey": to_key(assigned),
            "ReviewCompletedDateKey": completed_key,
            "ReviewStatus": status,
            "DaysOutstanding": days_outstanding,
            "IsOrphanedAccount": bool(is_orphan),
            "HasSoDConflict": bool(has_sod),
        })
        review_id += 1

fact_access_review = pd.DataFrame(access_rows)
fact_access_review.to_csv(f"{OUT}/Fact_AccessReview.csv", index=False)
print(f"Fact_AccessReview rows: {len(fact_access_review)}")
print(f"  Orphaned-account rows: {fact_access_review['IsOrphanedAccount'].sum()}")
print(f"  SoD-conflict rows: {fact_access_review['HasSoDConflict'].sum()}")
print(fact_access_review["ReviewStatus"].value_counts())

# ---------------------------------------------------------------------------
# 9. DIM_VENDOR
# ---------------------------------------------------------------------------
VENDOR_CATS = [
    ("Cloud Hosting", "High", 12),
    ("Payment Processing", "High", 12),
    ("Payroll Processing", "High", 12),
    ("Data Processing / Analytics", "High", 12),
    ("SaaS Application", "Medium", 18),
    ("Professional Services / Consulting", "Medium", 18),
    ("Facilities / Physical Security", "Low", 24),
    ("Legal / Compliance Services", "Low", 24),
]
VENDOR_NAME_STEMS = ["Nimbus","Meridian","Solstice","Vantage","Ironclad","Beacon","Crestline",
                     "Harborview","Northgate","Silverline","Bluepeak","Redshift","Alderbrook",
                     "Pinegrove","Fairmont","Wellspring","Cobalt","Granite","Lumen","Cascadia",
                     "Anchorpoint","Brightfield","Foxglove","Ridgeline","Summit"]

vendor_rows = []
vk = 1
for stem in VENDOR_NAME_STEMS:
    cat, tier, cadence = VENDOR_CATS[(vk - 1) % len(VENDOR_CATS)]
    vendor_rows.append({
        "VendorKey": vk,
        "VendorName": f"{stem} {cat.split('/')[0].strip()}" if False else f"{stem} {['Corp','Group','Partners','Solutions','Systems'][vk % 5]}",
        "ServiceCategory": cat,
        "InherentRiskTier": tier,
        "AssessmentCadenceMonths": cadence,
    })
    vk += 1
dim_vendor = pd.DataFrame(vendor_rows)
dim_vendor.to_csv(f"{OUT}/Dim_Vendor.csv", index=False)

# ---------------------------------------------------------------------------
# 10. FACT_VENDORASSESSMENT
# ---------------------------------------------------------------------------
vendor_assess_rows = []
va_id = 1
# deliberately push a meaningful share of High-tier vendors into "overdue for reassessment"
# to support a genuine third-party-oversight finding
overdue_high_tier_vendor_keys = set(
    dim_vendor[dim_vendor["InherentRiskTier"] == "High"]["VendorKey"].sample(
        frac=0.35, random_state=7
    )
)

for _, v in dim_vendor.iterrows():
    cadence = v["AssessmentCadenceMonths"]
    tier = v["InherentRiskTier"]
    findings_mean = {"High": 2.6, "Medium": 1.2, "Low": 0.4}[tier]

    # first assessment offset so vendors aren't all assessed on the same calendar day
    offset_days = int(rng.integers(0, cadence * 30))
    cur = WINDOW_START - timedelta(days=cadence * 30) + timedelta(days=offset_days)
    assessments_for_vendor = []
    while cur <= TODAY:
        if cur >= date(2024, 1, 1):
            assessments_for_vendor.append(cur)
        cur = cur + timedelta(days=cadence * 30)

    # if this vendor is flagged overdue, drop its most recent scheduled assessment
    if v["VendorKey"] in overdue_high_tier_vendor_keys and len(assessments_for_vendor) > 1:
        assessments_for_vendor = assessments_for_vendor[:-1]

    for i, adate in enumerate(assessments_for_vendor):
        open_findings = int(rng.poisson(findings_mean))
        critical_findings = int(rng.binomial(open_findings, 0.25)) if open_findings > 0 else 0
        residual_tier = tier
        if critical_findings >= 1 and tier == "Medium":
            residual_tier = "High"
        elif critical_findings >= 2 and tier == "Low":
            residual_tier = "Medium"
        next_due = adate + timedelta(days=cadence * 30)
        is_latest = (i == len(assessments_for_vendor) - 1)
        overdue_now = bool(is_latest and next_due < TODAY)

        vendor_assess_rows.append({
            "AssessmentKey": va_id,
            "VendorKey": v["VendorKey"],
            "AssessmentDateKey": to_key(adate),
            "NextDueDateKey": to_key(next_due),
            "InherentRiskTier": tier,
            "ResidualRiskTier": residual_tier,
            "OpenFindingsCount": open_findings,
            "CriticalFindingsCount": critical_findings,
            "IsLatestAssessment": is_latest,
            "OverdueForReassessment": overdue_now,
        })
        va_id += 1

fact_vendor_assessment = pd.DataFrame(vendor_assess_rows)
fact_vendor_assessment.to_csv(f"{OUT}/Fact_VendorAssessment.csv", index=False)
print(f"Dim_Vendor rows: {len(dim_vendor)}")
print(f"Fact_VendorAssessment rows: {len(fact_vendor_assessment)}")
print(f"  Overdue-for-reassessment (latest only): "
      f"{fact_vendor_assessment[fact_vendor_assessment['IsLatestAssessment']]['OverdueForReassessment'].sum()}")

print("\nAll tables written to", OUT)


