"""Data loading, cleaning and shared calculations for the dashboard."""

from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data"
REQUIRED_COLS = ["invoice_no", "invoice_type", "date", "time", "customer_id", "customer_type",
                 "product_id", "product_name", "category", "quantity", "unit_price_rm",
                 "discount_rm", "line_total_rm", "payment_method", "return_reason"]


@st.cache_data(show_spinner="Loading and cleaning data...")
def load(upload_bytes: bytes | None = None):
    """Return a dict of cleaned tables plus a cleaning log."""
    products = pd.read_csv(DATA / "products.csv")
    customers = pd.read_csv(DATA / "customers.csv", parse_dates=["join_date"])
    inventory = pd.read_csv(DATA / "inventory.csv")
    calendar = pd.read_csv(DATA / "calendar_events.csv", parse_dates=["start_date", "end_date"])

    raw = pd.read_csv(BytesIO(upload_bytes) if upload_bytes else DATA / "transactions.csv",
                      dtype={"customer_id": "string"})
    missing = [c for c in REQUIRED_COLS if c not in raw.columns]
    if missing:
        raise ValueError(f"Uploaded file is missing columns: {', '.join(missing)}")

    log = [("Raw rows loaded", len(raw), "")]
    tx = raw.copy()

    n = len(tx)
    tx = tx.drop_duplicates()
    log.append(("Removed exact duplicate rows (POS double scans)", n - len(tx), "drop"))

    n = len(tx)
    test = tx.invoice_no.astype(str).str.startswith("TEST") | (tx.unit_price_rm <= 0)
    tx = tx[~test]
    log.append(("Removed cashier test scans / RM0 lines", n - len(tx), "drop"))

    name_map = products.set_index("product_id").product_name
    blank = tx.product_name.isna() | (tx.product_name.astype(str).str.strip() == "")
    tx.loc[blank, "product_name"] = tx.loc[blank, "product_id"].map(name_map)
    log.append(("Filled missing product names from product master", int(blank.sum()), "fix"))

    tx["datetime"] = pd.to_datetime(tx.date.astype(str) + " " + tx.time.astype(str), errors="coerce")
    n = len(tx)
    tx = tx.dropna(subset=["datetime"])
    log.append(("Removed rows with invalid date/time", n - len(tx), "drop"))

    tx["date"] = tx.datetime.dt.normalize()
    tx["hour"] = tx.datetime.dt.hour
    tx["weekday"] = tx.datetime.dt.day_name()
    tx["month"] = tx.datetime.dt.to_period("M").dt.to_timestamp()
    tx["customer_id"] = tx.customer_id.replace({"": pd.NA})

    cost = products.set_index("product_id").cost_price_rm
    tx["cost_rm"] = tx.product_id.map(cost) * tx.quantity
    tx["gross_profit_rm"] = tx.line_total_rm - tx.cost_rm

    sales = tx[tx.invoice_type == "Sale"].copy()
    returns = tx[tx.invoice_type == "Return"].copy()
    log.append(("Sale lines after cleaning", len(sales), "result"))
    log.append(("Return lines (kept in a separate table)", len(returns), "result"))

    return dict(sales=sales, returns=returns, products=products, customers=customers,
                inventory=inventory, calendar=calendar,
                log=pd.DataFrame(log, columns=["Step", "Rows", "Type"]))


def filter_frame(df, f):
    """Apply the sidebar filters (date range, categories, customer type)."""
    m = (df.date >= pd.Timestamp(f["start"])) & (df.date <= pd.Timestamp(f["end"]))
    if f["categories"]:
        m &= df.category.isin(f["categories"])
    if f["customer_type"] != "All":
        m &= df.customer_type == f["customer_type"]
    return df[m]


def previous_period(df, f):
    """Same-length period immediately before the selected range (for KPI deltas)."""
    start, end = pd.Timestamp(f["start"]), pd.Timestamp(f["end"])
    length = end - start
    prev = dict(f, start=start - length - pd.Timedelta(days=1), end=start - pd.Timedelta(days=1))
    return filter_frame(df, prev)


def rfm(sales, as_of):
    """Rule-based RFM: each of R, F, M scored 1-5 by quintile, then mapped to a segment."""
    m = sales.dropna(subset=["customer_id"])
    g = m.groupby("customer_id").agg(
        last=("date", "max"), first=("date", "min"),
        frequency=("invoice_no", "nunique"), monetary=("line_total_rm", "sum"))
    g["recency_days"] = (pd.Timestamp(as_of) - g["last"]).dt.days
    g["R"] = pd.qcut(g.recency_days.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    g["F"] = pd.qcut(g.frequency.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    g["M"] = pd.qcut(g.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def label(r):
        if r.R >= 4 and r.F >= 4:
            return "Champions"
        if r.R >= 3 and r.F >= 3:
            return "Loyal"
        if r.R >= 4 and r.F <= 2:
            return "New / Promising"
        if r.R <= 2 and r.F >= 3:
            return "At Risk"
        if r.R == 3:
            return "Needs Attention"
        return "Lost"

    g["segment"] = g.apply(label, axis=1)
    return g.reset_index()


SEGMENT_ORDER = ["Champions", "Loyal", "New / Promising", "Needs Attention", "At Risk", "Lost"]
SEGMENT_ACTION = {
    "Champions": "Reward: early access to promos, member-only bundles",
    "Loyal": "Keep engaged: points multiplier on staple items",
    "New / Promising": "Build habit: welcome voucher for 2nd and 3rd visit",
    "Needs Attention": "Nudge: targeted WhatsApp promo on their usual items",
    "At Risk": "Win back: personal offer before they switch store",
    "Lost": "Low priority: include in seasonal mass campaigns only",
}


def reorder_table(sales, products, inventory, window_days=60, safety_days=3):
    """Rule-based reorder point = avg daily demand x (lead time + safety days)."""
    as_of = sales.date.max()
    recent = sales[sales.date > as_of - pd.Timedelta(days=window_days)]
    d = recent.groupby("product_id").quantity.sum() / window_days
    t = products.merge(inventory, on="product_id").set_index("product_id")
    t["avg_daily_units"] = d.reindex(t.index).fillna(0)
    t["reorder_point"] = np.ceil(t.avg_daily_units * (t.lead_time_days + safety_days))
    t["days_of_cover"] = np.where(t.avg_daily_units > 0, t.stock_on_hand / t.avg_daily_units, np.inf)
    t["suggested_order_qty"] = np.maximum(
        np.ceil(t.avg_daily_units * (t.lead_time_days + safety_days + 14)) - t.stock_on_hand, 0)
    t["stock_value_rm"] = t.stock_on_hand * t.cost_price_rm

    def status(r):
        if r.avg_daily_units == 0:
            return "No recent sales"
        if r.stock_on_hand <= r.avg_daily_units * r.lead_time_days:
            return "Reorder now"
        if r.stock_on_hand <= r.reorder_point:
            return "Reorder soon"
        if r.days_of_cover > 45:
            return "Overstock"
        return "OK"

    t["status"] = t.apply(status, axis=1)
    return t.reset_index()
