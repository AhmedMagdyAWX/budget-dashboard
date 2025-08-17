import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Budget Dashboard", layout="wide")

st.title("📊 Budget Dashboard with Versions & Items")

# Sample Data Creation
@st.cache_data
def generate_sample_data():
    versions = [f"V{i}" for i in range(1, 4)]
    months = pd.date_range("2024-01-01", "2024-12-01", freq="MS")
    items = ["Rentals", "Fuel", "Construction", "Salaries", "Marketing"]

    data = []
    for version in versions:
        for item in items:
            for month in months:
                planned = int(10000 + 2000 * (hash(item + version + str(month)) % 10))
                actual = planned + int(planned * 0.1 * ((hash(str(month) + item) % 3) - 1))  # +/-10%
                data.append({
                    "Version": version,
                    "Item": item,
                    "Month": month,
                    "Planned": planned,
                    "Actual": actual
                })

    return pd.DataFrame(data)

df = generate_sample_data()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

selected_version = st.sidebar.selectbox("📄 Budget Version", sorted(df["Version"].unique(), reverse=True))
from_date = st.sidebar.date_input("📅 From", datetime(2024, 1, 1))
to_date = st.sidebar.date_input("📅 To", datetime(2024, 12, 1))

filtered_df = df[
    (df["Version"] == selected_version) &
    (df["Month"] >= pd.to_datetime(from_date)) &
    (df["Month"] <= pd.to_datetime(to_date))
]

st.subheader(f"📁 Budget Overview: {selected_version} ({from_date} to {to_date})")

# --- Line Chart by Item ---
st.markdown("### 📈 Budget Trends per Item")
pivot = filtered_df.pivot_table(index="Month", columns="Item", values="Planned", aggfunc="sum")
st.line_chart(pivot)

# --- Table View ---
st.markdown("### 📋 Budget Details Table")

summary = filtered_df.groupby("Item").agg({
    "Planned": "sum",
    "Actual": "sum"
}).reset_index()

summary["Variance"] = summary["Actual"] - summary["Planned"]

st.dataframe(summary.style
    .format({"Planned": "{:,.0f}", "Actual": "{:,.0f}", "Variance": "{:,.0f}"})
    .applymap(lambda v: "background-color: lightgreen" if isinstance(v, (int, float)) and v >= 0 else "background-color: salmon", subset=["Variance"])
)

# --- KPIs ---
total_planned = summary["Planned"].sum()
total_actual = summary["Actual"].sum()
variance_total = total_actual - total_planned

st.markdown("### 🔍 Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Planned", f"{total_planned:,.0f} EGP")
col2.metric("Total Actual", f"{total_actual:,.0f} EGP", delta=f"{variance_total:,.0f} EGP")
col3.metric("Variance %", f"{(variance_total/total_planned)*100:.2f}%", delta=f"{variance_total:,.0f} EGP")

