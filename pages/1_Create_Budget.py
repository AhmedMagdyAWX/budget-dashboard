# pages/1_Create_Budget.py — Tree view grid (AG Grid) + hierarchy validation + export

import streamlit as st
import pandas as pd
from datetime import date
from collections import defaultdict, deque
import json as _json

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode

st.set_page_config(page_title="Create Budget (Tree)", layout="wide")
st.title("🌳 Create Budget — Tree Editor")

# ---------------- Helpers ----------------
def month_range(start_dt: date, end_dt: date):
    s = pd.Timestamp(start_dt).replace(day=1)
    e = pd.Timestamp(end_dt).replace(day=1)
    if e < s:
        s, e = e, s
    return pd.date_range(s, e, freq="MS")

def parse_multi(cell):
    if isinstance(cell, list):
        return [str(x).strip() for x in cell if str(x).strip()]
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s:
        return []
    return [p.strip() for p in s.replace(";", ",").split(",") if p.strip()]

def make_empty_grid(items, months, extra_cols):
    cols = ["Code", "ParentCode", "Item"] + extra_cols + [m.strftime("%Y-%m") for m in months]
    df = pd.DataFrame(columns=cols)
    if items:
        df["Item"] = items
    df["Code"] = ""
    df["ParentCode"] = ""
    for m in [m.strftime("%Y-%m") for m in months]:
        df[m] = 0
    for c in extra_cols:
        df[c] = ""  # edit as strings in-grid; parse on export
    return df

def normalize_types(df, extra_cols):
    df = df.copy()
    # Ensure presence and string type
    for c in ["Code", "ParentCode", "Item"]:
        if c not in df.columns:
            df[c] = "" if c != "Item" else df.get("Item", "")
        df[c] = df[c].fillna("").astype(str)
    for c in extra_cols:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str)
    # Ensure month cols exist and are numeric
    for c in df.columns:
        if len(c) == 7 and c[:4].isdigit() and c[4] == "-":
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def build_tree_path(df):
    """
    Returns:
      paths: list[list[str]] path from root to node (by display names)
      is_leaf: list[bool]
      has_cycle: bool
    """
    codes = df["Code"].astype(str).tolist()
    parents = df["ParentCode"].astype(str).tolist()
    items = df["Item"].astype(str).tolist()

    parent_of = {c: p for c, p in zip(codes, parents) if c}
    name_of = {c: it for c, it in zip(codes, items) if c}

    # Detect cycles (Kahn)
    pairs = [(parent_of.get(c, ""), c) for c in codes if c]
    graph = defaultdict(list)
    indeg = defaultdict(int)
    nodes = set()
    for p, c in pairs:
        if c:
            nodes.add(c)
        if p:
            graph[p].append(c)
            indeg[c] += 1
            nodes.add(p)
    dq = deque([n for n in nodes if indeg[n] == 0])
    seen = 0
    while dq:
        u = dq.popleft()
        seen += 1
        for v in graph.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                dq.append(v)
    has_cycle = (seen != len(nodes)) and len(nodes) > 0

    def path_for(code, fallback_name):
        if not code:
            return [fallback_name or "(unnamed)"]
        path, guard = [], set()
        cur = code
        while True:
            if cur in guard:  # cycle guard
                path.append(f"!!CYCLE:{cur}")
                break
            guard.add(cur)
            nm = name_of.get(cur, cur)
            path.append(nm)
            p = parent_of.get(cur, "")
            if not p or p not in name_of:
                break
            cur = p
        return list(reversed(path))

    paths = []
    is_parent_set = set(parent_of.values()) - {""}
    for _, row in df.iterrows():
        code = str(row["Code"])
        nm = str(row["Item"])
        paths.append(path_for(code, nm))

    is_leaf = [str(row["Code"]) not in is_parent_set for _, row in df.iterrows()]
    return paths, is_leaf, has_cycle

def to_long_format(df, months_cols, meta, extra_cols):
    rows = []
    for _, r in df.iterrows():
        code = str(r.get("Code", "")).strip()
        parent = str(r.get("ParentCode", "")).strip()
        item = str(r.get("Item", "")).strip()
        for m in months_cols:
            val = pd.to_numeric(r.get(m, 0), errors="coerce")
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
                "Item": item,
                "Planned": val,
            }
            for c in extra_cols:
                entry[c] = ";".join(parse_multi(r.get(c, "")))
            rows.append(entry)
    return pd.DataFrame(rows).sort_values(["Code", "Item", "Month"]).reset_index(drop=True)

