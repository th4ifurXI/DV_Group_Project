import numpy as np
import plotly.express as px
import streamlit as st

from core.data import filter_frame
from core import style
from core.style import (AXIS, CONTEXT, HIGHLIGHT, MUTED, PRIMARY, SERIES, highlight_colours, insight, money_axis,
                        plot, rm, rm_short)

# 13 categories are too many colours (L2 #8 data density), so they are grouped into 4 roles
GROUP = {
    "Rice & Grains": "Staples", "Cooking Essentials": "Staples", "Dairy & Eggs": "Staples",
    "Fresh Produce": "Staples", "Bakery": "Staples",
    "Instant Food": "Convenience", "Beverages": "Convenience", "Snacks & Confectionery": "Convenience",
    "Frozen Food": "Convenience",
    "Household": "Non-food", "Personal Care": "Non-food", "Stationery & Student": "Non-food",
    "Festive & Seasonal": "Seasonal",
}
GROUP_ORDER = ["Staples", "Convenience", "Non-food", "Seasonal"]


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
    g["group"] = g.category.map(GROUP)

    names = {"revenue": "Revenue", "gross_profit": "Gross profit", "units": "Units sold"}
    has_cost = D["products"].cost_price_rm.notna().any()
    if not has_cost:
        names.pop("gross_profit")
    metric = st.segmented_control("Rank by", list(names), default="revenue", format_func=names.get) or "revenue"
    money = metric != "units"

    a, b = st.columns(2)
    for col, title, data, colour in [(a, "Top 10", g.nlargest(10, metric), PRIMARY),
                                     (b, "Bottom 10", g.nsmallest(10, metric), CONTEXT)]:
        d = data.sort_values(metric)
        fig = px.bar(d, x=metric, y="product_name", orientation="h", title=f"{title} products by {names[metric].lower()}",
                     labels={metric: names[metric] + (f" ({style.CUR})" if money else ""), "product_name": ""},
                     custom_data=["category"],
                     text=[rm_short(v) if money else f"{v:,.0f}" for v in d[metric]])
        fig.update_traces(marker_color=colour, textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>%{customdata[0]}<br>%{x:,.0f}<extra></extra>")
        fig.update_layout(height=420, xaxis_range=[0, d[metric].max() * 1.22])
        if money:
            money_axis(fig, "x")
        plot(fig, col)

    if has_cost:
        _portfolio(g)
    _pareto(g)
    if has_cost:
        _margin_by_category(s)
    else:
        st.info("This file has no cost prices, so the margin charts are hidden.")
    if D["inventory"].empty:
        st.info("This file has no stock counts, so the slow-mover table is hidden.")
    else:
        _slow_movers(D)


def _portfolio(g):
    # L5 multivariate scatter: 4 variables in one view (revenue, margin, units = size, role = colour)
    st.subheader("Product portfolio: revenue vs margin")
    mx, my = g.revenue.median(), g.margin.median()
    # scatter = all colour pairs compared at once, so only 3 hues + grey for the small seasonal group
    fig = px.scatter(g, x="revenue", y="margin", size="units", color="group", size_max=34,
                     category_orders={"group": GROUP_ORDER},
                     color_discrete_map={"Staples": SERIES[0], "Convenience": SERIES[1], "Non-food": SERIES[2],
                                         "Seasonal": MUTED},
                     hover_name="product_name", custom_data=["category", "units"],
                     title="Each bubble is a product · bubble size = units sold · colour = product role",
                     labels={"revenue": "Revenue (RM)", "margin": "Gross margin", "group": ""})
    fig.update_traces(marker=dict(line=dict(color="white", width=1), opacity=0.85),
                      hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}<br>Revenue RM%{x:,.0f}"
                                    "<br>Margin %{y:.0%}<br>%{customdata[1]:,.0f} units<extra></extra>")
    fig.add_vline(x=mx, line_dash="dot", line_color=AXIS)
    fig.add_hline(y=my, line_dash="dot", line_color=AXIS)
    for x, y, txt, xa in [(1, 1, "Stars: high sales, high margin", "right"),
                          (0, 1, "Niche profit: promote more", "left"),
                          (1, 0, "Traffic builders: keep in stock", "right"),
                          (0, 0, "Review: low sales, low margin", "left")]:
        fig.add_annotation(xref="paper", yref="paper", x=x, y=y, text=txt, showarrow=False, xanchor=xa,
                           yanchor="top" if y else "bottom", font=dict(size=11, color=MUTED))
    fig.update_layout(height=480, yaxis_tickformat=".0%", xaxis_type="log",
                      legend=dict(orientation="h", yanchor="top", y=-0.12, x=0))
    ticks = [v for v in [1e3, 3e3, 1e4, 3e4, 1e5, 3e5] if g.revenue.min() / 2 <= v <= g.revenue.max() * 2]
    fig.update_xaxes(tickvals=ticks, ticktext=[rm_short(v) for v in ticks])
    plot(fig)
    stars = g[(g.revenue >= mx) & (g.margin >= my)].nlargest(3, "revenue").product_name.tolist()
    insight(f"Dotted lines are the medians. Stars such as <b>{', '.join(stars)}</b> deserve the best shelf space; "
            "products in the bottom-left are candidates to drop. Revenue is on a log scale so small products stay visible.")



