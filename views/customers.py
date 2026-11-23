import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import SEGMENT_ACTION, SEGMENT_ORDER, filter_frame, rfm
from core.style import SEQ, SERIES, bar_style, insight, rm


def render():
    D, F = st.session_state["D"], st.session_state["F"]
    s = filter_frame(D["sales"], F)
    st.title("👥 Customer Insights")
    st.caption("Who are our best customers, and who are we losing? (Loyalty members only - walk-ins have no ID.)")
    m = s.dropna(subset=["customer_id"])
    if len(m.customer_id.unique()) < 20:
        st.warning("Not enough member transactions in this selection. Set Customer type to 'All' or 'Member'.")
        return

    r = rfm(m, F["end"])
    seg = r.groupby("segment").agg(customers=("customer_id", "count"), revenue=("monetary", "sum")).reindex(SEGMENT_ORDER).fillna(0)
    seg["rev_share"] = seg.revenue / seg.revenue.sum()
    seg = seg.reset_index()

    c = st.columns(4)
    c[0].metric("Members who shopped", f"{len(r):,}")
    c[1].metric("Avg visits per member", f"{r.frequency.mean():.1f}")
    c[2].metric("Avg spend per member", rm(r.monetary.mean()))
    member_share = s[s.customer_type == "Member"].line_total_rm.sum() / s.line_total_rm.sum()
    c[3].metric("Revenue from members", f"{member_share:.0%}")

    a, b = st.columns(2)
    fig = px.bar(seg, x="segment", y="customers", title="Members by RFM segment",
                 labels={"segment": "", "customers": "Members"}, custom_data=["rev_share"])
    fig.update_traces(marker_color=SERIES[0], hovertemplate="%{x}<br>%{y:,} members<br>%{customdata[0]:.0%} of member revenue<extra></extra>")
    fig.update_layout(height=360)
    a.plotly_chart(bar_style(fig), width="stretch")
    fig = px.bar(seg, x="segment", y="rev_share", title="Share of member revenue by segment",
                 labels={"segment": "", "rev_share": ""}, custom_data=["revenue"])
    fig.update_traces(marker_color=SERIES[2], hovertemplate="%{x}<br>%{y:.0%} (RM%{customdata[0]:,.0f})<extra></extra>")
    fig.update_layout(height=360, yaxis_tickformat=".0%")
    b.plotly_chart(bar_style(fig), width="stretch")

    champ = seg.set_index("segment").loc["Champions"]
    risk = seg.set_index("segment").loc["At Risk"]
    insight(f"<b>Champions</b> are {champ.customers / seg.customers.sum():.0%} of members but bring "
            f"{champ.rev_share:.0%} of member revenue. <b>{int(risk.customers)} At Risk</b> members used to shop "
            f"often but have stopped - they were worth {rm(risk.revenue)}.")

    with st.expander("How the segments are scored (rule-based, no machine learning)"):
        st.markdown(
            "- **R**ecency (days since last visit), **F**requency (number of visits), **M**onetary (total spend) "
            "are each scored 1-5 by quintile (5 = best).\n"
            "- Champions: R≥4 and F≥4 · Loyal: R≥3 and F≥3 · New / Promising: R≥4 and F≤2 · "
            "At Risk: R≤2 and F≥3 · Needs Attention: R=3 · Lost: everyone else.")
        st.dataframe(pd.DataFrame({"Segment": SEGMENT_ORDER, "Suggested action": [SEGMENT_ACTION[k] for k in SEGMENT_ORDER]}),
                     hide_index=True, width="stretch")

    st.subheader("Customer list by segment")
    pick = st.selectbox("Segment", SEGMENT_ORDER, index=SEGMENT_ORDER.index("At Risk"))
    lst = r[r.segment == pick].merge(D["customers"], on="customer_id", how="left", suffixes=("", "_profile"))
    lst = lst[["customer_id", "segment_profile", "area", "recency_days", "frequency", "monetary", "last"]] \
        .rename(columns={"segment_profile": "shopper_type", "last": "last_visit"}) \
        .sort_values("monetary", ascending=False)
    st.caption(f"Action: {SEGMENT_ACTION[pick]}")
    st.dataframe(lst, hide_index=True, width="stretch", height=260,
                 column_config={"monetary": st.column_config.NumberColumn("Total spend", format="RM %.2f"),
                                "last_visit": st.column_config.DateColumn("Last visit")})
    st.download_button("Download list (CSV)", lst.to_csv(index=False), f"{pick.lower().replace(' / ', '_')}_customers.csv")

    # what each shopper type buys
    prof = s.merge(D["customers"][["customer_id", "segment"]], on="customer_id", how="left")
    prof["shopper_type"] = prof.segment.fillna("Walk-in")
    h = prof.pivot_table(index="category", columns="shopper_type", values="line_total_rm", aggfunc="sum").fillna(0)
    h = h / h.sum()
    h = h[[c for c in ["Student", "Staff", "Resident", "Walk-in"] if c in h.columns]]
    fig = px.imshow(h, text_auto=".0%", aspect="auto", color_continuous_scale=SEQ,
                    title="What each shopper type spends on (share of their spend)", labels=dict(color="Share"))
    fig.update_traces(hovertemplate="%{y}<br>%{x}: %{z:.1%}<extra></extra>")
    fig.update_layout(height=480, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, width="stretch")
    if "Student" in h.columns and "Resident" in h.columns:
        d = (h.Student - h.Resident).sort_values()
        insight(f"Students over-index on <b>{d.index[-1]}</b>; residents on <b>{d.index[0]}</b>. "
                "Use this to plan promos around UTP term dates vs. weekend family shopping.")

    # cohort retention
    first = m.groupby("customer_id").month.min().rename("cohort")
    c2 = m.merge(first, on="customer_id")
    c2["age"] = (c2.month.dt.year - c2.cohort.dt.year) * 12 + (c2.month.dt.month - c2.cohort.dt.month)
    tab = c2.groupby(["cohort", "age"]).customer_id.nunique().unstack(fill_value=0)
    tab = tab.div(tab[0], axis=0).iloc[:, :13]
    last = m.month.max()
    for coh in tab.index:  # months after the data ends are unknown, not 0%
        observed = (last.year - coh.year) * 12 + (last.month - coh.month)
        tab.loc[coh, [c for c in tab.columns if c > observed]] = float("nan")
    tab.index = tab.index.strftime("%b %Y")
    fig = px.imshow(tab, text_auto=".0%", aspect="auto", color_continuous_scale=SEQ, zmin=0, zmax=1,
                    title="Cohort retention: % of new members still shopping N months later",
                    labels=dict(x="Months since first visit", y="First visit", color="Retained"))
    fig.update_traces(hovertemplate="Joined %{y}<br>Month %{x}: %{z:.0%} still shopping<extra></extra>")
    fig.update_layout(height=520, coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")
    if tab.shape[1] > 3:
        insight(f"On average {tab[1].mean():.0%} of new members come back the next month and "
                f"{tab[3].mean():.0%} are still shopping 3 months later.")
