# pages/1_Create_Budget.py  — inline editors with graceful fallback

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
    """Ensure proper Python types post-edit/import."""
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
                v = row.get(c
