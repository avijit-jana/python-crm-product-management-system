# app/main.py
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
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
    category_performance,
    payment_method_analysis,
    low_stock_alerts,
    customer_retention_metrics,
)
from app.db import init_db

# Page configuration
st.set_page_config(
    page_title="CRPM System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB & service
init_db()
service = CRPM()

# Initialize session state
if "last_action" not in st.session_state:
    st.session_state.last_action = None
if "show_success" not in st.session_state:
    st.session_state.show_success = False

# Sidebar Navigation
st.sidebar.markdown("## 📊 CRPM System")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "👥 Customers", "📦 Products", "🛒 Purchases", "📈 Analytics", "⚙️ Settings"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# Quick Actions in Sidebar
st.sidebar.markdown("### Quick Actions")
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# Low Stock Alert in Sidebar
low_stock = low_stock_alerts()
if low_stock:
    st.sidebar.warning(f"⚠️ {len(low_stock)} products low on stock!")
    with st.sidebar.expander("View Low Stock Items"):
        for item in low_stock[:5]:
            st.sidebar.text(f"• {item['name']}: {item['stock']} units")

st.sidebar.markdown("---")
st.sidebar.caption("CRPM System v2.0")

# Main Content Area
st.markdown('<h1 class="main-header">Customer Relationship & Product Management</h1>', unsafe_allow_html=True)

# Show success message if any
if st.session_state.show_success and st.session_state.last_action:
    st.success(f"✅ {st.session_state.last_action}")
    st.session_state.show_success = False
    st.session_state.last_action = None

# ==================== DASHBOARD ====================
if menu == "🏠 Dashboard":
    st.header("📊 Dashboard Overview")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        date_range = st.selectbox(
            "Time Period",
            ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
            index=4
        )
    
    # Calculate date range
    date_from, date_to = None, None
    if date_range != "All Time":
        date_to = datetime.now()
        if date_range == "Today":
            date_from = date_to.replace(hour=0, minute=0, second=0)
        elif date_range == "Last 7 Days":
            date_from = date_to - timedelta(days=7)
        elif date_range == "Last 30 Days":
            date_from = date_to - timedelta(days=30)
        elif date_range == "Last 90 Days":
            date_from = date_to - timedelta(days=90)
        
        date_from = date_from.strftime("%Y-%m-%d") if date_from else None
        date_to = date_to.strftime("%Y-%m-%d") if date_to else None
    
    # Get metrics
    stats = total_revenue_and_count(date_from, date_to)
    retention = customer_retention_metrics()
    
    # Key Metrics Row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "💰 Total Revenue",
            f"₹{stats['revenue']:,.2f}",
            help="Total revenue from all orders"
        )
    with col2:
        st.metric(
            "🛒 Total Orders",
            f"{stats['count']:,}",
            help="Number of orders placed"
        )
    with col3:
        st.metric(
            "📦 Items Sold",
            f"{stats['total_items']:,}",
            help="Total items sold"
        )
    with col4:
        st.metric(
            "💳 Avg Order Value",
            f"₹{stats['avg_order']:,.2f}",
            help="Average order value"
        )
    
    # Key Metrics Row 2
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "👥 Total Customers",
            f"{retention['total_customers']:,}",
            help="Total unique customers"
        )
    with col2:
        st.metric(
            "🔄 Repeat Rate",
            f"{retention['repeat_customer_rate']:.1f}%",
            help="Percentage of repeat customers"
        )
    with col3:
        st.metric(
            "💸 Total Discounts",
            f"₹{stats['total_discount']:,.2f}",
            help="Total discounts given"
        )
    with col4:
        st.metric(
            "🧾 Total Tax",
            f"₹{stats['total_tax']:,.2f}",
            help="Total tax collected"
        )
    
    st.markdown("---")
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Revenue Trend (Last 12 Months)")
        ts = revenue_timeseries(freq="M", periods=12)
        if not ts.empty:
            chart = alt.Chart(ts).mark_area(
                line={'color': '#1f77b4'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[
                        alt.GradientStop(color='#1f77b4', offset=0),
                        alt.GradientStop(color='white', offset=1)
                    ],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X("period:T", title="Period", axis=alt.Axis(format="%b %Y")),
                y=alt.Y("revenue:Q", title="Revenue (₹)"),
                tooltip=[
                    alt.Tooltip("period:T", format="%B %Y"),
                    alt.Tooltip("revenue:Q", format="₹,.2f"),
                    alt.Tooltip("orders:Q", format=",d")
                ]
            ).properties(height=300)
            st.altair_chart(chart, width='stretch')
        else:
            st.info("No revenue data available yet")
    
    with col2:
        st.subheader("🎯 Top 5 Products")
        pp = product_performance(5, by="revenue")
        if pp:
            df_pp = pd.DataFrame(pp)
            bar = alt.Chart(df_pp).mark_bar().encode(
                x=alt.X("revenue:Q", title="Revenue (₹)"),
                y=alt.Y("product_name:N", sort="-x", title=None),
                color=alt.Color("revenue:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=["product_name:N", "revenue:Q", "quantity_sold:Q"]
            ).properties(height=300)
            st.altair_chart(bar, width='stretch')
        else:
            st.info("No product sales data yet")
    
    st.markdown("---")
    
    # Recent Activity
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔔 Recent Purchases")
        recent = pd.DataFrame(service.get_all_purchases(limit=10))
        if not recent.empty:
            display_cols = ["purchased_at", "customer_name", "product_name", "quantity", "total_cost"]
            display_cols = [col for col in display_cols if col in recent.columns]
            recent_display = recent[display_cols].copy()
            if "purchased_at" in recent_display.columns:
                recent_display["purchased_at"] = pd.to_datetime(recent_display["purchased_at"]).dt.strftime("%Y-%m-%d %H:%M")
            if "total_cost" in recent_display.columns:
                recent_display["total_cost"] = recent_display["total_cost"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(recent_display, width='stretch', hide_index=True)
        else:
            st.info("No purchases yet")
    
    with col2:
        st.subheader("⭐ Top 5 Customers")
        tc = top_customers(5)
        if tc:
            df_tc = pd.DataFrame(tc)
            display_cols = ["customer_name", "total_spent", "orders", "last_purchase"]
            display_cols = [col for col in display_cols if col in df_tc.columns]
            df_tc_display = df_tc[display_cols].copy()
            if "total_spent" in df_tc_display.columns:
                df_tc_display["total_spent"] = df_tc_display["total_spent"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df_tc_display, width='stretch', hide_index=True)
        else:
            st.info("No customer data yet")

# ==================== CUSTOMERS ====================
elif menu == "👥 Customers":
    st.header("👥 Customer Management")
    
    tab1, tab2, tab3 = st.tabs(["📋 Customer List", "➕ Add Customer", "🔍 Search & Filter"])
    
    with tab1:
        st.subheader("All Customers")
        
        # Filters
        col1, col2 = st.columns([3, 1])
        with col1:
            show_inactive = st.checkbox("Include inactive customers", value=False)
        
        df = customers_summary()
        
        if not df.empty:
            # Format currency columns
            if "total_spent" in df.columns:
                df["total_spent"] = df["total_spent"].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(df, width='stretch', hide_index=True)
            
            st.markdown("---")
            st.subheader("Edit Customer")
            
            # Customer selection
            customer_ids = df["id"].tolist() if "id" in df.columns else []
            if customer_ids:
                sel_id = st.selectbox("Select customer to edit", customer_ids, format_func=lambda x: f"ID: {x}")
                
                if sel_id:
                    cust = service.get_customer_by_id(sel_id)
                    if cust:
                        with st.form("edit_customer"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                name = st.text_input("Name *", value=cust.get("name", ""))
                                email = st.text_input("Email", value=cust.get("email", "") or "")
                                phone = st.text_input("Phone", value=cust.get("phone", "") or "")
                                customer_type = st.selectbox(
                                    "Customer Type",
                                    ["retail", "wholesale", "corporate"],
                                    index=["retail", "wholesale", "corporate"].index(cust.get("customer_type", "retail"))
                                )
                            
                            with col2:
                                address = st.text_area("Address", value=cust.get("address", "") or "")
                                city = st.text_input("City", value=cust.get("city", "") or "")
                                state = st.text_input("State", value=cust.get("state", "") or "")
                                postal_code = st.text_input("Postal Code", value=cust.get("postal_code", "") or "")
                            
                            company_name = st.text_input("Company Name", value=cust.get("company_name", "") or "")
                            notes = st.text_area("Notes", value=cust.get("notes", "") or "")
                            active = st.checkbox("Active", value=bool(cust.get("active", 1)))
                            
                            col1, col2 = st.columns([1, 5])
                            with col1:
                                update_btn = st.form_submit_button("💾 Update", width='stretch')
                            with col2:
                                delete_btn = st.form_submit_button("🗑️ Deactivate", width='stretch', type="secondary")
                            
                            if update_btn:
                                try:
                                    service.update_customer(
                                        sel_id,
                                        name=name,
                                        email=email,
                                        phone=phone,
                                        address=address,
                                        city=city,
                                        state=state,
                                        postal_code=postal_code,
                                        customer_type=customer_type,
                                        company_name=company_name,
                                        notes=notes,
                                        active=int(active)
                                    )
                                    st.session_state.last_action = f"Customer '{name}' updated successfully!"
                                    st.session_state.show_success = True
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating customer: {e}")
                            
                            if delete_btn:
                                service.delete_customer(sel_id)
                                st.session_state.last_action = f"Customer '{name}' deactivated!"
                                st.session_state.show_success = True
                                st.rerun()
        else:
            st.info("No customers found. Add your first customer using the 'Add Customer' tab!")
    
    with tab2:
        st.subheader("Add New Customer")
        
        with st.form("add_customer", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name *", placeholder="Enter customer name")
                email = st.text_input("Email", placeholder="customer@example.com")
                phone = st.text_input("Phone", placeholder="+91 9876543210")
                customer_type = st.selectbox("Customer Type", ["retail", "wholesale", "corporate"])
            
            with col2:
                address = st.text_area("Address", placeholder="Street address")
                city = st.text_input("City", placeholder="City name")
                state = st.text_input("State", placeholder="State name")
                postal_code = st.text_input("Postal Code", placeholder="110001")
            
            company_name = st.text_input("Company Name (optional)", placeholder="For corporate customers")
            notes = st.text_area("Notes (optional)", placeholder="Any additional information")
            
            submitted = st.form_submit_button("➕ Add Customer", width='stretch')
            
            if submitted:
                if not name.strip():
                    st.error("❌ Customer name is required!")
                else:
                    try:
                        cid = service.add_customer(
                            name=name.strip(),
                            email=email.strip() if email else None,
                            phone=phone.strip() if phone else None,
                            address=address.strip() if address else None,
                            city=city.strip() if city else None,
                            state=state.strip() if state else None,
                            postal_code=postal_code.strip() if postal_code else None,
                            customer_type=customer_type,
                            company_name=company_name.strip() if company_name else None,
                            notes=notes.strip() if notes else None,
                        )
                        st.session_state.last_action = f"Customer '{name}' added successfully! (ID: {cid})"
                        st.session_state.show_success = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error adding customer: {e}")
    
    with tab3:
        st.subheader("Search Customers")
        search_term = st.text_input("🔍 Search by name, email, or phone", placeholder="Type to search...")
        
        if search_term:
            customers = service.get_customers(include_inactive=True, search=search_term)
            if customers:
                df_search = pd.DataFrame(customers)
                st.dataframe(df_search, width='stretch', hide_index=True)
                st.caption(f"Found {len(customers)} customer(s)")
            else:
                st.info("No customers found matching your search")

# ==================== PRODUCTS ====================
elif menu == "📦 Products":
    st.header("📦 Product Management")
    
    tab1, tab2, tab3 = st.tabs(["📋 Product List", "➕ Add Product", "🔍 Search & Filter"])
    
    with tab1:
        st.subheader("All Products")
        
        # Filters
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            show_inactive = st.checkbox("Include inactive products", value=False)
        with col2:
            show_low_stock = st.checkbox("Low stock only", value=False)
        
        df = products_summary()
        
        if not df.empty:
            # Apply low stock filter
            if show_low_stock:
                df = df[df["stock_status"].str.contains("Low|Out", case=False, na=False)]
            
            # Format currency columns
            if "price" in df.columns:
                df["price"] = df["price"].apply(lambda x: f"₹{x:,.2f}")
            if "cost_price" in df.columns:
                df["cost_price"] = df["cost_price"].apply(lambda x: f"₹{x:,.2f}")
            if "revenue_generated" in df.columns:
                df["revenue_generated"] = df["revenue_generated"].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(df, width='stretch', hide_index=True)
            
            st.markdown("---")
            st.subheader("Edit Product")
            
            # Product selection
            product_ids = df["id"].tolist() if "id" in df.columns else []
            if product_ids:
                sel_id = st.selectbox("Select product to edit", product_ids, format_func=lambda x: f"ID: {x}")
                
                if sel_id:
                    prod = service.get_product_by_id(sel_id)
                    if prod:
                        with st.form("edit_product"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                name = st.text_input("Product Name *", value=prod.get("name", ""))
                                sku = st.text_input("SKU", value=prod.get("sku", "") or "")
                                category = st.text_input("Category", value=prod.get("category", "General"))
                                brand = st.text_input("Brand", value=prod.get("brand", "") or "")
                                price = st.number_input("Price *", min_value=0.0, value=float(prod.get("price", 0.0)), format="%.2f")
                                cost_price = st.number_input("Cost Price", min_value=0.0, value=float(prod.get("cost_price", 0.0)), format="%.2f")
                            
                            with col2:
                                stock = st.number_input("Stock *", min_value=0, value=int(prod.get("stock", 0)), step=1)
                                reorder_level = st.number_input("Reorder Level", min_value=0, value=int(prod.get("reorder_level", 10)), step=1)
                                reorder_quantity = st.number_input("Reorder Quantity", min_value=0, value=int(prod.get("reorder_quantity", 50)), step=1)
                                unit = st.selectbox(
                                    "Unit",
                                    ["piece", "kg", "liter", "meter", "pack"],
                                    index=["piece", "kg", "liter", "meter", "pack"].index(prod.get("unit", "piece"))
                                )
                                supplier = st.text_input("Supplier", value=prod.get("supplier", "") or "")
                            
                            description = st.text_area("Description", value=prod.get("description", "") or "")
                            notes = st.text_area("Notes", value=prod.get("notes", "") or "")
                            active = st.checkbox("Active", value=bool(prod.get("active", 1)))
                            
                            col1, col2 = st.columns([1, 5])
                            with col1:
                                update_btn = st.form_submit_button("💾 Update", width='stretch')
                            with col2:
                                delete_btn = st.form_submit_button("🗑️ Deactivate", width='stretch', type="secondary")
                            
                            if update_btn:
                                try:
                                    service.update_product(
                                        sel_id,
                                        name=name,
                                        sku=sku,
                                        category=category,
                                        brand=brand,
                                        price=price,
                                        cost_price=cost_price,
                                        stock=stock,
                                        reorder_level=reorder_level,
                                        reorder_quantity=reorder_quantity,
                                        unit=unit,
                                        supplier=supplier,
                                        description=description,
                                        notes=notes,
                                        active=int(active)
                                    )
                                    st.session_state.last_action = f"Product '{name}' updated successfully!"
                                    st.session_state.show_success = True
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating product: {e}")
                            
                            if delete_btn:
                                service.delete_product(sel_id)
                                st.session_state.last_action = f"Product '{name}' deactivated!"
                                st.session_state.show_success = True
                                st.rerun()
        else:
            st.info("No products found. Add your first product using the 'Add Product' tab!")
    
    with tab2:
        st.subheader("Add New Product")
        
        with st.form("add_product", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Product Name *", placeholder="Enter product name")
                sku = st.text_input("SKU", placeholder="Product SKU code")
                category = st.text_input("Category", value="General", placeholder="Product category")
                brand = st.text_input("Brand", placeholder="Brand name")
                price = st.number_input("Selling Price *", min_value=0.0, value=0.0, format="%.2f")
                cost_price = st.number_input("Cost Price", min_value=0.0, value=0.0, format="%.2f")
            
            with col2:
                stock = st.number_input("Initial Stock *", min_value=0, value=0, step=1)
                reorder_level = st.number_input("Reorder Level", min_value=0, value=10, step=1)
                reorder_quantity = st.number_input("Reorder Quantity", min_value=0, value=50, step=1)
                unit = st.selectbox("Unit", ["piece", "kg", "liter", "meter", "pack"])
                supplier = st.text_input("Supplier", placeholder="Supplier name")
            
            description = st.text_area("Description", placeholder="Product description")
            notes = st.text_area("Notes", placeholder="Any additional notes")
            
            submitted = st.form_submit_button("➕ Add Product", width='stretch')
            
            if submitted:
                if not name.strip():
                    st.error("❌ Product name is required!")
                elif price <= 0:
                    st.error("❌ Price must be greater than 0!")
                else:
                    try:
                        pid = service.add_product(
                            name=name.strip(),
                            sku=sku.strip() if sku else None,
                            category=category.strip(),
                            brand=brand.strip() if brand else None,
                            price=price,
                            cost_price=cost_price,
                            stock=stock,
                            reorder_level=reorder_level,
                            reorder_quantity=reorder_quantity,
                            unit=unit,
                            supplier=supplier.strip() if supplier else None,
                            description=description.strip() if description else None,
                            notes=notes.strip() if notes else None,
                        )
                        st.session_state.last_action = f"Product '{name}' added successfully! (ID: {pid})"
                        st.session_state.show_success = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error adding product: {e}")
    
    with tab3:
        st.subheader("Search & Filter Products")
        
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔍 Search by name, SKU, or brand", placeholder="Type to search...")
        with col2:
            categories = service.get_categories()
            if categories:
                category_filter = st.selectbox("Filter by category", ["All"] + categories)
            else:
                category_filter = "All"
        
        if search_term or category_filter != "All":
            products = service.get_products(
                include_inactive=True,
                search=search_term if search_term else None,
                category=category_filter if category_filter != "All" else None
            )
            if products:
                df_search = pd.DataFrame(products)
                st.dataframe(df_search, width='stretch', hide_index=True)
                st.caption(f"Found {len(products)} product(s)")
            else:
                st.info("No products found matching your criteria")

# ==================== PURCHASES ====================
elif menu == "🛒 Purchases":
    st.header("🛒 Purchase Management")
    
    tab1, tab2 = st.tabs(["➕ Record Purchase", "📜 Purchase History"])
    
    with tab1:
        st.subheader("Record New Purchase")
        
        customers = service.get_customers()
        products = service.get_products()
        
        if not customers:
            st.warning("⚠️ Please add customers first before recording purchases.")
        elif not products:
            st.warning("⚠️ Please add products first before recording purchases.")
        else:
            with st.form("record_purchase", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Customer selection
                    c_options = {f"{c['name']} ({c.get('email', 'No email')})": c['id'] for c in customers}
                    cust_sel = st.selectbox("Select Customer *", list(c_options.keys()))
                    
                    # Product selection
                    p_options = {
                        f"{p['name']} - ₹{p['price']} (Stock: {p['stock']})": p['id'] 
                        for p in products
                    }
                    prod_sel = st.selectbox("Select Product *", list(p_options.keys()))
                    
                    # Get selected product details
                    selected_prod_id = p_options[prod_sel]
                    selected_prod = next(p for p in products if p['id'] == selected_prod_id)
                    
                    quantity = st.number_input(
                        f"Quantity * (Available: {selected_prod['stock']})",
                        min_value=1,
                        max_value=selected_prod['stock'],
                        value=1,
                        step=1
                    )
                
                with col2:
                    payment_method = st.selectbox(
                        "Payment Method",
                        ["cash", "card", "upi", "bank_transfer", "credit"]
                    )
                    payment_status = st.selectbox(
                        "Payment Status",
                        ["paid", "pending", "partial"]
                    )
                    
                    # Discount
                    discount_type = st.radio("Discount Type", ["None", "Percentage", "Fixed Amount"], horizontal=True)
                    if discount_type == "Percentage":
                        discount_percent = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=0.0, format="%.2f")
                        discount_amount = 0.0
                    elif discount_type == "Fixed Amount":
                        discount_percent = 0.0
                        discount_amount = st.number_input("Discount Amount", min_value=0.0, value=0.0, format="%.2f")
                    else:
                        discount_percent = 0.0
                        discount_amount = 0.0
                    
                    tax_percent = st.number_input("Tax % (GST)", min_value=0.0, max_value=100.0, value=0.0, format="%.2f")
                
                transaction_id = st.text_input("Transaction ID (optional)", placeholder="For digital payments")
                notes = st.text_area("Notes (optional)", placeholder="Any special instructions or notes")
                
                # Calculate preview
                unit_price = selected_prod['price']
                subtotal = unit_price * quantity
                if discount_percent > 0:
                    calc_discount = subtotal * discount_percent / 100
                else:
                    calc_discount = discount_amount
                amount_after_discount = subtotal - calc_discount
                tax_amount = amount_after_discount * tax_percent / 100
                total = amount_after_discount + tax_amount
                
                st.markdown("### Order Summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Subtotal", f"₹{subtotal:,.2f}")
                col2.metric("Discount", f"₹{calc_discount:,.2f}")
                col3.metric("Tax", f"₹{tax_amount:,.2f}")
                col4.metric("Total", f"₹{total:,.2f}")
                
                submitted = st.form_submit_button("🛒 Record Purchase", width='stretch')
                
                if submitted:
                    try:
                        cid = c_options[cust_sel]
                        pid = p_options[prod_sel]
                        
                        purchase_id = service.record_purchase(
                            customer_id=cid,
                            product_id=pid,
                            quantity=quantity,
                            discount_percent=discount_percent,
                            discount_amount=discount_amount,
                            tax_percent=tax_percent,
                            payment_method=payment_method,
                            payment_status=payment_status,
                            transaction_id=transaction_id.strip() if transaction_id else None,
                            notes=notes.strip() if notes else None,
                        )
                        st.session_state.last_action = f"Purchase recorded successfully! (Order ID: {purchase_id}, Total: ₹{total:,.2f})"
                        st.session_state.show_success = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error recording purchase: {e}")
    
    with tab2:
        st.subheader("Purchase History")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            limit = st.selectbox("Show records", [10, 25, 50, 100, "All"], index=1)
        
        hist_limit = None if limit == "All" else int(limit)
        hist = pd.DataFrame(service.get_all_purchases(limit=hist_limit))
        
        if not hist.empty:
            # Format columns
            if "purchased_at" in hist.columns:
                hist["purchased_at"] = pd.to_datetime(hist["purchased_at"]).dt.strftime("%Y-%m-%d %H:%M")
            
            currency_cols = ["unit_price", "subtotal", "discount_amount", "tax_amount", "total_cost"]
            for col in currency_cols:
                if col in hist.columns:
                    hist[col] = hist[col].apply(lambda x: f"₹{x:,.2f}")
            
            # Select relevant columns for display
            display_cols = [
                "id", "purchased_at", "customer_name", "product_name",
                "quantity", "unit_price", "total_cost", "payment_method", "payment_status"
            ]
            display_cols = [col for col in display_cols if col in hist.columns]
            
            st.dataframe(hist[display_cols], width='stretch', hide_index=True)
            st.caption(f"Showing {len(hist)} purchase(s)")
        else:
            st.info("No purchases recorded yet")

# ==================== ANALYTICS ====================
elif menu == "📈 Analytics":
    st.header("📈 Analytics & Reports")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Sales Analytics",
        "👥 Customer Analytics",
        "📦 Product Analytics",
        "💳 Payment Analytics"
    ])
    
    with tab1:
        st.subheader("Sales Performance")
        
        # Monthly breakdown
        ms = monthly_sales_breakdown(12)
        if not ms.empty:
            st.markdown("### Monthly Sales (Last 12 Months)")
            
            # Format currency
            ms_display = ms.copy()
            for col in ["revenue", "total_discount", "total_tax", "avg_order_value"]:
                if col in ms_display.columns:
                    ms_display[col] = ms_display[col].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(ms_display, width='stretch', hide_index=True)
            
            # Chart
            chart = alt.Chart(ms).mark_bar().encode(
                x=alt.X("period:T", title="Month", axis=alt.Axis(format="%b %Y")),
                y=alt.Y("revenue:Q", title="Revenue (₹)"),
                color=alt.value("#1f77b4"),
                tooltip=[
                    alt.Tooltip("period:T", format="%B %Y"),
                    alt.Tooltip("revenue:Q", format="₹,.2f"),
                    alt.Tooltip("orders:Q", format=",d")
                ]
            ).properties(height=350)
            st.altair_chart(chart, width='stretch')
        else:
            st.info("No sales data available")
        
        # Sales Pivot
        st.markdown("### Sales by Product Over Time")
        pivot = sales_pivot_by_product("M", periods=6)
        if not pivot.empty:
            st.dataframe(
                pivot.style.format("{:,.0f}").background_gradient(cmap="Blues", axis=1),
                width='stretch'
            )
        else:
            st.info("No sales pivot data available")
    
    with tab2:
        st.subheader("Customer Analytics")
        
        retention = customer_retention_metrics()
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Customers", f"{retention['total_customers']:,}")
        col2.metric("Active (30 days)", f"{retention['active_customers']:,}")
        col3.metric("New This Month", f"{retention['new_customers_this_month']:,}")
        col4.metric("Repeat Rate", f"{retention['repeat_customer_rate']:.1f}%")
        
        st.markdown("---")
        
        # Top customers
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Top Customers by Revenue")
            tc_revenue = top_customers(10, by="revenue")
            if tc_revenue:
                df_tc = pd.DataFrame(tc_revenue)
                if "total_spent" in df_tc.columns:
                    df_tc["total_spent"] = df_tc["total_spent"].apply(lambda x: f"₹{x:,.2f}")
                if "avg_order_value" in df_tc.columns:
                    df_tc["avg_order_value"] = df_tc["avg_order_value"].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(df_tc, width='stretch', hide_index=True)
            else:
                st.info("No data")
        
        with col2:
            st.markdown("### Top Customers by Orders")
            tc_orders = top_customers(10, by="orders")
            if tc_orders:
                df_tc = pd.DataFrame(tc_orders)
                if "total_spent" in df_tc.columns:
                    df_tc["total_spent"] = df_tc["total_spent"].apply(lambda x: f"₹{x:,.2f}")
                if "avg_order_value" in df_tc.columns:
                    df_tc["avg_order_value"] = df_tc["avg_order_value"].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(df_tc, width='stretch', hide_index=True)
            else:
                st.info("No data")
    
    with tab3:
        st.subheader("Product Analytics")
        
        # Product performance
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Top Products by Quantity Sold")
            pp_qty = product_performance(10, by="quantity")
            if pp_qty:
                df_pp = pd.DataFrame(pp_qty)
                if "revenue" in df_pp.columns:
                    df_pp["revenue"] = df_pp["revenue"].apply(lambda x: f"₹{x:,.2f}")
                if "avg_price" in df_pp.columns:
                    df_pp["avg_price"] = df_pp["avg_price"].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(df_pp, width='stretch', hide_index=True)
            else:
                st.info("No data")
        
        with col2:
            st.markdown("### Top Products by Revenue")
            pp_rev = product_performance(10, by="revenue")
            if pp_rev:
                df_pp = pd.DataFrame(pp_rev)
                if "revenue" in df_pp.columns:
                    df_pp["revenue"] = df_pp["revenue"].apply(lambda x: f"₹{x:,.2f}")
                if "avg_price" in df_pp.columns:
                    df_pp["avg_price"] = df_pp["avg_price"].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(df_pp, width='stretch', hide_index=True)
            else:
                st.info("No data")
        
        # Category performance
        st.markdown("### Performance by Category")
        cat_perf = category_performance()
        if not cat_perf.empty:
            cat_display = cat_perf.copy()
            if "revenue" in cat_display.columns:
                cat_display["revenue"] = cat_display["revenue"].apply(lambda x: f"₹{x:,.2f}")
            if "avg_order_value" in cat_display.columns:
                cat_display["avg_order_value"] = cat_display["avg_order_value"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(cat_display, width='stretch', hide_index=True)
        else:
            st.info("No category data available")
    
    with tab4:
        st.subheader("Payment Method Analytics")
        
        pm_analysis = payment_method_analysis()
        if not pm_analysis.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Pie chart
                chart = alt.Chart(pm_analysis).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("total_amount:Q"),
                    color=alt.Color("payment_method:N", legend=alt.Legend(title="Payment Method")),
                    tooltip=["payment_method:N", "total_amount:Q", "transactions:Q", "percentage:Q"]
                ).properties(height=300, title="Revenue by Payment Method")
                st.altair_chart(chart, width='stretch')
            
            with col2:
                pm_display = pm_analysis.copy()
                if "total_amount" in pm_display.columns:
                    pm_display["total_amount"] = pm_display["total_amount"].apply(lambda x: f"₹{x:,.2f}")
                if "avg_transaction" in pm_display.columns:
                    pm_display["avg_transaction"] = pm_display["avg_transaction"].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(pm_display, width='stretch', hide_index=True)
        else:
            st.info("No payment data available")

# ==================== SETTINGS ====================
elif menu == "⚙️ Settings":
    st.header("⚙️ System Settings")
    
    tab1, tab2 = st.tabs(["📊 System Info", "🔧 Actions"])
    
    with tab1:
        st.subheader("Database Statistics")
        
        customers = service.get_customers(include_inactive=True)
        products = service.get_products(include_inactive=True)
        purchases = service.get_all_purchases()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Customers", len(customers))
        col2.metric("Total Products", len(products))
        col3.metric("Total Purchases", len(purchases))
        
        st.markdown("---")
        
        # Low stock alerts
        st.subheader("⚠️ Stock Alerts")
        low_stock = low_stock_alerts()
        if low_stock:
            df_low = pd.DataFrame(low_stock)
            display_cols = ["name", "stock", "reorder_level", "reorder_quantity", "category"]
            display_cols = [col for col in display_cols if col in df_low.columns]
            st.dataframe(df_low[display_cols], width='stretch', hide_index=True)
        else:
            st.success("✅ All products have sufficient stock!")
    
    with tab2:
        st.subheader("System Actions")
        
        st.markdown("### Sample Data")
        if st.button("➕ Add Sample Data", width='stretch'):
            try:
                # Add sample customers
                if len(service.get_customers()) == 0:
                    service.add_customer("Rajesh Kumar", "rajesh@example.com", "+919876543210", customer_type="retail")
                    service.add_customer("Priya Sharma", "priya@example.com", "+919876543211", customer_type="wholesale")
                    service.add_customer("Tech Solutions Pvt Ltd", "tech@example.com", "+919876543212", 
                                       customer_type="corporate", company_name="Tech Solutions")
                
                # Add sample products
                if len(service.get_products()) == 0:
                    service.add_product("Laptop", 45000.00, 10, category="Electronics", cost_price=38000)
                    service.add_product("Mouse", 500.00, 50, category="Electronics", cost_price=350)
                    service.add_product("Keyboard", 1500.00, 30, category="Electronics", cost_price=1200)
                    service.add_product("Monitor", 12000.00, 15, category="Electronics", cost_price=10000)
                
                st.session_state.last_action = "Sample data added successfully!"
                st.session_state.show_success = True
                st.rerun()
            except Exception as e:
                st.error(f"Error adding sample data: {e}")
        
        st.markdown("---")
        st.markdown("### Data Export")
        st.info("📥 Data export feature coming soon...")
        
        st.markdown("---")
        st.markdown("### Database Maintenance")
        st.warning("⚠️ Advanced features - use with caution!")