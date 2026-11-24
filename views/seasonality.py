import pandas as pd
import plotly.express as px
import streamlit as st

from core import style
from core.data import filter_frame
from core.style import (CONTEXT, EVENT_TINT, HIGHLIGHT, PRIMARY, SEQ, SERIES, add_event_bands, highlight_colours,
                        insight, money_axis, plot, rm_short)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def in_events(dates, cal, name=None, etype=None):
    m = pd.Series(False, index=dates.index)
    c = cal
    if name:
        c = c[c.event == name]
    if etype:
        c = c[c.event_type == etype]
    for _, e in c.iterrows():
        m |= (dates >= e.start_date) & (dates <= e.end_date)
    return m


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    cal = D["calendar"]
    st.title("📅 Seasonality & Timing")
    st.caption("When should we prepare stock and staff?")
    if s.empty:
        st.warning("No sales in this selection.")
        return

    # L5 heatmap with the peak cell outlined (L3 pre-attentive)
    inv = s.drop_duplicates("invoice_no")
    n_days = inv.groupby("weekday").date.nunique()
    h = inv.groupby(["weekday", "hour"]).size().unstack(fill_value=0).reindex(DAYS)
    h = h.div(n_days.reindex(DAYS), axis=0)
    peak, quiet = h.stack().idxmax(), h.stack().idxmin()
    fig = px.imshow(h, aspect="auto", color_continuous_scale=SEQ, text_auto=".0f",
                    labels=dict(x="Hour of day", y="Day of week", color="Avg transactions"),
                    title="Average transactions per hour (darker = busier; outlined = busiest slot)")
    fig.update_traces(hovertemplate="%{y} %{x}:00<br>%{z:.1f} transactions on average<extra></extra>")
    cols = list(h.columns)
    yi = DAYS.index(peak[0])
    fig.add_shape(type="rect", x0=peak[1] - 0.5, x1=peak[1] + 0.5, y0=yi - 0.5, y1=yi + 0.5,
                  line=dict(color=HIGHLIGHT, width=3))
    fig.update_layout(height=400, coloraxis_showscale=False)
    fig.update_xaxes(tickvals=cols, ticktext=[f"{x}:00" for x in cols])
    plot(fig)
    part = lambda hr: "morning" if hr < 12 else ("afternoon" if hr < 17 else "evening")
    insight(f"Busiest slot: <b>{peak[0]} {peak[1]}:00</b>. Quietest: {quiet[0]} {quiet[1]}:00. "
            f"Roster an extra cashier for the {part(peak[1])} peak and restock during the quietest hours.")

    daily = s.groupby("date").line_total_rm.sum().reset_index()
    daily["7-day average"] = daily.line_total_rm.rolling(7, min_periods=1).mean()
    fig = px.line(daily, x="date", y="7-day average", title="Daily revenue, 7-day average",
                  labels={"date": "Date", "7-day average": "Revenue per day"})
    fig.update_traces(line_color=PRIMARY, line_width=2, hovertemplate="%{x|%d %b %Y}<br>RM%{y:,.0f} per day<extra></extra>")
    fig.update_layout(height=340, hovermode="x unified")
    money_axis(fig, "y")
    add_event_bands(fig, cal, F["start"], F["end"])
    add_event_bands(fig, cal.assign(event=""), F["start"], F["end"], types=("Semester break",), min_days=1)
    plot(fig)
    if not cal.empty:
        st.caption("Shaded bands: festive seasons (Ramadan labelled) and UTP semester breaks (unlabelled).")

    if cal.empty:
        st.info("No festive or term-break calendar for this file, so the period comparison is hidden.")
    else:
        _periods(s, daily, cal)
    if s.category.nunique() > 1:
        _small_multiples(s, cal, F)


