import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Project Dashboard", layout="wide")
st.title("🧱 Project Dashboard")

# ======================================================================================
# Helpers
# ======================================================================================
@st.cache_data
def _month_start(d): return pd.to_datetime(d).replace(day=1)

def _read_any(upload):
    if upload is None: return None
    return pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)

def _stdcol(df, name):
    """Return actual column name by case-insensitive match (or None)."""
    if df is None: return None
    names = {c.lower(): c for c in df.columns}
    return names.get(name.lower())

def _rename(df, mapping):
    out = df.copy()
    for want, have in mapping.items():
        if have and have in out.columns and want != have:
            out = out.rename(columns={have: want})
    return out

def _safe_num(s): return pd.to_numeric(s, errors="coerce").fillna(0.0)

# ======================================================================================
# Sample demo data (runs instantly if you don't upload)
# ======================================================================================
@st.cache_data
def sample_master_projects():
    rows = [
        {"Project":"Project A","Client":"Big Client Co","ContractAmount":5_000_000,"SubcontractAmount":1_300_000,
         "AdditionalWork":350_000,"StartDate":"2025-01-05","EndDate":"2025-12-31","AdvancePayment":600_000,"Currency":"EGP"},
        {"Project":"Project B","Client":"Infra Ltd","ContractAmount":3_800_000,"SubcontractAmount":900_000,
         "AdditionalWork":120_000,"StartDate":"2025-02-01","EndDate":"2025-10-31","AdvancePayment":300_000,"Currency":"EGP"},
    ]
    df = pd.DataFrame(rows)
    df["StartDate"] = pd.to_datetime(df["StartDate"]).dt.date
    df["EndDate"] = pd.to_datetime(df["EndDate"]).dt.date
    return df

@st.cache_data
def sample_budgets():
    # Long format: Project, Version, Month, Type (Revenue/Cost), Item, Planned
    rng = pd.date_range("2025-01-01","2025-12-01",freq="MS")
    rows=[]
    for p in ["Project A","Project B"]:
        for v in ["V1","V2"]:
            for m in rng:
                # planned revenue & cost
                rev = 380_000 + (abs(hash((p,v,"rev",m.month)))%80_000)
                cost = 250_000 + (abs(hash((p,v,"cost",m.month)))%60_000)
                rows.append({"Project":p,"Version":v,"Month":m,"Type":"Revenue","Item":"Revenue","Planned":float(rev)})
                rows.append({"Project":p,"Version":v,"Month":m,"Type":"Cost","Item":"Cost","Planned":float(cost)})
    return pd.DataFrame(rows)

@st.cache_data
def sample_actuals():
    # Date, Project, Type (Revenue/Expense), Category, Amount
    rng = pd.date_range("2025-01-01","2025-12-25",freq="7D")
    rows=[]
    cats_rev = ["Progress Bill","Variation"]
    cats_exp = ["Fuel","Rentals","Salaries","Materials","Subcontractors","Marketing","Misc"]
    rs = np.random.RandomState(7)
    for p in ["Project A","Project B"]:
        for d in rng:
            if rs.rand()<0.6:
                rows.append({"Date":d,"Project":p,"Type":"Revenue","Category":rs.choice(cats_rev),"Amount":float(rs.randint(80_000,180_000))})
            if rs.rand()<0.9:
                rows.append({"Date":d+pd.Timedelta(days=rs.randint(0,6)),"Project":p,"Type":"Expense","Category":rs.choice(cats_exp),"Amount":-float(rs.randint(30_000,120_000))})
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df

@st.cache_data
def sample_client_invoices():
    rows=[]; rs=np.random.RandomState(11)
    for p in ["Project A","Project B"]:
        for i in range(1,10):
            d = pd.to_datetime(f"2025-{(i%12)+1:02d}-10").date()
            amt = float(rs.randint(120_000, 280_000))
            paid = amt if rs.rand()<0.6 else (amt*rs.uniform(0.2,0.8) if rs.rand()<0.5 else 0.0)
            rows.append({"InvoiceNo":f"{p[:2].upper()}-INV-{i:03d}","Project":p,"Client": "Auto",
                         "Date":d,"DueDate":(pd.to_datetime(d)+pd.Timedelta(days=30)).date(),
                         "Amount":amt,"Collected":float(paid)})
    return pd.DataFrame(rows)

