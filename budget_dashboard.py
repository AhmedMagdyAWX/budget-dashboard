import streamlit as st
import pandas as pd
from datetime import datetime
from collections import defaultdict, deque

st.set_page_config(page_title="Budget Dashboard", layout="wide")
st.title("📊 Budget Dashboard (Budgets • Versions • Items • Hierarchy)")

# ---------------- Helpers ----------------
@st.cache_data
def generate_sample_data():
    """
    Demo dataset with Budgets, Versions, Items, Codes/ParentCodes, Month, Planned, Actual.
    Parents have 0 input; leaves carry amounts.
    """
    budgets = ["Company", "Project A", "Project B"]
    versions = [f"V{i}" for i in range(1, 6)]
    months = pd.date_range("2025-01-01", "2025-12-01", freq="MS")

    # A small hierarchy:
    # ROOT (no parent)
    # ├─ OPR (Operations)
    # │  ├─ RENT (Rentals)   [leaf]
    # │  ├─ FUEL (Fuel)      [leaf]
    # │  └─ CONST (Construction) [leaf]
    # └─ OVH (Overheads)
    #    ├─ SAL (Salaries)   [leaf]
    #    └─ MKT (Marketing)  [leaf]
    nodes = [
        ("ROOT", "",        "Total"),
        ("OPR",  "ROOT",    "Operations"),
        ("RENT", "OPR",     "Rentals"),
        ("FUEL", "OPR",     "Fuel"),
        ("CONST","OPR",     "Construction"),
        ("OVH",  "ROOT",    "Overheads"),
        ("SAL",  "OVH",     "Salaries"),
        ("MKT",  "OVH",     "Marketing"),
    ]
    leaf_codes = {"RENT","FUEL","CONST","SAL","MKT"}

    rows = []
    for budget in budgets:
        for version in versions:
            for code, parent, item in nodes:
                for m in months:
                    if code in leaf_codes:
                        base = 8000 + (abs(hash(f"{budget}-{item}")) % 6000)
                        v_adj = (int(version[1:]) - 3) * 350
                        season = (m.month % 6) * 200
                        planned = max(1000, base + v_adj + season)
                        jitter = ((abs(hash(f"{budget}-{version}-{item}-{m}")) % 21) - 10) / 100.0  # -10%..+10%
                        actual = int(planned * (1 + jitter))
                    else:
                        planned = 0
                        actual = 0
                    rows.append({
                        "Budget": budget,
                        "Version": version,
                        "Item": item,
                        "Code": code,
                        "ParentCode": parent,
                        "Month": m,
                        "Planned": int(planned),
                        "Actual": int(actual)
                    })
    df = pd.DataFrame(rows)
    return df

def load_uploaded(planned_df: pd.DataFrame | None, actuals_df: pd.DataFrame | None):
    """
    Accepts CSVs in long format:
      Budget, Version, Item, Code, ParentCode, Month(YYYY-MM or date), Planned [, Actual]
    If actuals_df provided: same keys + Actual. If not, Actual copied from Planned.
    """
    if planned_df is None or planned_df.empty:
        return None
    df = planned_df.copy()
    # Parse dates
    df["Month"] = pd.to_datetime(df["Month"])
    # Ensure required cols
    for col in ["Budget","Version","Item","Month"]:
        if col not in df.columns:
            raise ValueError(f"Missing column in Planned CSV: {col}")
    if "Planned" not in df.columns:
        df["Planned"] = 0.0

    # Actuals
    if actuals_df is not None and not actuals_df.empty:
        a = actuals_df.copy()
        a["Month"] = pd.to_datetime(a["Month"])
        key = ["Budget","Version","Item","Code","ParentCode","Month"]
        for c in ["Code","ParentCode"]:
            if c not in a.columns: a[c] = ""
            if c not in df.columns: df[c] = ""
        merged = pd.merge(
            df, a[key + ["Actual"]], on=key, how="left", validate="m:m"
        )
        merged["Actual"] = merged["Actual"].fillna(merged["Planned"])
        df = merged
    else:
        if "Actual" not in df.columns:
            df["Actual"] = df["Planned"]

    # Normalize hierarchy cols
    for c in ["Code","ParentCode"]:
        if c not in df.columns: df[c] = ""
        df[c] = df[c].fillna("").astype(str)

    return df

