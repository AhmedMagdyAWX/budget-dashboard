# pages/9_Overruns_Delays.py
# Track overdue tasks and hours overruns (fixed)

import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Overruns & Delays", layout="wide")

# ===================== DATA (replace with API later) =====================
TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","Planning", 80, date(2025,2,10),"Done"],
    ["T-002","PRJ-001","Modeling","E-02","Engineering", 200, date(2025,7,5),"In Progress"],
    ["T-003","PRJ-001","Scanning Field","E-03","Field", 260, date(2025,6,25),"In Progress"],
    ["T-004","PRJ-001","QA & Docs","E-02","QA", 140, date(2025,6,28),"Todo"],
    ["T-005","PRJ-001","Client Review","E-02","Admin", 16, date(2025,6,26),"Blocked"],
], columns=["task_id","project_id","title","assignee_id","category","estimate_hours","due_date","status"])

TIMEENTRIES = pd.DataFrame([
    ["TE-1","T-002","PRJ-001","E-02", date(2025,6,20), 120.0, True, None, ""],
    ["TE-2","T-003","PRJ-001","E-03", date(2025,6,27), 270.0, True, None, ""],
    ["TE-3","T-004","PRJ-001","E-02", date(2025,6,29), 10.0, False, None, ""],
], columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== PARAMS =====================
tolerance_yellow = st.sidebar.slider("Overrun tolerance (yellow)", 0, 50, 10, step=5)
tolerance_red    = st.sidebar.slider("Overrun tolerance (red)", 0, 100, 20, step=5)
due_soon_days    = st.sidebar.slider("Due soon threshold (days)", 1, 14, 3, step=1)

today = date(2025,6,30)
today_ts = pd.to_datetime(today)

# ===================== CALCS =====================
logged = TIMEENTRIES.groupby("task_id")["hours"].sum()
df = TASKS.copy()
df["Logged"] = df["task_id"].map(logged).fillna(0.0)
df["Overrun (h)"] = df["Logged"] - df["estimate_hours"]
df["Overrun %"] = (df["Overrun (h)"] / df["estimate_hours"] * 100).replace([float("inf"), -float("inf")], 0.0)

# Ensure due_date is datetime64 for vectorized operations
df["due_date_dt"] = pd.to_datetime(df["due_date"])

# FIX: compute days late safely (vectorized)
df["Days Late"] = (today_ts - df["due_date_dt"]).dt.days
df["Overdue"] = (df["Days Late"] > 0) & df["status"].ne("Done")

# Due soon (not done)
df["Days To Due"] = (df["due_date_dt"] - today_ts).dt.days
df["Due Soon"] = (df["Days To Due"] <= due_soon_days) & df["status"].isin(["Todo","In Progress"])

def flag_row(row):
    if row["Overrun %"] >= tolerance_red or (row["Overdue"] and row["Days Late"]>=1):
        return "🔴"
    if row["Overrun %"] >= tolerance_yellow or row["Due Soon"]:
        return "🟡"
    return "🟢"

df["Flag"] = df.apply(flag_row, axis=1)

# ===================== UI =====================
st.title("⏱️ Overruns & Delays")
k1,k2,k3 = st.columns(3)
k1.metric("Overdue", int(df["Overdue"].sum()))
k2.metric("Overrun (>= red %)", int((df["Overrun %"]>=tolerance_red).sum()))
k3.metric("Due Soon (<= days)", int(df["Due Soon"].sum()))

st.subheader("Risk List")
st.dataframe(
    df.sort_values(["Flag","Days Late","Overrun %"], ascending=[True, False, False])[
        ["Flag","title","assignee_id","category","estimate_hours","Logged","Overrun (h)","Overrun %","due_date","Days Late","status"]
    ].rename(columns={"title":"Task","assignee_id":"Assignee","due_date":"Due","estimate_hours":"Est. Hrs"})
     .style.format({"Est. Hrs":"{:.1f}","Logged":"{:.1f}","Overrun (h)":"{:+.1f}","Overrun %":"{:.0f}%"}),
    use_container_width=True
)

st.subheader("Overdue Calendar (Week Heat)")
df["Week"] = pd.to_datetime(df["due_date_dt"]).dt.to_period("W").astype(str)
wd = df.groupby("Week")["Overdue"].sum()
st.bar_chart(wd)

st.caption("Adjust thresholds in the sidebar to match your policy.")
