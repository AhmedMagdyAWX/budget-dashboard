# pages/6_Activity_Sheet.py
# Activity Sheet with Week/Month/Custom + merged Date/Day cells (rowspan).
# Columns: Date | Day | Task | Project | Hours
# Each day may have multiple task rows; Date/Day cells are merged across those rows.
# A TOTAL row is appended at the end.

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

# Demo time entries (Mon–Fri, last ~60 days)
today = date(2025, 6, 30)
def daterange(start, end):
    for n in range((end-start).days+1): yield start + timedelta(days=n)

TE=[]
rng = np.random.RandomState(12)
for d in daterange(today - timedelta(days=60), today):
    if d.weekday() < 5:
        hrs1 = rng.choice([0, 2, 3, 4, 5, 6])
        hrs2 = rng.choice([0, 1, 2, 3])
        if hrs1:
            TE.append([f"TE-{d}-1","T-002","PRJ-001","E-02", d, float(hrs1), True,  None, "dev work"])
        if hrs2:
            TE.append([f"TE-{d}-2","T-004","PRJ-002","E-02", d, float(hrs2), False, None, "docs"])
TIMEENTRIES = pd.DataFrame(TE, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# ===================== HELPERS =====================
def week_bounds(d: date):
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end

def month_bounds(d: date):
    start = date(d.year, d.month, 1)
    end = date(d.year, d.month, monthrange(d.year, d.month)[1])
    return start, end

def period_dates(start: date, end: date):
    return [start + timedelta(days=i) for i in range((end-start).days + 1)]

def build_rows(emp_id: str, start: date, end: date) -> pd.DataFrame:
    """Return detailed rows: Date | Day | Task | Project | Hours (one per log)."""
    sheet = TIMEENTRIES[
        (TIMEENTRIES["employee_id"] == emp_id) &
        (TIMEENTRIES["date"] >= start) &
        (TIMEENTRIES["date"] <= end)
    ].copy()

    # Ensure project_id exists (derive from tasks if not)
    if "project_id" not in sheet.columns:
        sheet = sheet.merge(TASKS[["task_id","project_id"]], on="task_id", how="left")
    # Join task title & project name
    sheet = sheet.merge(TASKS[["task_id","title","project_id"]], on="task_id", how="left", suffixes=("","_task"))
    if "project_id" not in sheet.columns and "project_id_task" in sheet.columns:
        sheet["project_id"] = sheet["project_id_task"]
    elif "project_id_task" in sheet.columns:
        sheet["project_id"] = sheet["project_id"].fillna(sheet["project_id_task"])
    proj_map = PROJECTS.set_index("project_id")["name"]
    sheet["project_name"] = sheet["project_id"].map(proj_map).fillna("Unknown Project")

    # Build per-task rows
    records = []
    for d in sorted(period_dates(start, end)):
        day_logs = sheet[sheet["date"] == d].sort_values(["project_name","title"], ascending=True)
        if day_logs.empty:
            # empty day still gets one row with 0 hours
            records.append([d, d.strftime("%A"), "", "", 0.0])
        else:
            for r in day_logs.itertuples():
                records.append([d, d.strftime("%A"), r.title, r.project_name, float(r.hours)])
    return pd.DataFrame(records, columns=["Date","Day","Task","Project","Hours"])

def render_html_table(df: pd.DataFrame) -> str:
    """Render HTML table with rowspan merged cells for Date/Day per day."""
    # group by Date to compute rowspans
    df_sorted = df.sort_values(["Date","Project","Task"]).reset_index(drop=True)
    groups = df_sorted.groupby("Date", sort=False)
    rows_html = []
    total_hours = df_sorted["Hours"].sum()

    for date_val, sub in groups:
        rowspan = len(sub)
        # first row with Date/Day
        first = sub.iloc[0]
        rows_html.append(
            f"<tr>"
            f"<td rowspan='{rowspan}' style='white-space:nowrap;font-weight:600'>{date_val}</td>"
            f"<td rowspan='{rowspan}' style='white-space:nowrap;color:#555'>{pd.Timestamp(date_val).strftime('%A')}</td>"
            f"<td>{first['Task']}</td>"
            f"<td>{first['Project']}</td>"
            f"<td style='text-align:right'>{first['Hours']:.1f}</td>"
            f"</tr>"
        )
        # remaining rows for that date
        for _, r in sub.iloc[1:].iterrows():
            rows_html.append(
                f"<tr>"
                f"<td>{r['Task']}</td>"
                f"<td>{r['Project']}</td>"
                f"<td style='text-align:right'>{r['Hours']:.1f}</td>"
                f"</tr>"
            )

    # TOTAL row
    rows_html.append(
        f"<tr style='background:#f8fafc;font-weight:700'>"
        f"<td></td><td style='text-align:right'>TOTAL</td>"
        f"<td></td><td></td>"
        f"<td style='text-align:right'>{total_hours:.1f}</td>"
        f"</tr>"
    )

    html = f"""
    <style>
      table.timesheet {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }}
      .timesheet th, .timesheet td {{
        border: 1px solid #e5e7eb;
        padding: 8px 10px;
        vertical-align: top;
      }}
      .timesheet thead th {{
        background: #f3f4f6;
        text-align: left;
        font-weight: 700;
      }}
      .timesheet tbody tr:nth-child(even) {{ background: #fcfcfd; }}
    </style>
    <table class="timesheet">
      <thead>
        <tr>
          <th style='width:130px'>Date</th>
          <th style='width:120px'>Day</th>
          <th>Task</th>
          <th>Project</th>
          <th style='width:120px; text-align:right'>Hours</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
    """
    return html

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
else:
    min_d = TIMEENTRIES["date"].min() if not TIMEENTRIES.empty else today - timedelta(days=30)
    max_d = TIMEENTRIES["date"].max() if not TIMEENTRIES.empty else today
    start, end = st.sidebar.date_input("From / To", value=(min_d, max_d), min_value=min_d, max_value=max_d)

# ===================== BUILD + RENDER =====================
detail = build_rows(emp_id, start, end)

st.write(f"**Employee:** {EMPLOYEES.set_index('employee_id').loc[emp_id,'name']}  •  "
         f"**Period:** {start} → {end}  •  "
         f"**Days:** {(end - start).days + 1}")

if detail.empty:
    st.info("No time entries in this period.")
else:
    html = render_html_table(detail)
    st.markdown(html, unsafe_allow_html=True)

# KPIs
cap_per_day = float(EMPLOYEES.set_index("employee_id").loc[emp_id, "capacity_hours_per_day"])
weekdays = sum(1 for d in period_dates(start, end) if d.weekday() < 5)
capacity = cap_per_day * weekdays
total_hours = float(detail["Hours"].sum())
util = (total_hours / capacity * 100) if capacity else 0.0

k1, k2, k3 = st.columns(3)
k1.metric("Total Logged (period)", f"{total_hours:.1f} h")
k2.metric("Capacity (weekdays)", f"{capacity:.1f} h")
k3.metric("Utilization", f"{util:.0f}%")

# Export (flat rows)
csv = detail.to_csv(index=False)
st.download_button("⬇️ Download CSV", data=csv, file_name=f"activity_{emp_id}_{start}_to_{end}.csv", mime="text/csv")

st.caption("Uses an HTML table to support merged Date/Day cells. Replace the DEMO DATA with your API results later.")
