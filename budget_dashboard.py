import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Budget Dashboard", layout="wide")

st.title("📊 Budget Dashboard (Budgets • Versions • Items)")

# ---------- Sample Data ----------
@st.cache_data
def generate_sample_data():
    budgets = ["Company", "Project A", "Project B"]
    versions = [f"V{i}" for i in range(1, 11)]  # V1..V10
    months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
    items = ["Rentals", "Fuel", "Construction", "Salaries", "Marketing", "Equipment"]

    rows = []
    for budget in budgets:
        for version in versions:
            for item in items:
                for m in months:
                    # deterministic pseudo-random numbers by hashing keys
                    base = 8000 + (abs(hash(f"{budget}-{item}")) % 6000)
                    v_adj = (int(version[1:]) - 5) * 250  # version shift
                    season = (m.month % 6) * 150  # seasonality
                    planned = max(1000, base + v_adj + season)
                    jitter = ((abs(hash(f"{budget}-{version}-{item}-{m}")) % 21) - 10) / 100.0  # -10%..+10%
                    actual = int(planned * (1 + jitter))
                    rows.append({
                        "Budget": budget,
                        "Version": version,
                        "Item": item,
                        "Month": m,
                        "Planned": int(planned),
                        "Actual": int(actual)
                    })
    df = pd.DataFrame(rows)
    return df

df = generate_sample_data()

# ---------- Sidebar Filters ----------
st.sidebar.header("Filters")

# 1) Choose Budget
budget_options = sorted(df["Budget"].unique())
selected_budget = st.sidebar.selectbox("🏷️ Budget", budget_options, index=0)

# 2) Choose Version (filtered by Budget)
vers_for_budget = sorted(df.loc[df["Budget"] == selected_budget, "Version"].unique(),
                         key=lambda v: int(v[1:]), reverse=True)
selected_version = st.sidebar.selectbox("📄 Version", vers_for_budget, index=0)

# 3) Date Range (bounded by available data)
df_bv = df[(df["Budget"] == selected_budget) & (df["Version"] == selected_version)]
min_month, max_month = df_bv["Month"].min().date(), df_bv["Month"].max().date()
col_from, col_to = st.sidebar.columns(2)
from_date = col_from.date_input("📅 From", min_month, min_value=min_month, max_value=max_month)
to_date = col_to.date_input("📅 To", max_month, min_value=min_month, max_value=max_month)

# 4) Items filter
all_items = sorted(df_bv["Item"].unique())
selected_items = st.sidebar.multiselect("🧩 Items (categories)", all_items, default=all_items)

# 5) Metric to chart
metric_choice = st.sidebar.radio("📈 Chart metric", ["Planned", "Actual"], index=0)

# ---------- Apply Filters ----------
filtered = df_bv[
    (df_bv["Month"] >= pd.to_datetime(from_date)) &
    (df_bv["Month"] <= pd.to_datetime(to_date)) &
    (df_bv["Item"].isin(selected_items))
].copy()

st.subheader(f"📁 {selected_budget} • {selected_version}  ({from_date} → {to_date})")

# ---------- Charts ----------
tab1, tab2, tab3 = st.tabs(["By Item over Time", "Totals over Time", "Table & KPIs"])

with tab1:
    st.markdown("#### Items vs Month")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        # pivot: rows = Month, columns = Item, values = metric
        pivot_items = filtered.pivot_table(index="Month", columns="Item", values=metric_choice, aggfunc="sum")
        st.line_chart(pivot_items)

with tab2:
    st.markdown("#### Overall Planned vs Actual")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        by_month = filtered.groupby("Month")[["Planned", "Actual"]].sum().sort_index()
        st.line_chart(by_month)

with tab3:
    st.markdown("#### Breakdown by Item (Totals)")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        summary = (filtered
                   .groupby("Item")[["Planned", "Actual"]]
                   .sum()
                   .reset_index())
        summary["Variance"] = summary["Actual"] - summary["Planned"]
        summary["Variance %"] = (summary["Variance"] / summary["Planned"]).replace([pd.NA, pd.NaT, float("inf")], 0) * 100

        st.dataframe(
            summary.style.format({
                "Planned": "{:,.0f}",
                "Actual": "{:,.0f}",
                "Variance": "{:,.0f}",
                "Variance %": "{:.2f}%"
            })
        )

        # KPIs
        total_planned = int(summary["Planned"].sum())
        total_actual = int(summary["Actual"].sum())
        variance_total = total_actual - total_planned
        variance_pct = (variance_total / total_planned * 100) if total_planned else 0

        st.markdown("#### KPIs")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Planned", f"{total_planned:,.0f} EGP")
        c2.metric("Total Actual", f"{total_actual:,.0f} EGP", delta=f"{variance_total:,.0f} EGP")
        c3.metric("Variance %", f"{variance_pct:.2f}%")
        c4.metric("Items Count", f"{len(selected_items)}")

    # --- NEW: Monthly breakdown per item ---
    st.markdown("#### Monthly Breakdown by Item")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        view = st.radio("Monthly table metric", ["All metrics", "Planned", "Actual", "Variance"], horizontal=True)

        monthly = (
            filtered.groupby(["Item", "Month"])[["Planned", "Actual"]].sum()
            .assign(Variance=lambda d: d["Actual"] - d["Planned"])
            .reset_index()
            .sort_values(["Item", "Month"])
        )

        if view == "All metrics":
            # Multi-index columns: (Metric, Month)
            wide = monthly.pivot_table(
                index="Item",
                columns="Month",
                values=["Planned", "Actual", "Variance"],
                aggfunc="sum"
            ).sort_index(axis=1)
            # Format month labels as YYYY-MM
            wide.columns = pd.MultiIndex.from_tuples(
                [(lvl0, col.strftime("%Y-%m")) for (lvl0, col) in wide.columns],
                names=["Metric", "Month"]
            )
            st.dataframe(wide)
        else:
            wide = monthly.pivot_table(
                index="Item",
                columns="Month",
                values=view,
                aggfunc="sum"
            ).sort_index(axis=1)
            wide.columns = [c.strftime("%Y-%m") for c in wide.columns]
            st.dataframe(wide.style.format("{:,.0f}"))

        # Download CSV of the monthly detail (long format)
        csv = monthly.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download monthly breakdown (CSV)",
            csv,
            file_name=f"monthly_breakdown_{selected_budget}_{selected_version}.csv",
            mime="text/csv"
        )


# ---------- Notes ----------
st.caption("Tip: Use the Items filter to focus on specific categories. Switch the chart metric to compare Planned vs Actual per item.")

