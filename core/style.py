"""Shared chart styling: one palette, one Plotly template, small UI helpers."""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Categorical slots - fixed order, never cycled (validated palette, light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
PRIMARY = SERIES[0]
EVENT_TINT = "rgba(235,104,52,0.10)"

pio.templates["shop"] = go.layout.Template(layout=dict(
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", size=13, color=INK_2),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=SERIES,
    xaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, ticks="", showgrid=False),
    yaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, ticks="", gridwidth=1),
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=13)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
    margin=dict(l=8, r=8, t=36, b=8),
    bargap=0.28,
    title=dict(font=dict(size=15, color=INK), x=0, xanchor="left"),
))
pio.templates.default = "shop"

STATUS_ICON = {"Reorder now": "🔴 Reorder now", "Reorder soon": "🟠 Reorder soon",
               "OK": "🟢 OK", "Overstock": "🔵 Overstock", "No recent sales": "⚪ No recent sales"}


def rm(x, decimals=0):
    return f"RM{x:,.{decimals}f}"


def rm_short(x):
    """Compact money for KPI tiles: RM2.88M, RM597k."""
    if abs(x) >= 1e6:
        return f"RM{x / 1e6:.2f}M"
    if abs(x) >= 1e4:
        return f"RM{x / 1e3:.0f}k"
    return f"RM{x:,.0f}"


def pct_delta(now, before):
    if before in (0, None) or before != before:
        return None
    return f"{(now - before) / before:+.1%}"


def insight(text):
    """A short 'what this means' callout under a chart."""
    st.markdown(
        f"<div style='border-left:3px solid {PRIMARY};padding:6px 12px;margin:4px 0 18px;"
        f"color:{INK_2};font-size:0.92rem'>💡 {text}</div>", unsafe_allow_html=True)


def bar_style(fig):
    fig.update_traces(marker_cornerradius=4, selector=dict(type="bar"))
    return fig


def add_event_bands(fig, calendar, start, end, types=("Festive / public holiday",), min_days=3):
    """Shade festive periods on a time-series chart (Ramadan, Raya, CNY)."""
    for _, e in calendar[calendar.event_type.isin(types)].iterrows():
        if (e.end_date - e.start_date).days + 1 < min_days:
            continue
        if e.end_date < start or e.start_date > end:
            continue
        label = e.event if (e.end_date - e.start_date).days >= 7 else ""
        fig.add_vrect(x0=e.start_date, x1=e.end_date, fillcolor=EVENT_TINT, line_width=0, layer="below",
                      annotation_text=label, annotation_position="top left",
                      annotation_font=dict(size=11, color=MUTED))
    return fig
