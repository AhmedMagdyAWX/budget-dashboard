# pages/12_Gantt.py
# Gantt with Baselines, Planned vs Actual, %Complete, Today line
# + AG-Grid Tree (true expand/collapse) that drives the chart via selection
# Requires: streamlit-aggrid==0.3.4.post3

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid import JsCode

st.set_page_config(page_title="Gantt (Projects & Activities)", layout="wide")

# ---------------- Demo Data ----------------
PROJECTS = pd.DataFrame([
    ["PRJ-001","Project Phoenix"],
    ["PRJ-002","Project Atlas"],
], columns=["project_id","name"])

ACTIVITIES = pd.DataFrame([
    ["A100","PRJ-001","Phase 1","1",   1, None, date(2025,1,10),date(2025,3,15), date(2025,1,15),date(2025,3,20), date(2025,1,12),date(2025,3,22), date(2025,1,12),date(2025,3,22),100,"Amr", False],
    ["A110","PRJ-001","Planning","1.1",2,"A100",date(2025,1,10),date(2025,2,1),  date(2025,1,12),date(2025,2,5),  date(2025,1,12),date(2025,2,3),  date(2025,1,12),date(2025,2,3), 100,"Amr", False],
    ["A120","PRJ-001","Model Setup","1.2",2,"A100",date(2025,2,1), date(2025,2,25),date(2025,2,5), date(2025,2,28), date(2025,2,3), date(2025,2,27), date(2025,2,4), date(2025,2,28),100,"Lina", True],
    ["A130","PRJ-001","Client Review 1","1.3",2,"A100",date(2025,2,25),date(2025,3,10),date(2025,2,28),date(2025,3,12), date(2025,2,27),date(2025,3,12), date(2025,2,27),date(2025,3,14),100,"Amr", False],
    ["B100","PRJ-001","Phase 2","2",   1, None, date(2025,3,16),date(2025,7,30), date(2025,3,20),date(2025,8,10), date(2025,3,18),date(2025,8,5),  date(2025,3,18),None,            60,"Lina", True],
    ["B110","PRJ-001","Field Scanning","2.1",2,"B100",date(2025,3,16),date(2025,5,10),date(2025,3,22),date(2025,5,20), date(2025,3,18),date(2025,5,15),date(2025,3,18),date(2025,5,18),100,"Omar", True],
    ["B120","PRJ-001","Modeling","2.2",2,"B100",date(2025,5,12),date(2025,7,1), date(2025,5,22),date(2025,7,10), date(2025,5,20),date(2025,7,5),  date(2025,5,21),None,            55,"Lina", True],
    ["B121","PRJ-001","Structural Frames","2.2.1",3,"B120",date(2025,5,12),date(2025,6,10),date(2025,5,24),date(2025,6,18), date(2025,5,20),date(2025,6,12),date(2025,5,21),date(2025,6,15),100,"Lina", True],
    ["B122","PRJ-001","MEP Coordination","2.2.2",3,"B120",date(2025,6,11),date(2025,7,1), date(2025,6,20),date(2025,7,10), date(2025,6,13),date(2025,7,5),  date(2025,6,14),None,            30,"Omar", True],
    ["C100","PRJ-002","Kickoff & Setup","1",1,None,date(2025,4,1),date(2025,4,20),date(2025,4,3),date(2025,4,22), date(2025,4,4),date(2025,4,24), date(2025,4,4),date(2025,4,24),100,"Sara", False],
], columns=[
    "id","project_id","name","wbs_path","level","parent_id",
    "baselineA_start","baselineA_finish","baselineB_start","baselineB_finish",
    "planned_start","planned_finish","actual_start","actual_finish",
    "pct_complete","owner","critical"
])

DEPENDENCIES = pd.DataFrame([
    ["A110","A120","FS",0],
    ["A120","A130","FS",0],
    ["A130","B110","FS",2],
    ["B110","B120","SS",0],
    ["B121","B122","FF",0],
], columns=["pred_id","succ_id","type","lag_days"])

# ---------------- Helpers ----------------
def nbspace(n): return "\u00A0" * (2 * max(int(n), 0))

