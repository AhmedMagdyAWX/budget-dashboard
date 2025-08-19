# pages/1_Create_Budget.py

import streamlit as st
import pandas as pd
from datetime import date
import json

st.set_page_config(page_title="Create Budget", layout="wide")
st.title("🧪 Create Budget")

# ---------------- Helpers ----------------
def month_range(start_dt: date, end_dt: date):
    """Return a Month-Start date_range from start_dt..end_dt (inclusive)."""
    s = pd.Timestamp(start_dt).replace(day=1)
    e = pd.Timestamp(end_dt).replace(day=1)
    if e < s:
        s, e = e, s
    return pd.date_range(s, e, freq="MS")

def make_empty_grid(items, months, extra_cols, multi_cols):
    cols = ["Item"] + extra_cols + [m.strftime("%Y-%m") for m in months]
    df = pd.DataFrame(columns=cols)
    if items:
        df["Item"] = items
    # init month columns
    for m in [m.strftime("%Y-%m") for m in months]:
        df[m] = df.get(m, 0).fillna(0)
    # init dims
    for c in extra_cols:
        if c in multi_cols:
            df[c] = [ [] for _ in range(len(df)) ]  # independent lists per row
        else:
            df[c] = df.get(c, "")
    return df

def parse_multi(cell):
    """Turn cell (str/list/None) into list[str] using , or ; separators."""
    if isinstance(cell, list):
        return [str(x).strip() for x in cell if str(x).strip()]
    if pd.isna(cell) or cell is None:
        return []
    s = str(cell).strip()
    if not s:
        return []
    # split on comma or semicolon
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    return [p for p in parts if p]

def normalize_dimension_columns(df, extra_cols, multi_cols):
    """Ensure correct types for dimension columns after upload/edit."""
    if df is None:
        return None
    df = df.copy()
    for c in extra_cols:
        if c in multi_cols:
            df[c] = df[c].apply(parse_multi)
        else:
            df[c] = df[c].apply(lambda v: "" if pd.isna(v) else str(v).strip())
    return df

def to_long_format(grid_df, months_cols, meta, extra_cols, multi_cols):
    """Convert editor grid to long format; multi dims exported as ';' joined strings."""
    long_rows = []
    for ridx, row in grid_df.iterrows():
        item_name = str(row.get("Item", "")).strip()
        for m in months_cols:
            val = pd.to_numeric(row.get(m, 0), errors="coerce")
            val = 0 if pd.isna(val) else float(val)
            entry = {
                "Budget": meta["budget_name"],
                "Version": meta["version"],
                "BudgetType": meta["budget_type"],
                "Project": meta.get("project_name") if meta["budget_type"] == "Project" else "",
                "Currency": meta["currency"],
                "Month": pd.to_datetime(m + "-01"),
                "Item": item_name,
                "Planned": val,
            }
            for c in extra_cols:
                v = row.get(c, [] if c in multi_cols else "")
                if c in multi_cols:
                    entry[c] = ";".join(parse_multi(v))
                else:
                    entry[c] = "" if pd.isna(v) else str(v)
            long_rows.append(entry)
    return pd.DataFrame(long_rows).sort_values(["Item", "Month"]).reset_index(drop=True)

def find_duplicate_assignments(df, extra_cols, multi_cols):
    """
    Returns dict: {dim_name: [(value, [row_idx1,row_idx2,...]), ...]}
    Duplicates mean the same dim value appears in more than one row.
    """
    issues = {}
    if df is None or df.empty:
        return issues
    for c in extra_cols:
        used = {}
        if c in multi_cols:
            # value used if present in that row's list
            for i, vals in enumerate(df[c].apply(parse_multi).tolist()):
                for v in vals:
                    used.setdefault(v, set()).add(i + 1)  # 1-based row index for UI
        else:
            for i, v in enumerate(df[c].tolist()):
                v = "" if pd.isna(v) else str(v).strip()
                if v:
                    used.setdefault(v, set()).add(i + 1)
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

colA, colB = st.sidebar.columns(2)
start_month = colA.date_input("From (month)", value=date(date.today().year, 1, 1))
end_month   = colB.date_input("To (month)",   value=date(date.today().year, 12, 1))
if pd.Timestamp(end_month) < pd.Timestamp(start_month):
    st.warning("⚠️ 'To (month)' is before 'From (month)'. Swapping them.")
    start_month, end_month = end_month, start_month

# Choose which dimensions to include
extra_cols = st.sidebar.multiselect(
    "Use dimensions",
    ["Entity", "CostCenter", "Asset"],
    default=["Entity", "CostCenter", "Asset"]
)
multi_cols = {"Entity", "Asset"}  # allow many links per budget line

# Catalogs for dropdowns
with st.sidebar.expander("📚 Dimension catalogs"):
    def _parse_catalog(label, default_lines):
        txt = st.text_area(label, value="\n".join(default_lines), height=100)
        return [x.strip() for x in txt.splitlines() if x.strip()]

    entity_options = _parse_catalog("Entities (one per line)", ["E001", "E002", "E003"])
    costcenter_options = _parse_catalog("Cost Centers (one per line)", ["CC-Admin", "CC-OPS", "CC-ENG"])
    asset_options = _parse_catalog("Assets (one per line)", ["AS-TRUCK-01", "AS-GEN-02", "AS-CRANE-03"])

