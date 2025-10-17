# pages/10_Executive_Overview.py
# Executive Project Overview (service projects: people x hours)
# KPIs + 4 key charts + variance tables — static demo data, API-ready

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Executive Project Overview", layout="wide")

# ===================== DEMO DATA (replace with API later) =====================
PROJECT = {
    "project_id": "PRJ-001",
    "name": "Project Phoenix",
    "start_date": date(2025, 1, 10),
    "end_date":   date(2025, 12, 31),
    "budget_hours": 4200.0,
    "budget_cost":  3_600_000.0,
    "budget_revenue": 5_000_000.0,   # if you don’t have this, use contract value
    "default_rate": 800.0,
    "status": "Active",
}

EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0,8.0],
    ["E-02","Lina","Eng",950.0,8.0],
    ["E-03","Omar","Tech",600.0,8.0],
], columns=["employee_id","name","role","default_rate","capacity_hours_per_day"])

TASKS = pd.DataFrame([
    ["T-001","Planning","E-01","Planning",       80, date(2025,2,10),"Done","High", None],
    ["T-002","Modeling","E-02","Engineering",   200, date(2025,7,15),"In Progress","High", None],
    ["T-003","Field Scanning","E-03","Field",   260, date(2025,8,10),"In Progress","Medium", 650.0],
    ["T-004","QA & Docs","E-02","QA",           140, date(2025,9,10),"Todo","Low", None],
    ["T-005","Client Reviews","E-01","Admin",    60, date(2025,10,5),"Todo","Low", None],
], columns=["task_id","title","assignee_id","category","estimate_hours","due_date","status","priority","override_rate"])

# Simulated month-by-month time entries (Jan→Sep)
rng = np.random.RandomState(9)
entries = []
for t in TASKS.itertuples():
    for d in pd.date_range("2025-01-15","2025-09-30", freq="14D"):
        hrs = rng.randint(6, 60) if t.status!="Done" or d.month<=2 else rng.randint(4, 25)
        if hrs>0:
            entries.append([f"TE-{t.task_id}-{d.date()}", t.task_id, PROJECT["project_id"], t.assignee_id, d.date(), float(hrs), True, None, f"log {t.title}"])
