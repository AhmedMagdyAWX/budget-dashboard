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

    # --- REPLACED: Monthly breakdown by item (stacked rows with merged item + Variance %) ---
    st.markdown("#### Monthly Breakdown by Item (stacked rows, merged item label + Variance %)")

    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        metric_options = ["Planned", "Actual", "Variance", "Variance %"]
        metrics_selected = st.multiselect(
            "Show rows for:",
            metric_options,
            default=metric_options,
            help="Uncheck to hide any of Planned / Actual / Variance / Variance %",
        )

        if not metrics_selected:
            st.warning("Select at least one metric to display.")
        else:
            # Build monthly sums and compute Variance + Variance %
            monthly = (
                filtered.groupby(["Item", "Month"])[["Planned", "Actual"]]
                .sum()
                .reset_index()
                .sort_values(["Item", "Month"])
            )
            monthly["Variance"] = monthly["Actual"] - monthly["Planned"]
            # Variance % = (Actual - Planned) / Planned * 100, safe for zero planned
            monthly["Variance %"] = (monthly["Variance"] / monthly["Planned"]).where(monthly["Planned"] != 0).mul(100)

            # Keep user-selected order for stacked metrics
            cat = pd.api.types.CategoricalDtype(categories=metrics_selected, ordered=True)

            long = monthly.melt(
                id_vars=["Item", "Month"],
                value_vars=metrics_selected,
                var_name="Metric",
                value_name="Amount",
            )
            long["Metric"] = long["Metric"].astype(cat)

            # Wide for display: rows = (Item, Metric), columns = months
            table = (
                long.pivot_table(
                    index=["Item", "Metric"],
                    columns="Month",
                    values="Amount",
                    aggfunc="sum",
                )
                .sort_index()
            )

            # Pretty month headers
            if table.shape[1] > 0:
                table.columns = [c.strftime("%Y-%m") for c in table.columns]

            # Reset index so we can "merge" the item label by blanking consecutive repeats
            table_disp = table.reset_index()

            # Show the item only on the first metric row of each item group
            is_first_of_group = table_disp["Item"].ne(table_disp["Item"].shift())
            table_disp["Item"] = table_disp["Item"].where(is_first_of_group, "")

            # Format numbers: percent for "Variance %", thousands for others
            month_cols = [c for c in table_disp.columns if c not in ["Item", "Metric"]]
            # Create a display copy with strings for pretty formatting
            table_show = table_disp.copy()
            for col in month_cols:
                # Percent rows
                mask_pct = table_show["Metric"] == "Variance %"
                table_show.loc[mask_pct, col] = table_show.loc[mask_pct, col].apply(
                    lambda v: "-" if pd.isna(v) else f"{float(v):.2f}%"
                )
                # Numeric rows
                mask_num = ~mask_pct
                table_show.loc[mask_num, col] = table_show.loc[mask_num, col].apply(
                    lambda v: "-" if pd.isna(v) else f"{int(round(float(v))):,}"
                )

            # Styling: color text by metric on the month columns
            color_map = {
                "Planned": "#1f77b4",    # blue
                "Actual": "#2ca02c",     # green
                "Variance": "#d62728",   # red
                "Variance %": "#9467bd", # purple
            }
            ncols = table_show.shape[1]

            def color_by_metric_row(row):
                color = color_map.get(row["Metric"])
                styles = []
                for col in table_show.columns:
                    if col in month_cols and color:
                        styles.append(f"color: {color}; font-weight:600")
                    else:
                        styles.append("")
                return styles

            def bold_first_item_row(row):
                if row["Item"]:
                    styles = [""] * ncols
                    styles[table_show.columns.get_loc("Item")] = "font-weight:700"
                    return styles
                return [""] * ncols

            styled = (
                table_show.style
                .apply(color_by_metric_row, axis=1)
                .apply(bold_first_item_row, axis=1)
            )

            st.dataframe(styled, use_container_width=True)

            # Download (long format) for Excel/Sheets — Variance % as numeric percent
            csv = long.sort_values(["Item", "Metric", "Month"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download monthly stacked breakdown (CSV)",
                csv,
                file_name=f"monthly_stacked_{selected_budget}_{selected_version}.csv",
                mime="text/csv",
            )

            st.caption("Colors — Planned: blue, Actual: green, Variance: red, Variance %: purple. Note: tables don’t support true row-spans; item label is shown on the first metric row only.")


# ---------- Notes ----------
st.caption("Tip: Use the Items filter to focus on specific categories. Switch the chart metric to compare Planned vs Actual per item.")




