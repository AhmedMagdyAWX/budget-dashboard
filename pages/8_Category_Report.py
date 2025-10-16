# pages/8_Category_Report.py
# Time & cost by Task Category

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

st.set_page_config(page_title="Category Report", layout="wide")

# ===================== DATA (replace with API later) =====================
TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","Planning", 80, date(2025,2,10),"Done"],
    ["T-002","PRJ-001","Modeling","E-02","Engineering", 200, date(2025,7,5),"In Progress"],
    ["T-003","PRJ-001","Scanning Field","E-03","Field", 260, date(2025,7,2),"In Progress"],
    ["T-004","PRJ-001","QA & Docs","E-02","QA", 140, date(2025,7,20),"Todo"],
], columns=["task_id","project_id","title","assignee_id","category","estimate_hours","due_date","status"])

EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0], ["E-02","Lina","Eng",950.0], ["E-03","Omar","Tech",600.0],
], columns=["employee_id","name","role","default_rate"])

TIMEENTRIES = pd.DataFrame([
    ["TE-1","T-001","PRJ-001","E-01", date(2025,6,1), 8.0, True, None, ""],
    ["TE-2","T-002","PRJ-001","E-02", date(2025,6,3), 6.0, True, None, ""],
    ["TE-3","T-002","PRJ-001","E-02", date(2025,6,5), 7.0, True, None, ""],
    ["TE-4","T-003","PRJ-001","E-03", date(2025,6,6), 7.0, True, None, ""],
    ["TE-5","T-004","PRJ-001","E-02", date(2025,6,7), 3.0, False, None, ""],
], columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== HELPER =====================
def eff_rate(row):
    # rate_at_entry -> employee default
    if pd.notna(row.get("rate_at_entry")): return float(row["rate_at_entry"])
    return float(EMPLOYEES.set_index("employee_id").loc[row["employee_id"],"default_rate"])

# ===================== CALCS =====================
TE = TIMEENTRIES.merge(TASKS[["task_id","category"]], on="task_id", how="left")
TE["rate"] = TE.apply(eff_rate, axis=1)
TE["cost"] = TE["hours"] * TE["rate"]
TE["month"] = pd.to_datetime(TE["date"]).dt.to_period("M").dt.to_timestamp()

by_cat = TE.groupby("category")[["hours","cost"]].sum().sort_values("hours", ascending=False)
monthly = TE.groupby(["month","category"])["hours"].sum().unstack(fill_value=0)

# ===================== UI =====================
st.title("🏷️ Category Report")
c1, c2 = st.columns(2)
with c1:
    st.write("Hours by Category (Top)")
    st.bar_chart(by_cat["hours"])
with c2:
    st.write("Cost by Category")
    st.bar_chart(by_cat["cost"])

st.subheader("Stacked Hours by Category (Monthly)")
st.bar_chart(monthly)

st.subheader("Category Table")
base = TASKS.groupby("category")["estimate_hours"].sum().to_frame("Est. Hrs").join(by_cat, how="left").fillna(0.0)
base["Variance (h)"] = base["hours"] - base["Est. Hrs"]
base["Billable %"] = 100.0  # demo
st.dataframe(base.style.format({"Est. Hrs":"{:.1f}","hours":"{:.1f}","cost":"{:,.0f}","Variance (h)":"{:+.1f}","Billable %":"{:.0f}%"}), use_container_width=True)