@st.cache_data
def sample_supplier_invoices():
    rows=[]; rs=np.random.RandomState(13)
    for p in ["Project A","Project B"]:
        for i in range(1,12):
            d = pd.to_datetime(f"2025-{(i%12)+1:02d}-15").date()
            amt = float(rs.randint(50_000, 160_000))
            paid = amt if rs.rand()<0.55 else (amt*rs.uniform(0.1,0.7) if rs.rand()<0.5 else 0.0)
            rows.append({"InvoiceNo":f"{p[:2].upper()}-SUP-{i:03d}","Supplier":f"Supplier {rs.randint(1,6)}","Project":p,
                         "Date":d,"DueDate":(pd.to_datetime(d)+pd.Timedelta(days=45)).date(),
                         "Amount":amt,"Paid":float(paid)})
    return pd.DataFrame(rows)

@st.cache_data
def sample_client_payments():
    rows=[]; rs=np.random.RandomState(17)
    statuses=["collected","under_collection","rejected"]
    methods=["cash","transfer","cheque"]
    for p in ["Project A","Project B"]:
        for i in range(1,12):
            d = pd.to_datetime(f"2025-{(i%12)+1:02d}-20").date()
            amt = float(rs.randint(50_000, 180_000))
            stt = rs.choice(statuses, p=[0.7,0.25,0.05])
            rows.append({"PaymentNo":f"{p[:2].upper()}-PAY-{i:03d}","Project":p,"Date":d,
                         "Amount":amt,"Method":rs.choice(methods),"Status":stt,"Reference":"-"})
    return pd.DataFrame(rows)

@st.cache_data
def sample_supplier_payments():
    rows=[]; rs=np.random.RandomState(23)
    statuses=["paid","cheque_issued","cheque_under_collection"]
    methods=["transfer","cash","cheque"]
    for p in ["Project A","Project B"]:
        for i in range(1,10):
            d = pd.to_datetime(f"2025-{(i%12)+1:02d}-25").date()
            amt = float(rs.randint(30_000, 140_000))
            stt = rs.choice(statuses, p=[0.6,0.25,0.15])
            rows.append({"PaymentNo":f"{p[:2].upper()}-SPY-{i:03d}","Project":p,"Date":d,
                         "Amount":amt,"Method":rs.choice(methods),"Status":stt,"Supplier":f"Supplier {rs.randint(1,6)}"})
    return pd.DataFrame(rows)

@st.cache_data
def sample_employees():
    rows=[]
    for p in ["Project A","Project B"]:
        for i,role in enumerate(["PM","Engineer","Surveyor","Technician","Driver"], start=1):
            rows.append({"Employee":f"Emp {i:02d}","Role":role,"Project":p,
                         "Start":pd.to_datetime("2025-01-10").date(),"End":pd.to_datetime("2025-12-31").date(),
                         "CostRate": float(15_000 + i*1200), "AllocationPct": float(0.5 if role in ["Technician","Driver"] else 1.0)})
    return pd.DataFrame(rows)

# ======================================================================================
# Uploads (each section can be overridden)
# ======================================================================================
with st.expander("📥 Optional uploads (CSV/Excel) — override the sample data", expanded=False):
    col1, col2, col3 = st.columns(3)
    up_master   = col1.file_uploader("Projects master", type=["csv","xlsx"])
    up_budget   = col2.file_uploader("Budgets (long format)", type=["csv","xlsx"])
    up_actuals  = col3.file_uploader("Actuals (Revenue/Expense)", type=["csv","xlsx"])
    col4, col5, col6 = st.columns(3)
    up_cinv     = col4.file_uploader("Client invoices", type=["csv","xlsx"])
    up_sinv     = col5.file_uploader("Supplier invoices", type=["csv","xlsx"])
    up_emp      = col6.file_uploader("Employees/Assignments", type=["csv","xlsx"])
    col7, col8 = st.columns(2)
    up_cpay     = col7.file_uploader("Client payments", type=["csv","xlsx"])
    up_spay     = col8.file_uploader("Supplier payments", type=["csv","xlsx"])

