from pathlib import Path

import pandas as pd
import streamlit as st

from core.style import SAMPLE_SOURCE


def render():
    D = st.session_state["D"]
    st.title("ℹ️ About the Data")
    if D["source"] == SAMPLE_SOURCE:
        st.info(
            "**About this dataset.** The dashboard is built around an anonymised neighbourhood mini-market in "
            "Perak, covering 1 Jan 2025 to 31 Oct 2026: Malaysian products with prices in RM, local payment "
            "methods, loyalty members (UTP students, residents and staff), the UTP semester calendar and "
            "Malaysian festive seasons. Shelf prices for 45 of the 99 products are real KPDN PriceCatcher prices: "
            "the November 2026 median across 196 mini-markets, grocery shops and supermarkets in Perak. "
            "Any shop can upload its own POS export with the same columns from the "
            "sidebar, and the UCI Online Retail II file is also accepted as-is.")
    else:
        st.info(f"**Showing an uploaded file.** {D['source']}. Views that need cost prices, stock counts, "
                "categories or customer areas are hidden when the file does not contain them.")

    c = st.columns(4)
    s = D["sales"]
    c[0].metric("Sale lines", f"{len(s):,}")
    c[1].metric("Transactions", f"{s.invoice_no.nunique():,}")
    c[2].metric("Products", f"{len(D['products'])}")
    c[3].metric("Loyalty members", f"{len(D['customers']):,}")

    st.subheader("How the dashboard applies TEB3133 concepts")
    st.markdown("""
| Lecture | Concept | Where it is applied |
|---|---|---|
| L1 Introduction | Audience, goal (explore + present), data types | Built for shop managers; each page answers one question; categorical, ordinal, time and geographic data |
| L2 #1 Chart format | Web, interactive | Plotly charts with hover tooltips, zoom and CSV downloads |
| L2 #2 Colour | Colour only when meaningful, high contrast, no red + green | One orange highlight on light-blue context; validated colour-blind-safe palette; inventory chart avoids red/green |
| L2 #3-4 Text, labels, readability | Descriptive titles, axis titles, direct labels, no angled text | Value labels on small bar charts; horizontal bars for long names; 💡 takeaway under every chart |
| L2 #5 Scales | Zero baseline for bars, natural increments, highest denomination | Bars start at 0; money axes show RM100k / RM1.2M |
| L2 #6 Data integrity | Lie factor = 1, no 3D | Flat 2D marks only, log scale labelled on the product scatter |
| L2 #7 Chartjunk | Remove non-data ink | No borders, shadows or backgrounds; light grey grid |
| L2 #8-9 Density, richness | Small multiples on a common scale | Monthly revenue by category trellis (Seasonality); 13 categories grouped into 4 roles in the scatter |
| L2 #10 Attribution | Source + author on every chart | Caption under every chart |
| L3 Audience | Five questions, key takeaway, pre-attentive attributes | Takeaway callouts; peak month, busiest hour, selected segment drawn in orange |
| L4 Linked views | Selection in one view updates others | Click a category (Overview), segment (Customers), area (Map) or return reason (Returns); sidebar filters link every page |
| L5 High-dimensional | Heatmap, multivariate scatter, trellis | Weekday x hour, category x shopper type, cohort heatmaps; revenue x margin x units x role scatter; small multiples |
| L6 Maps | Title, legend, source, proportional symbols for quantities | Customer Map: bubble map of member revenue by area, linked to a bar chart and category comparison |
| L7 Evaluation | Accuracy, usability, SUS | Cleaning log below for accuracy checks; usability test plan in the report |
""")

    st.subheader("Cleaning log")
    st.dataframe(D["log"], hide_index=True, width="stretch")

    st.subheader("Data dictionary - transactions.csv")
    st.markdown("""
| Column | Meaning |
|---|---|
| invoice_no | Receipt number. `RTN` prefix = return, `TEST` = cashier test scan (removed) |
| invoice_type | Sale or Return |
| date, time | When the receipt was printed |
| customer_id | Loyalty member ID (blank for walk-in customers) |
| customer_type | Member or Walk-in |
| product_id, product_name, category | What was sold (product details in products.csv) |
| quantity | Units (negative for returns) |
| unit_price_rm | Selling price per unit (RM) |
| discount_rm | Promotion discount on the line (RM) |
| line_total_rm | quantity x unit price - discount (RM) |
| payment_method | Cash, DuitNow QR, Touch 'n Go eWallet, Debit Card, Credit Card |
| return_reason | Only for returns |
""")
    st.markdown("Other tables: **products.csv** (cost price, supplier, lead time), **customers.csv** "
                "(shopper type, area, join date), **inventory.csv** (stock on hand at the last count), "
                "**calendar_events.csv** (festive seasons and UTP breaks).")
    ref = Path(__file__).resolve().parents[1] / "data" / "reference" / "pricecatcher_perak_2026-11.csv"
    if ref.exists():
        with st.expander("Price reference: KPDN PriceCatcher, Perak, November 2026"):
            st.caption("Median price per item across Perak mini-markets, grocery shops and supermarkets, converted to "
                       "the shop's pack size. Source: open.dosm.gov.my/data-catalogue/pricecatcher")
            st.dataframe(pd.read_csv(ref), hide_index=True, width="stretch")
    for name in ["products", "customers", "inventory", "calendar"]:
        with st.expander(f"Preview: {name}"):
            st.dataframe(D[name].head(20), hide_index=True, width="stretch")
