# pages/3_Project_Dashboard.py
# Single-project dashboard (static data now; swap DATA section with API later)

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date

st.set_page_config(page_title="Project Dashboard", layout="wide")

# ===================== THEME & STYLES =====================
st.markdown(
    """
    <style>
      /* page padding */
      .block-container{padding-top:1.5rem;padding-bottom:2rem;}

      /* soft cards */
      .card{border-radius:18px;border:1px solid rgba(0,0,0,0.08);
            padding:14px 16px;background:linear-gradient(180deg,rgba(255,255,255,.85),rgba(255,255,255,.95));
            box-shadow:0 4px 18px rgba(0,0,0,0.06)}
      .metric{font-size:28px;font-weight:700;margin-top:-6px}
      .metric-sub{font-size:12px;color:#6b7280;margin-top:-2px}

      /* section titles */
      h2 span{background: #f3f4f6; padding:6px 12px; border-radius:12px;}
      /* dataframes: tight row height */
      .dataframe tbody tr th, .dataframe tbody tr td{padding:6px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏗️ Project Dashboard")

# ===================== DATA (STATIC) =====================
# You can replace this whole block with API responses later.
PROJECT = "Project Phoenix"
CURRENCY = "EGP"

master = {
    "Project": PROJECT,
    "Client": "Al Qimma Developments",
    "ContractAmount": 5_400_000.0,
    "SubcontractAmount": 1_250_000.0,
    "AdditionalWork": 420_000.0,
    "AdvancePayment": 600_000.0,
    "StartDate": date(2025, 1, 10),
    "EndDate": date(2025, 12, 31),
}

# Months of the year
months = pd.date_range("2025-01-01", "2025-12-01", freq="MS")

# Planned budget (per month)
rng = np.random.RandomState(20)
planned_rev = 380_000 + rng.randint(0, 80_000, len(months))
planned_cost = 250_000 + rng.randint(0, 60_000, len(months))

# Actuals (per month)
rng2 = np.random.RandomState(33)
actual_rev = planned_rev * (0.88 + rng2.rand(len(months))*0.25)       # 88% – 113% of plan
actual_cost = planned_cost * (0.9  + rng2.rand(len(months))*0.3)      # 90% – 120% of plan

budget_df = pd.DataFrame({
    "Month": months,
    "Planned Revenue": planned_rev.astype(float),
    "Planned Cost": planned_cost.astype(float),
    "Actual Revenue": actual_rev.astype(float),
    "Actual Cost": actual_cost.astype(float),
})
budget_df["MonthLabel"] = budget_df["Month"].dt.strftime("%Y-%m")

# Client invoices (subset paid/collected)
client_invoices = pd.DataFrame([
    ["PHX-INV-001","2025-01-20","2025-02-20", 240_000, 160_000, "Mobilization"],
    ["PHX-INV-002","2025-02-25","2025-03-27", 260_000, 260_000, "Progress #1"],
    ["PHX-INV-003","2025-03-25","2025-04-26", 310_000,  90_000, "Progress #2"],
    ["PHX-INV-004","2025-04-28","2025-05-28", 295_000,   0,      "Variation #1"],
    ["PHX-INV-005","2025-05-25","2025-06-25", 320_000, 200_000, "Progress #3"],
], columns=["InvoiceNo","Date","DueDate","Amount","Collected","Notes"])
for c in ["Date","DueDate"]:
    client_invoices[c] = pd.to_datetime(client_invoices[c]).dt.date
client_invoices["Outstanding"] = client_invoices["Amount"] - client_invoices["Collected"]

# Supplier invoices
supplier_invoices = pd.DataFrame([
    ["PHX-SUP-001","Supplier A","2025-01-18","2025-03-04", 160_000, 160_000],
    ["PHX-SUP-002","Supplier B","2025-02-10","2025-03-27", 120_000,  70_000],
    ["PHX-SUP-003","Supplier C","2025-03-05","2025-04-20", 210_000,  80_000],
    ["PHX-SUP-004","Supplier A","2025-04-12","2025-05-27", 140_000,  60_000],
    ["PHX-SUP-005","Supplier D","2025-05-19","2025-07-03", 180_000,   0],
], columns=["InvoiceNo","Supplier","Date","DueDate","Amount","Paid"])
for c in ["Date","DueDate"]:
    supplier_invoices[c] = pd.to_datetime(supplier_invoices[c]).dt.date
supplier_invoices["Outstanding"] = supplier_invoices["Amount"] - supplier_invoices["Paid"]

# Client payments (cheques under collection etc.)
client_payments = pd.DataFrame([
    ["PHX-PAY-001","2025-02-05", 160_000,"cheque","collected"],
    ["PHX-PAY-002","2025-03-10",  90_000,"cheque","under_collection"],
    ["PHX-PAY-003","2025-04-02", 200_000,"transfer","collected"],
    ["PHX-PAY-004","2025-05-15", 110_000,"cheque","under_collection"],
], columns=["PaymentNo","Date","Amount","Method","Status"])
client_payments["Date"] = pd.to_datetime(client_payments["Date"]).dt.date

# Supplier payments (cheques issued)
supplier_payments = pd.DataFrame([
    ["PHX-SPY-001","2025-03-07", 70_000,"cheque","cheque_issued","Supplier B"],
    ["PHX-SPY-002","2025-03-22", 80_000,"cheque","cheque_under_collection","Supplier C"],
    ["PHX-SPY-003","2025-04-29", 60_000,"transfer","paid","Supplier A"],
], columns=["PaymentNo","Date","Amount","Method","Status","Supplier"])
supplier_payments["Date"] = pd.to_datetime(supplier_payments["Date"]).dt.date

# Employees assigned
employees = pd.DataFrame([
    ["Emp 01","Project Manager","2025-01-10","2025-12-31", 38_000, 1.0],
    ["Emp 02","Site Engineer","2025-01-15","2025-12-31", 23_000, 1.0],
    ["Emp 03","Surveyor","2025-01-20","2025-12-31", 18_000, 0.8],
    ["Emp 04","Technician","2025-01-25","2025-12-31", 14_000, 0.7],
    ["Emp 05","Driver","2025-02-01","2025-12-31", 12_000, 0.7],
], columns=["Employee","Role","Start","End","CostRate","AllocationPct"])
for c in ["Start","End"]:
    employees[c] = pd.to_datetime(employees[c]).dt.date
employees["MonthlyCost"] = employees["CostRate"] * employees["AllocationPct"]

# ===================== CALCS =====================
executed_revenue = budget_df["Actual Revenue"].sum()
executed_cost    = budget_df["Actual Cost"].sum()
profit           = executed_revenue - executed_cost
margin_pct       = (profit / executed_revenue * 100) if executed_revenue else 0.0

contract_total   = master["ContractAmount"] + master["AdditionalWork"]
backlog          = max(contract_total - executed_revenue, 0.0)

cheques_under_collection = client_payments.query("Method=='cheque' and Status=='under_collection'")["Amount"].sum()
client_collected         = client_payments.query("Status=='collected'")["Amount"].sum()
supplier_cheques_out     = supplier_payments.query("Status in ['cheque_issued','cheque_under_collection']")["Amount"].sum()
supplier_total_invoices  = supplier_invoices["Amount"].sum()

# ===================== HEADER =====================
st.write(f"**Project:** {PROJECT}  •  **Client:** {master['Client']}")

# KPIs Row 1
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
with r1c1:
    st.markdown('<div class="card"><div>Contract amount</div>'
                f'<div class="metric">{master["ContractAmount"]:,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Additional work: {master["AdditionalWork"]:,.0f}</div></div>', unsafe_allow_html=True)
with r1c2:
    st.markdown('<div class="card"><div>Subcontract amount</div>'
                f'<div class="metric">{master["SubcontractAmount"]:,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Advance: {master["AdvancePayment"]:,.0f}</div></div>', unsafe_allow_html=True)
with r1c3:
    st.markdown('<div class="card"><div>Total executed (Revenue)</div>'
                f'<div class="metric">{executed_revenue:,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Progress vs contract</div></div>', unsafe_allow_html=True)
    st.progress(min(1.0, executed_revenue / max(contract_total, 1)))
with r1c4:
    st.markdown('<div class="card"><div>Margins</div>'
                f'<div class="metric">{profit:,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Margin: {margin_pct:.2f}%</div></div>', unsafe_allow_html=True)

# KPIs Row 2
r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    st.markdown('<div class="card"><div>Client</div>'
                f'<div class="metric">{master["Client"]}</div>'
                f'<div class="metric-sub">Backlog: {backlog:,.0f} {CURRENCY}</div></div>', unsafe_allow_html=True)
with r2c2:
    st.markdown('<div class="card"><div>Start date</div>'
                f'<div class="metric">{master["StartDate"]}</div>'
                f'<div class="metric-sub">End: {master["EndDate"]}</div></div>', unsafe_allow_html=True)
with r2c3:
    st.markdown('<div class="card"><div>Cheques under collection</div>'
                f'<div class="metric">{cheques_under_collection:,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Client collected: {client_collected:,.0f}</div></div>', unsafe_allow_html=True)
with r2c4:
    st.markdown('<div class="card"><div>Suppliers cheques</div>'
                f'<div class="metric">{supplier_cheques_out:,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Total supplier invoices: {supplier_total_invoices:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("## <span>Budgets — Actual vs Planned</span>", unsafe_allow_html=True)

# ===================== CHARTS =====================
def money_fmt(v): return f"{v:,.0f}"

def line_block(df, plan_col, actual_col, title):
    base = alt.Chart(df).encode(x=alt.X('Month:T', title=None))
    line_plan = base.mark_line(strokeDash=[6,4], strokeWidth=2).encode(y=alt.Y(f'{plan_col}:Q', title=None), color=alt.value("#9CA3AF"))
    line_act  = base.mark_line(point=True, strokeWidth=3).encode(y=alt.Y(f'{actual_col}:Q'), color=alt.value("#2563EB"))
    rule = alt.Chart(df).mark_rule(color="#E5E7EB").encode(x='monthdate(Month):T')
    return (line_plan + line_act + rule).properties(height=280, title=title).configure_title(fontSize=14, anchor='start')

col_a, col_b = st.columns(2)
with col_a:
    st.altair_chart(line_block(budget_df, "Planned Revenue", "Actual Revenue", "Revenue"), use_container_width=True)
with col_b:
    st.altair_chart(line_block(budget_df, "Planned Cost", "Actual Cost", "Cost"), use_container_width=True)

# Variance table
summary = pd.DataFrame({
    "Planned Revenue": [budget_df["Planned Revenue"].sum()],
    "Actual Revenue":  [budget_df["Actual Revenue"].sum()],
    "Planned Cost":    [budget_df["Planned Cost"].sum()],
    "Actual Cost":     [budget_df["Actual Cost"].sum()],
})
summary["Revenue Var"] = summary["Actual Revenue"] - summary["Planned Revenue"]
summary["Cost Var"]    = summary["Actual Cost"] - summary["Planned Cost"]
summary["Actual Profit"] = summary["Actual Revenue"] - summary["Actual Cost"]
st.dataframe(summary.style.format(money_fmt), use_container_width=True)

# ===================== INVOICES =====================
st.markdown("## <span>Invoices</span>", unsafe_allow_html=True)
i_left, i_right = st.columns(2)

with i_left:
    st.markdown("#### Client invoices")
    st.dataframe(
        client_invoices.sort_values("Date")
            .style.format({"Amount":money_fmt,"Collected":money_fmt,"Outstanding":money_fmt}),
        use_container_width=True
    )
    ci_tot = client_invoices[["Amount","Collected","Outstanding"]].sum()
    st.markdown(f"**Totals** — Amount: {money_fmt(ci_tot['Amount'])} • Collected: {money_fmt(ci_tot['Collected'])} • Outstanding: {money_fmt(ci_tot['Outstanding'])}")

with i_right:
    st.markdown("#### Suppliers invoices")
    st.dataframe(
        supplier_invoices.sort_values("Date")
            .style.format({"Amount":money_fmt,"Paid":money_fmt,"Outstanding":money_fmt}),
        use_container_width=True
    )
    si_tot = supplier_invoices[["Amount","Paid","Outstanding"]].sum()
    st.markdown(f"**Total** — Amount: {money_fmt(si_tot['Amount'])} • Paid: {money_fmt(si_tot['Paid'])} • Outstanding: {money_fmt(si_tot['Outstanding'])}")

# ===================== DUES & AGING =====================
st.markdown("## <span>Dues & Cheques</span>", unsafe_allow_html=True)
d_left, d_right = st.columns(2)

with d_left:
    st.markdown("#### Clients dues (A/R)")
    ar = client_invoices.groupby("DueDate")[["Outstanding"]].sum().reset_index()
    if not ar.empty:
        chart_ar = alt.Chart(ar).mark_bar().encode(
            x=alt.X('yearmonth(DueDate):T', title=None),
            y=alt.Y('Outstanding:Q', title='Outstanding'),
            tooltip=['yearmonth(DueDate):T','Outstanding:Q']
        ).properties(height=240)
        st.altair_chart(chart_ar, use_container_width=True)
    else:
        st.info("No A/R.")

with d_right:
    st.markdown("#### Suppliers cheques & A/P")
    ap = supplier_invoices.groupby("DueDate")[["Outstanding"]].sum().reset_index()
    if not ap.empty:
        chart_ap = alt.Chart(ap).mark_bar(color="#F59E0B").encode(
            x=alt.X('yearmonth(DueDate):T', title=None),
            y=alt.Y('Outstanding:Q', title='Outstanding'),
            tooltip=['yearmonth(DueDate):T','Outstanding:Q']
        ).properties(height=240)
        st.altair_chart(chart_ap, use_container_width=True)
    else:
        st.info("No A/P.")

# ===================== EMPLOYEES =====================
st.markdown("## <span>Employees assigned</span>", unsafe_allow_html=True)
e_left, e_right = st.columns([2,1])

with e_left:
    st.dataframe(
        employees[["Employee","Role","Start","End","AllocationPct","CostRate","MonthlyCost"]]
        .style.format({"AllocationPct":"{:.0%}","CostRate":money_fmt,"MonthlyCost":money_fmt}),
        use_container_width=True
    )

with e_right:
    headcount_by_role = employees.groupby("Role")["Employee"].count().reset_index(name="Headcount")
    bar = alt.Chart(headcount_by_role).mark_bar().encode(
        x=alt.X("Headcount:Q"),
        y=alt.Y("Role:N", sort='-x'),
        tooltip=["Role","Headcount"]
    ).properties(height=260, title="Headcount by role")
    st.altair_chart(bar, use_container_width=True)
    st.markdown('<div class="card">'
                f'<div>Total monthly personnel cost</div>'
                f'<div class="metric">{employees["MonthlyCost"].sum():,.0f} {CURRENCY}</div>'
                f'<div class="metric-sub">Allocated across roles</div>'
                '</div>', unsafe_allow_html=True)

st.caption("This page uses static demo data. Replace the DATA block at the top with your API results when ready.")
