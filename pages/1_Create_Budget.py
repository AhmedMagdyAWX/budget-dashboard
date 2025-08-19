# pages/1_Create_Budget.py  (compat: no MultiSelectColumn required)

import streamlit as st
import pandas as pd
from datetime import date
import json

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
    cols = ["Item"] + extra_cols + [m.strftime("%Y-%m") for m in months]
    df = pd.DataFrame(columns=cols)
    if items:
        df["Item"] = items
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
    rows = []
    for _, row in grid_df.iterrows():
        item_name = str(row.get("Item", "")).strip()
        for m in months_cols:
            val = pd.to_numeric(row.get(m, 0), errors="coerce")
            val = 0.0 if pd.isna(val) else float(val)
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
                entry[c] = ";".join(parse_multi(v)) if c in multi_cols else ("" if pd.isna(v) else str(v))
            rows.append(entry)
    return pd.DataFrame(rows).sort_values(["Item", "Month"]).reset_index(drop=True)

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
                v = "" if pd.isna(v) else str(v).strip()
                if v:
                    used.setdefault(v, set()).add(i + 1)
        dups = [(val, sorted(list(rows))) for val, rows in used.items() if len(rows) > 1]
        if dups:
            issues[c] = dups
    return issues

def display_copy_for_editor(df, extra_cols, multi_cols):
    """Make a read-only view for dimension columns (shown in table), while months remain editable."""
    view = df.copy()
    for c in extra_cols:
        if c in multi_cols:
            view[c] = view[c].apply(lambda lst: ";".join(parse_multi(lst)))
        else:
            view[c] = view[c].astype(str)
    return view

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
st.subheader("1) Items & Monthly Planned amounts")

with st.expander("📥 Import from CSV/Excel (optional)", expanded=False):
    st.markdown(
        "- **Template** columns: `Item`, your selected dimensions, then months `YYYY-MM`.\n"
        "- For multi dims (Entity/Asset) use **semicolon or comma** : `E001;E002`."
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
        for col in ["Item"] + extra_cols:
            if col not in uploaded_df.columns:
                uploaded_df[col] = "" if col != "Item" else uploaded_df.get("Item", "")
        for m in month_labels:
            if m not in uploaded_df.columns:
                uploaded_df[m] = 0
        uploaded_df = uploaded_df[["Item"] + extra_cols + month_labels]
        uploaded_df = normalize_dimension_columns(uploaded_df, extra_cols, multi_cols)

# ---------------- Init state ----------------
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

st.caption("Tip: Edit amounts in the table. Assign dimensions with the dropdowns below.")

# ---------------- Data editor (dimensions read-only here) ----------------
cfg = {}
for m in month_labels:
    cfg[m] = st.column_config.NumberColumn(m, min_value=0.0, step=1.0, help="Planned amount")

for c in extra_cols:
    # show as read-only strings; edit below in dropdown panel
    cfg[c] = st.column_config.TextColumn(c, help="Managed via dropdowns below", disabled=True)

# Build display copy
display_df = display_copy_for_editor(st.session_state["grid_df"], extra_cols, multi_cols)

edited_display = st.data_editor(
    display_df,
    num_rows="dynamic",
    column_config=cfg,
    use_container_width=True,
    key="grid_editor",
)

# Push edited item/months back into the real grid
for col in ["Item"] + month_labels:
    if col in edited_display.columns:
        st.session_state["grid_df"][col] = edited_display[col]

grid_df = st.session_state["grid_df"]

# ---------------- Dimension assignment panel (dropdowns) ----------------
st.subheader("2) Assign Dimensions (no duplicates across rows)")

def remaining_options(all_opts, taken_sets, current_set):
    taken = set().union(*[set(parse_multi(s)) for s in taken_sets]) - set(parse_multi(current_set))
    return [o for o in all_opts if o not in taken]

def remaining_single_options(all_opts, taken_vals, current_val):
    taken = set(v for v in taken_vals if v) - ({current_val} if current_val else set())
    return [o for o in all_opts if o not in taken]

if grid_df.empty:
    st.info("Add at least one row in the table above.")
else:
    for idx in range(len(grid_df)):
        row = grid_df.iloc[idx]
        with st.expander(f"Row {idx+1}: {row.get('Item','(no item)')}", expanded=False):
            # Entity (multi)
            if "Entity" in extra_cols:
                others = grid_df["Entity"].tolist()
                opts = remaining_options(entity_options, others[:idx] + others[idx+1:], row.get("Entity", []))
                sel = st.multiselect(
                    "Entity (multi)",
                    options=opts + [x for x in parse_multi(row.get("Entity", [])) if x not in opts],
                    default=parse_multi(row.get("Entity", [])),
                    key=f"entity_{idx}"
                )
                grid_df.at[idx, "Entity"] = sel

            # CostCenter (single)
            if "CostCenter" in extra_cols:
                others = grid_df["CostCenter"].tolist()
                cur = row.get("CostCenter", "")
                opts = remaining_single_options(costcenter_options, others[:idx] + others[idx+1:], cur)
                sel = st.selectbox(
                    "CostCenter (single)",
                    options=[""] + opts + ([cur] if cur and cur not in opts else []),
                    index=([""] + opts + ([cur] if cur and cur not in opts else [])).index(cur) if cur in ([""] + opts + ([cur] if cur and cur not in opts else [])) else 0,
                    key=f"cc_{idx}"
                )
                grid_df.at[idx, "CostCenter"] = sel

            # Asset (multi)
            if "Asset" in extra_cols:
                others = grid_df["Asset"].tolist()
                opts = remaining_options(asset_options, others[:idx] + others[idx+1:], row.get("Asset", []))
                sel = st.multiselect(
                    "Asset (multi)",
                    options=opts + [x for x in parse_multi(row.get("Asset", [])) if x not in opts],
                    default=parse_multi(row.get("Asset", [])),
                    key=f"asset_{idx}"
                )
                grid_df.at[idx, "Asset"] = sel

# ---------------- Validation ----------------
issues = find_duplicate_assignments(grid_df, extra_cols, multi_cols)
if issues:
    st.error("🚫 Duplicate dimension assignments detected. Fix these before export:")
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

st.caption("Dimensions via dropdowns below. Entity/Asset allow multiple per row; CostCenter is single. Values can’t repeat across rows; duplicates block export.")
