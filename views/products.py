import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import filter_frame
from core.style import AXIS, MUTED, SERIES, bar_style, insight, rm


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    st.title("📦 Product Performance")
    st.caption("What should we stock more of, and what is just taking up shelf space?")
    if s.empty:
        st.warning("No sales in this selection.")
        return

    g = s.groupby(["product_id", "product_name", "category"], as_index=False).agg(
        revenue=("line_total_rm", "sum"), units=("quantity", "sum"),
        gross_profit=("gross_profit_rm", "sum"), invoices=("invoice_no", "nunique"))
    g["margin"] = g.gross_profit / g.revenue

    metric = st.segmented_control("Rank by", ["revenue", "gross_profit", "units"], default="revenue",
                                  format_func=lambda x: {"revenue": "Revenue", "gross_profit": "Gross profit",
                                                         "units": "Units sold"}[x])
    metric = metric or "revenue"
    fmt = "RM%{x:,.0f}" if metric != "units" else "%{x:,.0f} units"

    a, b = st.columns(2)
    for col, title, data in [(a, "Top 10", g.nlargest(10, metric)), (b, "Bottom 10", g.nsmallest(10, metric))]:
        d = data.sort_values(metric)
        fig = px.bar(d, x=metric, y="product_name", orientation="h", title=f"{title} products",
                     labels={metric: "", "product_name": ""}, custom_data=["category"])
        fig.update_traces(marker_color=SERIES[0] if title == "Top 10" else SERIES[1],
                          hovertemplate="%{y}<br>%{customdata[0]}<br>" + fmt + "<extra></extra>")
        fig.update_layout(height=400)
        col.plotly_chart(bar_style(fig), width="stretch")

    # Pareto
    p = g.sort_values("revenue", ascending=False).reset_index(drop=True)
    p["cum_share"] = p.revenue.cumsum() / p.revenue.sum()
    p["product_share"] = (np.arange(len(p)) + 1) / len(p)
    n80 = int((p.cum_share < 0.8).sum() + 1)
    fig = px.area(p, x="product_share", y="cum_share", title="Pareto: share of revenue from top products",
                  labels={"product_share": "Share of products (ranked by revenue)", "cum_share": "Cumulative revenue"},
                  custom_data=["product_name"])
    fig.update_traces(line_color=SERIES[0], line_width=2, fillcolor="rgba(42,120,214,0.12)",
                      hovertemplate="Top %{x:.0%} of products<br>= %{y:.0%} of revenue<br>(incl. %{customdata[0]})<extra></extra>")
    fig.add_hline(y=0.8, line_dash="dot", line_color=AXIS, annotation_text="80% of revenue",
                  annotation_font_color=MUTED)
    fig.add_vline(x=n80 / len(p), line_dash="dot", line_color=AXIS)
    fig.update_layout(height=340, xaxis_tickformat=".0%", yaxis_tickformat=".0%", yaxis_range=[0, 1.02])
    st.plotly_chart(fig, width="stretch")
    insight(f"Just <b>{n80} of {len(p)} products ({n80 / len(p):.0%})</b> make 80% of revenue. "
            "These are your 'A' items - never let them run out.")

    # margin by category
    c = s.groupby("category", as_index=False).agg(rev=("line_total_rm", "sum"), gp=("gross_profit_rm", "sum"))
    c["margin"] = c.gp / c.rev
    c = c.sort_values("margin")
    fig = px.bar(c, x="margin", y="category", orientation="h", title="Gross margin by category",
                 labels={"margin": "", "category": ""}, custom_data=["gp"])
    fig.update_traces(marker_color=SERIES[2], hovertemplate="%{y}<br>Margin %{x:.1%}<br>Gross profit RM%{customdata[0]:,.0f}<extra></extra>")
    fig.update_layout(height=400, xaxis_tickformat=".0%")
    st.plotly_chart(bar_style(fig), width="stretch")
    lo, hi = c.iloc[0], c.iloc[-1]
    insight(f"<b>{lo.category}</b> sells a lot but earns only {lo.margin:.0%} margin - it brings customers in. "
            f"<b>{hi.category}</b> earns {hi.margin:.0%}; place it near the counter for impulse buys.")

    # slow movers
    st.subheader("Slow movers")
    as_of = D["sales"].date.max()
    last_sale = D["sales"].groupby("product_id").date.max()
    inv = D["inventory"].set_index("product_id").stock_on_hand
    sm = D["products"][["product_id", "product_name", "category", "cost_price_rm"]].copy()
    sm["days_since_last_sale"] = (as_of - sm.product_id.map(last_sale)).dt.days
    sm["stock_on_hand"] = sm.product_id.map(inv)
    sm["stock_value_rm"] = (sm.stock_on_hand * sm.cost_price_rm).round(2)
    days = st.slider("Flag products with no sale in the last ... days", 7, 120, 30)
    out = sm[sm.days_since_last_sale >= days].sort_values("stock_value_rm", ascending=False)
    if out.empty:
        st.success(f"Every product sold at least once in the last {days} days.")
    else:
        st.dataframe(out.drop(columns="cost_price_rm"), hide_index=True, width="stretch",
                     column_config={"stock_value_rm": st.column_config.NumberColumn("Stock value", format="RM %.2f")})
        insight(f"{len(out)} products have not sold in {days}+ days, holding {rm(out.stock_value_rm.sum())} "
                "of stock at cost. Clear seasonal leftovers with a bundle or discount; stop reordering the rest.")