def _periods(s, daily, cal):
    # period comparison + Ramadan category change
    daily["period"] = "Normal day"
    daily.loc[in_events(daily.date, cal, etype="Semester break"), "period"] = "UTP semester break"
    daily.loc[in_events(daily.date, cal, name="Ramadan"), "period"] = "Ramadan"
    daily.loc[in_events(daily.date, cal, name="Hari Raya Aidilfitri"), "period"] = "Hari Raya week"
    comp = daily.groupby("period").line_total_rm.mean().reindex(
        ["Normal day", "Ramadan", "Hari Raya week", "UTP semester break"]).dropna().reset_index()
    base = comp.set_index("period").line_total_rm.get("Normal day")
    a, b = st.columns(2)
    fig = px.bar(comp, x="period", y="line_total_rm", title="Average revenue per day by period",
                 labels={"period": "Period", "line_total_rm": "Revenue per day"},
                 text=[rm_short(v) for v in comp.line_total_rm])
    fig.update_traces(marker_color=highlight_colours(comp.period, "Ramadan"), textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}<br>RM%{y:,.0f} per day<extra></extra>")
    fig.update_layout(height=380, yaxis_range=[0, comp.line_total_rm.max() * 1.18])
    money_axis(fig, "y")
    plot(fig, a)

    sd = s.copy()
    sd["is_ramadan"] = in_events(sd.date, cal, name="Ramadan")
    msg = ""
    if sd.is_ramadan.any() and (~sd.is_ramadan).any():
        nd = sd.groupby("is_ramadan").date.nunique()
        cr = sd.groupby(["category", "is_ramadan"]).line_total_rm.sum().unstack(fill_value=0)
        cr = cr.div(nd, axis=1)
        cr["lift"] = cr[True] / cr[False] - 1
        cr = cr.drop(index="Festive & Seasonal", errors="ignore").sort_values("lift").reset_index()
        fig = px.bar(cr, x="lift", y="category", orientation="h", title="Daily sales change during Ramadan vs other days",
                     labels={"lift": "Change in daily sales", "category": ""}, text=[f"{v:+.0%}" for v in cr.lift])
        # diverging: orange = sells more, blue = sells less (polarity, not identity)
        fig.update_traces(marker_color=[HIGHLIGHT if v > 0 else PRIMARY for v in cr.lift], textposition="outside",
                          cliponaxis=False, hovertemplate="%{y}<br>%{x:+.0%}<extra></extra>")
        lim = cr.lift.abs().max() * 1.3
        fig.update_layout(height=380, xaxis_tickformat="+.0%", xaxis_range=[-lim, lim])
        plot(fig, b)
        up = cr.iloc[-1]
        msg = (f"During Ramadan, <b>{up.category}</b> sells {up.lift:+.0%} per day vs other days "
               "(festive items like kurma and kuih raya sell almost only in Ramadan, so they are left out).")
    else:
        b.info("Select a period that includes Ramadan to see which categories move.")
    brk = comp.set_index("period").line_total_rm.get("UTP semester break")
    if base and brk:
        msg += f" During UTP semester breaks daily revenue is {brk / base - 1:+.0%} vs normal - order less student stock."
    if msg:
        insight(msg)



def _small_multiples(s, cal, F):
    # L2 #9 / L5 trellis: small multiples on one shared scale
    st.subheader("Monthly revenue by category (small multiples)")
    mc = s.pivot_table(index="month", columns="category", values="line_total_rm", aggfunc="sum").fillna(0)
    mc = mc.stack().rename("line_total_rm").reset_index()  # months with no sales count as RM0, not a gap
    order = mc.groupby("category").line_total_rm.sum().sort_values(ascending=False).index.tolist()
    fig = px.line(mc, x="month", y="line_total_rm", facet_col="category", facet_col_wrap=4,
                  category_orders={"category": order}, facet_row_spacing=0.09, facet_col_spacing=0.04,
                  labels={"month": "", "line_total_rm": "Revenue"},
                  title="Same scale in every panel so categories can be compared directly")
    fig.update_traces(line_color=PRIMARY, line_width=1.8,
                      hovertemplate="%{x|%b %Y}<br>RM%{y:,.0f}<extra></extra>")
    fig.for_each_annotation(lambda an: an.update(text=an.text.split("=")[-1], font=dict(size=12)))
    fig.update_yaxes(tickprefix=style.CUR, tickformat="~s", title_text="")
    fig.update_xaxes(tickformat="%b %y", nticks=4, title_text="")
    for _, e in cal[cal.event == "Ramadan"].iterrows():
        if e.end_date >= F["start"] and e.start_date <= F["end"]:
            fig.add_vrect(x0=e.start_date, x1=e.end_date, fillcolor=EVENT_TINT, line_width=0, layer="below",
                          row="all", col="all")
    fig.update_layout(height=760)
    plot(fig)
    insight("Each panel is one category on the same RM scale (shaded = Ramadan). Staples like rice stay flat and high, "
            "while festive items spike only around Ramadan - order them just in time.")
