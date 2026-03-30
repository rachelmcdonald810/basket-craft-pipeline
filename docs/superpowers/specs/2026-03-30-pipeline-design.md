# Basket Craft Monthly Sales Pipeline — Design Spec

**Date:** 2026-03-30
**Status:** Approved

## Overview

An ELT pipeline that extracts order data from the Basket Craft MySQL database, loads it into a local PostgreSQL instance (Docker), and transforms it into a `monthly_sales` summary table for a monthly sales dashboard.

**Dashboard metrics:** revenue, order count, and average order value — grouped by product and month.

---

## Architecture

```
run_pipeline.py (manual trigger)
    │
    ├─ 1. extract.py   → DataFrame
    ├─ 2. load.py      → raw_order_items (PostgreSQL staging)
    └─ 3. transform.py → monthly_sales (PostgreSQL final)
```

Pattern: **ELT** (Extract → Load raw → Transform in Postgres)

---

## Source

- **Database:** MySQL at `db.isba.co:3306`, database `basket_craft`
- **Tables used:**
  - `order_items` — `order_item_id`, `order_id`, `product_id`, `price_usd`, `created_at`
  - `orders` — `order_id`, `created_at`
  - `products` — `product_id`, `product_name`
- **Revenue definition:** gross (sum of `order_items.price_usd`, no refund deduction)
- **Category definition:** each `product_name` is its own category

---

## Destination

- **Database:** PostgreSQL in Docker (local)
- **Staging tables** (full replace each run):
  - `raw_order_items` — raw joined extract from MySQL
- **Final table:**
  - `monthly_sales(product_name, month, revenue, order_count, avg_order_value)`

---

## Components

| File | Responsibility |
|------|---------------|
| `extract.py` | Connects to MySQL, joins `orders`/`order_items`/`products`, returns a DataFrame |
| `load.py` | Truncates and inserts raw DataFrame into `raw_order_items` in PostgreSQL |
| `transform.py` | Reads staging table, computes aggregates, rebuilds `monthly_sales` |
| `run_pipeline.py` | Orchestrates extract → load → transform, prints stage status |
| `.env` | MySQL credentials (`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`) + Postgres credentials (`PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE`) |
| `requirements.txt` | `pymysql`, `psycopg2-binary`, `pandas`, `python-dotenv` |

---

## Data Flow

### Extract

Single query joining all three source tables:

```sql
SELECT
    o.order_id,
    DATE_FORMAT(o.created_at, '%Y-%m') AS month,
    p.product_name,
    oi.price_usd
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
```

Returns a pandas DataFrame passed directly to load.

### Load (staging)

Truncate `raw_order_items`, then insert the full DataFrame. Full replace on every run — no incremental logic.

### Transform

Truncate `monthly_sales`, then populate from staging:

```sql
INSERT INTO monthly_sales (product_name, month, revenue, order_count, avg_order_value)
SELECT
    product_name,
    month,
    SUM(price_usd)                        AS revenue,
    COUNT(DISTINCT order_id)              AS order_count,
    SUM(price_usd) / COUNT(DISTINCT order_id) AS avg_order_value
FROM raw_order_items
GROUP BY product_name, month
```

---

## Error Handling

- Each stage prints a status line on success (e.g., `[extract] 4,821 rows extracted`)
- Unhandled exceptions surface with Python's default traceback
- `run_pipeline.py` halts immediately on any stage failure — no partial loads

---

## Running the Pipeline

```bash
python run_pipeline.py
```

Manual trigger only. No cron scheduling.

---

## Verification

```bash
psql -c "SELECT * FROM monthly_sales ORDER BY month, product_name LIMIT 20;"
```
