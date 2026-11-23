import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import filter_frame
from core.style import SEQ, SERIES, add_event_bands, bar_style, insight, rm

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

    inv = s.drop_duplicates("invoice_no")
    n_days = inv.groupby("weekday").date.nunique()
    h = inv.groupby(["weekday", "hour"]).size().unstack(fill_value=0).reindex(DAYS)
    h = h.div(n_days.reindex(DAYS), axis=0)
    fig = px.imshow(h, aspect="auto", color_continuous_scale=SEQ, text_auto=".0f",
                    labels=dict(x="Hour of day", y="", color="Avg transactions"),
                    title="Average transactions per hour")
    fig.update_traces(hovertemplate="%{y} %{x}:00<br>%{z:.1f} transactions on average<extra></extra>")
    fig.update_layout(height=380, coloraxis_showscale=False)
    fig.update_xaxes(tickvals=list(h.columns), ticktext=[f"{x}:00" for x in h.columns])
    st.plotly_chart(fig, width="stretch")
    peak = h.stack().idxmax()
    quiet = h.stack().idxmin()
    insight(f"Busiest slot: <b>{peak[0]} {peak[1]}:00</b>. Quietest: {quiet[0]} {quiet[1]}:00. "
            "Roster two cashiers for the evening peak and schedule restocking in the quiet morning slots.")

    daily = s.groupby("date").line_total_rm.sum().reset_index()
    daily["7-day average"] = daily.line_total_rm.rolling(7, min_periods=1).mean()
    fig = px.line(daily, x="date", y="7-day average", title="Daily revenue, 7-day average (RM)",
                  labels={"date": "", "7-day average": "Revenue (RM)"})
    fig.update_traces(line_color=SERIES[0], line_width=2, hovertemplate="%{x|%d %b %Y}<br>RM%{y:,.0f} per day<extra></extra>")
    fig.update_layout(height=340, hovermode="x unified")
    add_event_bands(fig, cal, F["start"], F["end"])
    add_event_bands(fig, cal.assign(event=""), F["start"], F["end"], types=("Semester break",), min_days=1)
    st.plotly_chart(fig, width="stretch")
    st.caption("Shaded bands: festive seasons (Ramadan labelled) and UTP semester breaks (unlabelled).")

    # period comparison
    daily["period"] = "Normal day"
    daily.loc[in_events(daily.date, cal, etype="Semester break"), "period"] = "UTP semester break"
    daily.loc[in_events(daily.date, cal, name="Ramadan"), "period"] = "Ramadan"
    daily.loc[in_events(daily.date, cal, name="Hari Raya Aidilfitri"), "period"] = "Hari Raya week"
    comp = daily.groupby("period").line_total_rm.mean().reindex(
        ["Normal day", "Ramadan", "Hari Raya week", "UTP semester break"]).dropna().reset_index()
    base = comp.set_index("period").line_total_rm.get("Normal day")
    a, b = st.columns(2)
    fig = px.bar(comp, x="period", y="line_total_rm", title="Average revenue per day by period (RM)",
                 labels={"period": "", "line_total_rm": ""})
    fig.update_traces(marker_color=SERIES[0], hovertemplate="%{x}<br>RM%{y:,.0f} per day<extra></extra>")
    fig.update_layout(height=360)
    a.plotly_chart(bar_style(fig), width="stretch")

    # which categories move during Ramadan
    sd = s.copy()
    sd["is_ramadan"] = in_events(sd.date, cal, name="Ramadan")
    if sd.is_ramadan.any() and (~sd.is_ramadan).any():
        nd = sd.groupby("is_ramadan").date.nunique()
        cr = sd.groupby(["category", "is_ramadan"]).line_total_rm.sum().unstack(fill_value=0)
        cr = cr.div(nd, axis=1)
        cr["lift"] = cr[True] / cr[False] - 1
        cr = cr.drop(index="Festive & Seasonal", errors="ignore").sort_values("lift").reset_index()
        fig = px.bar(cr, x="lift", y="category", orientation="h", title="Daily sales change during Ramadan vs other days",
                     labels={"lift": "", "category": ""})
        fig.update_traces(marker_color=[SERIES[1] if v > 0 else SERIES[0] for v in cr.lift],
                          hovertemplate="%{y}<br>%{x:+.0%}<extra></extra>")
        fig.update_layout(height=360, xaxis_tickformat="+.0%")
        b.plotly_chart(bar_style(fig), width="stretch")
        up = cr.iloc[-1]
        msg = (f"During Ramadan, <b>{up.category}</b> sells {up.lift:+.0%} per day vs other days "
               "(festive items like kurma and kuih raya sell almost only in this window, so they are left out of the chart).")
    else:
        b.info("Select a period that includes Ramadan to see which categories move.")
        msg = ""
    if base:
        brk = comp.set_index("period").line_total_rm.get("UTP semester break")
        if brk:
            msg += f" During UTP semester breaks daily revenue is {brk / base - 1:+.0%} vs normal - order less student stock."
    if msg:
        insight(msg)