# ---------------- Months for grid ----------------
months = month_range(start_month, end_month)
month_labels = [m.strftime("%Y-%m") for m in months]

# ---------------- Data import / template ----------------
st.subheader("1) Items & Monthly Planned amounts")

with st.expander("📥 Import from CSV/Excel (optional)", expanded=False):
    st.markdown(
        "- **Template** columns: `Item`, optional selected dimensions, then month columns like `YYYY-MM`.\n"
        "- For multi dims (Entity/Asset), you may use **semicolon or comma** separators in a cell, e.g. `E001;E002`."
    )
    tmpl_cols = ["Item"] + extra_cols + month_labels
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

        # Ensure required columns exist; add missing selected month columns with zeros
        for col in ["Item"] + extra_cols:
            if col not in uploaded_df.columns:
                uploaded_df[col] = "" if col != "Item" else uploaded_df.get("Item", "")
        for m in month_labels:
            if m not in uploaded_df.columns:
                uploaded_df[m] = 0

        uploaded_df = uploaded_df[["Item"] + extra_cols + month_labels]
        uploaded_df = normalize_dimension_columns(uploaded_df, extra_cols, multi_cols)

# ---------------- Init / session state ----------------
default_items = ["Rentals", "Fuel", "Construction", "Salaries", "Marketing", "Equipment"]

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

st.caption("Tip: Double-click cells to edit. Use the ➕ button to add rows.")

# ---------------- Editor config ----------------
cfg = {}
# numeric month columns
for m in month_labels:
    cfg[m] = st.column_config.NumberColumn(m, min_value=0.0, step=1.0, help="Planned amount")

# dimension columns
if "Entity" in extra_cols:
    cfg["Entity"] = st.column_config.MultiSelectColumn(
        "Entity",
        options=entity_options,
        help="Select one or more Entities. Each Entity can be used in only one row.",
    )
if "CostCenter" in extra_cols:
    cfg["CostCenter"] = st.column_config.SelectboxColumn(
        "CostCenter",
        options=[""] + costcenter_options,
        help="Select one Cost Center. A Cost Center cannot be reused in another row.",
    )
if "Asset" in extra_cols:
    cfg["Asset"] = st.column_config.MultiSelectColumn(
        "Asset",
        options=asset_options,
        help="Select one or more Assets. Each Asset can be used in only one row.",
    )

grid_df = st.data_editor(
    st.session_state["grid_df"],
    num_rows="dynamic",
    column_config=cfg,
    use_container_width=True,
    key="grid_editor",
)

# Ensure proper types after editing
grid_df = normalize_dimension_columns(grid_df, extra_cols, multi_cols)

# ---------------- Validation: no duplicate assignments across rows ----------------
issues = find_duplicate_assignments(grid_df, extra_cols, multi_cols)
if issues:
    st.error("🚫 Duplicate dimension assignments detected (a value is used in more than one row). Fix these before export:")
    for dim, vals in issues.items():
        for v, rows in vals:
            st.write(f"- **{dim}** `{v}` used in rows: {rows}")
else:
    st.success("✅ No duplicate dimension assignments.")

# ---------------- Totals preview ----------------
with st.expander("👀 Preview Totals", expanded=False):
    numeric = grid_df[month_labels].apply(pd.to_numeric, errors="coerce").fillna(0)
    row_totals = numeric.sum(axis=1)
    prev = grid_df[["Item"] + [c for c in extra_cols if c not in {"Entity", "Asset"}]].copy()
    # show counts of multi dims for quick glance
    if "Entity" in extra_cols:
        prev["#Entities"] = grid_df["Entity"].apply(lambda x: len(parse_multi(x)))
    if "Asset" in extra_cols:
        prev["#Assets"] = grid_df["Asset"].apply(lambda x: len(parse_multi(x)))
    prev["Row Total Planned"] = row_totals
    st.dataframe(prev, use_container_width=True)

    col_totals = numeric.sum(axis=0)
    st.write("Per-Month Totals:")
    st.dataframe(col_totals.to_frame(name="Planned").T, use_container_width=True)

# ---------------- Save / Export ----------------
st.subheader("2) Save & Export")

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

# Validate required fields
errors = []
if not meta["budget_name"]:
    errors.append("Budget Name is required.")
if budget_type == "Project" and not meta["project_name"]:
    errors.append("Project Name is required for Project budgets.")
if len(months) == 0:
    errors.append("Please choose a valid month range.")
if issues:
    errors.append("Resolve duplicate dimension assignments before exporting.")

if errors:
    st.error(" • " + "\n • ".join(errors))
else:
    long_df = to_long_format(grid_df, month_labels, meta, extra_cols, multi_cols)

    c1, c2 = st.columns(2)
    c1.download_button(
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
    c2.download_button(
        "⬇️ Export Budget as JSON",
        json.dumps(payload, indent=2).encode("utf-8"),
        file_name=f"{meta['budget_name']}_{meta['version']}.json",
        mime="application/json",
        key="dl_json"
    )

st.caption("Notes: Entity & Asset accept multiple values; CostCenter is single. Export is blocked if any dimension value is used in more than one row. Multi values are stored as ';' joined strings.")