def find_duplicate_dims_leaf_only(df_leaf, extra_cols):
    issues = {}
    if df_leaf.empty:
        return issues
    for c in extra_cols:
        used = {}
        for i, v in enumerate(df_leaf[c].tolist()):
            vals = parse_multi(v)
            if not vals:
                continue
            for one in vals:
                used.setdefault(one, set()).add(i + 1)  # 1-based for UI
        dups = [(val, sorted(list(rows))) for val, rows in used.items() if len(rows) > 1]
        if dups:
            issues[c] = dups
    return issues

# ---------------- Sidebar: metadata ----------------
st.sidebar.header("Budget Metadata")

budget_type = st.sidebar.radio("Budget Type", ["Company", "Project"], index=0)
budget_name = st.sidebar.text_input("Budget Name", value="Company")
project_name = st.sidebar.text_input("Project Name (if Project)", value="", disabled=(budget_type != "Project"))

version = st.sidebar.text_input("Version label", value="V1")
currency = st.sidebar.text_input("Currency", value="EGP")

c1, c2 = st.sidebar.columns(2)
start_month = c1.date_input("From (month)", value=date(date.today().year, 1, 1))
end_month   = c2.date_input("To (month)",   value=date(date.today().year, 12, 1))
if pd.Timestamp(end_month) < pd.Timestamp(start_month):
    st.warning("⚠️ Swapped date range (To < From).")
    start_month, end_month = end_month, start_month

extra_cols = st.sidebar.multiselect(
    "Dimensions (leaf rows)",
    ["Entity", "CostCenter", "Asset"],
    default=["Entity", "CostCenter", "Asset"]
)

with st.sidebar.expander("📚 Dimension catalogs"):
    def _parse_catalog(label, defaults):
        return st.text_area(label, value="\n".join(defaults), height=100).splitlines()
    entity_options = [x.strip() for x in _parse_catalog("Entities", ["E001", "E002", "E003"]) if x.strip()]
    costcenter_options = [x.strip() for x in _parse_catalog("Cost Centers", ["CC-Admin", "CC-OPS", "CC-ENG"]) if x.strip()]
    asset_options = [x.strip() for x in _parse_catalog("Assets", ["AS-TRUCK-01", "AS-GEN-02", "AS-CRANE-03"]) if x.strip()]

months = month_range(start_month, end_month)
month_labels = [m.strftime("%Y-%m") for m in months]

# ---------------- Import / template ----------------
st.subheader("1) Import (optional)")

with st.expander("📥 Upload CSV/Excel (long or wide acceptable)", expanded=False):
    st.markdown(
        "- **Wide format**: `Code, ParentCode, Item, [dims...], 2025-01, 2025-02, ...`\n"
        "- **Long format**: `Budget, Version, Code, ParentCode, Item, Month, Planned, [dims...]`"
    )
    up = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
    uploaded_df = None
    if up is not None:
        uploaded_df = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
        # Long -> wide
        if "Month" in uploaded_df.columns and "Planned" in uploaded_df.columns:
            tmp = uploaded_df.copy()
            tmp["Month"] = pd.to_datetime(tmp["Month"]).dt.strftime("%Y-%m")
            need = ["Code", "ParentCode", "Item"]
            for c in need:
                if c not in tmp.columns:
                    tmp[c] = ""
            for c in extra_cols:
                if c not in tmp.columns:
                    tmp[c] = ""
            wide = tmp.pivot_table(index=need + extra_cols, columns="Month", values="Planned", aggfunc="sum").reset_index()
            for m in month_labels:
                if m not in wide.columns:
                    wide[m] = 0
            uploaded_df = wide[need + extra_cols + month_labels]
        else:
            # Assume wide; ensure required columns
            for c in ["Code", "ParentCode", "Item"]:
                if c not in uploaded_df.columns:
                    uploaded_df[c] = "" if c != "Item" else uploaded_df.get("Item", "")
            for c in extra_cols:
                if c not in uploaded_df.columns:
                    uploaded_df[c] = ""
            for m in month_labels:
                if m not in uploaded_df.columns:
                    uploaded_df[m] = 0
            uploaded_df = uploaded_df[["Code", "ParentCode", "Item"] + extra_cols + month_labels]

