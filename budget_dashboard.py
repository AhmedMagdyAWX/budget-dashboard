import streamlit as st
import pandas as pd

st.set_page_config(page_title="Budget Dashboard", layout="wide")

st.title("📊 Budget Dashboard")

# Sample data
st.sidebar.header("Filters")
selected_project = st.sidebar.selectbox("Select Project", ["Company", "Project A", "Project B"])

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
data = {
    "Month": months,
    "Planned": [10000, 12000, 11000, 13000, 12500, 14000],
    "Actual": [9500, 11800, 10700, 13500, 12000, 14500]
}
df = pd.DataFrame(data)

st.subheader(f"📁 Budget Overview - {selected_project}")
st.line_chart(df.set_index("Month"))

st.subheader("📋 Budget Table")
st.dataframe(df.style.highlight_between(subset=["Actual"], left=0, right=999999, color="lightgreen"))

# KPIs
planned_total = df["Planned"].sum()
actual_total = df["Actual"].sum()
variance = actual_total - planned_total

st.metric("Total Planned", f"{planned_total:,.0f} EGP")
st.metric("Total Actual", f"{actual_total:,.0f} EGP", delta=f"{variance:,.0f} EGP")
