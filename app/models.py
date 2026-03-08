from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from app.db import get_conn


@dataclass
class Customer:
    id: Optional[int]
    name: str
    email: Optional[str]
    phone: Optional[str]
    active: int = 1


@dataclass
class Product:
    id: Optional[int]
    name: str
    price: float
    stock: int
    active: int = 1


@dataclass
class Purchase:
    id: Optional[int]
    customer_id: int
    product_id: int
    quantity: int
    total_cost: float


class CRPM:
    """High-level service exposing CRUD operations and purchase flow."""

    def __init__(self):
        from app.db import init_db

        init_db()

    # Customers
    def add_customer(self, name: str, email: str = None, phone: str = None) -> int:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?,?,?)",
            (name, email, phone),
        )
        conn.commit()
        cid = cur.lastrowid
        conn.close()
        return cid

    def get_customers(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        conn = get_conn()
        cur = conn.cursor()
        if include_inactive:
            cur.execute("SELECT * FROM customers ORDER BY id DESC")
        else:
            cur.execute("SELECT * FROM customers WHERE active=1 ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def update_customer(self, customer_id: int, **fields) -> None:
        allowed = ["name", "email", "phone", "active"]
        sets = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return
        params.append(customer_id)
        conn = get_conn()
        conn.execute(f"UPDATE customers SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    def delete_customer(self, customer_id: int) -> None:
        # Soft-delete (deactivate)
        self.update_customer(customer_id, active=0)

    # Products
    def add_product(self, name: str, price: float, stock: int = 0) -> int:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, price, stock) VALUES (?,?,?)",
            (name, price, stock),
        )
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return pid

    def get_products(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        conn = get_conn()
        cur = conn.cursor()
        if include_inactive:
            cur.execute("SELECT * FROM products ORDER BY id DESC")
        else:
            cur.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def update_product(self, product_id: int, **fields) -> None:
        allowed = ["name", "price", "stock", "active"]
        sets = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return
        params.append(product_id)
        conn = get_conn()
        conn.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    def delete_product(self, product_id: int) -> None:
        self.update_product(product_id, active=0)

    # Purchases
    def record_purchase(self, customer_id: int, product_id: int, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("Quantity must be > 0")
        conn = get_conn()
        cur = conn.cursor()
        # check product stock and price
        cur.execute("SELECT stock, price, active FROM products WHERE id = ?", (product_id,))
        prod = cur.fetchone()
        if not prod:
            conn.close()
            raise ValueError("Product not found")
        if prod[2] != 1:
            conn.close()
            raise ValueError("Product not active")
        stock, price = prod[0], prod[1]
        if stock < quantity:
            conn.close()
            raise ValueError("Insufficient stock")
        total = round(price * quantity, 2)
        # insert purchase
        cur.execute(
            "INSERT INTO purchases (customer_id, product_id, quantity, total_cost) VALUES (?,?,?,?)",
            (customer_id, product_id, quantity, total),
        )
        # update stock
        cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return pid

    def get_purchases_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT p.*, pr.name as product_name, pr.price as product_price FROM purchases p JOIN products pr ON p.product_id = pr.id WHERE p.customer_id = ? ORDER BY p.purchased_at DESC",
            (customer_id,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_all_purchases(self) -> List[Dict[str, Any]]:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT p.*, c.name as customer_name, pr.name as product_name FROM purchases p JOIN customers c ON p.customer_id = c.id JOIN products pr ON p.product_id = pr.id ORDER BY p.purchased_at DESC"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows