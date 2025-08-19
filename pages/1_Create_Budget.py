# pages/1_Create_Budget.py  — inline editors with hierarchy + validation (upgrade-safe)

import streamlit as st
import pandas as pd
from datetime import date
import json
from collections import defaultdict, deque

st.set_page_config(page_title="Create Budget", layout="wide")
st.title("🧪 Create Budget")

# ---------------- Helpers ----------------
def month_range(start_dt: date, end_dt: date):
    s = pd.Timestamp(start_dt).replace(day=1)
    e = pd.Timestamp(end_dt).replace(day=1)
    if e < s:
        s, e = e, s
    return pd.date_range(s, e, freq="MS")

def parse_multi(cell):
    """Turn cell (str/list/None) into list[str] using , or ; separators."""
    if isinstance(cell, list):
        return [str(x).strip() for x in cell if str(x).strip()]
    if pd.isna(cell) or cell is None:
        return []
    s = str(cell).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    return [p for p in parts if p]

def make_empty_grid(items, months, extra_cols, multi_cols):
    cols = ["Code", "ParentCode", "Item"] + extra_cols + [m.strftime("%Y-%m") for m in months]
    df = pd.DataFrame(columns=cols)
    if items:
        df["Item"] = items
    df["Code"] = ""          # user will fill
    df["ParentCode"] = ""    # user will fill
    # init months
    for m in [m.strftime("%Y-%m") for m in months]:
        df[m] = 0
    # init dims
    for c in extra_cols:
        if c in multi_cols:
            df[c] = [[] for _ in range(len(df))]
        else:
            df[c] = ""
    return df

def normalize_dimension_columns(df, extra_cols, multi_cols):
    """Ensure proper Python types post-edit/import and presence of hierarchy cols."""
    if df is None:
        return None
    df = df.copy()
    # hierarchy cols must exist
    for c in ["Code","ParentCode","Item"]:
        if c not in df.columns:
            df[c] = "" if c != "Item" else df.get("Item", "")
    for c in extra_cols:
        if c in multi_cols:
            df[c] = df[c].apply(parse_multi) if c in df.columns else pd.Series([[] for _ in range(len(df))], index=df.index)
        else:
            df[c] = df[c].apply(lambda v: "" if pd.isna(v) else str(v).strip()) if c in df.columns else ""
    for c in ["Code","ParentCode"]:
        df[c] = df[c].fillna("").astype(str)
    return df

def to_long_format(grid_df, months_cols, meta, extra_cols, multi_cols):
    rows = []
    for _, row in grid_df.iterrows():
        item_name = str(row.get("Item", "")).strip()
        code = str(row.get("Code","")).strip()
        parent = str(row.get("ParentCode","")).strip()
        for m in months_cols:
            val = pd.to_numeric(row.get(m, 0), errors="coerce")
            val = 0.0 if pd.isna(val) else float(val)
            entry = {
                "Budget": meta["budget_name"],
                "Version": meta["version"],
                "BudgetType": meta["budget_type"],
                "Project": meta.get("project_name") if meta["budget_type"] == "Project" else "",
                "Currency": meta["currency"],
                "Code": code,
                "ParentCode": parent,
                "Month": pd.to_datetime(m + "-01"),
                "Item": item_name,
                "Planned": val,
            }
            for c in extra_cols:
                v = row.get(c, [] if c in multi_cols else "")
                entry[c] = ";".join(parse_multi(v)) if c in multi_cols else ("" if pd.isna(v) else str(v))
            rows.append(entry)
    return pd.DataFrame(rows).sort_values(["Code","Item","Month"]).reset_index(drop=True)

def find_duplicate_assignments(df, extra_cols, multi_cols):
    issues = {}
    if df is None or df.empty:
        return issues
    for c in extra_cols:
        used = {}
        if c in multi_cols:
            for i, vals in enumerate(df[c].apply(parse_multi).tolist()):
                for v in vals:
                    used.setdefault(v, set()).add(i + 1)
        else:
            for i, v in enumerate(df[c].tolist()):
                v = "" if pd.isna(v) else str(v).str ip() if isinstance(v, pd.Series) else ("" if pd.isna(v) else str(v).strip())
                if v:
                    used.setdefault(v, set()).add(i + 1)
        dups = [(val, sorted(list(rows))) for val, rows in used.items() if len(rows) > 1]
        if dups:
            issues[c] = dups
    return issues

