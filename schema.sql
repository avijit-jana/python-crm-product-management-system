-- Enhanced CRPM Database Schema
PRAGMA foreign_keys = ON;

-- Customers table with extended fields
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    -- Additional contact information
    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'India',
    postal_code TEXT,
    -- Business information
    customer_type TEXT DEFAULT 'retail' CHECK(customer_type IN ('retail', 'wholesale', 'corporate')),
    company_name TEXT,
    tax_id TEXT,
    -- Status and metadata
    active INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'suspended')),
    loyalty_points INTEGER DEFAULT 0,
    notes TEXT,
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Products table with extended fields
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    -- Pricing and cost
    price REAL NOT NULL CHECK(price >= 0),
    cost_price REAL DEFAULT 0 CHECK(cost_price >= 0),
    -- Inventory
    stock INTEGER DEFAULT 0 CHECK(stock >= 0),
    reorder_level INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 50,
    -- Categorization
    category TEXT DEFAULT 'General',
    subcategory TEXT,
    brand TEXT,
    -- Product details
    description TEXT,
    unit TEXT DEFAULT 'piece' CHECK(unit IN ('piece', 'kg', 'liter', 'meter', 'pack')),
    barcode TEXT,
    supplier TEXT,
    -- Status and metadata
    active INTEGER DEFAULT 1,
    status TEXT DEFAULT 'available' CHECK(status IN ('available', 'out_of_stock', 'discontinued')),
    is_featured INTEGER DEFAULT 0,
    tags TEXT,
    notes TEXT,
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Purchases table with extended fields
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    -- Quantities and pricing
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    subtotal REAL NOT NULL CHECK(subtotal >= 0),
    discount_percent REAL DEFAULT 0 CHECK(discount_percent >= 0 AND discount_percent <= 100),
    discount_amount REAL DEFAULT 0 CHECK(discount_amount >= 0),
    tax_percent REAL DEFAULT 0 CHECK(tax_percent >= 0),
    tax_amount REAL DEFAULT 0 CHECK(tax_amount >= 0),
    total_cost REAL NOT NULL CHECK(total_cost >= 0),
    -- Transaction details
    payment_method TEXT DEFAULT 'cash' CHECK(payment_method IN ('cash', 'card', 'upi', 'bank_transfer', 'credit')),
    payment_status TEXT DEFAULT 'paid' CHECK(payment_status IN ('paid', 'pending', 'partial', 'refunded')),
    transaction_id TEXT,
    -- Order information
    order_status TEXT DEFAULT 'completed' CHECK(order_status IN ('completed', 'pending', 'cancelled', 'returned')),
    delivery_status TEXT DEFAULT 'delivered' CHECK(delivery_status IN ('delivered', 'pending', 'in_transit', 'cancelled')),
    -- Additional information
    notes TEXT,
    -- Timestamps
    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    delivered_at DATETIME,
    -- Foreign keys
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE RESTRICT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status, active);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status, active);
CREATE INDEX IF NOT EXISTS idx_purchases_customer ON purchases(customer_id);
CREATE INDEX IF NOT EXISTS idx_purchases_product ON purchases(product_id);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchased_at);
CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(order_status);

-- Triggers to automatically update the updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_customers_timestamp 
AFTER UPDATE ON customers
BEGIN
    UPDATE customers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_products_timestamp 
AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_purchases_timestamp 
AFTER UPDATE ON purchases
BEGIN
    UPDATE purchases SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to update product status based on stock
CREATE TRIGGER IF NOT EXISTS update_product_status_on_stock_change
AFTER UPDATE OF stock ON products
BEGIN
    UPDATE products 
    SET status = CASE 
        WHEN NEW.stock = 0 THEN 'out_of_stock'
        WHEN NEW.stock > 0 AND NEW.active = 1 THEN 'available'
        ELSE status
    END
    WHERE id = NEW.id;
END;