# Load / normalize
master = _read_any(up_master) or sample_master_projects()
# standardize master
master = _rename(master, {
    "Project": _stdcol(master,"Project"),
    "Client": _stdcol(master,"Client"),
    "ContractAmount": _stdcol(master,"ContractAmount"),
    "SubcontractAmount": _stdcol(master,"SubcontractAmount"),
    "AdditionalWork": _stdcol(master,"AdditionalWork"),
    "StartDate": _stdcol(master,"StartDate"),
    "EndDate": _stdcol(master,"EndDate"),
    "AdvancePayment": _stdcol(master,"AdvancePayment"),
    "Currency": _stdcol(master,"Currency"),
})
master["StartDate"] = pd.to_datetime(master["StartDate"]).dt.date
master["EndDate"] = pd.to_datetime(master["EndDate"]).dt.date

budget = _read_any(up_budget) or sample_budgets()
budget = _rename(budget, {
    "Project": _stdcol(budget,"Project"),
    "Version": _stdcol(budget,"Version") or "Version",
    "Month": _stdcol(budget,"Month"),
    "Type": _stdcol(budget,"Type") or "Type",
    "Item": _stdcol(budget,"Item") or "Item",
    "Planned": _stdcol(budget,"Planned"),
})
budget["Month"] = pd.to_datetime(budget["Month"]).dt.to_period("M").dt.to_timestamp("MS")
budget["Planned"] = _safe_num(budget["Planned"])
if "Version" not in budget.columns: budget["Version"] = "V1"
if "Type" not in budget.columns: budget["Type"] = "Cost"  # fallback

actuals = _read_any(up_actuals) or sample_actuals()
actuals = _rename(actuals, {
    "Date": _stdcol(actuals,"Date"),
    "Project": _stdcol(actuals,"Project"),
    "Type": _stdcol(actuals,"Type"),
    "Category": _stdcol(actuals,"Category") or "Category",
    "Amount": _stdcol(actuals,"Amount"),
})
actuals["Date"] = pd.to_datetime(actuals["Date"]).dt.date
actuals["Month"] = pd.to_datetime(actuals["Date"]).to_period("M").dt.to_timestamp("MS")
actuals["Amount"] = _safe_num(actuals["Amount"])
actuals["Type"] = actuals["Type"].str.title()

cinv = _read_any(up_cinv) or sample_client_invoices()
cinv = _rename(cinv, {
    "InvoiceNo": _stdcol(cinv,"InvoiceNo") or "InvoiceNo",
    "Project": _stdcol(cinv,"Project"),
    "Client": _stdcol(cinv,"Client") or "Client",
    "Date": _stdcol(cinv,"Date"),
    "DueDate": _stdcol(cinv,"DueDate") or "DueDate",
    "Amount": _stdcol(cinv,"Amount"),
    "Collected": _stdcol(cinv,"Collected") or "Collected",
})
for col in ["Date","DueDate"]:
    if col in cinv.columns: cinv[col] = pd.to_datetime(cinv[col]).dt.date
cinv["Amount"] = _safe_num(cinv["Amount"])
if "Collected" not in cinv.columns: cinv["Collected"] = 0.0
cinv["Collected"] = _safe_num(cinv["Collected"])
cinv["Outstanding"] = cinv["Amount"] - cinv["Collected"]

