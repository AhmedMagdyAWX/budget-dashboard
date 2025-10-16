# pages/7_My_Tasks.py
# My Tasks & Assigned by Me — kanban-style filters + quick insights

import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="My Tasks", layout="wide")

# ===================== DATA (replace with API later) =====================
ME = "E-02"  # demo current user

PROJECTS = pd.DataFrame([["PRJ-001","Project Phoenix"]], columns=["project_id","name"])
TASKS = pd.DataFrame([
    ["T-001","PRJ-001","Planning","E-01","E-02","Planning", 80, date(2025,2,10),"Done","High"],
    ["T-002","PRJ-001","Modeling","E-02","E-01","Engineering", 200, date(2025,7,5),"In Progress","High"],
    ["T-003","PRJ-001","Scanning Field","E-03","E-02","Field", 260, date(2025,7,2),"In Progress","Medium"],
    ["T-004","PRJ-001","QA & Docs","E-02","E-02","QA", 140, date(2025,7,20),"Todo","Low"],
    ["T-005","PRJ-001","Client Review","E-02","E-01","Admin", 16, date(2025,6,28),"Blocked","Medium"],
], columns=["task_id","project_id","title","assignee_id","assigner_id","category","estimate_hours","due_date","status","priority"])

TIMEENTRIES = pd.DataFrame([
    ["TE-1","T-002","PRJ-001","E-02", date(2025,6,28), 6.0, True, None, ""],
    ["TE-2","T-003","PRJ-001","E-03", date(2025,6,28), 7.0, True, None, ""],
    ["TE-3","T-004","PRJ-001","E-02", date(2025,6,29), 2.0, False, None, ""],
], columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== HELPERS =====================
def logged_hours(task_id):
    return TIMEENTRIES.loc[TIMEENTRIES["task_id"]==task_id, "hours"].sum()

def status_tag(task):
    if task["status"]=="Done": return "✅ Done"
    if task["status"]=="Blocked": return "⛔ Blocked"
    if task["due_date"] < date.today(): return "⚠️ Overdue"
    if task["status"]=="In Progress": return "🟡 In Progress"
    return "📝 Todo"

# ===================== FILTERS =====================
st.title("🧩 My Tasks")
tab1, tab2 = st.tabs(["Assigned to Me", "Assigned by Me"])

for tab, df in [(tab1, TASKS[TASKS["assignee_id"]==ME]), (tab2, TASKS[TASKS["assigner_id"]==ME])]:
    with tab:
        left, right = st.columns([3,1])
        with right:
            project = st.selectbox("Project", ["All"]+PROJECTS["project_id"].tolist(), format_func=lambda pid: "All" if pid=="All" else PROJECTS.set_index("project_id").loc[pid,"name"])
            status = st.multiselect("Status", ["Todo","In Progress","Blocked","Done"], default=["Todo","In Progress","Blocked","Done"])
            overdue_only = st.checkbox("Overdue only")
        with left:
            # apply filters
            q = df.copy()
            if project!="All": q = q[q["project_id"]==project]
            q = q[q["status"].isin(status)]
            if overdue_only: q = q[q["due_date"]<date.today() & q["status"].ne("Done")]

            st.subheader(f"{'Assigned to Me' if 'assignee_id' in df.columns else 'Assigned by Me'} — {len(q)} tasks")
            # simple kanban columns
            k1,k2,k3,k4 = st.columns(4)
            for col, stat in zip([k1,k2,k3,k4], ["Todo","In Progress","Blocked","Done"]):
                subset = q[q["status"]==stat].copy()
                subset["Logged"] = subset["task_id"].apply(logged_hours)
                subset["Remain"] = (subset["estimate_hours"] - subset["Logged"]).clip(lower=0)
                subset["Tag"] = subset.apply(status_tag, axis=1)
                col.markdown(f"**{stat} ({len(subset)})**")
                if subset.empty:
                    col.info("No tasks")
                else:
                    col.dataframe(subset[["title","priority","due_date","estimate_hours","Logged","Remain","Tag"]]
                                  .rename(columns={"title":"Task","due_date":"Due","estimate_hours":"Est. Hrs"})
                                  .style.format({"Est. Hrs":"{:.1f}","Logged":"{:.1f}","Remain":"{:.1f}"}),
                                  use_container_width=True)