def compute_fields(df):
    d = df.copy()
    d["label"] = d["level"].apply(nbspace) + d["name"]
    d["plan_days"] = (pd.to_datetime(d["planned_finish"]) - pd.to_datetime(d["planned_start"])).dt.days
    d["progress_days"] = (d["plan_days"] * (d["pct_complete"] / 100.0)).round().fillna(0).astype(int)
    d["progress_end"]  = pd.to_datetime(d["planned_start"]) + pd.to_timedelta(d["progress_days"], unit="D")
    d["finish_var_days_A"] = (pd.to_datetime(d["planned_finish"]) - pd.to_datetime(d["baselineA_finish"])).dt.days
    d["finish_var_days_B"] = (pd.to_datetime(d["planned_finish"]) - pd.to_datetime(d["baselineB_finish"])).dt.days
    today = pd.to_datetime(date.today())
    late = (pd.to_datetime(d["planned_finish"]) < today) & (d["pct_complete"] < 100)
    d["status"] = np.where(late, "Late", np.where(d["pct_complete"]>=100, "Done", "In Progress"))
    return d

def to_iso(series):
    s = pd.to_datetime(series)
    return s.dt.date.astype("string").where(~s.isna(), None)

def make_links(df_rows: pd.DataFrame, deps: pd.DataFrame) -> pd.DataFrame:
    """Return two rows per link, fields: link_id, x (ISO date), label (y)."""
    rows = []
    act = df_rows.set_index("id")
    for _, dep in deps.iterrows():
        if dep["pred_id"] not in act.index or dep["succ_id"] not in act.index:
            continue
        pred = act.loc[dep["pred_id"]]; succ = act.loc[dep["succ_id"]]
        lag = pd.to_timedelta(int(dep["lag_days"]), unit="D")
        t = dep["type"]
        if t == "FS":
            x1 = pd.to_datetime(pred["planned_finish"]) + lag; x2 = pd.to_datetime(succ["planned_start"])
        elif t == "SS":
            x1 = pd.to_datetime(pred["planned_start"]) + lag;  x2 = pd.to_datetime(succ["planned_start"])
        elif t == "FF":
            x1 = pd.to_datetime(pred["planned_finish"]) + lag; x2 = pd.to_datetime(succ["planned_finish"])
        else:  # SF
            x1 = pd.to_datetime(pred["planned_start"]) + lag;  x2 = pd.to_datetime(succ["planned_finish"])
        link_id = f"{dep['pred_id']}→{dep['succ_id']}({dep['type']})"
        rows += [{"link_id": link_id, "x": x1, "label": pred["label"]},
                 {"link_id": link_id, "x": x2, "label": succ["label"]}]
    out = pd.DataFrame(rows, columns=["link_id","x","label"])
    if out.empty: return out
    out["x"] = to_iso(out["x"])
    return out

# ---------------- Sidebar ----------------
st.title("🗂️ Gantt — Activities")
with st.sidebar:
    st.markdown("### Filters")
    proj_map = PROJECTS.set_index("project_id")["name"].to_dict()
    selected_projects = st.multiselect("Projects", PROJECTS["project_id"].tolist(),
                                       default=PROJECTS["project_id"].tolist(),
                                       format_func=lambda pid: proj_map.get(pid, pid))
    baseline_choice = st.radio("Baseline", ["Baseline A","Baseline B"], index=0)
    # Window
    min_date = pd.to_datetime(ACTIVITIES[["baselineA_start","planned_start","actual_start"]].stack().min())
    max_date = pd.to_datetime(ACTIVITIES[["baselineB_finish","planned_finish","actual_finish"]].stack().max())
    start_date, end_date = st.date_input("Window", value=(min_date.date(), max_date.date()),
                                         min_value=min_date.date(), max_value=max_date.date())

# ---------------- Filter & Prep ----------------
df_all = ACTIVITIES.query("project_id in @selected_projects").copy()
df_all = compute_fields(df_all)

# Baseline fields
if baseline_choice == "Baseline A":
    df_all["bl_start"] = pd.to_datetime(df_all["baselineA_start"]); df_all["bl_finish"] = pd.to_datetime(df_all["baselineA_finish"])
    df_all["finish_var_days"] = df_all["finish_var_days_A"]
else:
    df_all["bl_start"] = pd.to_datetime(df_all["baselineB_start"]); df_all["bl_finish"] = pd.to_datetime(df_all["baselineB_finish"])
    df_all["finish_var_days"] = df_all["finish_var_days_B"]