sinv = _read_any(up_sinv) or sample_supplier_invoices()
sinv = _rename(sinv, {
    "InvoiceNo": _stdcol(sinv,"InvoiceNo") or "InvoiceNo",
    "Supplier": _stdcol(sinv,"Supplier") or "Supplier",
    "Project": _stdcol(sinv,"Project"),
    "Date": _stdcol(sinv,"Date"),
    "DueDate": _stdcol(sinv,"DueDate") or "DueDate",
    "Amount": _stdcol(sinv,"Amount"),
    "Paid": _stdcol(sinv,"Paid") or "Paid",
})
for col in ["Date","DueDate"]:
    if col in sinv.columns: sinv[col] = pd.to_datetime(sinv[col]).dt.date
sinv["Amount"] = _safe_num(sinv["Amount"])
if "Paid" not in sinv.columns: sinv["Paid"] = 0.0
sinv["Paid"] = _safe_num(sinv["Paid"])
sinv["Outstanding"] = sinv["Amount"] - sinv["Paid"]

cpay = _read_any(up_cpay) or sample_client_payments()
cpay = _rename(cpay, {
    "PaymentNo": _stdcol(cpay,"PaymentNo") or "PaymentNo",
    "Project": _stdcol(cpay,"Project"),
    "Date": _stdcol(cpay,"Date"),
    "Amount": _stdcol(cpay,"Amount"),
    "Method": _stdcol(cpay,"Method") or "Method",
    "Status": _stdcol(cpay,"Status") or "Status",
})
cpay["Date"] = pd.to_datetime(cpay["Date"]).dt.date
cpay["Amount"] = _safe_num(cpay["Amount"])
cpay["Status"] = cpay["Status"].str.lower()

spay = _read_any(up_spay) or sample_supplier_payments()
spay = _rename(spay, {
    "PaymentNo": _stdcol(spay,"PaymentNo") or "PaymentNo",
    "Project": _stdcol(spay,"Project"),
    "Date": _stdcol(spay,"Date"),
    "Amount": _stdcol(spay,"Amount"),
    "Method": _stdcol(spay,"Method") or "Method",
    "Status": _stdcol(spay,"Status") or "Status",
    "Supplier": _stdcol(spay,"Supplier") or "Supplier",
})
spay["Date"] = pd.to_datetime(spay["Date"]).dt.date
spay["Amount"] = _safe_num(spay["Amount"])
spay["Status"] = spay["Status"].str.lower()

emps = _read_any(up_emp) or sample_employees()
emps = _rename(emps, {
    "Employee": _stdcol(emps,"Employee") or "Employee",
    "Role": _stdcol(emps,"Role") or "Role",
    "Project": _stdcol(emps,"Project"),
    "Start": _stdcol(emps,"Start") or "Start",
    "End": _stdcol(emps,"End") or "End",
    "CostRate": _stdcol(emps,"CostRate") or "CostRate",
    "AllocationPct": _stdcol(emps,"AllocationPct") or "AllocationPct",
})
for c in ["Start","End"]:
    if c in emps.columns: emps[c] = pd.to_datetime(emps[c]).dt.date
for c in ["CostRate","AllocationPct"]:
    if c in emps.columns: emps[c] = _safe_num(emps[c])

# ======================================================================================
# Sidebar filters
# ======================================================================================
st.sidebar.header("Filters")

projects = sorted(list(set(master["Project"]) | set(budget["Project"]) | set(actuals["Project"]) |
                      set(cinv["Project"]) | set(sinv["Project"])))
project = st.sidebar.selectbox("Project", projects, index=0)

# Version list from budgets
versions = sorted(budget.loc[budget["Project"]==project,"Version"].unique().tolist())
version = st.sidebar.selectbox("Budget Version", versions, index=0 if versions else None)

