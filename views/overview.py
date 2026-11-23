import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import filter_frame, previous_period
from core.style import SERIES, add_event_bands, bar_style, insight, pct_delta, rm, rm_short


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    p = previous_period(D["sales"], F)
    st.title("📊 Executive Overview")
    st.caption("How is the shop doing? Figures compare against the same-length period just before.")
    if s.empty:
        st.warning("No sales in this selection.")
        return

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

    # revenue trend
    days = (F["end"] - F["start"]).days
    freq = "D" if days <= 92 else ("W-MON" if days <= 200 else "MS")
    label = {"D": "Daily", "W-MON": "Weekly", "MS": "Monthly"}[freq]
    t = s.set_index("date").line_total_rm.resample(freq).sum().reset_index()
    fig = px.line(t, x="date", y="line_total_rm", title=f"{label} revenue (RM)",
                  labels={"date": "", "line_total_rm": "Revenue (RM)"}, markers=freq == "MS")
    fig.update_traces(line_width=2, line_color=SERIES[0], hovertemplate="%{x|%d %b %Y}<br>RM%{y:,.0f}")
    fig.update_layout(hovermode="x unified", height=340)
    add_event_bands(fig, D["calendar"], F["start"], F["end"])
    st.plotly_chart(fig, width="stretch")
    st.caption("Shaded bands: Ramadan, Hari Raya, Chinese New Year and Hari Raya Haji.")
    if freq == "MS" and len(t) > 3:
        best = t.loc[t.line_total_rm.idxmax()]
        insight(f"Best month: <b>{best.date:%b %Y}</b> at {rm(best.line_total_rm)}, "
                f"{best.line_total_rm / t.line_total_rm.median() - 1:+.0%} vs a typical month. "
                "Shaded bands mark festive seasons - plan stock 2-3 weeks ahead of them.")

    a, b = st.columns(2)
    cat = s.groupby("category", as_index=False).agg(rev=("line_total_rm", "sum"), gp=("gross_profit_rm", "sum"))
    cat["share"] = cat.rev / cat.rev.sum()
    cat = cat.sort_values("rev")
    fig = px.bar(cat, x="rev", y="category", orientation="h", title="Revenue by category (RM)",
                 labels={"rev": "", "category": ""}, custom_data=["share", "gp"])
    fig.update_traces(marker_color=SERIES[0], hovertemplate="%{y}<br>RM%{x:,.0f} (%{customdata[0]:.1%})"
                                                          "<br>Gross profit RM%{customdata[1]:,.0f}<extra></extra>")
    fig.update_layout(height=430)
    a.plotly_chart(bar_style(fig), width="stretch")

    pay = s.drop_duplicates("invoice_no").groupby(["month", "payment_method"]).size().reset_index(name="n")
    pay["share"] = pay.n / pay.groupby("month").n.transform("sum")
    order = ["Cash", "DuitNow QR", "Touch 'n Go eWallet", "Debit Card", "Credit Card"]
    fig = px.bar(pay, x="month", y="share", color="payment_method", title="Payment method share of transactions",
                 category_orders={"payment_method": order}, color_discrete_sequence=SERIES,
                 labels={"month": "", "share": "", "payment_method": ""})
    fig.update_traces(marker_line_color="white", marker_line_width=1,
                      hovertemplate="%{x|%b %Y}<br>%{fullData.name}: %{y:.0%}<extra></extra>")
    fig.update_layout(height=430, yaxis_tickformat=".0%", bargap=0.15,
                      legend=dict(orientation="h", yanchor="top", y=-0.08, x=0))
    b.plotly_chart(fig, width="stretch")

    top = cat.iloc[-1]
    cash = pay[pay.payment_method == "Cash"].sort_values("month")
    msg = f"<b>{top.category}</b> brings in {top.share:.0%} of revenue."
    if len(cash) > 2:
        msg += (f" Cash fell from {cash.share.iloc[0]:.0%} to {cash.share.iloc[-1]:.0%} of transactions - "
                "keep QR and e-wallet terminals reliable at every counter.")
    insight(msg)
