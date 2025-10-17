# pages/11_Portfolio_Snapshot.py
# Multi-project portfolio snapshot: heatmap-style table + bubble chart + top/bottom bars
# Uses Streamlit + Vega-Lite (no matplotlib dependency)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

st.set_page_config(page_title="Portfolio Snapshot", layout="wide")

# ===================== DEMO DATA (replace with API later) =====================
PROJECTS = pd.DataFrame([
    ["PRJ-001","Project Phoenix",   4200.0, 3_600_000.0, 5_000_000.0, 800.0, "Active"],
    ["PRJ-002","Project Atlas",     3100.0, 2_400_000.0, 3_500_000.0, 750.0, "Active"],
    ["PRJ-003","Project Orion",     2800.0, 2_100_000.0, 3_000_000.0, 720.0, "Active"],
    ["PRJ-004","Project Helios",    3600.0, 2_900_000.0, 4_000_000.0, 790.0, "On Hold"],
    ["PRJ-005","Project Neptune",   2500.0, 1_900_000.0, 2_600_000.0, 700.0, "Active"],
], columns=["project_id","name","budget_hours","budget_cost","budget_revenue","default_rate","status"])

EMPLOYEES = pd.DataFrame([
    ["E-01","Amr","PM",1200.0,8.0],
    ["E-02","Lina","Eng",950.0,8.0],
    ["E-03","Omar","Tech",600.0,8.0],
    ["E-04","Sara","Eng",900.0,8.0],
], columns=["employee_id","name","role","default_rate","capacity_hours_per_day"])

# Simulate time entries per project (Jan→Aug)
rng = np.random.RandomState(22)
entries = []
for p in PROJECTS.itertuples():
    for d in pd.date_range("2025-01-10","2025-08-31", freq="14D"):
        hrs = rng.randint(100, 500)
        emp = rng.choice(EMPLOYEES["employee_id"])
        entries.append([f"TE-{p.project_id}-{d.date()}", None, p.project_id, emp, d.date(), float(hrs), True, None, "work"])
TIMEENTRIES = pd.DataFrame(entries, columns=["timeentry_id","task_id","project_id","employee_id","date","hours","billable","rate_at_entry","notes"])

# Demo billing/collections
BILLING = pd.DataFrame([
    ["INV-001","PRJ-001",date(2025,2,28), 650_000, 650_000, "collected"],
    ["INV-002","PRJ-001",date(2025,5,30), 820_000, 600_000, "partially_collected"],
    ["INV-003","PRJ-002",date(2025,4,15), 540_000, 540_000, "collected"],
    ["INV-004","PRJ-002",date(2025,7,15), 620_000,   0,     "issued"],
    ["INV-005","PRJ-003",date(2025,6,10), 480_000, 120_000, "partially_collected"],
    ["INV-006","PRJ-004",date(2025,5,20), 400_000,   0,     "dispute"],
    ["INV-007","PRJ-005",date(2025,7,5),  350_000, 350_000, "collected"],
], columns=["invoice_no","project_id","date","amount","collected_amount","status"])

# ===================== HELPERS =====================
def money(x):
    try: return f"{float(x):,.0f}"
    except: return "0"

def pct(n, d):
    return (n/d*100) if d else 0.0

# ===================== CALCS PER PROJECT =====================
TE = TIMEENTRIES.copy()
TE["rate"] = TE["employee_id"].map(EMPLOYEES.set_index("employee_id")["default_rate"]).fillna(PROJECTS["default_rate"].mean())
TE["cost"] = TE["hours"] * TE["rate"]

agg_hours = TE.groupby("project_id")["hours"].sum()
agg_cost  = TE.groupby("project_id")["cost"].sum()
rev_to_date = BILLING.groupby("project_id")["amount"].sum()

# AR Days proxy (DSO): outstanding / avg monthly revenue * 30
collected = BILLING.groupby("project_id")["collected_amount"].sum()
outstanding = rev_to_date.sub(collected, fill_value=0)
avg_month_rev = rev_to_date / 6.0  # demo ~6 months
dso = (outstanding / avg_month_rev.replace(0, np.nan) * 30).replace([np.inf, -np.inf], np.nan).fillna(0)

