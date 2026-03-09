from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db import get_conn


@dataclass
class Customer:
    id: Optional[int]
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    postal_code: Optional[str] = None
    customer_type: str = "retail"
    company_name: Optional[str] = None
    tax_id: Optional[str] = None
    active: int = 1
    status: str = "active"
    loyalty_points: int = 0
    notes: Optional[str] = None


@dataclass
class Product:
    id: Optional[int]
    name: str
    sku: Optional[str] = None
    price: float = 0.0
    cost_price: float = 0.0
    stock: int = 0
    reorder_level: int = 10
    reorder_quantity: int = 50
    category: str = "General"
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    unit: str = "piece"
    barcode: Optional[str] = None
    supplier: Optional[str] = None
    active: int = 1
    status: str = "available"
    is_featured: int = 0
    tags: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Purchase:
    id: Optional[int]
    customer_id: int
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    tax_percent: float = 0.0
    tax_amount: float = 0.0
    total_cost: float = 0.0
    payment_method: str = "cash"
    payment_status: str = "paid"
    transaction_id: Optional[str] = None
    order_status: str = "completed"
    delivery_status: str = "delivered"
    notes: Optional[str] = None
    purchased_at: Optional[datetime] = None


class CRPM:
    """Enhanced service with comprehensive CRUD operations and business logic."""

    def __init__(self):
        from app.db import init_db
        init_db()

    # ==================== CUSTOMER OPERATIONS ====================
    
    def add_customer(
        self,
        name: str,
        email: str = None,
        phone: str = None,
        address: str = None,
        city: str = None,
        state: str = None,
        country: str = "India",
        postal_code: str = None,
        customer_type: str = "retail",
        company_name: str = None,
        tax_id: str = None,
        notes: str = None,
    ) -> int:
        """Add a new customer with extended fields."""
        if not name or not name.strip():
            raise ValueError("Customer name is required")
        
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO customers 
                (name, email, phone, address, city, state, country, postal_code,
                 customer_type, company_name, tax_id, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    name.strip(),
                    email.strip() if email else None,
                    phone.strip() if phone else None,
                    address.strip() if address else None,
                    city.strip() if city else None,
                    state.strip() if state else None,
                    country,
                    postal_code.strip() if postal_code else None,
                    customer_type,
                    company_name.strip() if company_name else None,
                    tax_id.strip() if tax_id else None,
                    notes.strip() if notes else None,
                ),
            )
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_customers(self, include_inactive: bool = False, search: str = None) -> List[Dict[str, Any]]:
        """Get all customers with optional filtering."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            query = "SELECT * FROM customers"
            conditions = []
            params = []
            
            if not include_inactive:
                conditions.append("active = 1")
            
            if search:
                conditions.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR company_name LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param] * 4)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY id DESC"
            
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get a single customer by ID."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_customer(self, customer_id: int, **fields) -> None:
        """Update customer with flexible fields."""
        allowed = [
            "name", "email", "phone", "address", "city", "state", "country",
            "postal_code", "customer_type", "company_name", "tax_id",
            "active", "status", "loyalty_points", "notes"
        ]
        sets = []
        params = []
        
        for k, v in fields.items():
            if k in allowed and v is not None:
                sets.append(f"{k} = ?")
                params.append(v)
        
        if not sets:
            return
        
        params.append(customer_id)
        conn = get_conn()
        try:
            conn.execute(
                f"UPDATE customers SET {', '.join(sets)} WHERE id = ?",
                params
            )
            conn.commit()
        finally:
            conn.close()

    def delete_customer(self, customer_id: int, hard_delete: bool = False) -> None:
        """Delete or deactivate a customer."""
        if hard_delete:
            conn = get_conn()
            try:
                conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                conn.commit()
            finally:
                conn.close()
        else:
            self.update_customer(customer_id, active=0, status="inactive")

    # ==================== PRODUCT OPERATIONS ====================
    
    def add_product(
        self,
        name: str,
        price: float,
        stock: int = 0,
        sku: str = None,
        cost_price: float = 0.0,
        category: str = "General",
        subcategory: str = None,
        brand: str = None,
        description: str = None,
        unit: str = "piece",
        reorder_level: int = 10,
        reorder_quantity: int = 50,
        barcode: str = None,
        supplier: str = None,
        tags: str = None,
        notes: str = None,
    ) -> int:
        """Add a new product with extended fields."""
        if not name or not name.strip():
            raise ValueError("Product name is required")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if stock < 0:
            raise ValueError("Stock cannot be negative")
        
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO products 
                (name, sku, price, cost_price, stock, reorder_level, reorder_quantity,
                 category, subcategory, brand, description, unit, barcode, supplier, tags, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    name.strip(),
                    sku.strip() if sku else None,
                    float(price),
                    float(cost_price),
                    int(stock),
                    int(reorder_level),
                    int(reorder_quantity),
                    category,
                    subcategory,
                    brand,
                    description,
                    unit,
                    barcode,
                    supplier,
                    tags,
                    notes,
                ),
            )
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_products(
        self,
        include_inactive: bool = False,
        category: str = None,
        search: str = None,
        low_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all products with optional filtering."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            query = "SELECT * FROM products"
            conditions = []
            params = []
            
            if not include_inactive:
                conditions.append("active = 1")
            
            if category:
                conditions.append("category = ?")
                params.append(category)
            
            if search:
                conditions.append("(name LIKE ? OR sku LIKE ? OR brand LIKE ? OR tags LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param] * 4)
            
            if low_stock_only:
                conditions.append("stock <= reorder_level")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY id DESC"
            
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get a single product by ID."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_product(self, product_id: int, **fields) -> None:
        """Update product with flexible fields."""
        allowed = [
            "name", "sku", "price", "cost_price", "stock", "reorder_level",
            "reorder_quantity", "category", "subcategory", "brand", "description",
            "unit", "barcode", "supplier", "active", "status", "is_featured",
            "tags", "notes"
        ]
        sets = []
        params = []
        
        for k, v in fields.items():
            if k in allowed and v is not None:
                sets.append(f"{k} = ?")
                params.append(v)
        
        if not sets:
            return
        
        params.append(product_id)
        conn = get_conn()
        try:
            conn.execute(
                f"UPDATE products SET {', '.join(sets)} WHERE id = ?",
                params
            )
            conn.commit()
        finally:
            conn.close()

    def delete_product(self, product_id: int, hard_delete: bool = False) -> None:
        """Delete or deactivate a product."""
        if hard_delete:
            conn = get_conn()
            try:
                conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
                conn.commit()
            finally:
                conn.close()
        else:
            self.update_product(product_id, active=0, status="discontinued")

    def get_categories(self) -> List[str]:
        """Get all unique product categories."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT category FROM products WHERE active = 1 ORDER BY category")
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    # ==================== PURCHASE OPERATIONS ====================
    
    def record_purchase(
        self,
        customer_id: int,
        product_id: int,
        quantity: int,
        discount_percent: float = 0.0,
        discount_amount: float = 0.0,
        tax_percent: float = 0.0,
        payment_method: str = "cash",
        payment_status: str = "paid",
        transaction_id: str = None,
        notes: str = None,
    ) -> int:
        """Record a purchase with detailed pricing and automatic stock update."""
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        
        conn = get_conn()
        try:
            cur = conn.cursor()
            
            # Get product details
            cur.execute("SELECT stock, price, active, status FROM products WHERE id = ?", (product_id,))
            prod = cur.fetchone()
            if not prod:
                raise ValueError("Product not found")
            if prod[2] != 1:
                raise ValueError("Product is not active")
            if prod[3] == "discontinued":
                raise ValueError("Product is discontinued")
            
            stock, unit_price = prod[0], prod[1]
            
            if stock < quantity:
                raise ValueError(f"Insufficient stock. Available: {stock}, Requested: {quantity}")
            
            # Calculate amounts
            subtotal = round(unit_price * quantity, 2)
            
            # Apply discount (either percent or fixed amount, not both)
            if discount_percent > 0:
                discount_amount = round(subtotal * discount_percent / 100, 2)
            
            amount_after_discount = subtotal - discount_amount
            
            # Apply tax
            if tax_percent > 0:
                tax_amount = round(amount_after_discount * tax_percent / 100, 2)
            else:
                tax_amount = 0.0
            
            total_cost = round(amount_after_discount + tax_amount, 2)
            
            # Insert purchase
            cur.execute(
                """INSERT INTO purchases 
                (customer_id, product_id, quantity, unit_price, subtotal, 
                 discount_percent, discount_amount, tax_percent, tax_amount, total_cost,
                 payment_method, payment_status, transaction_id, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    customer_id, product_id, quantity, unit_price, subtotal,
                    discount_percent, discount_amount, tax_percent, tax_amount, total_cost,
                    payment_method, payment_status, transaction_id, notes
                ),
            )
            
            # Update stock
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
            
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_purchases_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all purchases for a specific customer."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT p.*, pr.name as product_name, pr.sku, pr.category
                FROM purchases p 
                JOIN products pr ON p.product_id = pr.id 
                WHERE p.customer_id = ? 
                ORDER BY p.purchased_at DESC""",
                (customer_id,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def get_all_purchases(self, limit: int = None, date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """Get all purchases with optional filters."""
        conn = get_conn()
        try:
            cur = conn.cursor()
            query = """
                SELECT p.*, 
                       c.name as customer_name, c.email as customer_email,
                       pr.name as product_name, pr.sku, pr.category
                FROM purchases p 
                JOIN customers c ON p.customer_id = c.id 
                JOIN products pr ON p.product_id = pr.id
            """
            conditions = []
            params = []
            
            if date_from:
                conditions.append("p.purchased_at >= ?")
                params.append(date_from)
            
            if date_to:
                conditions.append("p.purchased_at <= ?")
                params.append(date_to)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY p.purchased_at DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def update_purchase_status(
        self,
        purchase_id: int,
        order_status: str = None,
        payment_status: str = None,
        delivery_status: str = None
    ) -> None:
        """Update purchase status fields."""
        updates = {}
        if order_status:
            updates["order_status"] = order_status
        if payment_status:
            updates["payment_status"] = payment_status
        if delivery_status:
            updates["delivery_status"] = delivery_status
        
        if not updates:
            return
        
        sets = [f"{k} = ?" for k in updates.keys()]
        params = list(updates.values())
        params.append(purchase_id)
        
        conn = get_conn()
        try:
            conn.execute(
                f"UPDATE purchases SET {', '.join(sets)} WHERE id = ?",
                params
            )
            conn.commit()
        finally:
            conn.close()