def detect_cycles(pairs):
    """pairs: list of (parent, child). Return True if a cycle exists."""
    graph = defaultdict(list)
    indeg = defaultdict(int)
    nodes = set()
    for p,c in pairs:
        if p and c:
            graph[p].append(c); indeg[c]+=1
            nodes.add(p); nodes.add(c)
        elif c:
            nodes.add(c)
    dq = deque([n for n in nodes if indeg[n]==0])
    count=0
    while dq:
        u = dq.popleft(); count += 1
        for v in graph.get(u, []):
            indeg[v]-=1
            if indeg[v]==0: dq.append(v)
    return count != len(nodes)

# ---------------- Sidebar: metadata ----------------
st.sidebar.header("Budget Metadata")

budget_type = st.sidebar.radio("Budget Type", ["Company", "Project"], index=0)
budget_name = st.sidebar.text_input("Budget Name", value="Company")
project_name = st.sidebar.text_input("Project Name (if Project)", value="", disabled=(budget_type != "Project"))

version = st.sidebar.text_input("Version label", value="V1")
currency = st.sidebar.text_input("Currency", value="EGP")

colA, colB = st.sidebar.columns(2)
start_month = colA.date_input("From (month)", value=date(date.today().year, 1, 1))
end_month   = colB.date_input("To (month)",   value=date(date.today().year, 12, 1))
if pd.Timestamp(end_month) < pd.Timestamp(start_month):
    st.warning("⚠️ 'To (month)' is before 'From (month)'. Swapping them.")
    start_month, end_month = end_month, start_month

# Choose dimensions
extra_cols = st.sidebar.multiselect(
    "Use dimensions",
    ["Entity", "CostCenter", "Asset"],
    default=["Entity", "CostCenter", "Asset"]
)
multi_cols = {"Entity", "Asset"}  # allow many links per line

# Catalogs
with st.sidebar.expander("📚 Dimension catalogs"):
    def _parse_catalog(label, default_lines):
        txt = st.text_area(label, value="\n".join(default_lines), height=100)
        return [x.strip() for x in txt.splitlines() if x.strip()]
    entity_options = _parse_catalog("Entities (one per line)", ["E001", "E002", "E003"])
    costcenter_options = _parse_catalog("Cost Centers (one per line)", ["CC-Admin", "CC-OPS", "CC-ENG"])
    asset_options = _parse_catalog("Assets (one per line)", ["AS-TRUCK-01", "AS-GEN-02", "AS-CRANE-03"])

# ---------------- Months ----------------
months = month_range(start_month, end_month)
month_labels = [m.strftime("%Y-%m") for m in months]

# ---------------- Import / template ----------------
st.subheader("1) Items, Hierarchy & Monthly Planned amounts")

with st.expander("📥 Import from CSV/Excel (optional)", expanded=False):
    st.markdown(
        "- **Template** columns: `Code`, `ParentCode`, `Item`, your selected dimensions, then months `YYYY-MM`.\n"
        "- For multi dims (Entity/Asset) use **semicolon or comma** : `E001;E002`."
    )
    tmpl_cols = ["Code","ParentCode","Item"] + extra_cols + month_labels
    tmpl_df = pd.DataFrame(columns=tmpl_cols)
    st.download_button(
        "⬇️ Download empty template (CSV)",
        tmpl_df.to_csv(index=False).encode("utf-8"),
        file_name="budget_template.csv",
        mime="text/csv",
        key="dl_tmpl"
    )

    up = st.file_uploader("Upload CSV or Excel to prefill the grid", type=["csv", "xlsx"])
    uploaded_df = None
    if up is not None:
        if up.name.lower().endswith(".csv"):
            uploaded_df = pd.read_csv(up)
        else:
            uploaded_df = pd.read_excel(up)
        # Ensure required columns exist
        for col in ["Code","ParentCode","Item"] + extra_cols:
            if col not in uploaded_df.columns:
                uploaded_df[col] = "" if col != "Item" else uploaded_df.get("Item", "")
        for m in month_labels:
            if m not in uploaded_df.columns:
                uploaded_df[m] = 0
        uploaded_df = uploaded_df[["Code","ParentCode","Item"] + extra_cols + month_labels]
        uploaded_df = normalize_dimension_columns(uploaded_df, extra_cols, multi_cols)

