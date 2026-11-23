"""
Kedai Runcit Sales & Inventory Decision Dashboard
Run:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from core.data import load
from views import about, customers, inventory, overview, products, returns, seasonality

st.set_page_config(page_title="Kedai Runcit Dashboard", page_icon="🛒", layout="wide")

# ---------------- data ----------------
with st.sidebar:
    st.markdown("### 🛒 Kedai Runcit Dashboard")
    st.caption("Sales & inventory decisions for a Seri Iskandar mini-market (simulated data)")
    with st.expander("Use your own POS export"):
        up = st.file_uploader("transactions.csv (same columns as the sample)", type="csv")

try:
    D = load(up.getvalue() if up else None)
except ValueError as e:
    st.sidebar.error(str(e))
    D = load(None)

sales = D["sales"]
dmin, dmax = sales.date.min().date(), sales.date.max().date()

# ---------------- filters (apply to every page) ----------------
with st.sidebar:
    st.markdown("#### Filters")
    preset = st.radio("Period", ["Last 90 days", "Last 12 months", "All data", "Custom"],
                      index=2, horizontal=False)
    if preset == "Last 90 days":
        start, end = dmax - pd.Timedelta(days=89), dmax
    elif preset == "Last 12 months":
        start, end = (pd.Timestamp(dmax) - pd.DateOffset(months=12) + pd.Timedelta(days=1)).date(), dmax
    elif preset == "All data":
        start, end = dmin, dmax
    else:
        rng = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
        start, end = (rng if isinstance(rng, tuple) and len(rng) == 2 else (dmin, dmax))
    cats = st.multiselect("Category", sorted(sales.category.unique()), placeholder="All categories")
    ctype = st.radio("Customer type", ["All", "Member", "Walk-in"], horizontal=True)
    st.caption(f"Data covers {dmin:%d %b %Y} to {dmax:%d %b %Y}")

st.session_state["D"] = D
st.session_state["F"] = dict(start=pd.Timestamp(start), end=pd.Timestamp(end),
                             categories=cats, customer_type=ctype)

pages = [
    st.Page(overview.render, title="Executive Overview", icon="📊", url_path="overview", default=True),
    st.Page(products.render, title="Product Performance", icon="📦", url_path="products"),
    st.Page(customers.render, title="Customer Insights", icon="👥", url_path="customers"),
    st.Page(seasonality.render, title="Seasonality & Timing", icon="📅", url_path="seasonality"),
    st.Page(returns.render, title="Returns & Losses", icon="↩️", url_path="returns"),
    st.Page(inventory.render, title="Inventory Alerts", icon="🚨", url_path="inventory"),
    st.Page(about.render, title="About the Data", icon="ℹ️", url_path="about"),
]
st.navigation(pages, position="sidebar").run()