# Simple SPI/CPI proxies
plan_done = (agg_hours / PROJECTS.set_index("project_id")["budget_hours"]).clip(upper=1.0)
actual_done = plan_done * np.random.uniform(0.85, 1.05, size=len(plan_done))
SPI = (actual_done / plan_done.replace(0, np.nan)).replace([np.inf,-np.inf], np.nan).fillna(1.0)

EV = (PROJECTS.set_index("project_id")["budget_cost"] * actual_done).reindex(PROJECTS["project_id"])
AC = agg_cost.reindex(PROJECTS["project_id"]).fillna(0)
CPI = (EV / AC.replace(0, np.nan)).replace([np.inf,-np.inf], np.nan).fillna(1.0)

budget_used_pct = pct(agg_hours, PROJECTS.set_index("project_id")["budget_hours"])
blended_rate = (agg_cost / agg_hours.replace(0, np.nan)).replace([np.inf,-np.inf], np.nan).fillna(PROJECTS["default_rate"].mean())
remaining_hrs = (PROJECTS.set_index("project_id")["budget_hours"] - agg_hours).clip(lower=0)
EAC_cost = agg_cost + remaining_hrs * blended_rate
forecast_margin_pct = pct(PROJECTS.set_index("project_id")["budget_revenue"] - EAC_cost, PROJECTS.set_index("project_id")["budget_revenue"])

perf = PROJECTS[["project_id","name","budget_hours","budget_cost","budget_revenue","status"]].copy()
perf["Hours"] = perf["project_id"].map(agg_hours).fillna(0.0)
perf["Cost"]  = perf["project_id"].map(agg_cost).fillna(0.0)
perf["Revenue"] = perf["project_id"].map(rev_to_date).fillna(0.0)
perf["GM (EGP)"] = perf["Revenue"] - perf["Cost"]
perf["GM%"] = pct(perf["GM (EGP)"], perf["Revenue"])
perf["Budget Used%"] = budget_used_pct.reindex(perf["project_id"]).fillna(0.0)
perf["CPI"] = CPI.reindex(perf["project_id"]).fillna(1.0)
perf["SPI"] = SPI.reindex(perf["project_id"]).fillna(1.0)
perf["AR Days"] = dso.reindex(perf["project_id"]).fillna(0.0)
perf["Forecast Margin%"] = forecast_margin_pct.reindex(perf["project_id"]).fillna(0.0)
perf["Remaining Budget (EGP)"] = perf["budget_revenue"] - EAC_cost.reindex(perf["project_id"]).fillna(0.0)

# ===================== FILTERS =====================
st.title("📊 Portfolio Snapshot")
with st.sidebar:
    status_filter = st.multiselect("Status", sorted(perf["status"].unique().tolist()), default=sorted(perf["status"].unique().tolist()))
perf_f = perf[perf["status"].isin(status_filter)].reset_index(drop=True)

# ===================== HEATMAP-STYLE TABLE =====================
st.subheader("Health Heatmap (table)")
heat_cols = ["GM%","Forecast Margin%","Budget Used%","CPI","SPI","AR Days"]
ht = perf_f[["name"] + heat_cols].set_index("name").copy()

def color_scale(v, good_high=True):
    if pd.isna(v): return "background-color: rgba(0,0,0,0)"
    if good_high:
        g = min(max((v - 50) / 50, 0), 1)  # >50 good
        r = 1 - g
        return f"background-color: rgba({int(255*r)},{int(255*g)},120,0.25)"
    else:
        r = min(max((v - 45) / 45, 0), 1)  # >45 goes red
        g = 1 - r
        return f"background-color: rgba({int(255*r)},{int(255*g)},120,0.25)"

def style_fn(val, col):
    if col in ("GM%","Forecast Margin%","Budget Used%","CPI","SPI"):
        return color_scale(val, good_high=True)
    if col=="AR Days":
        return color_scale(val, good_high=False)
    return ""