def compute_hierarchy_rollup(filtered: pd.DataFrame) -> pd.DataFrame:
    """
    Roll up Planned/Actual along Code/ParentCode and return indented table.
    """
    if not {"Code","ParentCode"}.issubset(filtered.columns):
        return None

    nodes = filtered[["Item","Code","ParentCode"]].drop_duplicates().copy()
    sums = filtered.groupby(["Code"])[["Planned","Actual"]].sum().reset_index()

    kids = defaultdict(list); indeg = defaultdict(int)
    codes = set(nodes["Code"].astype(str))
    parent_map = dict(zip(nodes["Code"].astype(str), nodes["ParentCode"].fillna("").astype(str)))
    name_map = dict(zip(nodes["Code"].astype(str), nodes["Item"]))

    for _, r in nodes.iterrows():
        c = str(r["Code"]); p = str(r["ParentCode"]) if pd.notna(r["ParentCode"]) else ""
        if p and p in codes:
            kids[p].append(c); indeg[c] += 1
        else:
            indeg[c] += 0

    q = deque([c for c in codes if indeg[c] == 0])
    order = []
    while q:
        u = q.popleft(); order.append(u)
        for v in kids.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0: q.append(v)

    agg = {c: {"Planned":0.0,"Actual":0.0} for c in codes}
    own = dict(zip(sums["Code"].astype(str), sums[["Planned","Actual"]].values))
    for c in codes:
        if c in own:
            agg[c]["Planned"] = float(own[c][0])
            agg[c]["Actual"]  = float(own[c][1])

    for u in reversed(order):
        for v in kids.get(u, []):
            agg[u]["Planned"] += agg[v]["Planned"]
            agg[u]["Actual"]  += agg[v]["Actual"]

    # levels (for indentation)
    level = {c:0 for c in codes}
    def get_level(x):
        if level.get(x, None) not in (None, 0): return level[x]
        seen=set(); cur=x; d=0
        while True:
            p = parent_map.get(cur, "")
            if not p or p not in codes or p in seen: break
            d += 1; seen.add(p); cur = p
        level[x]=d; return d

    rows=[]
    for c in order:
        nm = name_map.get(c, c)
        d  = get_level(c)
        plan = agg[c]["Planned"]; act = agg[c]["Actual"]; var = act - plan
        rows.append({
            "Item": (" "*d) + ("• " if d>0 else "") + nm,
            "Code": c,
            "Planned": round(plan,2),
            "Actual": round(act,2),
            "Variance": round(var,2),
            "Variance %": (round((var/plan)*100,2) if plan else None)
        })
    return pd.DataFrame(rows)

def format_month(dt):
    return pd.to_datetime(dt).strftime("%Y-%m")

# ---------------- Data source ----------------
with st.expander("📥 Optional: upload your CSVs (exported from Create page)", expanded=False):
    st.markdown("- **Planned CSV** must include: Budget, Version, Item, Month, Planned. (Optional: Code, ParentCode)")
    up_plan = st.file_uploader("Planned CSV", type=["csv"], key="up_plan")
    up_act  = st.file_uploader("Actuals CSV (optional)", type=["csv"], key="up_act")

df = None
if up_plan is not None:
    plan_df = pd.read_csv(up_plan)
    act_df = pd.read_csv(up_act) if up_act is not None else None
    df = load_uploaded(plan_df, act_df)
else:
    df = generate_sample_data()

# ---------------- Sidebar Filters ----------------
st.sidebar.header("Filters")

budget_options = sorted(df["Budget"].unique())
selected_budget = st.sidebar.selectbox("🏷️ Budget", budget_options, index=0)

vers_for_budget = sorted(
    df.loc[df["Budget"] == selected_budget, "Version"].unique(),
    key=lambda v: int(v[1:]) if isinstance(v, str) and v[1:].isdigit() else 0,
    reverse=True
)
selected_version = st.sidebar.selectbox("📄 Version", vers_for_budget, index=0)

df_bv = df[(df["Budget"] == selected_budget) & (df["Version"] == selected_version)].copy()
min_month, max_month = df_bv["Month"].min().date(), df_bv["Month"].max().date()
col_from, col_to = st.sidebar.columns(2)
from_date = col_from.date_input("📅 From", min_month, min_value=min_month, max_value=max_month)
to_date   = col_to.date_input("📅 To", max_month, min_value=min_month, max_value=max_month)

