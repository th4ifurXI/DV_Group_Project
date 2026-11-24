import plotly.express as px
import streamlit as st

from core.data import reorder_table
from core import style
from core.style import STATUS_COLOUR, STATUS_ICON, insight, money_axis, plot, rm, rm_short


def render():
    D = st.session_state["D"]
    st.title("🚨 Inventory Alerts")
    if D["inventory"].empty:
        st.info("This file has no stock counts or supplier lead times, so reorder alerts cannot be calculated.")
        return
    as_of = D["sales"].date.max()
    st.caption(f"What do we need to reorder now? Based on stock count on {as_of:%d %b %Y} "
               "(not affected by the date filter).")

    a, b = st.columns(2)
    window = a.slider("Average demand over the last ... days", 14, 120, 60, step=7)
    safety = b.slider("Safety buffer (days of extra stock)", 0, 14, 3)
    with st.expander("How the alert is calculated"):
        st.latex(r"\text{Reorder point} = \bar{d} \times (L + S)")
        st.markdown("- **d̄** = average units sold per day over the window above\n"
                    "- **L** = supplier lead time (days), **S** = safety buffer (days)\n"
                    "- 🔴 **Reorder now**: stock will run out before a new delivery arrives (stock ≤ d̄ × L)\n"
                    "- 🟠 **Reorder soon**: stock is at or below the reorder point\n"
                    "- 🔵 **Overstock**: more than 45 days of stock · ⚪ **No recent sales** in the window\n"
                    "- Suggested order = enough for lead time + safety + 14 days, minus stock on hand")

    t = reorder_table(D["sales"], D["products"], D["inventory"], window, safety)
    counts = t.status.value_counts()
    c = st.columns(5)
    for col, k in zip(c, ["Reorder now", "Reorder soon", "OK", "Overstock", "No recent sales"]):
        col.metric(STATUS_ICON[k], int(counts.get(k, 0)))

    order = ["Reorder now", "Reorder soon", "Overstock", "No recent sales", "OK"]
    t["status_rank"] = t.status.map({k: i for i, k in enumerate(order)})
    show = st.multiselect("Show", order, default=["Reorder now", "Reorder soon"], format_func=lambda k: STATUS_ICON[k])
    view = t[t.status.isin(show)].sort_values(["status_rank", "days_of_cover"])
    view = view.assign(status=view.status.map(STATUS_ICON))
    cols = ["status", "product_name", "category", "stock_on_hand", "avg_daily_units", "days_of_cover",
            "lead_time_days", "reorder_point", "suggested_order_qty", "supplier", "stock_value_rm"]
    st.dataframe(view[cols], hide_index=True, width="stretch",
                 column_config={
                     "avg_daily_units": st.column_config.NumberColumn("Avg units/day", format="%.1f"),
                     "days_of_cover": st.column_config.NumberColumn("Days of cover", format="%.1f"),
                     "lead_time_days": st.column_config.NumberColumn("Lead time (days)"),
                     "suggested_order_qty": st.column_config.NumberColumn("Suggested order"),
                     "stock_value_rm": st.column_config.NumberColumn("Stock value", format=style.money_fmt())})
    st.download_button("Download purchase list (CSV)",
                       view[view.status.str.contains("Reorder")][["product_name", "supplier", "suggested_order_qty"]]
                       .to_csv(index=False), "purchase_list.csv")

    now = t[t.status == "Reorder now"]
    if not now.empty:
        by_sup = now.groupby("supplier").size().sort_values(ascending=False)
        insight(f"<b>{len(now)} products</b> will run out before the next delivery. "
                f"Call <b>{by_sup.index[0]}</b> first ({by_sup.iloc[0]} items).")

    # where cash is tied up - no red + green pair (L2 #2): OK is neutral grey
    cap = t.groupby("status", as_index=False).stock_value_rm.sum()
    cap = cap.set_index("status").reindex(order).dropna().reset_index()
    cap["label"] = cap.status.map(STATUS_ICON)
    fig = px.bar(cap, x="stock_value_rm", y="label", orientation="h", title="Stock value at cost by status",
                 labels={"stock_value_rm": "Stock value at cost", "label": ""},
                 text=[rm_short(v) for v in cap.stock_value_rm])
    fig.update_traces(marker_color=[STATUS_COLOUR[k] for k in cap.status], textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>RM%{x:,.0f}<extra></extra>")
    fig.update_layout(height=320, yaxis_categoryorder="array", yaxis_categoryarray=cap.label[::-1].tolist(),
                      xaxis_range=[0, cap.stock_value_rm.max() * 1.18])
    money_axis(fig, "x")
    plot(fig)
    idle = cap[cap.status.isin(["Overstock", "No recent sales"])].stock_value_rm.sum()
    insight(f"{rm(idle)} of cash is sitting in overstocked or non-selling items. "
            "Pause reorders on these and run a clearance promotion.")