# Clip to window
win_start, win_end = pd.to_datetime(start_date), pd.to_datetime(end_date)
def clip_range(s, f):
    s = pd.to_datetime(s); f = pd.to_datetime(f)
    return (s.clip(lower=win_start), f.clip(upper=win_end))
df_all["plan_s_clip"], df_all["plan_f_clip"] = clip_range(df_all["planned_start"], df_all["planned_finish"])
df_all["act_s_clip"],  df_all["act_f_clip"]  = clip_range(df_all["actual_start"], df_all["actual_finish"].fillna(win_end))
df_all["prog_end_clip"] = pd.to_datetime(df_all["progress_end"]).clip(upper=win_end)

# Overlap window & sort
overlap = (pd.to_datetime(df_all["planned_finish"]) >= win_start) & (pd.to_datetime(df_all["planned_start"]) <= win_end)
df_all = df_all[overlap].sort_values(["project_id","wbs_path"]).reset_index(drop=True)
df_all["bucket"] = np.where(df_all["critical"], "Critical", df_all["status"])
df_all["Project Name"] = df_all["project_id"].map(proj_map)
df_all["Delay (days)"] = df_all["finish_var_days"].fillna(0).astype(int)

# ISO date strings for JSON
for c in ["bl_start","bl_finish","planned_start","planned_finish","actual_start","actual_finish",
          "plan_s_clip","plan_f_clip","act_s_clip","act_f_clip","progress_end","prog_end_clip"]:
    df_all[c] = to_iso(df_all[c])

# Build a data path for AG-Grid tree from the WBS (e.g., "1.2.1") + names
def wbs_to_path(row):
    parts = row["wbs_path"].split(".")
    labels = []
    # Walk the WBS and use the names of each ancestor if available; fallback to parts
    # For demo, we simply use the running WBS prefixes (1 -> '1', 1.2 -> '1.2', etc.)
    acc = []
    for p in parts:
        acc.append(p)
        labels.append(".".join(acc))
    # Replace the last with Activity name for nicer leaf label
    labels[-1] = row["name"]
    return labels

df_all["path"] = df_all.apply(wbs_to_path, axis=1)

# ---------------- Layout: Grid (left) + Chart (right) ----------------
left, right = st.columns([0.46, 0.54], gap="large")

with left:
    st.subheader("Work Breakdown (expand/collapse)")
    depth = st.slider("Expand depth", 0, int(df_all["level"].max()), value=int(df_all["level"].max()))
    st.caption("Tip: expand/collapse nodes with the arrows; select any set of rows to filter the Gantt.")

    # Build AG-Grid tree options
    grid_df = df_all[["id","project_id","wbs_path","level","owner","pct_complete","status","critical","path"]].copy()
    gob = GridOptionsBuilder.from_dataframe(grid_df)
    gob.configure_pagination(enabled=False)
    gob.configure_selection(selection_mode="multiple", use_checkbox=True)
    gob.configure_grid_options(
    treeData=True,
    animateRows=True,
    groupDefaultExpanded=depth if depth > 0 else 0,  # -1 would expand all
    getDataPath=JsCode("function (data) { return data.path; }"),
    autoGroupColumnDef={
        "headerName": "Activity",
        "minWidth": 260,
        "cellRendererParams": {"suppressCount": True},
    },
    )
    # Hide technical columns except via tooltip
    gob.configure_column("path", hide=True)
    gob.configure_column("wbs_path", header_name="WBS", width=100)
    gob.configure_column("pct_complete", header_name="% Complete", type=["numericColumn"], valueFormatter="Math.round(value)")
    gob.configure_column("critical", header_name="Critical")
    gob.configure_side_bar()

    grid = AgGrid(
        grid_df,
        gridOptions=gob.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.FILTERING_CHANGED,
        allow_unsafe_jscode=True,
        height=520,
        theme="alpine",
        fit_columns_on_grid_load=True,
        key="wbs_tree",
    )

    selected_ids = {r["id"] for r in grid["selected_rows"]} if grid.get("selected_rows") else set()

