# pages/1_Create_Budget.py

import streamlit as st
import pandas as pd
from datetime import date
import json

st.set_page_config(page_title="Create Budget", layout="wide")
st.title("🧪 Create Budget")

# --- Helpers ---
def month_range(start_dt: date, end_dt: date):
    """Return a Month-Start date_range from start_dt..end_dt (inclusive)."""
    # Normalize to first day of month (avoids to_timestamp('MS') issues on some pandas versions)
    s = pd.Timestamp(start_dt).replace(day=1)
    e = pd.Timestamp(end_dt).replace(day=1)
    # Guard against reversed inputs
    if e < s:
        s, e = e, s
    return pd.date_range(s, e, freq="MS")

def make_empty_grid(items, months, extra_cols):
    cols = ["Item"] + extra_cols + [m.strftime("%Y-%m") for m in months]
    df = pd.DataFrame(columns=cols)
    if items:
        df["Item"] = items
    # Initialize numeric months to 0
    for m in [m.strftime("%Y-%m") for m in months]:
        df[m] = df.get(m, 0).fillna(0)
    # Initialize extra columns as empty text
    for c in extra_cols:
        df[c] = df.get(c, "")
    return df

def to_long_format(grid_df, months_cols, meta, extra_cols):
    """Convert editor grid to long format:
       Budget, Version, BudgetType, Project, Currency, Item, Month, Planned, [extra cols]
    """
    long_rows = []
    for _, row in grid_df.iterrows():
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
            # extra dimensional columns
            for c in extra_cols:
                entry[c] = str(row.get(c, "")).strip()
            long_rows.append(entry)
    return pd.DataFrame(long_rows).sort_values(["Item", "Month"]).reset_index(drop=True)

# --- Sidebar: metadata ---
st.sidebar.header("Budget Metadata")

budget_type = st.sidebar.radio("Budget Type", ["Company", "Project"], index=0)
budget_name = st.sidebar.text_input("Budget Name", value="Company")
project_name = st.sidebar.text_input("Project Name (if Project)", value="", disabled=(budget_type != "Project"))

version = st.sidebar.text_input("Version label", value="V1")
currency = st.sidebar.text_input("Currency", value="EGP")

colA, colB = st.sidebar.columns(2)
start_month = colA.date_input("From (month)", value=date(date.today().year, 1, 1))
end_month   = colB.date_input("To (month)",   value=date(date.today().year, 12, 1))

# Safety: swap if reversed selection
if pd.Timestamp(end_month) < pd.Timestamp(start_month):
    st.warning("⚠️ 'To (month)' is before 'From (month)'. Swapping them.")
    start_month, end_month = end_month, start_month

extra_cols = st.sidebar.multiselect(
    "Optional dimension columns",
    ["Entity", "CostCenter", "Asset"],
    default=[]
)

# --- Months for grid ---
months = month_range(start_month, end_month)
month_labels = [m.strftime("%Y-%m") for m in months]

# --- Data import / template ---
st.subheader("1) Items & Monthly Planned amounts")

with st.expander("📥 Import from CSV/Excel (optional)", expanded=False):
    st.markdown(
        "- **CSV/Excel template** expects columns: `Item`, any optional dimension columns you selected, then month columns like `YYYY-MM`.\n"
        "- Example: `Item,Entity,2025-01,2025-02,2025-03,...`"
    )

    # Generate a template to download
    tmpl_cols = ["Item"] + extra_cols + month_labels
    tmpl_df = pd.DataFrame(columns=tmpl_cols)
    csv_bytes = tmpl_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download empty template (CSV)",
        csv_bytes,
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
            # Requires openpyxl in requirements.txt
            uploaded_df = pd.read_excel(up)

        # Ensure required columns exist; add missing selected month columns with zeros
        for col in ["Item"] + extra_cols:
            if col not in uploaded_df.columns:
                uploaded_df[col] = "" if col != "Item" else uploaded_df.get("Item", "")
        for m in month_labels:
            if m not in uploaded_df.columns:
                uploaded_df[m] = 0

        # Keep only relevant columns in correct order
        uploaded_df = uploaded_df[["Item"] + extra_cols + month_labels]

# Initial items quick-fill
default_items = ["Rentals", "Fuel", "Construction", "Salaries", "Marketing", "Equipment"]

# --- State init: rebuild grid if months or extra columns changed ---
if (
    "grid_df" not in st.session_state
    or st.session_state.get("grid_months") != month_labels
    or st.session_state.get("grid_extras") != tuple(extra_cols)
):
    st.session_state["grid_df"] = make_empty_grid(default_items, months, extra_cols)
    st.session_state["grid_months"] = month_labels
    st.session_state["grid_extras"] = tuple(extra_cols)

# If file was uploaded, override the grid with uploaded content
if 'uploaded_df' in locals() and uploaded_df is not None:
    st.session_state["grid_df"] = uploaded_df.copy()

st.caption("Tip: Double-click cells to edit. Use the ➕ button in the table footer to add rows.")

# Column config for the editor
cfg = {}
for m in month_labels:
    cfg[m] = st.column_config.NumberColumn(m, min_value=0.0, step=1.0, help="Planned amount")
for c in extra_cols:
    cfg[c] = st.column_config.TextColumn(c)

grid_df = st.data_editor(
    st.session_state["grid_df"],
    num_rows="dynamic",
    column_config=cfg,
    use_container_width=True,
    key="grid_editor",
)

# --- Totals preview ---
with st.expander("👀 Preview Totals", expanded=False):
    numeric = grid_df[month_labels].apply(pd.to_numeric, errors="coerce").fillna(0)
    # Row totals
    row_totals = numeric.sum(axis=1)
    prev = grid_df[["Item"] + extra_cols].copy()
    prev["Row Total Planned"] = row_totals
    st.write("Per-Item Totals (across selected months):")
    st.dataframe(prev, use_container_width=True)

    # Column totals
    col_totals = numeric.sum(axis=0)
    st.write("Per-Month Totals:")
    st.dataframe(col_totals.to_frame(name="Planned").T, use_container_width=True)

# --- Save / Export ---
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

# Validate
errors = []
if not meta["budget_name"]:
    errors.append("Budget Name is required.")
if budget_type == "Project" and not meta["project_name"]:
    errors.append("Project Name is required for Project budgets.")
if len(months) == 0:
    errors.append("Please choose a valid month range.")

if errors:
    st.error(" • " + "\n • ".join(errors))
else:
    long_df = to_long_format(grid_df, month_labels, meta, extra_cols)

    # Export buttons
    c1, c2 = st.columns(2)
    csv_bytes = long_df.to_csv(index=False).encode("utf-8")
    c1.download_button(
        "⬇️ Export Planned as CSV (long format)",
        csv_bytes,
        file_name=f"{meta['budget_name']}_{meta['version']}_planned.csv",
        mime="text/csv",
        key="dl_csv"
    )

    # JSON schema friendly for future import
    payload = {
        "meta": meta,
        "data": long_df.assign(Month=lambda d: d["Month"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
    }
    json_bytes = json.dumps(payload, indent=2).encode("utf-8")
    c2.download_button(
        "⬇️ Export Budget as JSON",
        json_bytes,
        file_name=f"{meta['budget_name']}_{meta['version']}.json",
        mime="application/json",
        key="dl_json"
    )

st.caption("Note: This page captures **Planned** values. Actuals & Variance are computed in the viewer.")