# Date range from actuals/invoices
min_d = min(
    actuals.loc[actuals["Project"]==project,"Date"].min() if not actuals.empty else date.today(),
    cinv.loc[cinv["Project"]==project,"Date"].min() if not cinv.empty else date.today(),
    sinv.loc[sinv["Project"]==project,"Date"].min() if not sinv.empty else date.today(),
)
max_d = max(
    actuals.loc[actuals["Project"]==project,"Date"].max() if not actuals.empty else date.today(),
    cinv.loc[cinv["Project"]==project,"Date"].max() if not cinv.empty else date.today(),
    sinv.loc[sinv["Project"]==project,"Date"].max() if not sinv.empty else date.today(),
)
cfd1, cfd2 = st.sidebar.columns(2)
from_date = cfd1.date_input("From", min_d)
to_date   = cfd2.date_input("To",   max_d)

# Filtered views
mrow = master[master["Project"]==project].iloc[0] if (master["Project"]==project).any() else None
b_proj = budget[(budget["Project"]==project) & (budget["Version"]==version)].copy()
a_proj = actuals[(actuals["Project"]==project) & (actuals["Date"]>=from_date) & (actuals["Date"]<=to_date)].copy()
cinv_p = cinv[(cinv["Project"]==project) & (cinv["Date"]>=from_date) & (cinv["Date"]<=to_date)].copy()
sinv_p = sinv[(sinv["Project"]==project) & (sinv["Date"]>=from_date) & (sinv["Date"]<=to_date)].copy()
cpay_p = cpay[(cpay["Project"]==project) & (cpay["Date"]>=from_date) & (cpay["Date"]<=to_date)].copy()
spay_p = spay[(spay["Project"]==project) & (spay["Date"]>=from_date) & (spay["Date"]<=to_date)].copy()
emps_p = emps[emps["Project"]==project].copy()

# ======================================================================================
# TOP KPIs BLOCK (as in your sketch)
# ======================================================================================
st.subheader("Snapshot")

c1, c2, c3, c4 = st.columns(4)
c5, c6, c7, c8 = st.columns(4)

contract_amt   = float(mrow["ContractAmount"]) if mrow is not None else 0.0
subcontract_amt= float(mrow["SubcontractAmount"]) if mrow is not None else 0.0
additional_amt = float(mrow["AdditionalWork"]) if mrow is not None else 0.0
advance        = float(mrow["AdvancePayment"]) if mrow is not None else 0.0

revenue = a_proj.loc[a_proj["Type"]=="Revenue","Amount"].sum()
expense = a_proj.loc[a_proj["Type"]=="Expense","Amount"].sum()  # negative
profit  = revenue + expense
margin  = (profit/revenue*100.0) if revenue else 0.0

c1.metric("Contract amount", f"{contract_amt:,.0f}")
c2.metric("Subcontract amount", f"{subcontract_amt:,.0f}")
c3.metric("Additional work", f"{additional_amt:,.0f}")
c4.metric("Total executed (Revenue)", f"{revenue:,.0f}")

client_name = (mrow["Client"] if (mrow is not None and "Client" in mrow) else "")
c5.metric("Client", client_name)
c6.metric("Start date", str(mrow["StartDate"]) if mrow is not None else "-")
c7.metric("End date", str(mrow["EndDate"]) if mrow is not None else "-")
c8.metric("Margins", f"{profit:,.0f}  ({margin:.2f}%)")

# Cheques & cash positions (your boxes)
cheques_under_coll = cpay_p.loc[cpay_p["Status"]=="under_collection","Amount"].sum()
client_paid        = cpay_p.loc[cpay_p["Status"]=="collected","Amount"].sum()
sup_cheque_out     = spay_p.loc[spay_p["Status"].isin(["cheque_issued","cheque_under_collection"]),"Amount"].sum()
total_suppliers    = sinv_p["Amount"].sum()

st.write("")
d1,d2,d3,d4 = st.columns(4)
d1.metric("Cheques under collection", f"{cheques_under_coll:,.0f}")
d2.metric("Client payments (collected)", f"{client_paid:,.0f}")
d3.metric("Suppliers cheques (issued/under collection)", f"{sup_cheque_out:,.0f}")
d4.metric("Total suppliers (invoices)", f"{total_suppliers:,.0f}")

