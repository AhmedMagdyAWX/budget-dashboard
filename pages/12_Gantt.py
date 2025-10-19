# pages/12_Gantt.py
# Hierarchical Gantt (Primavera-style) with Baselines, Planned vs Actual, % Complete, Today line
# Static demo data; wire to your APIs later by replacing the DATA block.

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Gantt (Projects & Activities)", layout="wide")

# ===================== DEMO DATA (replace with API later) =====================
PROJECTS = pd.DataFrame([
    ["PRJ-001", "Project Phoenix"],
    ["PRJ-002", "Project Atlas"],
], columns=["project_id", "name"])

# Activities with hierarchy and two baselines
# id, project_id, name, wbs_path, level, parent_id, baselineA_start, baselineA_finish, baselineB_start, baselineB_finish,
# planned_start, planned_finish, actual_start, actual_finish (None if open), pct_complete, owner, critical
ACTIVITIES = pd.DataFrame([
    # WBS Level 1 (summary)
    ["A100", "PRJ-001", "Phase 1", "1", 1, None,
     date(2025, 1, 10), date(2025, 3, 15), date(2025, 1, 15), date(2025, 3, 20),
     date(2025, 1, 12), date(2025, 3, 22), date(2025, 1, 12), date(2025, 3, 22), 100, "Amr", False],

    # Level 2
    ["A110", "PRJ-001", "Planning", "1.1", 2, "A100",
     date(2025, 1, 10), date(2025, 2, 1), date(2025, 1, 12), date(2025, 2, 5),
     date(2025, 1, 12), date(2025, 2, 3),  date(2025, 1, 12), date(2025, 2, 3), 100, "Amr", False],
    ["A120", "PRJ-001", "Model Setup", "1.2", 2, "A100",
     date(2025, 2, 1), date(2025, 2, 25), date(2025, 2, 5), date(2025, 2, 28),
     date(2025, 2, 3), date(2025, 2, 27),  date(2025, 2, 4), date(2025, 2, 28), 100, "Lina", True],
    ["A130", "PRJ-001", "Client Review 1", "1.3", 2, "A100",
     date(2025, 2, 25), date(2025, 3, 10), date(2025, 2, 28), date(2025, 3, 12),
     date(2025, 2, 27), date(2025, 3, 12),  date(2025, 2, 27), date(2025, 3, 14), 100, "Amr", False],

    # Level 1 (summary)
    ["B100", "PRJ-001", "Phase 2", "2", 1, None,
     date(2025, 3, 16), date(2025, 7, 30), date(2025, 3, 20), date(2025, 8, 10),
     date(2025, 3, 18), date(2025, 8, 5),  date(2025, 3, 18), None,             60, "Lina", True],

    # Level 2 and Level 3
    ["B110", "PRJ-001", "Field Scanning", "2.1", 2, "B100",
     date(2025, 3, 16), date(2025, 5, 10), date(2025, 3, 22), date(2025, 5, 20),
     date(2025, 3, 18), date(2025, 5, 15), date(2025, 3, 18), date(2025, 5, 18), 100, "Omar", True],
    ["B120", "PRJ-001", "Modeling", "2.2", 2, "B100",
     date(2025, 5, 12), date(2025, 7, 1), date(2025, 5, 22), date(2025, 7, 10),
     date(2025, 5, 20), date(2025, 7, 5),  date(2025, 5, 21), None,             55, "Lina", True],
    ["B121", "PRJ-001", "Structural Frames", "2.2.1", 3, "B120",
     date(2025, 5, 12), date(2025, 6, 10), date(2025, 5, 24), date(2025, 6, 18),
     date(2025, 5, 20), date(2025, 6, 12), date(2025, 5, 21), date(2025, 6, 15), 100, "Lina", True],
    ["B122", "PRJ-001", "MEP Coordination", "2.2.2", 3, "B120",
     date(2025, 6, 11), date(2025, 7, 1), date(2025, 6, 20), date(2025, 7, 10),
     date(2025, 6, 13), date(2025, 7, 5),  date(2025, 6, 14), None,             30, "Omar", True],

    # Another project
    ["C100", "PRJ-002", "Kickoff & Setup", "1", 1, None,
     date(2025, 4, 1), date(2025, 4, 20), date(2025, 4, 3), date(2025, 4, 22),
     date(2025, 4, 4), date(2025, 4, 24), date(2025, 4, 4), date(2025, 4, 24), 100, "Sara", False],
], columns=[
    "id","project_id","name","wbs_path","level","parent_id",
    "baselineA_start","baselineA_finish","baselineB_start","baselineB_finish",
    "planned_start","planned_finish","actual_start","actual_finish",
    "pct_complete","owner","critical"
])

