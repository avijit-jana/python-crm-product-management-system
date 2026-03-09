# app/analytics.py
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from app.models import CRPM
from app.utils import to_float

service = CRPM()


def _purchases_df() -> pd.DataFrame:
    """Return all purchases as a DataFrame with parsed datetimes and helpful columns."""
    rows = service.get_all_purchases()
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    
    # Normalize column names and types
    if "purchased_at" in df.columns:
        df["purchased_at"] = pd.to_datetime(df["purchased_at"], errors="coerce")
    else:
        df["purchased_at"] = pd.NaT
    
    # Numeric columns
    numeric_cols = [
        "total_cost", "subtotal", "discount_amount", "tax_amount",
        "quantity", "unit_price"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)
    
    if "quantity" in df.columns:
        df["quantity"] = df["quantity"].astype(int)
    
    return df


def total_revenue_and_count(date_from: str = None, date_to: str = None) -> Dict[str, Any]:
    """Return comprehensive revenue metrics for an optional date range."""
    df = _purchases_df()
    if df.empty:
        return {
            "revenue": 0.0,
            "count": 0,
            "avg_order": 0.0,
            "total_items": 0,
            "total_discount": 0.0,
            "total_tax": 0.0,
        }
    
    # Apply date filters
    if date_from:
        df = df[df["purchased_at"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["purchased_at"] <= pd.to_datetime(date_to)]
    
    if df.empty:
        return {
            "revenue": 0.0,
            "count": 0,
            "avg_order": 0.0,
            "total_items": 0,
            "total_discount": 0.0,
            "total_tax": 0.0,
        }
    
    revenue = float(df["total_cost"].sum())
    count = int(df.shape[0])
    avg_order = float(df["total_cost"].mean()) if count else 0.0
    total_items = int(df["quantity"].sum())
    total_discount = float(df.get("discount_amount", pd.Series([0])).sum())
    total_tax = float(df.get("tax_amount", pd.Series([0])).sum())
    
    return {
        "revenue": revenue,
        "count": count,
        "avg_order": avg_order,
        "total_items": total_items,
        "total_discount": total_discount,
        "total_tax": total_tax,
    }


def revenue_timeseries(freq: str = "M", periods: int = 12) -> pd.DataFrame:
    """Return a timeseries DataFrame aggregated by freq with revenue and orders."""
    df = _purchases_df()
    if df.empty:
        return pd.DataFrame(columns=["period", "revenue", "orders", "items"])
    
    ts = df.set_index("purchased_at")
    
    # Aggregate multiple metrics
    agg_data = ts.resample(freq).agg({
        "total_cost": "sum",
        "id": "count",
        "quantity": "sum"
    })
    
    agg_data.columns = ["revenue", "orders", "items"]
    agg_data = agg_data.asfreq(freq, fill_value=0)
    
    df_ts = agg_data.reset_index().rename(columns={"purchased_at": "period"})
    
    # Limit to last `periods` if requested
    if periods is not None:
        df_ts = df_ts.tail(periods)
    
    return df_ts


def monthly_sales_breakdown(months: int = 12) -> pd.DataFrame:
    """Returns monthly aggregates with enhanced metrics."""
    df = _purchases_df()
    if df.empty:
        return pd.DataFrame(columns=[
            "period", "revenue", "quantity", "orders", 
            "avg_order_value", "total_discount", "total_tax"
        ])
    
    df["period"] = df["purchased_at"].dt.to_period("M").dt.to_timestamp()
    
    grp = df.groupby("period").agg(
        revenue=("total_cost", "sum"),
        quantity=("quantity", "sum"),
        orders=("id", "count"),
        total_discount=("discount_amount", "sum"),
        total_tax=("tax_amount", "sum"),
    )
    
    grp["avg_order_value"] = grp["revenue"] / grp["orders"]
    grp = grp.round(2)
    grp = grp.sort_index(ascending=False).reset_index().head(months)
    
    return grp


def top_customers(n: int = 10, by: str = "revenue") -> List[Dict[str, Any]]:
    """Return top customers by spend or order count with detailed metrics."""
    df = _purchases_df()
    if df.empty:
        return []
    
    grp = df.groupby(["customer_id", "customer_name"]).agg(
        total_spent=("total_cost", "sum"),
        orders=("id", "count"),
        items_purchased=("quantity", "sum"),
        avg_order_value=("total_cost", "mean"),
        last_purchase=("purchased_at", "max"),
        first_purchase=("purchased_at", "min"),
    )
    
    # Sort by specified metric
    if by == "orders":
        grp = grp.sort_values("orders", ascending=False)
    else:
        grp = grp.sort_values("total_spent", ascending=False)
    
    grp = grp.head(n).reset_index()
    
    # Format output
    grp["total_spent"] = grp["total_spent"].round(2)
    grp["avg_order_value"] = grp["avg_order_value"].round(2)
    grp["last_purchase"] = grp["last_purchase"].dt.strftime("%Y-%m-%d")
    grp["first_purchase"] = grp["first_purchase"].dt.strftime("%Y-%m-%d")
    
    return grp.to_dict(orient="records")


def product_performance(n: int = 10, by: str = "quantity") -> List[Dict[str, Any]]:
    """Return products ranked by quantity or revenue with comprehensive metrics."""
    df = _purchases_df()
    if df.empty:
        return []
    
    grp = df.groupby(["product_id", "product_name"]).agg(
        quantity_sold=("quantity", "sum"),
        revenue=("total_cost", "sum"),
        orders=("id", "count"),
        avg_price=("unit_price", "mean"),
        last_sold=("purchased_at", "max"),
    )
    
    # Sort by specified metric
    if by == "revenue":
        grp = grp.sort_values("revenue", ascending=False)
    else:
        grp = grp.sort_values("quantity_sold", ascending=False)
    
    grp = grp.head(n).reset_index()
    
    # Format output
    grp["revenue"] = grp["revenue"].round(2)
    grp["avg_price"] = grp["avg_price"].round(2)
    grp["last_sold"] = grp["last_sold"].dt.strftime("%Y-%m-%d")
    
    # Add category if available
    if "category" in df.columns:
        category_map = df.groupby("product_id")["category"].first()
        grp["category"] = grp["product_id"].map(category_map)
    
    return grp.to_dict(orient="records")


def customers_summary() -> pd.DataFrame:
    """Return customers augmented with purchase metrics."""
    df_p = _purchases_df()
    base = pd.DataFrame(service.get_customers(include_inactive=True))
    
    if base.empty:
        return pd.DataFrame()
    
    if df_p.empty:
        # No purchases yet, just return base customer data
        base["total_spent"] = 0.0
        base["orders_count"] = 0
        base["items_purchased"] = 0
        base["last_purchase"] = None
        return base
    
    # Aggregate purchase metrics
    grp = df_p.groupby("customer_id").agg(
        total_spent=("total_cost", "sum"),
        orders_count=("id", "count"),
        items_purchased=("quantity", "sum"),
        last_purchase=("purchased_at", "max"),
    )
    
    # Join with base customer data
    base = base.set_index("id").join(grp).reset_index()
    
    # Fill missing values and format
    base["total_spent"] = base["total_spent"].fillna(0.0).round(2)
    base["orders_count"] = base["orders_count"].fillna(0).astype(int)
    base["items_purchased"] = base["items_purchased"].fillna(0).astype(int)
    base["last_purchase"] = pd.to_datetime(base["last_purchase"], errors="coerce")
    base["last_purchase"] = base["last_purchase"].dt.strftime("%Y-%m-%d")
    
    return base


def products_summary() -> pd.DataFrame:
    """Return products augmented with sales metrics and stock status."""
    df_p = _purchases_df()
    base = pd.DataFrame(service.get_products(include_inactive=True))
    
    if base.empty:
        return pd.DataFrame()
    
    if df_p.empty:
        # No sales yet
        base["total_sold"] = 0
        base["revenue_generated"] = 0.0
        base["orders_count"] = 0
        base["last_sold"] = None
        base["stock_status"] = base.apply(
            lambda x: "Low Stock" if x.get("stock", 0) <= x.get("reorder_level", 0) else "In Stock",
            axis=1
        )
        return base
    
    # Aggregate sales metrics
    grp = df_p.groupby("product_id").agg(
        total_sold=("quantity", "sum"),
        revenue_generated=("total_cost", "sum"),
        orders_count=("id", "count"),
        last_sold=("purchased_at", "max"),
    )
    
    # Join with base product data
    base = base.set_index("id").join(grp).reset_index()
    
    # Fill missing values and format
    base["total_sold"] = base["total_sold"].fillna(0).astype(int)
    base["revenue_generated"] = base["revenue_generated"].fillna(0.0).round(2)
    base["orders_count"] = base["orders_count"].fillna(0).astype(int)
    base["last_sold"] = pd.to_datetime(base["last_sold"], errors="coerce")
    base["last_sold"] = base["last_sold"].dt.strftime("%Y-%m-%d")
    
    # Add stock status
    base["stock_status"] = base.apply(
        lambda x: "Out of Stock" if x.get("stock", 0) == 0 
        else "Low Stock" if x.get("stock", 0) <= x.get("reorder_level", 0)
        else "In Stock",
        axis=1
    )
    
    # Add profit margin if cost_price is available
    if "cost_price" in base.columns and "price" in base.columns:
        base["profit_margin"] = ((base["price"] - base["cost_price"]) / base["price"] * 100).round(2)
    
    return base


def sales_pivot_by_product(freq: str = "M", periods: int = 12) -> pd.DataFrame:
    """Pivot table: product vs time period showing quantity sold."""
    df = _purchases_df()
    
    if df.empty:
        return pd.DataFrame()
    
    # Ensure datetime
    df["purchased_at"] = pd.to_datetime(df["purchased_at"], errors="coerce")
    
    # Create period column
    df["period"] = df["purchased_at"].dt.to_period(freq).dt.to_timestamp()
    
    # Create pivot table
    pivot = df.pivot_table(
        index="product_name",
        columns="period",
        values="quantity",
        aggfunc="sum",
        fill_value=0
    )
    
    # Sort columns (periods) and limit to recent periods
    pivot = pivot.sort_index(axis=1)
    if periods:
        pivot = pivot.iloc[:, -periods:]
    
    # Format column labels
    if freq == "M":
        pivot.columns = pivot.columns.strftime("%Y-%m")
    elif freq == "D":
        pivot.columns = pivot.columns.strftime("%Y-%m-%d")
    elif freq == "W":
        pivot.columns = pivot.columns.strftime("%Y-W%W")
    
    return pivot


def category_performance() -> pd.DataFrame:
    """Analyze performance by product category."""
    df = _purchases_df()
    
    if df.empty or "category" not in df.columns:
        return pd.DataFrame()
    
    grp = df.groupby("category").agg(
        revenue=("total_cost", "sum"),
        quantity_sold=("quantity", "sum"),
        orders=("id", "count"),
        avg_order_value=("total_cost", "mean"),
    )
    
    grp = grp.sort_values("revenue", ascending=False)
    grp["revenue"] = grp["revenue"].round(2)
    grp["avg_order_value"] = grp["avg_order_value"].round(2)
    
    return grp.reset_index()


def payment_method_analysis() -> pd.DataFrame:
    """Analyze sales by payment method."""
    df = _purchases_df()
    
    if df.empty or "payment_method" not in df.columns:
        return pd.DataFrame()
    
    grp = df.groupby("payment_method").agg(
        transactions=("id", "count"),
        total_amount=("total_cost", "sum"),
        avg_transaction=("total_cost", "mean"),
    )
    
    grp = grp.sort_values("total_amount", ascending=False)
    grp["total_amount"] = grp["total_amount"].round(2)
    grp["avg_transaction"] = grp["avg_transaction"].round(2)
    grp["percentage"] = (grp["total_amount"] / grp["total_amount"].sum() * 100).round(2)
    
    return grp.reset_index()


def low_stock_alerts() -> List[Dict[str, Any]]:
    """Get products that are at or below reorder level."""
    products = service.get_products()
    
    low_stock = [
        p for p in products 
        if p.get("stock", 0) <= p.get("reorder_level", 0)
    ]
    
    # Sort by stock level (lowest first)
    low_stock.sort(key=lambda x: x.get("stock", 0))
    
    return low_stock


def customer_retention_metrics() -> Dict[str, Any]:
    """Calculate customer retention and activity metrics."""
    df = _purchases_df()
    
    if df.empty:
        return {
            "total_customers": 0,
            "active_customers": 0,
            "new_customers_this_month": 0,
            "repeat_customer_rate": 0.0,
        }
    
    # Get customer purchase counts
    customer_orders = df.groupby("customer_id").size()
    
    # Active customers (purchased in last 30 days)
    thirty_days_ago = pd.Timestamp.now() - pd.Timedelta(days=30)
    recent_df = df[df["purchased_at"] >= thirty_days_ago]
    active_customers = recent_df["customer_id"].nunique()
    
    # New customers this month
    month_start = pd.Timestamp.now().replace(day=1)
    first_purchases = df.groupby("customer_id")["purchased_at"].min()
    new_this_month = (first_purchases >= month_start).sum()
    
    # Repeat customer rate
    repeat_customers = (customer_orders > 1).sum()
    total_customers = len(customer_orders)
    repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
    
    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "new_customers_this_month": new_this_month,
        "repeat_customer_rate": round(repeat_rate, 2),
        "repeat_customers": repeat_customers,
    }


def sales_forecast_simple(periods: int = 3) -> pd.DataFrame:
    """Simple moving average forecast for next periods."""
    df = revenue_timeseries(freq="M", periods=12)
    
    if df.empty or len(df) < 3:
        return pd.DataFrame()
    
    # Calculate moving average
    df["ma_3"] = df["revenue"].rolling(window=3).mean()
    
    # Simple forecast: use last MA value
    last_ma = df["ma_3"].iloc[-1]
    last_period = df["period"].iloc[-1]
    
    # Generate future periods
    future_periods = pd.date_range(
        start=last_period + pd.DateOffset(months=1),
        periods=periods,
        freq="MS"
    )
    
    forecast_df = pd.DataFrame({
        "period": future_periods,
        "forecast": [last_ma] * periods
    })
    
    return forecast_df