# ---------------- Session grid init ----------------
default_items = ["Operations", "Rentals", "Fuel", "Construction", "Overheads", "Salaries", "Marketing"]
if (
    "grid_df" not in st.session_state
    or st.session_state.get("grid_months") != month_labels
    or st.session_state.get("grid_extras") != tuple(extra_cols)
):
    st.session_state["grid_df"] = make_empty_grid(default_items, months, extra_cols)
    st.session_state["grid_months"] = month_labels
    st.session_state["grid_extras"] = tuple(extra_cols)

if uploaded_df is not None:
    st.session_state["grid_df"] = uploaded_df.copy()

grid_df = normalize_types(st.session_state["grid_df"], extra_cols)

# ---------------- Build tree path & flags ----------------
paths, is_leaf, has_cycle = build_tree_path(grid_df)
# Store path as string for hashing; JS will split it
grid_df["_path"] = ["||".join(p) for p in paths]
grid_df["isLeaf"] = is_leaf

# Zero out parents in the backing frame (leaf-only input)
month_cols = [c for c in grid_df.columns if len(c) == 7 and c[4] == "-" and c[:4].isdigit()]
if grid_df["isLeaf"].notna().any():
    grid_df.loc[~grid_df["isLeaf"], month_cols] = 0

# ---------------- Tree Grid (AG Grid) ----------------
st.subheader("2) Edit Tree")

# Build grid display DF (hide helper)
display_cols = ["_path", "Code", "ParentCode", "Item"] + extra_cols + month_labels
gb = GridOptionsBuilder.from_dataframe(grid_df[display_cols])
gb.configure_grid_options(
    treeData=True,
    animateRows=True,
    groupDisplayType="tree",
    getDataPath=JsCode("function(data){ return data._path.split('||'); }"),
    autoGroupColumnDef={
        "headerName": "Item",
        "minWidth": 260,
        "cellRendererParams": {"suppressCount": True}
    },
    rowSelection="multiple",
    groupDefaultExpanded=0,
)

gb.configure_column("_path", header_name="Path", hide=True)
gb.configure_column("Code", editable=True, width=140)
gb.configure_column("ParentCode", editable=True, width=160)
gb.configure_column("Item", editable=True, width=220)

# Dimensions
if "Entity" in extra_cols:
    gb.configure_column("Entity", editable=True, header_name="Entity (E001;E002)", width=220)
if "CostCenter" in extra_cols:
    gb.configure_column(
        "CostCenter",
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": [""] + costcenter_options},
        width=160
    )
if "Asset" in extra_cols:
    gb.configure_column("Asset", editable=True, header_name="Asset (AS-1;AS-2)", width=220)

# Month columns: numeric, sum on parents, editable only on leaves
editable_leaf_js = JsCode("function(params){ return !!(params.data && params.data.isLeaf===true); }")
disable_parent_style = JsCode(
    "function(params){ if(params.data && params.data.isLeaf===true){return {'fontWeight':'600'};} "
    "else {return {'color':'#666','backgroundColor':'#f7f7f7'};} }"
)
for m in month_labels:
    gb.configure_column(
        m,
        type=["numericColumn"],
        editable=editable_leaf_js,
        aggFunc="sum",
        valueParser=JsCode("function(p){var v=Number(p.newValue); return isNaN(v)?0:v;}"),
        cellStyle=disable_parent_style,
        width=120
    )

gb.configure_side_bar()
gb.configure_selection("multiple", use_checkbox=True)
go = gb.build()

grid_resp = AgGrid(
    grid_df,
    gridOptions=go,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=560,
)

edited_df = pd.DataFrame(grid_resp.data) if grid_resp.data is not None else grid_df.copy()
edited_df = normalize_types(edited_df, extra_cols)

# Recompute tree after edits
paths, is_leaf, has_cycle = build_tree_path(edited_df)
edited_df["_path"] = ["||".join(p) for p in paths]
edited_df["isLeaf"] = is_leaf
edited_df.loc[~edited_df["isLeaf"], month_cols] = 0

# Persist
st.session_state["grid_df"] = edited_df
grid_df = edited_df

# Row add/delete
c_add, c_del = st.columns(2)
if c_add.button("➕ Add Row"):
    new = {col: "" for col in ["Code", "ParentCode", "Item"] + extra_cols}
    for m in month_labels:
        new[m] = 0
    grid_df = pd.concat([grid_df, pd.DataFrame([new])], ignore_index=True)
    st.session_state["grid_df"] = grid_df
    st.rerun()

