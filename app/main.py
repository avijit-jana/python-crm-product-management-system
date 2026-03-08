# app/main.py
import streamlit as st
import pandas as pd
import altair as alt
from app.models import CRPM
from app.analytics import (
    total_revenue_and_count,
    revenue_timeseries,
    monthly_sales_breakdown,
    top_customers,
    product_performance,
    sales_pivot_by_product,
    customers_summary,
    products_summary,
)
from app.db import init_db

st.set_page_config(page_title="CRPM System", layout="wide", initial_sidebar_state="expanded")

# Initialize DB & service
init_db()
service = CRPM()

# Sidebar: radio buttons (not dropdown) + small actions
st.sidebar.title("Navigation")
menu = st.sidebar.radio("", ["Dashboard", "Customers", "Products", "Purchases", "Analytics"])

st.sidebar.markdown("---")
if st.sidebar.button("Add sample data"):
    # Minimal sample rows to help demo (non-destructive)
    try:
        # Add 1 customer, 1 product if none exist
        if not service.get_customers():
            service.add_customer("Demo Customer", "demo@example.com", "9999999999")
        if not service.get_products():
            service.add_product("Demo Product", 9.99, 100)
        st.sidebar.success("Sample data added.")
    except Exception as e:
        st.sidebar.error(f"Sample data error: {e}")

st.title("Customer Relationship & Product Management (CRPM)")

# ---------- DASHBOARD ----------
if menu == "Dashboard":
    st.header("Quick Overview")
    stats = total_revenue_and_count()
    # defensive access
    revenue = stats.get("revenue", 0.0)
    count = stats.get("count", 0)
    avg_order = stats.get("avg_order", 0.0)

    k1, k2, k3 = st.columns([1.2, 1, 1])
    k1.metric("Total Revenue", f"${revenue:,.2f}")
    k2.metric("Total Orders", f"{count}")
    k3.metric("Average Order", f"${avg_order:,.2f}")

    st.markdown("### Recent purchases")
    recent = pd.DataFrame(service.get_all_purchases())
    if not recent.empty:
        st.dataframe(recent.head(20), width='stretch')
    else:
        st.info("No purchases yet.")

# ---------- CUSTOMERS ----------
elif menu == "Customers":
    st.header("Customers")
    with st.form("add_customer", clear_on_submit=True):
        st.subheader("Add customer")
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        submitted = st.form_submit_button("Create")
        if submitted:
            if not name.strip():
                st.error("Name is required.")
            else:
                cid = service.add_customer(name.strip(), email.strip() if email else None, phone.strip() if phone else None)
                st.success(f"Customer added (id={cid})")

    st.subheader("Customer list (expanded)")
    df = customers_summary()
    if not df.empty:
        st.dataframe(df, width='stretch')
        # quick actions per selected row
        sel_id = st.number_input("Edit customer id (enter id)", min_value=0, value=0, step=1)
        if sel_id:
            cust_rows = df[df["id"] == sel_id]
            if not cust_rows.empty:
                cust = cust_rows.iloc[0].to_dict()
                st.markdown(f"**Selected: {cust.get('name')}**")
                with st.form("edit_customer"):
                    new_name = st.text_input("Name", value=cust.get("name", ""))
                    new_email = st.text_input("Email", value=cust.get("email", "") or "")
                    new_phone = st.text_input("Phone", value=cust.get("phone", "") or "")
                    new_active = st.checkbox("Active", value=bool(cust.get("active", 1)))
                    do_update = st.form_submit_button("Update")
                    if do_update:
                        service.update_customer(sel_id, name=new_name, email=new_email, phone=new_phone, active=int(new_active))
                        st.success("Updated")
            else:
                st.info("Customer id not found in current list.")
    else:
        st.info("No customers found.")

# ---------- PRODUCTS ----------
elif menu == "Products":
    st.header("Products")
    with st.form("add_product", clear_on_submit=True):
        st.subheader("Add product")
        pname = st.text_input("Product name")
        sku = st.text_input("SKU (optional)")
        category = st.text_input("Category (optional)")
        price = st.number_input("Price", min_value=0.0, value=0.0, format="%.2f")
        stock = st.number_input("Stock", min_value=0, value=0, step=1)
        reorder_level = st.number_input("Reorder level (optional)", min_value=0, value=0, step=1)
        submitted = st.form_submit_button("Create")
        if submitted:
            if not pname.strip():
                st.error("Product name is required.")
            else:
                pid = service.add_product(pname.strip(), float(price), int(stock))
                # Optional fields like sku/category would require schema change to persist.
                st.success(f"Product added (id={pid})")

    st.subheader("Products (expanded)")
    dfp = products_summary()
    if not dfp.empty:
        st.dataframe(dfp, width='stretch')
        sel_id = st.number_input("Edit product id (enter id)", min_value=0, value=0, step=1)
        if sel_id:
            prod_rows = dfp[dfp["id"] == sel_id]
            if not prod_rows.empty:
                prod = prod_rows.iloc[0].to_dict()
                st.markdown(f"**Selected: {prod.get('name')}**")
                with st.form("edit_product"):
                    new_name = st.text_input("Name", value=prod.get("name", ""))
                    new_price = st.number_input("Price", min_value=0.0, value=float(prod.get("price", 0.0)), format="%.2f")
                    new_stock = st.number_input("Stock", min_value=0, value=int(prod.get("stock", 0)), step=1)
                    new_active = st.checkbox("Active", value=bool(prod.get("active", 1)))
                    do_update = st.form_submit_button("Update")
                    if do_update:
                        service.update_product(sel_id, name=new_name, price=float(new_price), stock=int(new_stock), active=int(new_active))
                        st.success("Updated")
            else:
                st.info("Product id not found in current list.")
    else:
        st.info("No products found.")

