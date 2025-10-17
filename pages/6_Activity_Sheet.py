# pages/6_Activity_Sheet.py
# Activity Sheet with period selector: Week / Month / Custom
# Rows = dates in period; columns: Date | Day | Logs | Total Hours

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
from calendar import monthrange

st.set_page_config(page_title="Activity Sheet", layout="wide")

# ===================== DEMO DATA (replace with API later) =====================
EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0,8.0],
    ["E-02","Lina","Eng",950.0,8.0],
    ["E-03","Omar","Tech",600.0,8.0],
], columns=["employee_id","name","role","default_rate","capacity_hours_per_day"])

PROJECTS = pd.DataFrame([
    ["PRJ-001","Project Phoenix"],
    ["PRJ-002","Project Atlas"],
], columns=["project_id","name"])

TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","Planning", 80, date(2025,2,10),"Done"],
    ["T-002","PRJ-001","Modeling","E-02","Engineering", 200, date(2025,7,5),"In Progress"],
    ["T-003","PRJ-001","Scanning Field","E-03","Field", 260, date(2025,7,2),"In Progress"],
    ["T-004","PRJ-002","QA & Docs","E-02","QA", 140, date(2025,7,20),"Todo"],
], columns=["task_id","project_id","title","assignee_id","category","estimate_hours","due_date","status"])

# Demo time entries across multiple weeks
today = date(2025, 6, 30)
def daterange(start, end):
    for n in range((end-start).days+1): yield start + timedelta(days=n)

TE=[]
rng = np.random.RandomState(12)
for d in daterange(today - timedelta(days=60), today):
    # random Mon–Fri activity
    if d.weekday() < 5:
        hrs1 = rng.choice([0, 2, 3, 4, 5, 6])
        hrs2 = rng.choice([0, 1, 2, 3])
        if hrs1:
            TE.append([f"TE-{d}-1","T-002","PRJ-001","E-02", d, float(hrs1), True, None, "dev work"])
        if hrs2:
            TE.append([f"TE-{d}-2","T-004","PRJ-002","E-02", d, float(hrs2), False, None, "docs"])
TIMEENTRIES = pd.DataFrame(TE, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== HELPERS =====================
def week_bounds(d: date):
    """Return Monday..Sunday containing date d."""
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end

def month_bounds(d: date):
    """First..last day of d's month."""
    start = date(d.year, d.month, 1)
    end = date(d.year, d.month, monthrange(d.year, d.month)[1])
    return start, end

def format_logs_for_day(df_day: pd.DataFrame) -> str:
    """Compact string: 'Project / Task — 6.0h • Project / Task — 2.0h'"""
    if df_day.empty: return ""
    parts = []
    for r in df_day.sort_values("hours", ascending=False).itertuples():
        parts.append(f"{r.project_name} / {r.title} — {r.hours:.1f}h")
    return " • ".join(parts)

def period_dates(start: date, end: date):
    return [start + timedelta(days=i) for i in range((end-start).days + 1)]

# ===================== UI CONTROLS =====================
st.title("🗓️ Activity Sheet")

emp_id = st.sidebar.selectbox(
    "Employee",
    EMPLOYEES["employee_id"],
    index=1,
    format_func=lambda eid: EMPLOYEES.set_index("employee_id").loc[eid, "name"]
)

period_mode = st.sidebar.radio("Period", ["Week", "Month", "Custom"], index=0)

if period_mode == "Week":
    base_day = st.sidebar.date_input("Any day in the week", value=today)
    start, end = week_bounds(base_day)
elif period_mode == "Month":
    month_day = st.sidebar.date_input("Any day in the month", value=today)
    start, end = month_bounds(month_day)
else:  # Custom
    # use available TE range as defaults
    min_d = TIMEENTRIES["date"].min() if not TIMEENTRIES.empty else today - timedelta(days=30)
    max_d = TIMEENTRIES["date"].max() if not TIMEENTRIES.empty else today
    start, end = st.sidebar.date_input("From / To", value=(min_d, max_d), min_value=min_d, max_value=max_d)

days = period_dates(start, end)

# ===================== BUILD SHEET =====================
# Filter entries for employee & period
sheet = TIMEENTRIES[
    (TIMEENTRIES["employee_id"] == emp_id) &
    (TIMEENTRIES["date"] >= start) &
    (TIMEENTRIES["date"] <= end)
].copy()

# Join project/task names
TASKS_L = TASKS[["task_id","title","project_id"]]
PROJECTS_L = PROJECTS.set_index("project_id")["name"]
sheet = sheet.merge(TASKS_L, on="task_id", how="left")
sheet["project_name"] = sheet["project_id"].map(PROJECTS_L)

rows = []
grand_total = 0.0
for d in days:
    day_logs = sheet[sheet["date"] == d]
    total = float(day_logs["hours"].sum()) if not day_logs.empty else 0.0
    grand_total += total
    rows.append({
        "Date": d,
        "Day": d.strftime("%A"),
        "Logs": format_logs_for_day(day_logs),
        "Total Hours": round(total, 1),
    })

df_view = pd.DataFrame(rows, columns=["Date","Day","Logs","Total Hours"])

# Append TOTAL row
df_total = pd.DataFrame([{
    "Date": pd.NaT,
    "Day": "TOTAL",
    "Logs": "",
    "Total Hours": round(grand_total, 1),
}])
df_view = pd.concat([df_view, df_total], ignore_index=True)

# ===================== RENDER =====================
emp_name = EMPLOYEES.set_index("employee_id").loc[emp_id,'name']
st.write(f"**Employee:** {emp_name}  •  **Period:** {start} → {end}  •  **Days:** {len(days)}")

st.dataframe(
    df_view.style.format({"Total Hours":"{:.1f}"}),
    use_container_width=True
)

# KPIs for the selected period
cap_per_day = float(EMPLOYEES.set_index("employee_id").loc[emp_id, "capacity_hours_per_day"])
weekdays = sum(1 for d in days if d.weekday() < 5)
capacity = cap_per_day * weekdays
util = (grand_total / capacity * 100) if capacity else 0.0

k1, k2, k3 = st.columns(3)
k1.metric("Total Logged (period)", f"{grand_total:.1f} h")
k2.metric("Capacity (weekdays)", f"{capacity:.1f} h")
k3.metric("Utilization", f"{util:.0f}%")

# Export
csv = df_view.to_csv(index=False)
st.download_button("⬇️ Download CSV", data=csv, file_name=f"activity_{emp_id}_{start}_to_{end}.csv", mime="text/csv")

st.caption("Replace the DEMO DATA block with your API results. Keep column names to reuse this view unchanged.")
