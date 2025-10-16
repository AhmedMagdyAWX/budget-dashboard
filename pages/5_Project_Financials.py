# pages/5_Project_Financials.py
# Project financials: KPIs, burn-up, task variance

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Project Financials", layout="wide")

# ===================== DATA (replace with API later) =====================
PROJECTS = pd.DataFrame([
    ["PRJ-001", "Project Phoenix", date(2025,1,10), date(2025,12,31), 4200.0, 3_600_000.0, 800.0, "T&M", "Active"],
], columns=["project_id","name","start_date","end_date","budget_hours","budget_cost","default_rate","billing_model","status"])

EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0,8.0], ["E-02","Lina","Eng",950.0,8.0], ["E-03","Omar","Tech",600.0,8.0],
], columns=["employee_id","name","role","default_rate","capacity_hours_per_day"])

TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","Planning", 80, date(2025,2,10),"Done", None, "High"],
    ["T-002","PRJ-001","Modeling","E-02","Engineering", 200, date(2025,5,30),"In Progress", None, "High"],
    ["T-003","PRJ-001","Scanning Field","E-03","Field", 260, date(2025,6,20),"In Progress", 650.0, "Medium"],
    ["T-004","PRJ-001","QA & Docs","E-02","QA", 140, date(2025,8,15),"Todo", None, "Low"],
], columns=["task_id","project_id","title","assignee_id","category","estimate_hours","due_date","status","override_rate","priority"])

# Month series
months = pd.date_range("2025-01-01","2025-12-01",freq="MS")

# Time entries (demo)
TE = []
rng = np.random.RandomState(7)
for m in months:
    for t in TASKS.itertuples():
        hrs = rng.randint(20, 90) if t.status!="Done" or m.month<=2 else rng.randint(10, 40)
        if hrs<=0: continue
        TE.append([f"TE-{m.strftime('%m')}-{t.task_id}", t.task_id, t.project_id, t.assignee_id, m.date(), float(hrs), True, None, f"log {t.title}"])
TIMEENTRIES = pd.DataFrame(TE, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== HELPERS =====================
def money(x): return f"{x:,.0f}"
def month_start(d): 
    ts=pd.to_datetime(d); return pd.Timestamp(ts.year, ts.month, 1)

def effective_rate(row):
    # priority: rate_at_entry -> task.override_rate -> employee.default_rate -> project.default_rate
    if pd.notna(row.get("rate_at_entry")): return float(row["rate_at_entry"])
    tr = TASKS.loc[TASKS["task_id"]==row["task_id"], "override_rate"]
    if not tr.empty and pd.notna(tr.iloc[0]): return float(tr.iloc[0])
    er = EMPLOYEES.loc[EMPLOYEES["employee_id"]==row["employee_id"], "default_rate"].iloc[0]
    if pd.notna(er): return float(er)
    pr = PROJECTS.loc[PROJECTS["project_id"]==row["project_id"], "default_rate"].iloc[0]
    return float(pr)

# pick project (single in demo)
project_id = PROJECTS.iloc[0]["project_id"]
proj = PROJECTS.iloc[0]

# ===================== CALCS =====================
TEp = TIMEENTRIES[TIMEENTRIES["project_id"]==project_id].copy()
TEp["rate"] = TEp.apply(effective_rate, axis=1)
TEp["cost"] = TEp["hours"] * TEp["rate"]
TEp["Month"] = TEp["date"].apply(month_start)

hours_consumed = TEp["hours"].sum()
cost_consumed = TEp["cost"].sum()
budget_hours = float(proj["budget_hours"])
budget_cost  = float(proj["budget_cost"])
hrs_var = hours_consumed - budget_hours
cost_var = cost_consumed - budget_cost

# ETC/EAC
task_hours_logged = TEp.groupby("task_id")["hours"].sum().reindex(TASKS["task_id"]).fillna(0)
remaining_per_task = (TASKS.set_index("task_id")["estimate_hours"] - task_hours_logged).clip(lower=0)
ETC_hours = remaining_per_task.sum()
blended_rate = TEp["rate"].mean() if not TEp.empty else proj["default_rate"]
EAC_cost = cost_consumed + ETC_hours * blended_rate

# SPI/CPI (simple)
planned_done = (TASKS["status"].eq("Done").mean())  # proxy %
actual_done = (task_hours_logged / TASKS.set_index("task_id")["estimate_hours"]).clip(0,1).mean()
SPI = (actual_done / max(planned_done, 0.01))
Earned_Value = actual_done * budget_cost
CPI = (Earned_Value / cost_consumed) if cost_consumed else 1.0

# ===================== UI =====================
st.title("📊 Project Financials")
st.write(f"**Project:** {proj['name']}  •  **Billing:** {proj['billing_model']}  •  **Status:** {proj['status']}")

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Hours Consumed", f"{hours_consumed:,.1f}", f"Var {hrs_var:+.1f}h")
k2.metric("Cost Consumed", money(cost_consumed), f"Var {money(cost_var)}")
k3.metric("% Budget Used (hrs)", f"{(hours_consumed/budget_hours*100):.1f}%")
k4.metric("ETC (hrs)", f"{ETC_hours:,.1f}", f"EAC {money(EAC_cost)}")
k5.metric("SPI / CPI", f"{SPI:.2f}", f"CPI {CPI:.2f}")

st.subheader("Burn-up")
burn = TEp.groupby("Month")[["hours","cost"]].sum().sort_index().cumsum()
burn = burn.reindex(months, fill_value=0).ffill()
burn["Budget Hours"] = budget_hours
burn["Budget Cost"]  = budget_cost

c1,c2 = st.columns(2)
with c1:
    st.write("Cumulative Hours vs Budget")
    st.line_chart(burn[["hours","Budget Hours"]].rename(columns={"hours":"Consumed"}))
with c2:
    st.write("Cumulative Cost vs Budget")
    st.line_chart(burn[["cost","Budget Cost"]].rename(columns={"cost":"Consumed"}))

st.subheader("Task Variance")
task_df = TASKS.copy()
task_df["Logged"] = TASKS["task_id"].map(task_hours_logged).fillna(0.0)
task_df["Remaining"] = (task_df["estimate_hours"] - task_df["Logged"]).clip(lower=0)
task_df["Over/Under (h)"] = task_df["Logged"] - task_df["estimate_hours"]
st.dataframe(
    task_df[["title","assignee_id","category","estimate_hours","Logged","Remaining","status","due_date","priority","Over/Under (h)"]]
    .rename(columns={"title":"Task","assignee_id":"Assignee","estimate_hours":"Est. Hrs"})
    .style.format({"Est. Hrs":"{:.1f}","Logged":"{:.1f}","Remaining":"{:.1f}","Over/Under (h)":"{:+.1f}"}),
    use_container_width=True
)

st.caption("Static demo. Replace the DATA block with API results; keep column names to reuse calculations.")