# ===================== HELPERS =====================
def nbspace(n):  # visual indent in labels
    return "\u00A0" * (2 * max(int(n), 0))

def compute_fields(df):
    d = df.copy()
    # Indented label for hierarchy
    d["label"] = d["level"].apply(nbspace) + d["name"]
    # Durations
    d["plan_days"] = (pd.to_datetime(d["planned_finish"]) - pd.to_datetime(d["planned_start"])).dt.days
    d["act_days"]  = (pd.to_datetime(d["actual_finish"]) - pd.to_datetime(d["actual_start"])).dt.days
    # Planned progress end date (for % complete stripe)
    d["progress_days"] = (d["plan_days"] * (d["pct_complete"] / 100.0)).round().fillna(0).astype(int)
    d["progress_end"] = pd.to_datetime(d["planned_start"]) + pd.to_timedelta(d["progress_days"], unit="D")
    # Delays (finish variance)
    d["finish_var_days_A"] = (pd.to_datetime(d["planned_finish"]) - pd.to_datetime(d["baselineA_finish"])).dt.days
    d["finish_var_days_B"] = (pd.to_datetime(d["planned_finish"]) - pd.to_datetime(d["baselineB_finish"])).dt.days
    # Status (late if planned finished before today but <100%)
    today = pd.to_datetime(date.today())
    late = (pd.to_datetime(d["planned_finish"]) < today) & (d["pct_complete"] < 100)
    d["status"] = np.where(late, "Late", np.where(d["pct_complete"]>=100, "Done", "In Progress"))
    return d

# ===================== SIDEBAR CONTROLS =====================
st.title("🗂️ Gantt — Activities")

with st.sidebar:
    st.markdown("### Filters")
    # Projects
    proj_map = PROJECTS.set_index("project_id")["name"].to_dict()
    selected_projects = st.multiselect(
        "Projects", PROJECTS["project_id"].tolist(),
        default=PROJECTS["project_id"].tolist(),
        format_func=lambda pid: proj_map.get(pid, pid)
    )
    # Baseline toggle
    baseline_choice = st.radio("Baseline", ["Baseline A", "Baseline B"], index=0)
    # Date window
    min_date = pd.to_datetime(ACTIVITIES[["baselineA_start","planned_start","actual_start"]].stack().min())
    max_date = pd.to_datetime(ACTIVITIES[["baselineB_finish","planned_finish","actual_finish"]].stack().max())
    start_date, end_date = st.date_input(
        "Window",
        value=(min_date.date(), (max_date.date())),
        min_value=min_date.date(), max_value=max_date.date()
    )
    # Show parent summary rows
    show_parents = st.checkbox("Show summary (parent) activities", value=True)
    max_level = st.slider("Max WBS level", 1, int(ACTIVITIES["level"].max()), value=int(ACTIVITIES["level"].max()))

# ===================== FILTER & PREP =====================
df = ACTIVITIES[ACTIVITIES["project_id"].isin(selected_projects)].copy()
df = df[df["level"] <= max_level]
if not show_parents:
    child_ids = set(df["parent_id"].dropna())
    df = df[~df["id"].isin(child_ids)]