# ======================================================================================
# Budgets: Planned vs Actual (Revenue & Cost) — big panel in your sketch
# ======================================================================================
st.subheader("Budgets — Actual vs Planned")

if b_proj.empty and a_proj.empty:
    st.info("No data for this project.")
else:
    # Planned per month (Revenue/Cost)
    plan = (b_proj.groupby(["Month","Type"])["Planned"].sum()
                  .unstack(fill_value=0.0)
                  .reindex(columns=["Revenue","Cost"], fill_value=0.0)
                  .sort_index())
    # Actuals per month (Revenue/Expense)
    actual = (a_proj.groupby(["Month","Type"])["Amount"].sum()
                    .unstack(fill_value=0.0)
                    .reindex(columns=["Revenue","Expense"], fill_value=0.0)
                    .sort_index())
    # Build a single frame for charts
    chart = pd.DataFrame(index=sorted(set(plan.index) | set(actual.index)))
    chart["Planned Revenue"] = plan.get("Revenue",0.0)
    chart["Planned Cost"]    = plan.get("Cost",0.0)
    chart["Actual Revenue"]  = actual.get("Revenue",0.0)
    chart["Actual Cost"]     = -actual.get("Expense",0.0)  # show positive cost for chart
    chart = chart.fillna(0.0)

    st.line_chart(chart)

    # Summary table with variance
    summary = pd.DataFrame({
        "Planned Revenue": [chart["Planned Revenue"].sum()],
        "Actual Revenue": [chart["Actual Revenue"].sum()],
        "Planned Cost": [chart["Planned Cost"].sum()],
        "Actual Cost": [chart["Actual Cost"].sum()],
    })
    summary["Revenue Var"] = summary["Actual Revenue"] - summary["Planned Revenue"]
    summary["Cost Var"]    = summary["Actual Cost"] - summary["Planned Cost"]
    summary["Profit (Actual)"] = summary["Actual Revenue"] - summary["Actual Cost"]
    st.dataframe(summary.style.format("{:,.0f}"), use_container_width=True)

# ======================================================================================
# Client invoices (left) & Supplier invoices (right) — with totals like your sketch
# ======================================================================================
st.subheader("Invoices")

left, right = st.columns(2)

with left:
    st.markdown("##### Client invoices")
    if cinv_p.empty:
        st.info("No client invoices in range.")
    else:
        st.dataframe(
            cinv_p.sort_values("Date", ascending=False)
                  .assign(Outstanding=lambda d: d["Amount"]-d["Collected"])
                  .style.format({"Amount":"{:,.0f}","Collected":"{:,.0f}","Outstanding":"{:,.0f}"}),
            use_container_width=True
        )
        totals = cinv_p.agg({"Amount":"sum","Collected":"sum"})
        st.write(f"**Totals** — Amount: {totals['Amount']:,.0f} • Collected: {totals['Collected']:,.0f} • Outstanding: {(totals['Amount']-totals['Collected']):,.0f}")

with right:
    st.markdown("##### Suppliers invoices")
    if sinv_p.empty:
        st.info("No supplier invoices in range.")
    else:
        st.dataframe(
            sinv_p.sort_values("Date", ascending=False)
                  .assign(Outstanding=lambda d: d["Amount"]-d["Paid"])
                  .style.format({"Amount":"{:,.0f}","Paid":"{:,.0f}","Outstanding":"{:,.0f}"}),
            use_container_width=True
        )
        totals = sinv_p.agg({"Amount":"sum","Paid":"sum"})
        st.write(f"**Total** — Amount: {totals['Amount']:,.0f} • Paid: {totals['Paid']:,.0f} • Outstanding: {(totals['Amount']-totals['Paid']):,.0f}")

# ======================================================================================
# Dues & Cheques panels — bottom blocks in your sketch
# ======================================================================================
st.subheader("Dues & Cheques")

