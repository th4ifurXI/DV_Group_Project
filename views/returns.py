import plotly.express as px
import streamlit as st

from core.data import filter_frame
from core.style import SERIES, bar_style, insight, rm


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    r = filter_frame(D["returns"], F)
    st.title("↩️ Returns & Losses")
    st.caption("Where are we losing money after the sale?")
    if s.empty:
        st.warning("No sales in this selection.")
        return

    lost = -r.line_total_rm.sum()
    c = st.columns(3)
    c[0].metric("Value refunded", rm(lost))
    c[1].metric("Return rate (value)", f"{lost / s.line_total_rm.sum():.2%}")
    c[2].metric("Return transactions", f"{r.invoice_no.nunique():,}")
    if r.empty:
        st.success("No returns in this selection.")
        return

    a, b = st.columns(2)
    m = r.groupby("month").line_total_rm.sum().abs().reset_index()
    fig = px.bar(m, x="month", y="line_total_rm", title="Value refunded per month (RM)",
                 labels={"month": "", "line_total_rm": ""})
    fig.update_traces(marker_color=SERIES[1], hovertemplate="%{x|%b %Y}<br>RM%{y:,.0f}<extra></extra>")
    fig.update_layout(height=360)
    a.plotly_chart(bar_style(fig), width="stretch")

    why = r.groupby("return_reason").line_total_rm.sum().abs().sort_values().reset_index()
    fig = px.bar(why, x="line_total_rm", y="return_reason", orientation="h", title="Refunds by reason (RM)",
                 labels={"line_total_rm": "", "return_reason": ""})
    fig.update_traces(marker_color=SERIES[1], hovertemplate="%{y}<br>RM%{x:,.0f}<extra></extra>")
    fig.update_layout(height=360)
    b.plotly_chart(bar_style(fig), width="stretch")

    sold = s.groupby(["product_id", "product_name", "category"]).quantity.sum()
    back = r.groupby(["product_id", "product_name", "category"]).quantity.sum().abs()
    t = (back / sold).dropna().rename("return_rate").to_frame()
    t["units_returned"] = back
    t["value_refunded"] = r.groupby(["product_id", "product_name", "category"]).line_total_rm.sum().abs()
    t["main_reason"] = r.groupby(["product_id", "product_name", "category"]).return_reason.agg(lambda x: x.mode().iat[0])
    t = t.reset_index().sort_values("value_refunded", ascending=False)
    st.subheader("Most-returned products")
    st.dataframe(t.head(15).drop(columns="product_id"), hide_index=True, width="stretch",
                 column_config={"return_rate": st.column_config.ProgressColumn(
                                    "Return rate", format="percent", min_value=0, max_value=float(t.return_rate.max())),
                                "value_refunded": st.column_config.NumberColumn("Value refunded", format="RM %.2f")})
    top_reason = why.iloc[-1]
    perish = r[r.category.isin(["Dairy & Eggs", "Bakery", "Fresh Produce", "Frozen Food"])].line_total_rm.sum()
    insight(f"Top reason: <b>{top_reason.return_reason}</b> ({rm(top_reason.line_total_rm)}). "
            f"Perishables account for {perish / r.line_total_rm.sum():.0%} of refunds - order them in smaller, "
            "more frequent batches and rotate stock first-in-first-out.")
