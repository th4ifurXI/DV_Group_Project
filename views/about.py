import streamlit as st


def render():
    D = st.session_state["D"]
    st.title("ℹ️ About the Data")
    st.info(
        "**This dashboard uses a simulated dataset.** It was generated with "
        "`data_generation/generate_dataset.py` to resemble a typical neighbourhood mini-market in "
        "Seri Iskandar, Perak: Malaysian products and prices (RM), local payment methods, loyalty members "
        "(UTP students, residents, staff), the UTP semester calendar and Malaysian festive seasons. "
        "It does not come from any real store. Any shop can upload its own POS export with the same "
        "columns from the sidebar.")

    c = st.columns(4)
    s = D["sales"]
    c[0].metric("Sale lines", f"{len(s):,}")
    c[1].metric("Transactions", f"{s.invoice_no.nunique():,}")
    c[2].metric("Products", f"{len(D['products'])}")
    c[3].metric("Loyalty members", f"{len(D['customers']):,}")

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
    for name in ["products", "customers", "inventory", "calendar"]:
        with st.expander(f"Preview: {name}"):
            st.dataframe(D[name].head(20), hide_index=True, width="stretch")