df = compute_fields(df)

# Choose baseline fields
if baseline_choice == "Baseline A":
    df["bl_start"] = pd.to_datetime(df["baselineA_start"])
    df["bl_finish"] = pd.to_datetime(df["baselineA_finish"])
    df["finish_var_days"] = df["finish_var_days_A"]
else:
    df["bl_start"] = pd.to_datetime(df["baselineB_start"])
    df["bl_finish"] = pd.to_datetime(df["baselineB_finish"])
    df["finish_var_days"] = df["finish_var_days_B"]

# Clip chart to window
win_start = pd.to_datetime(start_date)
win_end   = pd.to_datetime(end_date)
def clip_range(s, f):
    s = pd.to_datetime(s); f = pd.to_datetime(f)
    return (s.clip(lower=win_start), f.clip(upper=win_end))
df["plan_s_clip"], df["plan_f_clip"] = clip_range(df["planned_start"], df["planned_finish"])
df["act_s_clip"],  df["act_f_clip"]  = clip_range(df["actual_start"], df["actual_finish"].fillna(win_end))
# progress end clip as series
df["prog_end_clip"] = pd.to_datetime(df["progress_end"]).clip(upper=win_end)

# Order rows by WBS path (string sort keeps 1,1.1,1.2,2,2.1 etc.)
df = df.sort_values(["project_id","wbs_path"]).reset_index(drop=True)

# ===================== CHART (Vega-Lite layered) =====================
st.subheader("Gantt Chart")

# Show rows that overlap the window
mask_overlap = (pd.to_datetime(df["planned_finish"]) >= win_start) & (pd.to_datetime(df["planned_start"]) <= win_end)
df_vis = df[mask_overlap].copy()

# Encode color by status / critical
def status_bucket(row):
    if row["critical"]:
        return "Critical"
    return row["status"]
df_vis["bucket"] = df_vis.apply(status_bucket, axis=1)

# Data for tooltips
df_vis["Project Name"] = df_vis["project_id"].map(proj_map)
df_vis["Planned Start"] = pd.to_datetime(df_vis["planned_start"])
df_vis["Planned Finish"] = pd.to_datetime(df_vis["planned_finish"])
df_vis["Actual Start"] = pd.to_datetime(df_vis["actual_start"])
df_vis["Actual Finish"] = pd.to_datetime(df_vis["actual_finish"])
df_vis["Baseline Start"] = pd.to_datetime(df_vis["bl_start"])
df_vis["Baseline Finish"] = pd.to_datetime(df_vis["bl_finish"])
df_vis["Delay (days)"] = df_vis["finish_var_days"].fillna(0).astype(int)

# Today (vertical rule)
today = pd.to_datetime(date.today())

spec = {
    "data": {"values": df_vis.to_dict(orient="records")},
    "height": 520,
    "layer": [
        # Baseline (thin, gray)
        {
            "mark": {"type": "bar", "height": 6, "color": "#9ca3af", "opacity": 0.25},
            "encoding": {
                "y": {"field": "label", "type": "ordinal", "sort": df_vis["label"].tolist(), "title": None},
                "x": {"field": "Baseline Start", "type": "temporal"},
                "x2": {"field": "Baseline Finish"},
            }
        },
        # Planned (main)
        {
            "mark": {"type": "bar", "height": 16},
            "encoding": {
                "y": {"field": "label", "type": "ordinal", "sort": df_vis["label"].tolist(), "title": None},
                "x": {"field": "plan_s_clip", "type": "temporal", "title": None},
                "x2": {"field": "plan_f_clip"},
                "color": {
                    "field": "bucket", "type": "nominal", "title": "Status",
                    "scale": {"domain": ["Done","In Progress","Late","Critical"],
                              "range":  ["#10b981","#3b82f6","#ef4444","#d97706"]}
                },
                "tooltip": [
                    {"field":"Project Name", "type":"nominal"},
                    {"field":
