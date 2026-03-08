# app/analytics.py
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from app.models import CRPM
from app.utils import to_float

service = CRPM()


def _purchases_df() -> pd.DataFrame:
    """Return all purchases as a DataFrame with parsed datetimes and helpful columns."""
    rows = service.get_all_purchases()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # normalize column names and types
    if "purchased_at" in df.columns:
        df["purchased_at"] = pd.to_datetime(df["purchased_at"], errors="coerce")
    else:
        df["purchased_at"] = pd.NaT
    df["total_cost"] = pd.to_numeric(df.get("total_cost", 0.0), errors="coerce").fillna(0.0)
    df["quantity"] = pd.to_numeric(df.get("quantity", 0), errors="coerce").fillna(0).astype(int)
    return df


def total_revenue_and_count(date_from: str = None, date_to: str = None) -> Dict[str, Any]:
    """Return total revenue and purchase count for an optional date range.
    Always returns keys: revenue, count, avg_order.
    """
    df = _purchases_df()
    if df.empty:
        return {"revenue": 0.0, "count": 0, "avg_order": 0.0}
    if date_from:
        df = df[df["purchased_at"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["purchased_at"] <= pd.to_datetime(date_to)]
    revenue = float(df["total_cost"].sum())
    count = int(df.shape[0])
    avg_order = float(df["total_cost"].mean()) if count else 0.0
    return {"revenue": revenue, "count": count, "avg_order": avg_order}


def revenue_timeseries(freq: str = "M", periods: int = 12) -> pd.DataFrame:
    """Return a timeseries DataFrame aggregated by freq (e.g., 'D','W','M') with columns: period, revenue"""
    df = _purchases_df()
    if df.empty:
        # return empty frame with period column
        return pd.DataFrame(columns=["period", "revenue"])
    ts = df.set_index("purchased_at")["total_cost"].resample(freq).sum().rename("revenue")
    ts = ts.asfreq(freq, fill_value=0)
    df_ts = ts.reset_index().rename(columns={"purchased_at": "period"})
    # limit to last `periods` if requested
    if periods is not None:
        df_ts = df_ts.tail(periods)
    return df_ts


def monthly_sales_breakdown(months: int = 12) -> pd.DataFrame:
    """Returns monthly period aggregates: period, revenue, quantity, orders (latest first)."""
    df = _purchases_df()
    if df.empty:
        return pd.DataFrame(columns=["period", "revenue", "quantity", "orders"])
    df["period"] = df["purchased_at"].dt.to_period("M").dt.to_timestamp()
    grp = df.groupby("period").agg(
        revenue=("total_cost", "sum"),
        quantity=("quantity", "sum"),
        orders=("id", "count"),
    )
    grp = grp.sort_index(ascending=False).reset_index().head(months)
    return grp


def top_customers(n: int = 5) -> List[Dict[str, Any]]:
    """Return top customers by total spend with orders count and last purchase date."""
    df = _purchases_df()
    if df.empty:
        return []
    grp = df.groupby("customer_name").agg(
        total_spent=("total_cost", "sum"),
        orders=("id", "count"),
        last_purchase=("purchased_at", "max"),
    )
    grp = grp.sort_values("total_spent", ascending=False).head(n).reset_index()
    grp["total_spent"] = grp["total_spent"].round(2)
    grp["last_purchase"] = grp["last_purchase"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return grp.to_dict(orient="records")


def product_performance(n: int = 10) -> List[Dict[str, Any]]:
    """Return products ranked by quantity sold and revenue, with last sold date."""
    df = _purchases_df()
    if df.empty:
        return []
    grp = df.groupby("product_name").agg(
        quantity_sold=("quantity", "sum"),
        revenue=("total_cost", "sum"),
        last_sold=("purchased_at", "max"),
    )
    grp = grp.sort_values("quantity_sold", ascending=False).head(n).reset_index()
    grp["revenue"] = grp["revenue"].round(2)
    grp["last_sold"] = grp["last_sold"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return grp.to_dict(orient="records")


def customers_summary() -> pd.DataFrame:
    """Return customers augmented with total_spent, orders_count, last_purchase."""
    df_p = _purchases_df()
    if df_p.empty:
        # fetch base customers to show columns
        from app.models import CRPM

        svc = CRPM()
        custs = svc.get_customers(include_inactive=True)
        return pd.DataFrame(custs)
    grp = df_p.groupby("customer_id").agg(
        total_spent=("total_cost", "sum"),
        orders_count=("id", "count"),
        last_purchase=("purchased_at", "max"),
    )
    base = pd.DataFrame(service.get_customers(include_inactive=True))
    if base.empty:
        return grp.reset_index()
    base = base.set_index("id").join(grp).reset_index()
    base["total_spent"] = base["total_spent"].fillna(0.0).round(2)
    base["orders_count"] = base["orders_count"].fillna(0).astype(int)
    base["last_purchase"] = pd.to_datetime(base["last_purchase"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return base


def products_summary() -> pd.DataFrame:
    """Return products augmented with total_sold, revenue_generated, last_sold."""
    df_p = _purchases_df()
    if df_p.empty:
        return pd.DataFrame(service.get_products(include_inactive=True))
    grp = df_p.groupby("product_id").agg(
        total_sold=("quantity", "sum"),
        revenue_generated=("total_cost", "sum"),
        last_sold=("purchased_at", "max"),
    )
    base = pd.DataFrame(service.get_products(include_inactive=True))
    if base.empty:
        return grp.reset_index()
    base = base.set_index("id").join(grp).reset_index()
    base["total_sold"] = base["total_sold"].fillna(0).astype(int)
    base["revenue_generated"] = base["revenue_generated"].fillna(0.0).round(2)
    base["last_sold"] = pd.to_datetime(base["last_sold"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return base

def sales_pivot_by_product(freq: str = "M"):
    """
    Pivot table: product vs time period showing quantity sold
    """

    df = _purchases_df()

    if df.empty:
        return pd.DataFrame()

    # ensure datetime
    df["purchased_at"] = pd.to_datetime(df["purchased_at"], errors="coerce")

    # create period column
    df["period"] = df["purchased_at"].dt.to_period(freq).dt.to_timestamp()

    pivot = df.pivot_table(
        index="product_name",
        columns="period",
        values="quantity",
        aggfunc="sum",
        fill_value=0
    )

    pivot = pivot.sort_index(axis=1)

    # cleaner column labels
    pivot.columns = pivot.columns.strftime("%Y-%m")

    return pivot