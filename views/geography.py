"""Customer Map - where members live and what they buy (L6 map visualisation + L4 linked views)."""

import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import filter_frame
from core.style import CONTEXT, HIGHLIGHT, highlight_colours, insight, money_axis, plot, rm, rm_short, selected

# Approximate town-centre coordinates for the member areas (store sits in Seri Iskandar)
AREAS = pd.DataFrame([
    ("Seri Iskandar", 4.3605, 100.9705),
    ("UTP Campus", 4.3850, 100.9790),
    ("Bandar Universiti", 4.3720, 100.9880),
    ("Bota", 4.3470, 100.8800),
    ("Tronoh", 4.4180, 101.0050),
    ("Parit", 4.4730, 100.9100),
], columns=["area", "lat", "lon"])
STORE = (4.3610, 100.9690)


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    st.title("🗺️ Customer Map")
    st.caption("Where do our loyalty members live, and does what they buy differ by area? "
               "(Walk-in customers have no address, so only members are mapped.)")
    m = s.dropna(subset=["customer_id"]).merge(D["customers"][["customer_id", "area"]], on="customer_id")
    if m.empty:
        st.warning("No member transactions in this selection. Set Customer type to 'All' or 'Member'.")
        return

    g = m.groupby("area").agg(revenue=("line_total_rm", "sum"), members=("customer_id", "nunique"),
                              visits=("invoice_no", "nunique")).reset_index()
    g["spend_per_member"] = g.revenue / g.members
    g["share"] = g.revenue / g.revenue.sum()
    g = AREAS.merge(g, on="area", how="inner")
    if g.empty:
        st.info("The customers in this file are not from the mapped areas around the store, so the map is hidden.")
        return

    # L4 linked views: the area chosen in the bar chart is highlighted on the map and drives the category comparison
    pick = selected("geo_area") or g.loc[g.revenue.idxmax(), "area"]
    g["selected"] = g.area.eq(pick).map({True: "Selected area", False: "Other areas"})

    c = st.columns(3)
    row = g.set_index("area").loc[pick]
    c[0].metric(f"Members in {pick}", f"{int(row.members):,}")
    c[1].metric("Member revenue", rm_short(row.revenue), help=f"{row.share:.0%} of member revenue")
    c[2].metric("Spend per member", rm(row.spend_per_member))

    left, right = st.columns([3, 2])
    fig = px.scatter_map(g, lat="lat", lon="lon", size="revenue", color="selected", size_max=48,
                         color_discrete_map={"Selected area": HIGHLIGHT, "Other areas": "#2a78d6"},
                         hover_name="area", text="area", zoom=10.6, center=dict(lat=4.40, lon=100.95),
                         map_style="carto-positron", custom_data=["members", "revenue", "spend_per_member"],
                         title="Member revenue by home area (bubble size = revenue)")
    fig.update_traces(textposition="top center", textfont=dict(size=12, color="#0b0b0b"), marker=dict(opacity=0.75),
                      hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]:,} members<br>RM%{customdata[1]:,.0f} revenue"
                                    "<br>RM%{customdata[2]:,.0f} per member<extra></extra>")
    fig.add_scattermap(lat=[STORE[0]], lon=[STORE[1]], mode="markers+text", text=["🛒 Store"],
                       textposition="bottom center", marker=dict(size=11, color="#0b0b0b"), name="Store",
                       hoverinfo="text", hovertext=["The store (approximate location)"])
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=48, b=0),
                      legend=dict(orientation="h", yanchor="top", y=-0.02, x=0))
    plot(fig, left)
    left.caption("North is up. Bubble positions are approximate town centres. Map tiles © OpenStreetMap contributors, © CARTO.")

    gb = g.sort_values("revenue")
    fig = px.bar(gb, x="revenue", y="area", orientation="h", title="Member revenue by area (click to select)",
                 labels={"revenue": "Member revenue", "area": ""}, custom_data=["members"],
                 text=[rm_short(v) for v in gb.revenue])
    fig.update_traces(marker_color=highlight_colours(gb.area, pick), textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>RM%{x:,.0f}<br>%{customdata[0]:,} members<extra></extra>")
    fig.update_layout(height=520, xaxis_range=[0, gb.revenue.max() * 1.22])
    money_axis(fig, "x")
    plot(fig, right, on_select="rerun", selection_mode="points", key="geo_area")

    # what the selected area buys vs everyone (same scale, two series)
    mix = m.groupby(["area", "category"]).line_total_rm.sum().reset_index()
    a = mix[mix.area == pick].set_index("category").line_total_rm
    allm = mix.groupby("category").line_total_rm.sum()
    comp = pd.DataFrame({pick: a / a.sum(), "All areas": allm / allm.sum()}).fillna(0)
    comp = comp.sort_values(pick).reset_index(names="category").melt(id_vars="category", var_name="group", value_name="share")
    fig = px.bar(comp, x="share", y="category", color="group", barmode="group", orientation="h",
                 color_discrete_map={pick: HIGHLIGHT, "All areas": CONTEXT},
                 title=f"What {pick} members buy vs all members (share of their spend)",
                 labels={"share": "Share of spend", "category": "", "group": ""})
    fig.update_traces(hovertemplate="%{y}<br>%{fullData.name}: %{x:.1%}<extra></extra>")
    fig.update_layout(height=540, xaxis_tickformat=".0%",
                      legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, traceorder="reversed"))
    plot(fig)
    d = (comp.pivot(index="category", columns="group", values="share")[pick]
         - comp.pivot(index="category", columns="group", values="share")["All areas"]).sort_values()
    insight(f"<b>{pick}</b> members spend {row.share:.0%} of member revenue. They buy relatively more "
            f"<b>{d.index[-1]}</b> and less <b>{d.index[0]}</b> than average - use this to target flyers and "
            "WhatsApp promos by area.")
