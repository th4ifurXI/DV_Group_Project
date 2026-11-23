import plotly.express as px
import streamlit as st

from core.data import filter_frame, previous_period
from core.style import (CONTEXT, HIGHLIGHT, PRIMARY, SERIES, add_event_bands, highlight_colours, insight,
                        money_axis, pct_delta, plot, rm, rm_short, selected)

PAY_ORDER = ["Cash", "DuitNow QR", "Touch 'n Go eWallet", "Debit Card", "Credit Card"]


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s_all = filter_frame(D["sales"], F)
    st.title("📊 Executive Overview")
    st.caption("How is the shop doing? KPI changes compare against the same-length period just before.")
    if s_all.empty:
        st.warning("No sales in this selection.")
        return

    # L4 linked views: a click on the category chart filters every other chart on this page
    pick = selected("ov_cat")
    if pick not in set(s_all.category):
        pick = None
    s = s_all[s_all.category == pick] if pick else s_all
    pf = dict(F, categories=[pick]) if pick else F
    p = previous_period(D["sales"], pf)
    if pick:
        st.info(f"Linked view: showing **{pick}** only. Double-click the category chart to clear.")

    def kpis(df):
        inv = df.invoice_no.nunique()
        rev = df.line_total_rm.sum()
        return dict(rev=rev, inv=inv, basket=rev / inv if inv else 0,
                    gp=df.gross_profit_rm.sum(), margin=df.gross_profit_rm.sum() / rev if rev else 0,
                    members=df.customer_id.nunique())

    k, kp = kpis(s), kpis(p) if not p.empty else None
    c = st.columns(5)
    c[0].metric("Net revenue", rm_short(k["rev"]), pct_delta(k["rev"], kp and kp["rev"]))
    c[1].metric("Transactions", f"{k['inv']:,}", pct_delta(k["inv"], kp and kp["inv"]))
    c[2].metric("Avg basket", rm(k["basket"], 2), pct_delta(k["basket"], kp and kp["basket"]))
    c[3].metric("Gross profit", rm_short(k["gp"]), pct_delta(k["gp"], kp and kp["gp"]),
                help=f"Gross margin {k['margin']:.1%}")
    c[4].metric("Active members", f"{k['members']:,}", pct_delta(k["members"], kp and kp["members"]))

    # revenue trend with the best period highlighted (L3 pre-attentive attribute)
    days = (F["end"] - F["start"]).days
    freq = "D" if days <= 92 else ("W-MON" if days <= 200 else "MS")
    label = {"D": "Daily", "W-MON": "Weekly", "MS": "Monthly"}[freq]
    t = s.set_index("date").line_total_rm.resample(freq).sum().reset_index()
    best = t.loc[t.line_total_rm.idxmax()]
    fig = px.line(t, x="date", y="line_total_rm", title=f"{label} revenue{' - ' + pick if pick else ''}",
                  labels={"date": "Month" if freq == "MS" else "Date", "line_total_rm": "Revenue"},
                  markers=freq == "MS")
    fig.update_traces(line_width=2, line_color=PRIMARY, marker_color=PRIMARY,
                      hovertemplate="%{x|%d %b %Y}<br>RM%{y:,.0f}<extra></extra>")
    fig.add_scatter(x=[best.date], y=[best.line_total_rm], mode="markers+text", showlegend=False,
                    marker=dict(size=12, color=HIGHLIGHT, line=dict(color="white", width=2)),
                    text=[f"Peak {rm_short(best.line_total_rm)}"], textposition="middle right",
                    textfont=dict(color=HIGHLIGHT, size=12), hoverinfo="skip")
    fig.update_layout(hovermode="x unified", height=360)
    money_axis(fig, "y")
    add_event_bands(fig, D["calendar"], F["start"], F["end"])
    plot(fig)
    if freq == "MS" and len(t) > 3:
        insight(f"Peak month: <b>{best.date:%b %Y}</b> at {rm(best.line_total_rm)}, "
                f"{best.line_total_rm / t.line_total_rm.median() - 1:+.0%} vs a typical month. "
                "Shaded bands mark festive seasons - plan stock 2-3 weeks ahead of them.")

    a, b = st.columns(2)
    cat = s_all.groupby("category", as_index=False).agg(rev=("line_total_rm", "sum"), gp=("gross_profit_rm", "sum"))
    cat["share"] = cat.rev / cat.rev.sum()
    cat = cat.sort_values("rev")
    top = cat.iloc[-1]
    fig = px.bar(cat, x="rev", y="category", orientation="h", title="Revenue by category (click a bar to filter)",
                 labels={"rev": "Revenue", "category": ""}, custom_data=["share", "gp"],
                 text=[rm_short(v) for v in cat.rev])
    fig.update_traces(marker_color=highlight_colours(cat.category, pick or top.category),
                      textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>RM%{x:,.0f} (%{customdata[0]:.1%})"
                                    "<br>Gross profit RM%{customdata[1]:,.0f}<extra></extra>")
    fig.update_layout(height=470, xaxis_range=[0, cat.rev.max() * 1.18])
    money_axis(fig, "x")
    plot(fig, a, on_select="rerun", selection_mode="points", key="ov_cat")

    inv = s.drop_duplicates("invoice_no")
    pay = inv.groupby(["month", "payment_method"]).size().reset_index(name="n")
    pay["share"] = pay.n / pay.groupby("month").n.transform("sum")
    fig = px.bar(pay, x="month", y="share", color="payment_method",
                 title=f"Payment method share of transactions{' - ' + pick if pick else ''}",
                 category_orders={"payment_method": PAY_ORDER}, color_discrete_sequence=SERIES,
                 labels={"month": "Month", "share": "Share of transactions", "payment_method": ""})
    fig.update_traces(marker_line_color="white", marker_line_width=1,
                      hovertemplate="%{x|%b %Y}<br>%{fullData.name}: %{y:.0%}<extra></extra>")
    fig.update_layout(height=470, yaxis_tickformat=".0%", bargap=0.15,
                      legend=dict(orientation="h", yanchor="top", y=-0.15, x=0))
    plot(fig, b)

    cash = pay[pay.payment_method == "Cash"].sort_values("month")
    msg = f"<b>{top.category}</b> brings in {top.share:.0%} of revenue (highlighted)."
    if len(cash) > 2:
        msg += (f" Cash fell from {cash.share.iloc[0]:.0%} to {cash.share.iloc[-1]:.0%} of transactions - "
                "keep QR and e-wallet terminals reliable at every counter.")
    insight(msg)