all_items = sorted(df_bv["Item"].unique())
selected_items = st.sidebar.multiselect("🧩 Items (categories)", all_items, default=all_items)
metric_choice = st.sidebar.radio("📈 Chart metric", ["Planned", "Actual"], index=0)

filtered = df_bv[
    (df_bv["Month"] >= pd.to_datetime(from_date)) &
    (df_bv["Month"] <= pd.to_datetime(to_date)) &
    (df_bv["Item"].isin(selected_items))
].copy()

st.subheader(f"📁 {selected_budget} • {selected_version}  ({from_date} → {to_date})")

# ---------------- Tabs ----------------
tab1, tab2, tab3, tab4 = st.tabs(["By Item over Time", "Totals over Time", "Table & KPIs", "Hierarchy (Roll-up)"])

with tab1:
    st.markdown("#### Items vs Month")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
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
            }),
            use_container_width=True
        )

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

    # --- Monthly stacked table with merged item label + Variance % ---
    st.markdown("#### Monthly Breakdown by Item (stacked rows, merged item label + Variance %)")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        metric_options = ["Planned", "Actual", "Variance", "Variance %"]
        metrics_selected = st.multiselect(
            "Show rows for:",
            metric_options,
            default=metric_options,
            help="Uncheck to hide any metric",
        )
        if not metrics_selected:
            st.warning("Select at least one metric to display.")
        else:
            monthly = (
                filtered.groupby(["Item", "Month"])[["Planned", "Actual"]]
                .sum()
                .reset_index()
                .sort_values(["Item", "Month"])
            )
            monthly["Variance"] = monthly["Actual"] - monthly["Planned"]
            monthly["Variance %"] = (monthly["Variance"] / monthly["Planned"]).where(monthly["Planned"] != 0).mul(100)

            cat = pd.api.types.CategoricalDtype(categories=metrics_selected, ordered=True)
            long = monthly.melt(
                id_vars=["Item", "Month"],
                value_vars=metrics_selected,
                var_name="Metric",
                value_name="Amount",
            )
            long["Metric"] = long["Metric"].astype(cat)

            table = (
                long.pivot_table(
                    index=["Item", "Metric"],
                    columns="Month",
                    values="Amount",
                    aggfunc="sum",
                )
                .sort_index()
            )
            if table.shape[1] > 0:
                table.columns = [format_month(c) for c in table.columns]

            table_disp = table.reset_index()
            is_first_of_group = table_disp["Item"].ne(table_disp["Item"].shift())
            table_disp["Item"] = table_disp["Item"].where(is_first_of_group, "")

            month_cols = [c for c in table_disp.columns if c not in ["Item", "Metric"]]
            table_show = table_disp.copy()
            for col in month_cols:
                mask_pct = table_show["Metric"] == "Variance %"
                table_show.loc[mask_pct, col] = table_show.loc[mask_pct, col].apply(
                    lambda v: "-" if pd.isna(v) else f"{float(v):.2f}%"
                )
                mask_num = ~mask_pct
                table_show.loc[mask_num, col] = table_show.loc[mask_num, col].apply(
                    lambda v: "-" if pd.isna(v) else f"{int(round(float(v))):,}"
                )

            color_map = {
                "Planned": "#1f77b4",
                "Actual": "#2ca02c",
                "Variance": "#d62728",
                "Variance %": "#9467bd",
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

            csv = long.sort_values(["Item", "Metric", "Month"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download monthly stacked breakdown (CSV)",
                csv,
                file_name=f"monthly_stacked_{selected_budget}_{selected_version}.csv",
                mime="text/csv",
            )

with tab4:
    st.markdown("#### Tree totals (auto-summed from children)")
    if filtered.empty:
        st.info("No data for the selected filters.")
    else:
        out = compute_hierarchy_rollup(filtered)
        if out is None:
            st.info("No hierarchy columns found (Code/ParentCode). Upload/create data with hierarchy to use this tab.")
        else:
            show_leaves_only = st.checkbox("Show leaves only", value=False, key="leaf_only")
            if show_leaves_only and {"Code","ParentCode"}.issubset(filtered.columns):
                leaf_codes = set(
                    filtered.loc[~filtered["Code"].isin(filtered["ParentCode"].replace("", pd.NA).dropna()), "Code"]
                )
                out = out[out["Code"].isin(leaf_codes)]
            st.dataframe(out.drop(columns=["Code"]), use_container_width=True)