sel = pd.DataFrame(grid_resp.get("selected_rows", []))
if c_del.button("🗑️ Delete Selected") and not sel.empty:
    key_cols = ["Code", "ParentCode", "Item"]
    merged = grid_df.merge(sel[key_cols].drop_duplicates(), on=key_cols, how="left", indicator=True)
    grid_df = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
    st.session_state["grid_df"] = grid_df
    st.rerun()

# ---------------- Validation ----------------
err_msgs = []

# Hierarchy checks
dups = grid_df["Code"].astype(str).str.strip()
dups = dups[dups != ""]
dup_codes = sorted(dups[dups.duplicated()].unique())
if dup_codes:
    err_msgs.append(f"Duplicate Codes: {', '.join(dup_codes)}")

self_parent = grid_df[
    grid_df["Code"].astype(str).str.strip()
    == grid_df["ParentCode"].astype(str).str.strip()
]
if len(self_parent) > 0:
    err_msgs.append("Self-parenting detected (a row has ParentCode equal to its own Code).")

if has_cycle:
    err_msgs.append("Hierarchy cycle detected. Fix ParentCode assignments.")

# Dimension duplicates on leaves only
leaf_df = grid_df[grid_df["isLeaf"]].copy() if "isLeaf" in grid_df.columns else grid_df.copy()
dims_present = [c for c in ["Entity", "CostCenter", "Asset"] if c in extra_cols]
if dims_present and not leaf_df.empty:
    dup_dims = find_duplicate_dims_leaf_only(leaf_df[dims_present], dims_present)
    for dim, vals in dup_dims.items():
        for v, rows in vals:
            err_msgs.append(f"Duplicate {dim} value '{v}' across leaf rows {rows}")

if err_msgs:
    st.error("🚫 Please fix before export:\n- " + "\n- ".join(err_msgs))
else:
    st.success("✅ Hierarchy & dimension checks passed.")

# ---------------- Preview totals ----------------
with st.expander("👀 Preview (leaf rows only)", expanded=False):
    if not leaf_df.empty:
        leaf_numeric = leaf_df[month_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        leaf_df["Row Total Planned"] = leaf_numeric.sum(axis=1)
        st.dataframe(leaf_df[["Code", "ParentCode", "Item"] + dims_present + ["Row Total Planned"]], use_container_width=True)
        col_totals = leaf_numeric.sum(axis=0)
        st.write("Per-Month Totals:")
        st.dataframe(col_totals.to_frame(name="Planned").T, use_container_width=True)
    else:
        st.info("No leaf rows to preview.")

# ---------------- Export ----------------
st.subheader("3) Save & Export")

meta = {
    "budget_type": budget_type,
    "budget_name": budget_name.strip(),
    "project_name": project_name.strip(),
    "version": version.strip(),
    "currency": currency.strip(),
    "start_month": months.min().strftime("%Y-%m-%d") if len(months) else "",
    "end_month": months.max().strftime("%Y-%m-%d") if len(months) else "",
    "months_count": len(months),
    "extra_columns": extra_cols,
}

can_export = (
    len(err_msgs) == 0
    and len(months) > 0
    and bool(meta["budget_name"])
    and (budget_type != "Project" or meta["project_name"])
)

if not can_export:
    st.warning("Fill required fields and fix errors to enable export.")

c_csv, c_json = st.columns(2)
if can_export:
    long_df = to_long_format(leaf_df, month_labels, meta, extra_cols)
    c_csv.download_button(
        "⬇️ Export Planned as CSV (long format)",
        long_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{meta['budget_name']}_{meta['version']}_planned.csv",
        mime="text/csv",
        key="dl_csv"
    )
    payload = {
        "meta": meta,
        "data": long_df.assign(Month=lambda d: d["Month"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
    }
    c_json.download_button(
        "⬇️ Export Budget as JSON",
        _json.dumps(payload, indent=2).encode("utf-8"),
        file_name=f"{meta['budget_name']}_{meta['version']}.json",
        mime="application/json",
        key="dl_json"
    )

st.caption("Use **Code** + **ParentCode** to build the tree. Edit amounts on **leaf** rows only; parents auto-sum in the tree.")
