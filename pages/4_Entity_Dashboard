# pages/4_Entity_Dashboard.py
# ENTITY Dashboard (static demo data; safe fallbacks for charts)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

# Try Altair, but fall back to Streamlit charts if unavailable
ALT_OK = True
try:
    import altair as alt
except Exception:
    ALT_OK = False

st.set_page_config(page_title="Entity Dashboard", layout="wide")
st.write("👤 **Entity Dashboard**")  # early render so the page never looks blank

# ---------- Styles ----------
st.markdown(
    """
    <style>
      .block-container{padding-top:1.2rem;padding-bottom:2rem;}
      .card{border-radius:18px;border:1px solid rgba(0,0,0,0.08);
            padding:14px 16px;background:linear-gradient(180deg,rgba(255,255,255,.9),rgba(255,255,255,.98));
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

# ---------- Static DATA (swap this block with API calls later) ----------
ENTITY = {
    "Name": "Atlas Engineering LLC",
    "Type": ["Client", "Supplier"],
    "Status": "Active",
    "Owner": "Sales Team A",
    "Email": "ops@atlas-eg.com",
    "Phone": "+20 10 1234 5678",
    "Address": "New Cairo, Cairo, Egypt",
    "CreditLimit": 2_500_000.0,
    "PaymentTermsDays": 45,
    "RiskScore": 0.28,  # 0 low -> 1 high
    "Currency": "EGP",
}
CURRENCY = ENTITY["Currency"]

months = pd.date_range("2025-01-01", "2025-12-01", freq="MS")

client_invoices = pd.DataFrame([
    ["AT-INV-001","2025-01-20","2025-02-20", 240_000, "Mobilization"],
    ["AT-INV-002","2025-02-25","2025-03-27", 260_000, "Progress #1"],
    ["AT-INV-003","2025-03-25","2025-04-26", 310_000, "Progress #2"],
    ["AT-INV-004","2025-04-28","2025-05-28", 295_000, "Variation #1"],
    ["AT-INV-005","2025-05-25","2025-06-25", 320_000, "Progress #3"],
    ["AT-INV-006","2025-06-25","2025-07-25", 330_000, "Progress #4"],
], columns=["InvoiceNo","Date","DueDate","Amount","Notes"])
for c in ["Date","DueDate"]:
    client_invoices[c] = pd.to_datetime(client_invoices[c]).dt.date

supplier_invoices = pd.DataFrame([
    ["AT-SUP-001","Supplier A","2025-01-18","2025-03-04", 160_000],
    ["AT-SUP-002","Supplier B","2025-02-10","2025-03-27", 120_000],
    ["AT-SUP-003","Supplier C","2025-03-05","2025-04-20", 210_000],
    ["AT-SUP-004","Supplier A","2025-04-12","2025-05-27", 140_000],
    ["AT-SUP-005","Supplier D","2025-05-19","2025-07-03", 180_000],
    ["AT-SUP-006","Supplier B","2025-06-14","2025-07-29", 150_000],
], columns=["InvoiceNo","Supplier","Date","DueDate","Amount"])
for c in ["Date","DueDate"]:
    supplier_invoices[c] = pd.to_datetime(supplier_invoices[c]).dt.date

client_payments = pd.DataFrame([
    ["AT-PAY-001","2025-02-05", 160_000,"cheque","collected"],
    ["AT-PAY-002","2025-03-10",  90_000,"cheque","under_collection"],
    ["AT-PAY-003","2025-03-15",  60_000,"cheque","in_treasury"],
    ["AT-PAY-004","2025-04-02", 200_000,"transfer","collected"],
    ["AT-PAY-005","2025-05-15", 110_000,"cheque","under_collection"],
], columns=["PaymentNo","Date","Amount","Method","Status"])
client_payments["Date"] = pd.to_datetime(client_payments["Date"]).dt.date

supplier_payments = pd.DataFrame([
    ["AT-SPY-001","2025-03-07", 70_000,"cheque","cheque_issued","Supplier B"],
    ["AT-SPY-002","2025-03-22", 80_000,"cheque","cheque_under_collection","Supplier C"],
    ["AT-SPY-003","2025-04-29", 60_000,"transfer","paid","Supplier A"],
    ["AT-SPY-004","2025-06-10", 75_000,"transfer","paid","Supplier B"],
], columns=["PaymentNo","Date","Amount","Method","Status","Counterparty"])
supplier_payments["Date"] = pd.to_datetime(supplier_payments["Date"]).dt.date

client_dues_items = pd.DataFrame([
    ["Retention",        420_000],
    ["Advance to Adjust",280_000],
    ["Insurance",        110_000],
    ["Other Deductions",  60_000],
], columns=["Item","Amount"])
supplier_dues_items = pd.DataFrame([
    ["Advance Payments", 130_000],
    ["Insurance",         75_000],
    ["Performance Bonds", 40_000],
    ["Penalties",         25_000],
], columns=["Item","Amount"])

# ---------- Helpers / calcs ----------
def money(v): return f"{v:,.0f}"
def month_start(d):
    ts = pd.to_datetime(d)
    return pd.Timestamp(ts.year, ts.month, 1)

# Revenue/Cost by month (from invoices)
rev_m = (client_invoices.assign(Month=lambda d: d["Date"].apply(month_start))
                     .groupby("Month")["Amount"].sum())
cost_m = (supplier_invoices.assign(Month=lambda d: d["Date"].apply(month_start))
                      .groupby("Month")["Amount"].sum())
rc = pd.DataFrame(index=months).assign(Revenue=rev_m, Cost=cost_m).fillna(0.0)

# Cashflow by month (actual receipts/payments only)
cash_in  = (client_payments[client_payments["Status"]=="collected"]
            .assign(Month=lambda d: d["Date"].apply(month_start))
            .groupby("Month")["Amount"].sum())
cash_out = (supplier_payments[supplier_payments["Status"]=="paid"]
            .assign(Month=lambda d: d["Date"].apply(month_start))
            .groupby("Month")["Amount"].sum())
cf = pd.DataFrame(index=months).assign(**{"Cash In": cash_in, "Cash Out": cash_out}).fillna(0.0)
cf["Net Cash"] = cf["Cash In"] - cf["Cash Out"]

# Outstanding allocations (simple FIFO)
client_invoices["Collected"] = 0.0
for _, p in client_payments.iterrows():
    remain = p["Amount"] if p["Status"] in ("collected","under_collection","in_treasury") else 0.0
    for i in client_invoices.sort_values("DueDate").index:
        due = client_invoices.loc[i, "Amount"] - client_invoices.loc[i, "Collected"]
        if due <= 0: continue
        take = min(remain, due); client_invoices.loc[i, "Collected"] += take; remain -= take
        if remain <= 0: break
client_invoices["Outstanding"] = client_invoices["Amount"] - client_invoices["Collected"]

supplier_invoices["Paid"] = 0.0
for _, p in supplier_payments.iterrows():
    if p["Status"] not in ("paid","cheque_under_collection","cheque_issued"): continue
    remain = p["Amount"]
    for i in supplier_invoices.sort_values("DueDate").index:
        due = supplier_invoices.loc[i, "Amount"] - supplier_invoices.loc[i, "Paid"]
        if due <= 0: continue
        take = min(remain, due); supplier_invoices.loc[i, "Paid"] += take; remain -= take
        if remain <= 0: break
supplier_invoices["Outstanding"] = supplier_invoices["Amount"] - supplier_invoices["Paid"]

AR = float(client_invoices["Outstanding"].sum())
AP = float(supplier_invoices["Outstanding"].sum())
Cheques_UC = float(client_payments.query("Status=='under_collection'")["Amount"].sum())
Cheques_Treasury = float(client_payments.query("Status=='in_treasury'")["Amount"].sum())

accounts = pd.DataFrame([
    ["Accounts Receivable", AR],
    ["Accounts Payable", -AP],
    ["Client Advances", float(client_dues_items.loc[client_dues_items["Item"]=="Advance to Adjust","Amount"].sum())],
    ["Supplier Advances", -float(supplier_dues_items.loc[supplier_dues_items["Item"]=="Advance Payments","Amount"].sum())],
    ["Retention (Client)", float(client_dues_items.loc[client_dues_items["Item"]=="Retention","Amount"].sum())],
    ["Retention (Supplier)", -float(supplier_dues_items.loc[supplier_dues_items["Item"]=="Performance Bonds","Amount"].sum())],
    ["Cheques Under Collection", Cheques_UC],
    ["Cheques in Treasury", Cheques_Treasury],
], columns=["Account Group","Balance"])
net_exposure = float(accounts["Balance"].sum())

avg_month_rev = max(rc["Revenue"].mean(), 1.0)
avg_month_cost = max(rc["Cost"].mean(), 1.0)
DSO = (AR / avg_month_rev) * 30.0 if avg_month_rev else 0.0
DPO = (AP / avg_month_cost) * 30.0 if avg_month_cost else 0.0
credit_util = (max(AR + Cheques_UC + Cheques_Treasury, 0.0) / ENTITY["CreditLimit"]) if ENTITY["CreditLimit"] else 0.0

# ---------- Header/Profile ----------
st.subheader(f"{ENTITY['Name']}  ·  {', '.join(ENTITY['Type'])}")
st.write(f"📍 {ENTITY['Address']}  ·  ✉️ {ENTITY['Email']}  ·  ☎️ {ENTITY['Phone']}  ·  Owner: {ENTITY['Owner']}")

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="card"><div>AR Outstanding</div><div class="metric">{money(AR)} {CURRENCY}</div>'
                f'<div class="metric-sub">DSO ≈ {DSO:.0f} days</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="card"><div>AP Outstanding</div><div class="metric">{money(AP)} {CURRENCY}</div>'
                f'<div class="metric-sub">DPO ≈ {DPO:.0f} days</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="card"><div>Net Exposure</div><div class="metric">{money(net_exposure)} {CURRENCY}</div>'
                f'<div class="metric-sub">AR + Advances + Cheques − AP</div></div>', unsafe_allow_html=True)
with k4:
    pill = ('<span class="pill bad">High Risk</span>' if ENTITY["RiskScore"]>=0.66
            else '<span class="pill warn">Medium Risk</span>' if ENTITY["RiskScore"]>=0.33
            else '<span class="pill ok">Low Risk</span>')
    st.markdown(f'<div class="card"><div>Credit Utilization</div><div class="metric">{credit_util*100:,.0f}%</div>'
                f'<div class="metric-sub">{pill}</div></div>', unsafe_allow_html=True)

# ---------- Charts (Altair or fallback) ----------
st.markdown("## Revenue/Cost & Cashflow")

c1, c2 = st.columns(2)

with c1:
    if ALT_OK:
        base = alt.Chart(rc.reset_index().rename(columns={"index":"Month"})).encode(x=alt.X('Month:T', title=None))
        rev_line  = base.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Revenue:Q', title=None), color=alt.value("#2563EB"))
        cost_line = base.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Cost:Q'), color=alt.value("#F59E0B"))
        rule = alt.Chart(rc.reset_index()).mark_rule(color="#e5e7eb").encode(x='monthdate(index):T')
        st.altair_chart((rev_line + cost_line + rule).properties(height=300, title="Revenue vs Cost (Monthly)"),
                        use_container_width=True)
    else:
        st.line_chart(rc[["Revenue","Cost"]])

with c2:
    if ALT_OK:
        base2 = alt.Chart(cf.reset_index().rename(columns={"index":"Month"})).encode(x=alt.X('Month:T', title=None))
        line_in  = base2.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Cash In:Q', title=None), color=alt.value("#16a34a"))
        line_out = base2.mark_line(point=True, strokeWidth=3).encode(y=alt.Y('Cash Out:Q'), color=alt.value("#dc2626"))
        line_net = base2.mark_line(strokeDash=[6,4], strokeWidth=2).encode(y=alt.Y('Net Cash:Q'), color=alt.value("#64748b"))
        rule2 = alt.Chart(cf.reset_index()).mark_rule(color="#e5e7eb").encode(x='monthdate(index):T')
        st.altair_chart((line_in + line_out + line_net + rule2).properties(height=300, title="Cashflow (In / Out / Net)"),
                        use_container_width=True)
    else:
        st.line_chart(cf[["Cash In","Cash Out","Net Cash"]])

# ---------- Account groups summary ----------
st.markdown("## Account Groups — Summary")
st.dataframe(accounts.style.format({"Balance":"{:,.0f}"}), use_container_width=True)

# ---------- Cheques & payments ----------
st.markdown("## Cheques & Payments")
top_left, top_right = st.columns([2,1])

with top_left:
    st.markdown("#### Cheques under collection")
    cuc = client_payments.query("Method=='cheque' and Status=='under_collection'").copy()
    if cuc.empty:
        st.info("No cheques under collection.")
    else:
        st.dataframe(cuc[["PaymentNo","Date","Amount","Status"]].style.format({"Amount":"{:,.0f}"}), use_container_width=True)
        if ALT_OK:
            chart = alt.Chart(cuc).mark_bar().encode(
                x=alt.X("yearmonth(Date):T", title=None),
                y=alt.Y("sum(Amount):Q", title="Amount"),
                tooltip=["yearmonth(Date):T","sum(Amount):Q"]
            ).properties(height=220)
            st.altair_chart(chart, use_container_width=True)
        else:
            agg = cuc.groupby(pd.to_datetime(cuc["Date"]).astype("datetime64[M]"))["Amount"].sum()
            st.bar_chart(agg)

with top_right:
    st.markdown("#### Cheques in treasury")
    cit = client_payments.query("Method=='cheque' and Status=='in_treasury'")
    if cit.empty:
        st.info("No cheques in treasury.")
    else:
        st.dataframe(cit[["PaymentNo","Date","Amount"]].style.format({"Amount":"{:,.0f}"}), use_container_width=True)
        st.markdown(f"**Total:** {money(cit['Amount'].sum())} {CURRENCY}")

mid_left, mid_mid, mid_right = st.columns(3)
with mid_left:
    st.markdown("#### Payment receipts (all)")
    st.dataframe(client_payments[["PaymentNo","Date","Amount","Method","Status"]]
                 .sort_values("Date")
                 .style.format({"Amount":"{:,.0f}"}), use_container_width=True)
with mid_mid:
    st.markdown("#### Cheque handover (to suppliers)")
    handover = supplier_payments.query("Method=='cheque'")
    st.dataframe(handover[["PaymentNo","Date","Amount","Status","Counterparty"]]
                 .sort_values("Date")
                 .style.format({"Amount":"{:,.0f}"}), use_container_width=True)
with mid_right:
    st.markdown('<div class="card">'
                f'<div>Cheques UC</div><div class="metric">{money(Cheques_UC)} {CURRENCY}</div>'
                f'<div class="metric-sub">in treasury: {money(Cheques_Treasury)}</div></div>', unsafe_allow_html=True)

# ---------- Invoices ----------
st.markdown("## Invoices")
i_left, i_right = st.columns(2)
with i_left:
    st.markdown("#### Invoices to Entity (Clients)")
    st.dataframe(
        client_invoices.assign(Collected=lambda d: d["Amount"] - d["Outstanding"])
                       .style.format({"Amount":"{:,.0f}","Collected":"{:,.0f}","Outstanding":"{:,.0f}"}),
        use_container_width=True
    )
    ci_tot = client_invoices[["Amount","Outstanding"]].sum()
    st.markdown(f"**Totals** — Amount: {money(ci_tot['Amount'])} • Outstanding: {money(ci_tot['Outstanding'])}")

with i_right:
    st.markdown("#### Invoices from Entity (Suppliers)")
    st.dataframe(
        supplier_invoices.assign(Paid=lambda d: d["Amount"] - d["Outstanding"])
                         .style.format({"Amount":"{:,.0f}","Paid":"{:,.0f}","Outstanding":"{:,.0f}"}),
        use_container_width=True
    )
    si_tot = supplier_invoices[["Amount","Outstanding"]].sum()
    st.markdown(f"**Totals** — Amount: {money(si_tot['Amount'])} • Outstanding: {money(si_tot['Outstanding'])}")

# ---------- Dues totals ----------
st.markdown("## Dues — Totals by Item")
d_left, d_right = st.columns(2)
with d_left:
    st.markdown("#### Client-side dues")
    st.dataframe(client_dues_items.style.format({"Amount":"{:,.0f}"}), use_container_width=True)
    st.markdown(f"**Total Clients Dues:** {money(client_dues_items['Amount'].sum())} {CURRENCY}")
with d_right:
    st.markdown("#### Supplier-side dues")
    st.dataframe(supplier_dues_items.style.format({"Amount":"{:,.0f}"}), use_container_width=True)
    st.markdown(f"**Total Suppliers Dues:** {money(supplier_dues_items['Amount'].sum())} {CURRENCY}")

st.caption("Static demo data. Replace the DATA block with your ERP API calls and keep the column names to reuse these visuals.")
