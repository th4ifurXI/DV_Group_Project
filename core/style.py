"""
Shared chart styling: one palette, one Plotly template, small UI helpers.

Design rules applied everywhere (TEB3133 lectures):
- L2 #2 Colour: colour only when it means something; one highlight colour against a light context colour;
  no red + green pairs; colour-blind-safe validated palette.
- L2 #3-4 Text, labels, readability: every chart has a title, axis titles and horizontal text; small bar
  charts carry direct value labels.
- L2 #5 Scales: bars start at zero; money axes use RM with the highest denomination (RM400k, RM1.2M).
- L2 #7 Chartjunk: no borders, shadows, 3D or heavy gridlines; light grey grid only.
- L2 #10 Attribution: a source and author line under every chart (see plot()).
- L3 Pre-attentive attributes: the one data point that matters is drawn in HIGHLIGHT.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Categorical slots - fixed order, never cycled (validated palette, light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
WARNING, SERIOUS, CRITICAL = "#fab219", "#ec835a", "#d03b3b"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
PRIMARY = SERIES[0]
CONTEXT = "#9ec5f4"        # light blue: everything that is context
HIGHLIGHT = SERIES[1]      # orange: the one thing to look at (pre-attentive colour)
EVENT_TINT = "rgba(235,104,52,0.10)"

SAMPLE_SOURCE = "Data: anonymised mini-market, Perak, Jan 2025 - Oct 2026"
ATTRIBUTION = f"{SAMPLE_SOURCE} · Chart: WData (TEB3133)"
CUR = "RM"   # currency symbol; switched by set_source() when a file in another currency is uploaded


def set_source(source, currency="RM"):
    """Set the attribution line and currency used by every chart (L2 #10)."""
    global ATTRIBUTION, CUR
    ATTRIBUTION = f"{source} · Chart: WData (TEB3133)"
    CUR = currency

pio.templates["shop"] = go.layout.Template(layout=dict(
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", size=13, color=INK_2),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=SERIES,
    xaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, ticks="", showgrid=False,
               tickangle=0, automargin=True, title_font=dict(size=12, color=MUTED)),
    yaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, ticks="", gridwidth=1,
               automargin=True, title_font=dict(size=12, color=MUTED)),
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=13)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
    margin=dict(l=8, r=8, t=48, b=8),
    bargap=0.28,
    title=dict(font=dict(size=15, color=INK), x=0, xanchor="left"),
))
pio.templates.default = "shop"

STATUS_ICON = {"Reorder now": "🔴 Reorder now", "Reorder soon": "🟠 Reorder soon",
               "OK": "✔️ OK", "Overstock": "🔵 Overstock", "No recent sales": "⚪ No recent sales"}
# no red + green pair (L2 #2): OK is neutral grey, urgency carries the warm colours
STATUS_COLOUR = {"Reorder now": CRITICAL, "Reorder soon": SERIOUS, "OK": AXIS,
                 "Overstock": PRIMARY, "No recent sales": MUTED}


def rm(x, decimals=0):
    if x != x:
        return "n/a"
    return f"{CUR}{x:,.{decimals}f}"


def money_fmt():
    """Number format for money columns in st.dataframe."""
    return f"{CUR} %.2f"


def rm_short(x):
    """Compact money using the highest denomination: RM2.88M, RM597k."""
    if x != x:
        return "n/a"
    if abs(x) >= 1e6:
        return f"{CUR}{x / 1e6:.2f}M"
    if abs(x) >= 1e4:
        return f"{CUR}{x / 1e3:.0f}k"
    if abs(x) < 100:
        return f"{CUR}{x:,.2f}"
    return f"{CUR}{x:,.0f}"


def pct_delta(now, before):
    if before in (0, None) or before != before or now != now:
        return None
    return f"{(now - before) / before:+.1%}"


def insight(text, where=st):
    """Key takeaway under a chart (L3: the 'so what' for the audience)."""
    where.markdown(
        f"<div style='border-left:3px solid {PRIMARY};padding:6px 12px;margin:4px 0 18px;"
        f"color:{INK_2};font-size:0.92rem'>💡 {text}</div>", unsafe_allow_html=True)


def plot(fig, where=st, **kw):
    """Draw a chart with the attribution line under it (L2 #10). Returns the selection event if any."""
    fig.update_traces(marker_cornerradius=4, selector=dict(type="bar"))
    if CUR != "RM":  # hover text is written with RM; swap in the uploaded file's currency
        fig.for_each_trace(lambda t: t.update(hovertemplate=t.hovertemplate.replace("RM", CUR))
                           if t.hovertemplate else None)
    ev = where.plotly_chart(fig, width="stretch", config={"displaylogo": False}, **kw)
    where.caption(ATTRIBUTION)
    return ev


def highlight_colours(labels, chosen):
    """Context colour for every bar, highlight colour for the chosen one(s)."""
    chosen = set(chosen if isinstance(chosen, (list, set, tuple)) else [chosen])
    return [HIGHLIGHT if l in chosen else CONTEXT for l in labels]


def money_axis(fig, axis="x"):
    """Currency prefix and k / M suffix on a money axis (L2 #5)."""
    vals = [v for t in fig.data for v in (getattr(t, axis) if getattr(t, axis) is not None else [])
            if isinstance(v, (int, float))]
    small = bool(vals) and max(abs(v) for v in vals) < 1000   # "~s" would print 500m for 0.5
    fig.update_layout(**{f"{axis}axis": dict(tickprefix=CUR, tickformat=",.2~f" if small else "~s")})
    return fig


def selected(key, field="y"):
    """Read a click selection from a chart drawn with on_select (L4 linked views)."""
    ev = st.session_state.get(key)
    try:
        pts = ev["selection"]["points"]
    except (TypeError, KeyError):
        return None
    return pts[0].get(field) if pts else None


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