# ---------------- Init state ----------------
default_items = ["Operations","Rentals","Fuel","Construction","Overheads","Salaries","Marketing"]

if (
    "grid_df" not in st.session_state
    or st.session_state.get("grid_months") != month_labels
    or st.session_state.get("grid_extras") != tuple(extra_cols)
):
    st.session_state["grid_df"] = make_empty_grid(default_items, months, extra_cols, multi_cols)
    st.session_state["grid_months"] = month_labels
    st.session_state["grid_extras"] = tuple(extra_cols)

if uploaded_df is not None:
    st.session_state["grid_df"] = uploaded_df.copy()

grid_df = st.session_state["grid_df"]

# --- UPGRADE-SAFE: ensure required columns exist in current session grid ---
for col in ["Code","ParentCode","Item"]:
    if col not in grid_df.columns:
        # add with sensible defaults
        grid_df[col] = "" if col != "Item" else grid_df.get("Item", "")
for c in extra_cols:
    if c not in grid_df.columns:
        if c in multi_cols:
            grid_df[c] = pd.Series([[] for _ in range(len(grid_df))], index=grid_df.index)
        else:
            grid_df[c] = ""
for m in month_labels:
    if m not in grid_df.columns:
        grid_df[m] = 0
# normalize types after patch
grid_df = normalize_dimension_columns(grid_df, extra_cols, multi_cols)

# ---------------- Build inline editors with graceful fallback ----------------
has_multi  = hasattr(st.column_config, "MultiSelectColumn")
has_select = hasattr(st.column_config, "SelectboxColumn")

cfg = {}
# Hierarchy editors
cfg["Code"] = st.column_config.TextColumn("Code", help="Unique ID for this line (e.g., RENT, FUEL01).")

# Parent options based on current codes (may be blank initially)
existing_codes = sorted([c for c in grid_df["Code"].astype(str).unique() if c])
parent_options = [""] + existing_codes
if has_select:
    cfg["ParentCode"] = st.column_config.SelectboxColumn("ParentCode", options=parent_options, help="Parent line code (optional).")
else:
    cfg["ParentCode"] = st.column_config.TextColumn("ParentCode", help="Parent line code (optional).")

# Item
cfg["Item"] = st.column_config.TextColumn("Item", help="Budget line item / category")

# Month numeric editors
for m in month_labels:
    cfg[m] = st.column_config.NumberColumn(m, min_value=0.0, step=1.0, help="Planned amount")

# Dimension editors
if "Entity" in extra_cols:
    if has_multi:
        cfg["Entity"] = st.column_config.MultiSelectColumn("Entity", options=entity_options, help="Select one or more Entities")
    else:
        cfg["Entity"] = st.column_config.TextColumn("Entity", help="Enter semicolon/comma-separated list")
if "CostCenter" in extra_cols:
    if has_select:
        cfg["CostCenter"] = st.column_config.SelectboxColumn("CostCenter", options=[""] + costcenter_options, help="Single selection")
    else:
        cfg["CostCenter"] = st.column_config.TextColumn("CostCenter", help="Type a value")
if "Asset" in extra_cols:
    if has_multi:
        cfg["Asset"] = st.column_config.MultiSelectColumn("Asset", options=asset_options, help="Select one or more Assets")
    else:
        cfg["Asset"] = st.column_config.TextColumn("Asset", help="Enter semicolon/comma-separated list")

edited = st.data_editor(
    grid_df,
    num_rows="dynamic",
    column_config=cfg,
    use_container_width=True,
    key="grid_editor",
)

# Normalize types