c_left, c_right = st.columns(2)

with c_left:
    st.markdown("##### Clients dues (A/R)")
    if cinv_p.empty:
        st.info("No client invoices.")
    else:
        ar = (cinv_p.groupby("Client")[["Amount","Collected"]].sum()
                     .assign(Outstanding=lambda d: d["Amount"]-d["Collected"])
                     .sort_values("Outstanding", ascending=False)
                     .reset_index())
        st.dataframe(ar.style.format({"Amount":"{:,.0f}","Collected":"{:,.0f}","Outstanding":"{:,.0f}"}),
                     use_container_width=True)

        # Aging (optional)
        cinv_p["Age"] = (pd.to_datetime(date.today()) - pd.to_datetime(cinv_p["DueDate"])).dt.days
        aging_bins = pd.cut(cinv_p["Age"], [-10,0,30,60,90,9999], labels=["Not due","0-30","31-60","61-90","90+"])
        aging = cinv_p.assign(Outstanding=lambda d: d["Amount"]-d["Collected"]).groupby(aging_bins)["Outstanding"].sum()
        st.write("**A/R Aging**")
        st.bar_chart(aging)

with c_right:
    st.markdown("##### Suppliers dues (A/P)")
    if sinv_p.empty:
        st.info("No supplier invoices.")
    else:
        ap = (sinv_p.groupby("Supplier")[["Amount","Paid"]].sum()
                     .assign(Outstanding=lambda d: d["Amount"]-d["Paid"])
                     .sort_values("Outstanding", ascending=False)
                     .reset_index())
        st.dataframe(ap.style.format({"Amount":"{:,.0f}","Paid":"{:,.0f}","Outstanding":"{:,.0f}"}),
                     use_container_width=True)

        # Suppliers cheques quick total
        cheq_sup = spay_p.loc[spay_p["Status"].isin(["cheque_issued","cheque_under_collection"]),"Amount"].sum()
        st.write(f"**Suppliers cheques outstanding:** {cheq_sup:,.0f}")

# ======================================================================================
# Employees assigned to the project — panel in your sketch
# ======================================================================================
st.subheader("Employees assigned")

if emps_p.empty:
    st.info("No employees for this project.")
else:
    emps_p = emps_p.copy()
    emps_p["MonthlyCost"] = emps_p["CostRate"] * emps_p["AllocationPct"]
    st.dataframe(
        emps_p[["Employee","Role","Start","End","AllocationPct","CostRate","MonthlyCost"]]
              .style.format({"AllocationPct":"{:.0%}","CostRate":"{:,.0f}","MonthlyCost":"{:,.0f}"}),
        use_container_width=True
    )
    st.write(f"**Total monthly personnel cost (allocated):** {emps_p['MonthlyCost'].sum():,.0f}")

# ======================================================================================
# Extras I recommend on a project dashboard (helpful in practice)
# ======================================================================================
st.subheader("Extras (recommended)")

# Backlog & forecast margin
executed_rev = actuals[(actuals["Project"]==project)]["Amount"]
executed_rev = executed_rev[executed_rev>0].sum()
contract_total = contract_amt + additional_amt
backlog = max(contract_total - executed_rev, 0)
projected_profit = (contract_total - (sinv[sinv['Project']==project]['Amount'].sum()))  # simplistic
proj_margin_pct = (projected_profit/contract_total*100.0) if contract_total else 0.0

x1, x2, x3 = st.columns(3)
x1.metric("Backlog (remaining contract)", f"{backlog:,.0f}")
x2.metric("Projected profit (contract - supplier invoices)", f"{projected_profit:,.0f}")
x3.metric("Projected margin %", f"{proj_margin_pct:.2f}%")

st.caption("Upload your real files to replace the sample data. Budget file should be **long format**: "
           "`Project, Version, Month, Type (Revenue/Cost), Item, Planned`. Actuals: `Date, Project, Type (Revenue/Expense), Category, Amount`.")