# ---------- PURCHASES ----------
elif menu == "Purchases":
    st.header("Record Purchase")
    customers = service.get_customers()
    products = service.get_products()
    if not customers:
        st.warning("Add customers first.")
    elif not products:
        st.warning("Add products first.")
    else:
        c_map = {f"{c['name']} (id={c['id']})": c['id'] for c in customers}
        p_map = {f"{p['name']} (id={p['id']}) - ${p['price']} (stock={p['stock']})": p['id'] for p in products}
        with st.form("record_purchase"):
            cust_sel = st.selectbox("Customer", list(c_map.keys()))
            prod_sel = st.selectbox("Product", list(p_map.keys()))
            qty = st.number_input("Quantity", min_value=1, value=1, step=1)
            do_record = st.form_submit_button("Record Purchase")
            if do_record:
                try:
                    cid = c_map[cust_sel]
                    pid = p_map[prod_sel]
                    purchase_id = service.record_purchase(cid, pid, int(qty))
                    st.success(f"Purchase recorded (id={purchase_id})")
                except Exception as e:
                    st.error(f"Could not record purchase: {e}")

    st.subheader("Purchase History")
    hist = pd.DataFrame(service.get_all_purchases())
    if not hist.empty:
        st.dataframe(hist, width='stretch')
    else:
        st.info("No purchases yet.")

# ---------- ANALYTICS ----------
elif menu == "Analytics":
    st.header("Analytics")
    # Date range controls (based on monthly_sales_breakdown)
    ms = monthly_sales_breakdown()
    if not ms.empty:
        min_date = pd.to_datetime(ms["period"]).min().date()
        max_date = pd.to_datetime(ms["period"]).max().date()
    else:
        min_date = None
        max_date = None

    cols = st.columns(3)
    if min_date and max_date:
        date_from = cols[0].date_input("From", min_value=min_date, value=min_date)
        date_to = cols[1].date_input("To", min_value=min_date, value=max_date)
    else:
        date_from = None
        date_to = None

    date_from_iso = date_from.isoformat() if date_from else None
    date_to_iso = date_to.isoformat() if date_to else None
    stats = total_revenue_and_count(date_from_iso, date_to_iso)
    k1, k2, k3 = st.columns([1.2, 1, 1])
    k1.metric("Revenue", f"${stats.get('revenue', 0.0):,.2f}")
    k2.metric("Orders", f"{stats.get('count', 0)}")
    k3.metric("Avg Order", f"${stats.get('avg_order', 0.0):,.2f}")

    # Revenue trend (small clean altair chart)
    st.subheader("Revenue Trend")
    ts = revenue_timeseries(freq="M", periods=12)
    if not ts.empty:
        chart = alt.Chart(ts).mark_line(point=True).encode(
            x=alt.X("period:T", title="Period"),
            y=alt.Y("revenue:Q", title="Revenue"),
            tooltip=["period:T", "revenue:Q"],
        ).properties(height=220, width=520)
        st.altair_chart(chart, width='content')
    else:
        st.info("No revenue data yet.")

    # Top customers (compact)
    st.subheader("Top Customers")
    tc = top_customers(10)
    if tc:
        st.table(pd.DataFrame(tc))
    else:
        st.info("No customer data yet.")

    # Product performance (small bar)
    st.subheader("Product Performance (by units sold)")
    pp = product_performance(10)
    if pp:
        dfpp = pd.DataFrame(pp)
        bar = alt.Chart(dfpp).mark_bar().encode(
            x=alt.X("quantity_sold:Q", title="Units Sold"),
            y=alt.Y("product_name:N", sort='-x', title=None),
            tooltip=["product_name:N", "quantity_sold:Q", "revenue:Q"]
        ).properties(height=300, width=520)
        st.altair_chart(bar, width='content')
        st.dataframe(dfpp, width='content')
    else:
        st.info("No product sales yet.")

    # Sales pivot
    st.subheader("Sales Pivot: Products x Month")
    pivot = sales_pivot_by_product("M")
    if not pivot.empty:
        st.dataframe(
            pivot.style.format("{:,.0f}"),
            width='stretch'
        )    
    else:
        st.info("No pivot data yet.")