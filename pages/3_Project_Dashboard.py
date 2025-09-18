# pages/3_Project_Dashboard.py
# Single-project dashboard (static demo data) — tailored per latest spec

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
      .block-container{padding-top:1.4rem;padding-bottom:2rem;}
      .card{border-radius:18px;border:1px solid rgba(0,0,0,0.08);
            padding:14px 16px;background:linear-gradient(180deg,rgba(255,255,255,.85),rgba(255,255,255,.95));
            box-shadow:0 4px 18px rgba(0,0,0,0.06)}
      .metric{font-size:28px;font-weight:700;margin-top:-6px}
      .metric-sub{font-size:12px;color:#6b7280;margin-top:-2px}
      .pill{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:600;font-size:12px}
      .pill.ok{background:#e8fff1;color:#0f7a3b;border:1px solid #baf0d0}
      .pill.bad{background:#ffefef;color:#b91c1c;border:1px solid #f5c2c2}
      .pill.warn{background:#eef6ff;color:#1d4ed8;border:1px solid #c7ddff}
      h2 span{background:#f3f4f6;padding:6px 12px;border-radius:12px;}
      .dataframe tbody tr th, .dataframe tbody tr td{padding:6px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===================== STATIC DATA =====================
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

# Planned budget (per month) — totals
rng = np.random.RandomState(20)
planned_rev = 380_000 + rng.randint(0, 80_000, len(months))
planned_cost = 250_000 + rng.randint(0, 60_000, len(months))

# Actuals (per month) — totals
rng2 = np.random.RandomState(33)
actual_rev = planned_rev * (0.88 + rng2.rand(len(months))*0.25)       # 88%–113% of plan
actual_cost = planned_cost * (0.90 + rng2.rand(len(months))*0.30)     # 90%–120% of plan

budget_df = pd.DataFrame({
    "Month": months,
    "Revenue": actual_rev.astype(float),
    "Cost": actual_cost.astype(float),
    "Plan_Rev": planned_rev.astype(float),
    "Plan_Cost": planned_cost.astype(float),
})
budget_df["MonthLabel"] = budget_df["Month"].dt.strftime("%Y-%m")

# Budget ITEMS (for out-of-budget detection)
budget_items = pd.DataFrame([
    # Item, Planned, Actual, Type (cost/rev) — mostly cost items
    ["Fuel",            520_000, 610_000, "Cost"],
    ["Rentals",         480_000, 520_000, "Cost"],
    ["Materials",       900_000, 1_020_000, "Cost"],
    ["Subcontractors",  950_000, 1_050_000, "Cost"],
    ["Salaries",        780_000, 760_000, "Cost"],
    ["Equipment",       300_000, 280_000, "Cost"],
    ["Marketing",       120_000, 125_000, "Cost"],
    ["Variation Revenue", 350_000, 320_000, "Revenue"],
], columns=["Item","Planned","Actual","Type"])

# Client & Supplier invoices (kept for display lists)
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

# Client & Supplier payments (for cashflow)
client_payments = pd.DataFrame([
    ["PHX-PAY-001","2025-02-05", 160_000,"cheque","collected"],
    ["PHX-PAY-002","2025-03-10",  90_000,"cheque","under_collection"],
    ["PHX-PAY-003","2025-04-02", 200_000,"transfer","collected"],
    ["PHX-PAY-004","2025-05-15", 110_000,"cheque","under_collection"],
], columns=["PaymentNo","Date","Amount","Method","Status"])
client_payments["Date"] = pd.to_datetime(client_payments["Date"]).dt.date

supplier_payments = pd.DataFrame([
    ["PHX-SPY-001","2025-03-07", 70_000,"cheque","cheque_issued","Supplier B"],
    ["PHX-SPY-002","2025-03-22", 80_000,"cheque","cheque_under_collection","Supplier C"],
    ["PHX-SPY-003","2025-04-29", 60_000,"transfer","paid","Supplier A"],
], columns=["PaymentNo","Date","Amount","Method","Status","Supplier"])
supplier_payments["Date"] = pd.to_datetime(supplier_payments["Date"]).dt.date

# Dues by item (static totals per your request)
client_dues_items = pd.DataFrame([
    ["Retention",        450_000],
    ["Advance to Adjust",300_000],
    ["Insurance",        120_000],
    ["Other Deductions",  60_000],
], columns=["Item","Amount"])

supplier_dues_items = pd.DataFrame([
    ["Advance Payments", 150_000],
    ["Insurance",         80_000],
    ["Performance Bonds", 40_000],
    ["Penalties",         30_000],
], columns=["Item","Amount"])

# Employees (kept for section)
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
def money(v): return f"{v:,.0f}"

executed_revenue = budget_df["Revenue"].sum()
executed_cost    = budget_df["Cost"].sum()
profit           = executed_revenue - executed_cost
margin_pct       = (profit / executed_revenue * 100) if executed_revenue else 0.0

contract_total   = master["ContractAmount"] + master["AdditionalWork"]
backlog          = max(contract_total - executed_revenue, 0.0)

# Cashflow series (only cash that actually moved)
def month_start(d): return pd.to_datetime(d).to_period("M").to_timestamp("MS")
cashin = (client_payments[client_payments["Status"]=="collected"]
          .assign(Month=lambda d: d["Date"].apply(month_start))
          .groupby("Month")["Amount"].sum())
cashout = (supplier_payments[supplier_payments["Status"]=="paid"]
           .assign(Month=lambda d: d["Date"].apply(month_start))
           .groupby("Month")["Amount"].sum())
cash = pd.DataFrame(index=months)
cash["Cash In"] = cashin
cash["Cash Out"] = cashout
cash = cash.fillna(0.0)
cash["Net Cash"] = cash["Cash In"] - cash["Cash Out"]

# ===================== HEADER =====================
st.title("🏗️ Project Dashboard")
st.write(f"**Project:** {PROJECT}  •  **Client:** {master['Client']}")

# KPIs Row 1
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
with r1c1:
    st.markdown('<div class="card"><div>Contract amount</div>'
                f'<div class="metric">{money(master["ContractAmount"])} {CURRENCY}</div>'
                f'<div class="metric-sub">Additional work: {money(master["AdditionalWork"])}</div></div>', unsafe_allow_html=True)
with r1c2:
    st.markdown('<div class="card"><div>Subcontract amount</div>'
                f'<div class="metric">{money(master["SubcontractAmount"])} {CURRENCY}</div>'
                f'<div class="metric-sub">Advance: {money(master["AdvancePayment"])}</div></div>', unsafe_allow_html=True)
with r1c3:
    st.markdown('<div class="card"><div>Total executed (Revenue)</div>'
                f'<div class="metric">{money(executed_revenue)} {CURRENCY}</div>'
                f'<div class="metric-sub">Progress vs contract</div></div>', unsafe_allow_html=True)
    st.progress(min(1.0, executed_revenue / max(contract_total, 1)))
with r1c4:
    st.markdown('<div class="card"><div>Margins</div>'
                f'<div class="metric">{money(profit)} {CURRENCY}</div>'
                f'<div class="metric-sub">Margin: {margin_pct:.2f}%</div></div>', unsafe_allow_html=True)

# KPIs Row 2 (cheques/dues quick view)
cheques_under_collection = client_payments.query("Method=='cheque' and Status=='under_collection'")["Amount"].sum()
client_collected         = client_payments.query("Status=='collected'")["Amount"].sum()
supplier_cheques_out     = supplier_payments.query("Status in ['cheque_issued','cheque_under_collection']")["Amount"].sum()
supplier_total_invoices  = supplier_invoices["Amount"].sum()

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    st.markdown('<div class="card"><div>Start date</div>'
                f'<div class="metric">{master["StartDate"]}</div>'
                f'<div class="metric-sub">End: {master["EndDate"]}</div></div>', unsafe_allow_html=True)
with r2c2:
    st.markdown('<div class="card"><div>Backlog (remaining contract)</div>'
                f'<div class="metric">{money(backlog)} {CURRENCY}</div>'
                f'<div class="metric-sub">Contract+Add. − Executed Revenue</div></div>', unsafe_allow_html=True)
with r2c3:
    st.markdown('<div class="card"><div>Cheques under collection</div>'
                f'<div class="metric">{money(cheques_under_collection)} {CURRENCY}</div>'
                f'<div class="metric-sub">Client collected: {money(client_collected)}</div></div>', unsafe_allow_html=True)
with r2c4:
    st.markdown('<div class="card"><div>Suppliers cheques</div>'
                f'<div class="metric">{money(supplier_cheques_out)} {CURRENCY}</div>'
                f'<div class="metric-sub">Total supplier invoices: {money(supplier_total_invoices)}</div></div>', unsafe_allow_html=True)

# ===================== NEW CHARTS =====================
st.markdown("## <span>Cashflow & Revenue/Cost</span>", unsafe_allow_html=True)
c_left, c_right = st.columns(2)

# Cashflow chart (Cash In, Cash Out, Net)
with c_left:
    base = alt.Chart(cash.reset_index().rename(columns={"index":"Month"})).encode(x=alt.X('Month:T', title=None))
    line_in  = base.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Cash In:Q', title=None), color=alt.value("#16a34a"))
    line_out = base.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Cash Out:Q'), color=alt.value("#dc2626"))
    line_net = base.mark_line(strokeDash=[6,4], strokeWidth=2).encode(y=alt.Y('Net Cash:Q'), color=alt.value("#64748b"))
    rule = alt.Chart(cash.reset_index()).mark_rule(color="#e5e7eb").encode(x='monthdate(index):T')
    st.altair_chart((line_in + line_out + line_net + rule).properties(height=300, title="Cashflow (In / Out / Net)"),
                    use_container_width=True)

# Revenue vs Cost chart
with c_right:
    rc = budget_df[["Month","Revenue","Cost"]].copy()
    base2 = alt.Chart(rc).encode(x=alt.X('Month:T', title=None))
    rev = base2.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Revenue:Q', title=None), color=alt.value("#2563EB"))
    cost = base2.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Cost:Q'), color=alt.value("#F59E0B"))
    rule2 = alt.Chart(rc).mark_rule(color="#e5e7eb").encode(x='monthdate(Month):T')
    st.altair_chart((rev + cost + rule2).properties(height=300, title="Revenue vs Cost (Actual)"),
                    use_container_width=True)

# ===================== BUDGET STATUS =====================
st.markdown("## <span>Budget Status</span>", unsafe_allow_html=True)

planned_total = float(budget_df["Plan_Cost"].sum())
actual_total  = float(budget_df["Cost"].sum())
variance      = actual_total - planned_total
variance_pct  = (variance / planned_total * 100.0) if planned_total else 0.0

# Tag logic
THRESH = 3.0  # % band for "In-Budget"
if actual_total > planned_total * (1 + THRESH/100):
    tag_html = f'<span class="pill bad">Above-Budget (+{variance_pct:.1f}%)</span>'
elif actual_total < planned_total * (1 - THRESH/100):
    tag_html = f'<span class="pill warn">Under-Budget ({variance_pct:.1f}%)</span>'
else:
    tag_html = f'<span class="pill ok">In-Budget ({variance_pct:.1f}%)</span>'

b1, b2, b3 = st.columns(3)
with b1:
    st.markdown('<div class="card"><div>Planned Cost (Total)</div>'
                f'<div class="metric">{money(planned_total)} {CURRENCY}</div></div>', unsafe_allow_html=True)
with b2:
    st.markdown('<div class="card"><div>Actual Cost (Total)</div>'
                f'<div class="metric">{money(actual_total)} {CURRENCY}</div></div>', unsafe_allow_html=True)
with b3:
    st.markdown(f'<div class="card"><div>Status</div><div class="metric">{money(variance)} {CURRENCY}</div>'
                f'<div class="metric-sub">Variance</div><div style="margin-top:6px;">{tag_html}</div></div>', unsafe_allow_html=True)

# Out-of-budget items table (only rows where Actual > Planned)
bi = budget_items.copy()
bi["Variance"] = bi["Actual"] - bi["Planned"]
bi["Variance %"] = np.where(bi["Planned"]>0, bi["Variance"]/bi["Planned"]*100, 0.0)
out_of_budget = bi[(bi["Type"].str.lower()=="cost") & (bi["Actual"] > bi["Planned"])].sort_values("Variance", ascending=False)

st.markdown("#### Items Out of Budget")
if out_of_budget.empty:
    st.success("All cost items are within budget.")
else:
    st.dataframe(
        out_of_budget[["Item","Planned","Actual","Variance","Variance %"]]
            .style.format({"Planned":money,"Actual":money,"Variance":money,"Variance %":"{:.1f}%"}),
        use_container_width=True
    )

# ===================== INVOICES (kept from previous) =====================
st.markdown("## <span>Invoices</span>", unsafe_allow_html=True)
i_left, i_right = st.columns(2)

with i_left:
    st.markdown("#### Client invoices")
    st.dataframe(
        client_invoices.sort_values("Date")
            .style.format({"Amount":money,"Collected":money,"Outstanding":money}),
        use_container_width=True
    )
    ci_tot = client_invoices[["Amount","Collected","Outstanding"]].sum()
    st.markdown(f"**Totals** — Amount: {money(ci_tot['Amount'])} • Collected: {money(ci_tot['Collected'])} • Outstanding: {money(ci_tot['Outstanding'])}")

with i_right:
    st.markdown("#### Suppliers invoices")
    st.dataframe(
        supplier_invoices.sort_values("Date")
            .style.format({"Amount":money,"Paid":money,"Outstanding":money}),
        use_container_width=True
    )
    si_tot = supplier_invoices[["Amount","Paid","Outstanding"]].sum()
    st.markdown(f"**Total** — Amount: {money(si_tot['Amount'])} • Paid: {money(si_tot['Paid'])} • Outstanding: {money(si_tot['Outstanding'])}")

# ===================== DUES TOTALS (by item) =====================
st.markdown("## <span>Dues — Totals by Item</span>", unsafe_allow_html=True)
d_left, d_right = st.columns(2)

with d_left:
    st.markdown("#### Clients dues (totals)")
    st.dataframe(
        client_dues_items.style.format({"Amount":money}),
        use_container_width=True
    )
    st.markdown(f"**Total Clients Dues:** {money(client_dues_items['Amount'].sum())} {CURRENCY}")

with d_right:
    st.markdown("#### Suppliers dues (totals)")
    st.dataframe(
        supplier_dues_items.style.format({"Amount":money}),
        use_container_width=True
    )
    st.markdown(f"**Total Suppliers Dues:** {money(supplier_dues_items['Amount'].sum())} {CURRENCY}")

# ===================== EMPLOYEES =====================
st.markdown("## <span>Employees assigned</span>", unsafe_allow_html=True)
e_left, e_right = st.columns([2,1])

with e_left:
    st.dataframe(
        employees[["Employee","Role","Start","End","AllocationPct","CostRate","MonthlyCost"]]
        .style.format({"AllocationPct":"{:.0%}","CostRate":money,"MonthlyCost":money}),
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
                f'<div class="metric">{money(employees["MonthlyCost"].sum())} {CURRENCY}</div>'
                f'<div class="metric-sub">Allocated across roles</div>'
                '</div>', unsafe_allow_html=True)

st.caption("Static demo data shown. When ready, replace the DATA block with your API calls and keep the same column names to reuse the visuals.")