def _pareto(g):
    p = g.sort_values("revenue", ascending=False).reset_index(drop=True)
    p["cum_share"] = p.revenue.cumsum() / p.revenue.sum()
    p["product_share"] = (np.arange(len(p)) + 1) / len(p)
    n80 = int((p.cum_share < 0.8).sum() + 1)
    fig = px.area(p, x="product_share", y="cum_share", title="Pareto: share of revenue from top products",
                  labels={"product_share": "Share of products (ranked by revenue)", "cum_share": "Cumulative share of revenue"},
                  custom_data=["product_name"])
    fig.update_traces(line_color=PRIMARY, line_width=2, fillcolor="rgba(42,120,214,0.12)",
                      hovertemplate="Top %{x:.0%} of products<br>= %{y:.0%} of revenue<extra></extra>")
    fig.add_hline(y=0.8, line_dash="dot", line_color=AXIS)
    fig.add_scatter(x=[n80 / len(p)], y=[0.8], mode="markers+text", showlegend=False, hoverinfo="skip",
                    marker=dict(size=11, color=HIGHLIGHT, line=dict(color="white", width=2)),
                    text=[f"  {n80} products = 80% of revenue"], textposition="middle right",
                    textfont=dict(color=HIGHLIGHT, size=12))
    fig.update_layout(height=340, xaxis_tickformat=".0%", yaxis_tickformat=".0%", yaxis_range=[0, 1.02])
    plot(fig)
    insight(f"<b>{n80} of {len(p)} products ({n80 / len(p):.0%})</b> make 80% of revenue. "
            "These are the 'A' items - never let them run out.")



def _margin_by_category(s):
    # margin by category, direct labels instead of reading the axis (L2 #3)
    c = s.groupby("category", as_index=False).agg(rev=("line_total_rm", "sum"), gp=("gross_profit_rm", "sum"))
    c["margin"] = c.gp / c.rev
    c = c.sort_values("margin")
    lo, hi = c.iloc[0], c.iloc[-1]
    fig = px.bar(c, x="margin", y="category", orientation="h", title="Gross margin by category",
                 labels={"margin": "Gross margin", "category": ""}, custom_data=["gp"],
                 text=[f"{v:.0%}" for v in c.margin])
    fig.update_traces(marker_color=highlight_colours(c.category, [lo.category, hi.category]),
                      textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>Margin %{x:.1%}<br>Gross profit RM%{customdata[0]:,.0f}<extra></extra>")
    fig.update_layout(height=420, xaxis_tickformat=".0%", xaxis_range=[0, c.margin.max() * 1.15])
    plot(fig)
    insight(f"Highlighted: lowest and highest margin. <b>{lo.category}</b> earns only {lo.margin:.0%} - it brings customers in. "
            f"<b>{hi.category}</b> earns {hi.margin:.0%}; place it near the counter for impulse buys.")



def _slow_movers(D):
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
                     column_config={"stock_value_rm": st.column_config.NumberColumn("Stock value", format=style.money_fmt())})
        insight(f"{len(out)} products have not sold in {days}+ days, holding {rm(out.stock_value_rm.sum())} "
                "of stock at cost. Clear seasonal leftovers with a bundle or discount; stop reordering the rest.")
