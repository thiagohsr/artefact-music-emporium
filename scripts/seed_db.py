"""Create the store's SQLite database if needed and load the source CSVs into it."""

import contextlib
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "emporio.sqlite"
CSV_DIR = ROOT / "data" / "csv_origin"
CSV_NAME = "desafio_tecnico_ai_eng - {table}.csv"

# Ordered so that parent tables load before the tables referencing them.
TABLES = ("categories", "customers", "products", "promotions", "orders", "order_items")

# customers.email is not UNIQUE because the source data has a repeated address.
SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    city TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    price_brl REAL NOT NULL CHECK (price_brl > 0),
    name TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL REFERENCES categories (category_id),
    description TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
    status TEXT NOT NULL CHECK (status IN ('active', 'coming_soon', 'discontinued')),
    specs TEXT NOT NULL CHECK (json_valid(specs)),
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
    description TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
) STRICT;

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_brl REAL NOT NULL CHECK (total_brl >= 0),
    payment_method TEXT NOT NULL,
    tracking_code TEXT,
    estimated_delivery TEXT,
    notes TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders (order_id),
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id)
) STRICT;
"""


def load_table(conn: sqlite3.Connection, table: str, csv_dir: Path) -> int:
    with (csv_dir / CSV_NAME.format(table=table)).open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        if set(reader.fieldnames or ()) != set(columns):
            raise ValueError(f"{table}: CSV columns {reader.fieldnames} do not match {columns}")

        placeholders = ", ".join(f":{column}" for column in columns)
        statement = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        rows = [{key: value or None for key, value in row.items()} for row in reader]

    conn.executemany(statement, rows)
    return len(rows)


def seed(db_path: Path, csv_dir: Path) -> dict[str, int]:
    """Replace the database contents with the CSVs, keeping the old data if any row fails."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        with conn:
            for table in reversed(TABLES):
                conn.execute(f"DELETE FROM {table}")
            return {table: load_table(conn, table, csv_dir) for table in TABLES}


def main() -> None:
    found = DB_PATH.exists()
    print(f"{'Found' if found else 'Creating'} {DB_PATH.relative_to(ROOT)}")
    try:
        counts = seed(DB_PATH, CSV_DIR)
    except (sqlite3.Error, OSError, ValueError) as error:
        hint = " If the schema changed, run: make db-reset" if found else ""
        sys.exit(f"Seeding failed, no data was changed: {error}.{hint}")

    for table, count in counts.items():
        print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()