TIMEENTRIES = pd.DataFrame(entries, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# Demo billing / collections
BILLING = pd.DataFrame([
    ["INV-001", PROJECT["project_id"], date(2025,3,5),  320_000, 320_000, "collected"],
    ["INV-002", PROJECT["project_id"], date(2025,5,10), 480_000, 300_000, "partially_collected"],
    ["INV-003", PROJECT["project_id"], date(2025,7,8),  620_000,   0,     "issued"],
], columns=["invoice_no","project_id","date","amount","collected_amount","status"])

# ===================== HELPERS =====================
def month_start(d): 
    ts = pd.to_datetime(d); return pd.Timestamp(ts.year, ts.month, 1)

def effective_rate(row):
    # rate_at_entry -> task.override_rate -> employee.default_rate -> project.default_rate
    if pd.notna(row.get("rate_at_entry")): return float(row["rate_at_entry"])
    tr = TASKS.loc[TASKS["task_id"]==row["task_id"], "override_rate"]
    if not tr.empty and pd.notna(tr.iloc[0]): return float(tr.iloc[0])
    er = EMPLOYEES.loc[EMPLOYEES["employee_id"]==row["employee_id"], "default_rate"].iloc[0]
    if pd.notna(er): return float(er)
    return float(PROJECT["default_rate"])

def pct(n, d): 
    return (n/d*100) if d else 0.0

def money(x): 
    try: return f"{float(x):,.0f}"
    except: return "0"

# ===================== CALCULATIONS =====================
# Costing
TE = TIMEENTRIES.copy()
TE["rate"] = TE.apply(effective_rate, axis=1)
TE["cost"] = TE["hours"] * TE["rate"]
TE["Month"] = TE["date"].apply(month_start)

hours_consumed = TE["hours"].sum()
cost_consumed  = TE["cost"].sum()
budget_hours   = PROJECT["budget_hours"]
budget_cost    = PROJECT["budget_cost"]
budget_rev     = PROJECT["budget_revenue"]

# ETC/EAC
logged_by_task = TE.groupby("task_id")["hours"].sum().reindex(TASKS["task_id"]).fillna(0)
remaining_by_task = (TASKS.set_index("task_id")["estimate_hours"] - logged_by_task).clip(lower=0)
ETC_hours = float(remaining_by_task.sum())
blended_rate = float(TE["rate"].mean() if not TE.empty else PROJECT["default_rate"])
EAC_cost = cost_consumed + ETC_hours * blended_rate

# SPI/CPI (simple proxies)
planned_done = TASKS["status"].eq("Done").mean()  # planned % as proxy in demo
actual_done = (logged_by_task / TASKS.set_index("task_id")["estimate_hours"]).clip(0,1).mean()
SPI = actual_done / max(planned_done, 0.01)
EV = actual_done * budget_cost
AC = cost_consumed
CPI = (EV / AC) if AC else 1.0

# Revenue / margin
revenue_to_date = BILLING["amount"].sum()
gm = revenue_to_date - cost_consumed
gm_pct = pct(gm, revenue_to_date)
forecast_margin_pct = pct(budget_rev - EAC_cost, budget_rev)

# Realization (billed vs billable)
billable_hours = TE.loc[TE["billable"], "hours"].sum()
# if you bill per hour, billed_hours ≈ amount / avg_bill_rate (demo simple)
avg_bill_rate = 950.0
billed_hours_approx = BILLING["amount"].sum() / avg_bill_rate if avg_bill_rate else 0
realization = pct(billed_hours_approx, billable_hours)

# Utilization (team-level during project window)
proj_days = max((PROJECT["end_date"] - PROJECT["start_date"]).days+1, 1)
calendar = pd.date_range(PROJECT["start_date"], PROJECT["end_date"], freq="D")
workdays = int((calendar.weekday < 5).sum())
team_capacity = (EMPLOYEES["capacity_hours_per_day"].mean() * workdays)  # simple proxy
utilization = pct(billable_hours, team_capacity)

# Burn-ups
months = pd.date_range("2025-01-01", "2025-12-01", freq="MS")
burn = TE.groupby("Month")[["hours","cost"]].sum().sort_index().cumsum().reindex(months, fill_value=0).ffill()
burn["Budget Hours"] = budget_hours
burn["Budget Cost"]  = budget_cost

# Schedule health (% complete over time, simple)
sched = (TE.groupby("Month")["hours"].sum().cumsum() / max(budget_hours, 1)).clip(0,1)
sched = sched.reindex(months, fill_value=0).ffill()
planned = pd.Series(np.linspace(0, 1, len(months)), index=months)  # linear plan (demo)

# ===================== UI =====================
st.title("📈 Executive Project Overview")
st.write(f"**Project:** {PROJECT['name']} • **Status:** {PROJECT['status']} • **Billing:** T&M")

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("Revenue to date", f"{money(revenue_to_date)}")
k2.metric("Cost to date", f"{money(cost_consumed)}", f"GM {money(gm)}")
k3.metric("GM%", f"{gm_pct:.0f}%")
k4.metric("Budget used (hrs)", f"{pct(hours_consumed, budget_hours):.0f}%")
k5.metric("EAC (cost)", f"{money(EAC_cost)}", f"ETC {ETC_hours:.0f}h")
k6.metric("Forecast Margin%", f"{forecast_margin_pct:.0f}%")

k7,k8,k9 = st.columns(3)
k7.metric("Utilization", f"{utilization:.0f}%")
k8.metric("Realization", f"{realization:.0f}%")
k9.metric("SPI / CPI", f"{SPI:.2f}", f"CPI {CPI:.2f}")

st.subheader("Burn-up (Hours & Cost)")
c1,c2 = st.columns(2)
with c1:
    st.write("Cumulative Hours vs Budget")
    st.line_chart(burn[["hours","Budget Hours"]].rename(columns={"hours":"Consumed"}))
with c2:
    st.write("Cumulative Cost vs Budget")
    st.line_chart(burn[["cost","Budget Cost"]].rename(columns={"cost":"Consumed"}))

st.subheader("Earned vs Actual & Schedule Health")
c3,c4 = st.columns(2)
with c3:
    ev_ac = pd.DataFrame({"EV (Planned Value)": burn["Budget Cost"]*sched, "AC (Actual Cost)": burn["cost"]}, index=months)
    st.line_chart(ev_ac)
with c4:
    sh = pd.DataFrame({"Planned %": planned, "Actual %": sched}, index=months)
    st.line_chart(sh)

st.subheader("Task / Workpackage Variance")
task = TASKS.copy()
task["Logged"] = TASKS["task_id"].map(logged_by_task).fillna(0.0)
task["Remaining"] = (task["estimate_hours"] - task["Logged"]).clip(lower=0)
task["Over/Under (h)"] = task["Logged"] - task["estimate_hours"]
st.dataframe(
    task[["title","assignee_id","category","estimate_hours","Logged","Remaining","status","due_date","priority","Over/Under (h)"]]
      .rename(columns={"title":"Task","assignee_id":"Assignee","estimate_hours":"Est. Hrs"})
      .style.format({"Est. Hrs":"{:.1f}","Logged":"{:.1f}","Remaining":"{:.1f}","Over/Under (h)":"{:+.1f}"}),
    use_container_width=True
)

st.subheader("Staffing Mix & Rates")
by_emp = TE.groupby("employee_id")[["hours","cost"]].sum().reset_index()
by_emp["name"] = by_emp["employee_id"].map(EMPLOYEES.set_index("employee_id")["name"])
by_emp["Eff. Rate"] = by_emp["cost"] / by_emp["hours"]
by_emp["% of Hours"] = pct(by_emp["hours"], by_emp["hours"].sum())
st.dataframe(
    by_emp[["name","hours","Eff. Rate","cost","% of Hours"]]
      .rename(columns={"name":"Employee","hours":"Hours","cost":"Cost"})
      .style.format({"Hours":"{:.1f}","Eff. Rate":"{:,.0f}","Cost":"{:,.0f}","% of Hours":"{:.0f}%"}),
    use_container_width=True
)

st.caption("Static demo. Swap DATA blocks with API calls; keep column names to reuse all calculations.")
