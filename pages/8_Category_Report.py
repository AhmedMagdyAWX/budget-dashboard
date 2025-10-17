# pages/8_Category_Report.py
# Category reporting with project & timeframe filters (static demo, API-ready)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Category Report", layout="wide")

# ===================== DEMO DATA (replace with API later) =====================
PROJECTS = pd.DataFrame([
    ["PRJ-001","Project Phoenix"],
    ["PRJ-002","Project Atlas"],
    ["PRJ-003","Project Orion"],
], columns=["project_id","name"])

TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","Planning",     80, date(2025,2,10),"Done"],
    ["T-002","PRJ-001","Modeling","E-02","Engineering", 200, date(2025,7,5),"In Progress"],
    ["T-003","PRJ-001","Scanning Field","E-03","Field", 260, date(2025,7,2),"In Progress"],
    ["T-004","PRJ-001","QA & Docs","E-02","QA",         140, date(2025,7,20),"Todo"],
    ["T-101","PRJ-002","Concept","E-01","Planning",      60, date(2025,4,12),"Done"],
    ["T-102","PRJ-002","Detailing","E-02","Engineering",180, date(2025,6,18),"In Progress"],
    ["T-103","PRJ-002","Site Check","E-03","Field",     120, date(2025,6,26),"Todo"],
    ["T-201","PRJ-003","Setup","E-02","Admin",           40, date(2025,5,10),"Done"],
    ["T-202","PRJ-003","Fabrication","E-03","Engineering",240,date(2025,7,25),"In Progress"],
], columns=["task_id","project_id","title","assignee_id","category","estimate_hours","due_date","status"])

EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0], ["E-02","Lina","Eng",950.0], ["E-03","Omar","Tech",600.0],
], columns=["employee_id","name","role","default_rate"])

# Generate demo TIMEENTRIES across projects & months
rng = np.random.RandomState(42)
entries = []
for t in TASKS.itertuples():
    for d in pd.date_range("2025-03-01","2025-07-31", freq="7D"):
        hrs = rng.randint(0, 9)
        if hrs > 0:
            entries.append([f"TE-{t.task_id}-{d.date()}",
                            t.task_id, t.project_id, t.assignee_id, d.date(),
                            float(hrs), True, None, "work"])
TIMEENTRIES = pd.DataFrame(entries, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== HELPERS =====================
def eff_rate(row):
    if pd.notna(row.get("rate_at_entry")):
        return float(row["rate_at_entry"])
    return float(EMPLOYEES.set_index("employee_id").loc[row["employee_id"],"default_rate"])

def safe_bar_chart(df_or_series):
    if isinstance(df_or_series, pd.Series):
        if df_or_series.empty:
            st.info("No data for current filters."); return
        st.bar_chart(df_or_series)
    else:
        if df_or_series.empty or (df_or_series.sum(numeric_only=True)==0).all():
            st.info("No data for current filters."); return
        st.bar_chart(df_or_series)

# ===================== FILTERS =====================
st.title("🏷️ Category Report")

with st.sidebar:
    st.markdown("### Filters")
    all_projects = st.checkbox("All projects", value=True)
    if all_projects:
        selected_projects = PROJECTS["project_id"].tolist()
    else:
        selected_projects = st.multiselect(
            "Choose projects",
            PROJECTS["project_id"].tolist(),
            default=PROJECTS["project_id"].tolist()[:2],
            format_func=lambda pid: PROJECTS.set_index("project_id").loc[pid,"name"]
        )
    min_date = TIMEENTRIES["date"].min() if not TIMEENTRIES.empty else date(2025,3,1)
    max_date = TIMEENTRIES["date"].max() if not TIMEENTRIES.empty else date(2025,7,31)
    start, end = st.date_input(
        "Timeframe",
        value=(max(min_date, max_date - timedelta(days=90)), max_date),
        min_value=min_date, max_value=max_date
    )

# ===================== APPLY FILTERS =====================
TE = TIMEENTRIES.copy()
if selected_projects:
    TE = TE[TE["project_id"].isin(selected_projects)]
TE = TE[(TE["date"] >= start) & (TE["date"] <= end)]

if TE.empty:
    st.warning("No time entries for the selected filters (projects/timeframe).")
    st.dataframe(pd.DataFrame(columns=["Category","Est. Hrs","Hours","Cost","Variance (h)","Billable %"]), use_container_width=True)
    st.stop()

TASKS_F = TASKS[TASKS["project_id"].isin(TE["project_id"].unique())].copy()

# ===================== CALCS =====================
TE = TE.merge(TASKS_F[["task_id","category","project_id"]], on="task_id", how="left")
TE["rate"] = TE.apply(eff_rate, axis=1)
TE["cost"] = TE["hours"] * TE["rate"]

# ✅ FIX: use .dt when converting to period
TE["date_dt"] = pd.to_datetime(TE["date"])
TE["month"] = TE["date_dt"].dt.to_period("M").dt.to_timestamp()

by_cat = TE.groupby("category")[["hours","cost"]].sum().sort_values("hours", ascending=False)
monthly = TE.groupby(["month","category"])["hours"].sum().unstack(fill_value=0).sort_index()

est = TASKS_F.groupby("category")["estimate_hours"].sum().to_frame("Est. Hrs")
base = est.join(by_cat, how="left").fillna(0.0)
base["Variance (h)"] = base["hours"] - base["Est. Hrs"]
base["Billable %"] = 100.0  # demo

# =
