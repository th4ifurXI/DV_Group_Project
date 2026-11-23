import plotly.express as px
import streamlit as st

from core.data import filter_frame
from core.style import CONTEXT, PRIMARY, highlight_colours, insight, money_axis, plot, rm, selected

PERISHABLE = ["Dairy & Eggs", "Bakery", "Fresh Produce", "Frozen Food"]


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    r_all = filter_frame(D["returns"], F)
    st.title("↩️ Returns & Losses")
    st.caption("Where are we losing money after the sale?")
    if s.empty:
        st.warning("No sales in this selection.")
        return

    lost = -r_all.line_total_rm.sum()
    c = st.columns(3)
    c[0].metric("Value refunded", rm(lost))
    c[1].metric("Return rate (value)", f"{lost / s.line_total_rm.sum():.2%}")
    c[2].metric("Return transactions", f"{r_all.invoice_no.nunique():,}")
    if r_all.empty:
        st.success("No returns in this selection.")
        return

    # L4 linked views: click a reason to filter the monthly chart and the product table
    why = r_all.groupby("return_reason").line_total_rm.sum().abs().sort_values().reset_index()
    pick = selected("rt_reason")
    if pick not in set(why.return_reason):
        pick = None
    r = r_all[r_all.return_reason == pick] if pick else r_all
    st.caption("Click a reason to filter the monthly chart and product table (linked views). Double-click to clear.")

    a, b = st.columns(2)
    fig = px.bar(why, x="line_total_rm", y="return_reason", orientation="h", title="Refunds by reason",
                 labels={"line_total_rm": "Value refunded", "return_reason": ""},
                 text=[rm(v) for v in why.line_total_rm])
    fig.update_traces(marker_color=highlight_colours(why.return_reason, pick or why.return_reason.iloc[-1]),
                      textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>RM%{x:,.0f}<extra></extra>")
    fig.update_layout(height=380, xaxis_range=[0, why.line_total_rm.max() * 1.25])
    money_axis(fig, "x")
    plot(fig, a, on_select="rerun", selection_mode="points", key="rt_reason")

    m = r.groupby("month").line_total_rm.sum().abs().reset_index()
    fig = px.bar(m, x="month", y="line_total_rm", title=f"Value refunded per month{' - ' + pick if pick else ''}",
                 labels={"month": "Month", "line_total_rm": "Value refunded"})
    fig.update_traces(marker_color=PRIMARY, hovertemplate="%{x|%b %Y}<br>RM%{y:,.0f}<extra></extra>")
    fig.update_layout(height=380)
    money_axis(fig, "y")
    plot(fig, b)

    keys = ["product_id", "product_name", "category"]
    sold = s.groupby(keys).quantity.sum()
    back = r.groupby(keys).quantity.sum().abs()
    t = (back / sold).dropna().rename("return_rate").to_frame()
    t["units_returned"] = back
    t["value_refunded"] = r.groupby(keys).line_total_rm.sum().abs()
    t["main_reason"] = r.groupby(keys).return_reason.agg(lambda x: x.mode().iat[0])
    t = t.reset_index().sort_values("value_refunded", ascending=False)
    st.subheader(f"Most-returned products{' - ' + pick if pick else ''}")
    st.dataframe(t.head(15).drop(columns="product_id"), hide_index=True, width="stretch",
                 column_config={"return_rate": st.column_config.ProgressColumn(
                                    "Return rate", format="percent", min_value=0, max_value=float(t.return_rate.max())),
                                "units_returned": st.column_config.NumberColumn("Units returned"),
                                "value_refunded": st.column_config.NumberColumn("Value refunded", format="RM %.2f")})
    top_reason = why.iloc[-1]
    perish = r_all[r_all.category.isin(PERISHABLE)].line_total_rm.sum()
    insight(f"Top reason (highlighted): <b>{top_reason.return_reason}</b> ({rm(top_reason.line_total_rm)}). "
            f"Perishables account for {perish / r_all.line_total_rm.sum():.0%} of refunds - order them in smaller, "
            "more frequent batches and rotate stock first-in-first-out.")
