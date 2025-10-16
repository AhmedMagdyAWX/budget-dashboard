# pages/6_Activity_Sheet.py
# Weekly activity sheet for an employee (timesheet + insights)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Activity Sheet", layout="wide")

# ===================== DATA (replace with API later) =====================
EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0,8.0], ["E-02","Lina","Eng",950.0,8.0], ["E-03","Omar","Tech",600.0,8.0],
], columns=["employee_id","name","role","default_rate","capacity_hours_per_day"])

PROJECTS = pd.DataFrame([
    ["PRJ-001","Project Phoenix"]
], columns=["project_id","name"])

TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","Planning", 80, date(2025,2,10),"Done"],
    ["T-002","PRJ-001","Modeling","E-02","Engineering", 200, date(2025,5,30),"In Progress"],
    ["T-003","PRJ-001","Scanning Field","E-03","Field", 260, date(2025,6,20),"In Progress"],
    ["T-004","PRJ-001","QA & Docs","E-02","QA", 140, date(2025,8,15),"Todo"],
], columns=["task_id","project_id","title","assignee_id","category","estimate_hours","due_date","status"])

# generate demo time entries for recent 4 weeks
today = date(2025,6,30)
def daterange(start, end):
    for n in range((end-start).days+1): yield start + timedelta(days=n)

TE=[]
for d in daterange(today - timedelta(days=27), today):
    dow = d.weekday()
    if dow<5:
        TE.append([f"TE-{d}", "T-002","PRJ-001","E-02", d, 6.0 if dow<4 else 4.0, True, None, "dev work"])
        if dow in (1,3):
            TE.append([f"TE2-{d}", "T-004","PRJ-001","E-02", d, 2.0, False, None, "docs"])
TIMEENTRIES = pd.DataFrame(TE, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== PARAMS =====================
employee = st.sidebar.selectbox("Employee", EMPLOYEES["employee_id"], index=1, format_func=lambda eid: EMPLOYEES.set_index("employee_id").loc[eid,"name"])
week_start = st.sidebar.date_input("Week starting (Mon)", value=today - timedelta(days=today.weekday()))
week_days = [week_start + timedelta(days=i) for i in range(7)]
week_end = week_days[-1]

# ===================== CALCS =====================
sheet = TIMEENTRIES[(TIMEENTRIES["employee_id"]==employee) & (TIMEENTRIES["date"]>=week_start) & (TIMEENTRIES["date"]<=week_end)].copy()
capacity = EMPLOYEES.set_index("employee_id").loc[employee,"capacity_hours_per_day"]
target_total = capacity*5  # weekdays
billable_hours = sheet.loc[sheet["billable"],"hours"].sum()
total_hours = sheet["hours"].sum()
util_pct = (billable_hours / (capacity*5) * 100) if capacity else 0

# ===================== UI =====================
st.title("🗓️ Activity Sheet (Weekly)")
st.write(f"**Employee:** {EMPLOYEES.set_index('employee_id').loc[employee,'name']} • **Week:** {week_start} → {week_end}")

k1,k2,k3,k4 = st.columns(4)
k1.metric("Total Hours", f"{total_hours:.1f}")
k2.metric("Billable Hours", f"{billable_hours:.1f}")
k3.metric("Utilization", f"{util_pct:.0f}%")
k4.metric("Capacity (Mon–Fri)", f"{target_total:.1f} h")

st.subheader("Timesheet")
disp = sheet.merge(TASKS[["task_id","title","category"]], on="task_id", how="left").merge(PROJECTS, on="project_id", how="left")
disp = disp.rename(columns={"name":"Project","title":"Task","date":"Date"})
st.dataframe(
    disp[["Date","Project","Task","category","hours","billable","notes"]].rename(columns={"category":"Category","hours":"Hours","billable":"Billable","notes":"Notes"})
    .sort_values("Date")
    .style.format({"Hours":"{:.1f}"}), use_container_width=True
)

st.subheader("Daily trend")
daily = sheet.groupby("date")["hours"].sum().reindex(week_days, fill_value=0.0)
st.line_chart(daily)

st.subheader("Billable vs Non-billable")
pie = pd.Series({"Billable": billable_hours, "Non-billable": total_hours - billable_hours})
st.bar_chart(pie)

st.subheader("Capacity heatmap (this month)")
month_days = [date(2025,6,1)+timedelta(days=i) for i in range(30)]
mon = TIMEENTRIES[(TIMEENTRIES["employee_id"]==employee) & (TIMEENTRIES["date"]>=month_days[0]) & (TIMEENTRIES["date"]<=month_days[-1])]
mon = mon.groupby("date")["hours"].sum().reindex(month_days, fill_value=0.0)
st.area_chart(mon)
st.caption("Replace DATA section with API calls. Weekly timesheet uses simple metrics for the presentation.")