st.dataframe(
    ht.style.format({"GM%":"{:.0f}%","Forecast Margin%":"{:.0f}%","Budget Used%":"{:.0f}%","CPI":"{:.2f}","SPI":"{:.2f}","AR Days":"{:.0f}"})
      .apply(lambda s: [style_fn(v, s.name) for v in s], axis=1),
    use_container_width=True
)

# ===================== BUBBLE CHART (Vega-Lite) =====================
st.subheader("Margin vs Utilization (bubble ~ remaining budget)")

# Utilization proxy per project
months = 6
capacity_proxy = 480.0 * months
util = (perf_f["Hours"] / capacity_proxy * 100).clip(upper=200)

bubble = perf_f.copy()
bubble["Utilization %"] = util
bubble["Forecast Margin %"] = bubble["Forecast Margin%"]
bubble["Remaining Budget"] = bubble["Remaining Budget (EGP)"].clip(lower=0)

def cpi_bucket(v):
    if v >= 0.95: return "Good (≥0.95)"
    if v >= 0.85: return "Watch (0.85–0.95)"
    return "Risk (<0.85)"

bubble["CPI Bucket"] = bubble["CPI"].apply(cpi_bucket)

spec = {
    "mark": {"type": "circle", "opacity": 0.7},
    "encoding": {
        "x": {"field": "Forecast Margin %", "type": "quantitative", "title": "Forecast Margin %"},
        "y": {"field": "Utilization %", "type": "quantitative", "title": "Utilization % (proxy)"},
        "size": {
            "field": "Remaining Budget",
            "type": "quantitative",
            "title": "Remaining Budget (EGP)",
            "scale": {"range": [50, 1200]}
        },
        "color": {
            "field": "CPI Bucket",
            "type": "nominal",
            "scale": {"domain": ["Good (≥0.95)","Watch (0.85–0.95)","Risk (<0.85)"],
                      "range": ["#2ca02c","#ff7f0e","#d62728"]},
            "title": "CPI"
        },
        "tooltip": [
            {"field":"name","title":"Project"},
            {"field":"GM%","type":"quantitative","format":".0f","title":"GM%"},
            {"field":"Forecast Margin %","type":"quantitative","format":".0f"},
            {"field":"Utilization %","type":"quantitative","format":".0f"},
            {"field":"Remaining Budget","type":"quantitative","format":",.0f"},
            {"field":"CPI","type":"quantitative","format":".2f"},
            {"field":"SPI","type":"quantitative","format":".2f"},
        ]
    },
    "height": 380
}
st.vega_lite_chart(bubble, spec, use_container_width=True)

# ===================== TOP / BOTTOM BARS =====================
st.subheader("Top / Bottom Projects")
tb1, tb2 = st.columns(2)
with tb1:
    st.write("Top by Gross Margin (EGP)")
    top_gm = perf_f.sort_values("GM (EGP)", ascending=False).head(5).set_index("name")["GM (EGP)"]
    st.bar_chart(top_gm)
with tb2:
    st.write("Lowest Margin %")
    low_m = perf_f.sort_values("GM%").head(5).set_index("name")["GM%"]
    st.bar_chart(low_m)

# ===================== DETAIL TABLE =====================
st.subheader("Portfolio Table")
st.dataframe(
    perf_f[["name","status","Revenue","Cost","GM (EGP)","GM%","Budget Used%","CPI","SPI","AR Days","Forecast Margin%"]]
      .rename(columns={"name":"Project"})
      .style.format({"Revenue":"{:,.0f}","Cost":"{:,.0f}","GM (EGP)":"{:,.0f}","GM%":"{:.0f}%","Budget Used%":"{:.0f}%","CPI":"{:,.2f}","SPI":"{:,.2f}","AR Days":"{:.0f}","Forecast Margin%":"{:.0f}%"}),
    use_container_width=True
)

st.caption("Static demo. Replace DATA with your APIs; keep columns so metrics compute the same.")