with right:
    # If user selected rows, chart follows selection; otherwise show all rows in the window
    if selected_ids:
        df_vis = df_all[df_all["id"].isin(selected_ids)].copy()
    else:
        df_vis = df_all.copy()

    # Dependency lines are rebuilt based on visible rows
    links_df = make_links(df_vis[["id","label","planned_start","planned_finish"]], DEPENDENCIES)

    st.subheader("Gantt Chart")

    y_sort = list(df_vis["label"])
    acts_values  = df_vis.to_dict(orient="records")
    links_values = links_df.to_dict(orient="records")
    today_iso = date.today().isoformat()

    spec = {
        "height": 540,
        "datasets": {"acts": acts_values, "links": links_values},
        "layer": [
            *([] if not links_values else [
                {
                    "data": {"name": "links"},
                    "mark": {"type": "line", "stroke": "#6b7280", "strokeWidth": 1.5, "opacity": 0.8},
                    "encoding": {
                        "x": {"field": "x", "type": "temporal", "axis": {"title": None}},
                        "y": {"field": "label", "type": "ordinal", "sort": y_sort},
                        "detail": {"field": "link_id"}
                    }
                },
                {
                    "data": {"name": "links"},
                    "mark": {"type": "point", "filled": True, "size": 70, "color": "#6b7280"},
                    "encoding": {
                        "x": {"field": "x", "type": "temporal", "axis": {"title": None}},
                        "y": {"field": "label", "type": "ordinal", "sort": y_sort}
                    }
                }
            ]),
            {
                "data": {"name": "acts"},
                "mark": {"type": "bar", "height": 6, "color": "#9ca3af", "opacity": 0.25},
                "encoding": {
                    "y": {"field": "label", "type": "ordinal", "sort": y_sort, "title": None},
                    "x": {"field": "bl_start", "type": "temporal", "axis": {"title": None}},
                    "x2": {"field": "bl_finish"}
                }
            },
            {
                "data": {"name": "acts"},
                "mark": {"type": "bar", "height": 16},
                "encoding": {
                    "y": {"field": "label", "type": "ordinal", "sort": y_sort, "title": None},
                    "x": {"field": "plan_s_clip", "type": "temporal", "axis": {"title": None}},
                    "x2": {"field": "plan_f_clip"},
                    "color": {"field": "bucket", "type": "nominal", "title": "Status",
                              "scale": {"domain": ["Done","In Progress","Late","Critical"],
                                        "range":  ["#10b981","#3b82f6","#ef4444","#d97706"]}},
                    "tooltip": [
                        {"field":"Project Name"},
                        {"field":"name","title":"Activity"},
                        {"field":"wbs_path","title":"WBS"},
                        {"field":"owner","title":"Owner"},
                        {"field":"pct_complete","title":"% Complete","type":"quantitative"},
                        {"field":"planned_start","title":"Planned Start","type":"temporal"},
                        {"field":"planned_finish","title":"Planned Finish","type":"temporal"},
                        {"field":"actual_start","title":"Actual Start","type":"temporal"},
                        {"field":"actual_finish","title":"Actual Finish","type":"temporal"},
                        {"field":"bl_start","title":"Baseline Start","type":"temporal"},
                        {"field":"bl_finish","title":"Baseline Finish","type":"temporal"},
                        {"field":"Delay (days)","type":"quantitative"},
                        {"field":"critical","title":"Critical"}
                    ]
                }
            },
            {
                "data": {"name": "acts"},
                "mark": {"type": "bar", "height": 6, "color": "#0ea5e9", "opacity": 0.7},
                "encoding": {
                    "y": {"field": "label", "type": "ordinal", "sort": y_sort},
                    "x": {"field": "planned_start", "type": "temporal", "axis": {"title": None}},
                    "x2": {"field": "prog_end_clip"}
                }
            },
            {
                "data": {"name": "acts"},
                "transform": [{"filter": "datum['actual_start'] != null"}],
                "mark": {"type": "bar", "height": 8, "color": "#111827"},
                "encoding": {
                    "y": {"field": "label", "type": "ordinal", "sort": y_sort},
                    "x": {"field": "act_s_clip", "type": "temporal", "axis": {"title": None}},
                    "x2": {"field": "act_f_clip"}
                }
            },
            {
                "data": {"values": [{"today": today_iso}]},
                "mark": {"type": "rule", "stroke": "#ef4444", "strokeDash": [6,4], "strokeWidth": 2},
                "encoding": {"x": {"field": "today", "type": "temporal", "axis": {"title": None}}}
            }
        ]
    }

    st.vega_lite_chart(spec, use_container_width=True)

st.caption("Grid drives the Gantt: expand/collapse nodes; select any rows to filter the chart. If nothing is selected, the chart shows everything in the window. Static demo; wire to your APIs later.")
