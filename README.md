# Basket Craft Monthly Sales Pipeline

ELT pipeline that extracts order data from the Basket Craft MySQL database, loads it into an AWS RDS PostgreSQL instance holding the raw Basket Craft data, and transforms it into a `monthly_sales` summary table for the monthly sales dashboard.

**Dashboard metrics:** revenue, order count, and average order value, grouped by product and month.

## Architecture

```
run_pipeline.py
    |
    +-- 1. extract.py   (MySQL -> DataFrame)
    +-- 2. load.py      (DataFrame -> raw_order_items on RDS)
    +-- 3. transform.py (raw_order_items -> monthly_sales on RDS)
```

- **Source:** MySQL at `db.isba.co:3306`, database `basket_craft` (tables `orders`, `order_items`, `products`).
- **Destination:** AWS RDS PostgreSQL (`basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com:5432`, database `basket_craft`). Stores both the raw staging table and the `monthly_sales` aggregate.
- **Revenue:** gross (sum of `order_items.price_usd`, no refund deduction).

### Destination tables

| Table | Purpose |
|---|---|
| `raw_order_items` | Full joined MySQL extract, truncated and reloaded each run |
| `monthly_sales(product_name, month, revenue, order_count, avg_order_value)` | Final per-product/month aggregate |

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file with MySQL source and RDS destination credentials:
   ```
   MYSQL_HOST=db.isba.co
   MYSQL_PORT=3306
   MYSQL_USER=...
   MYSQL_PASSWORD=...
   MYSQL_DATABASE=basket_craft

   PG_HOST=basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com
   PG_PORT=5432
   PG_USER=...
   PG_PASSWORD=...
   PG_DATABASE=basket_craft
   ```

## Running the pipeline

Manual trigger only:

```bash
python run_pipeline.py
```

Each stage prints a status line (`[extract] N rows extracted`, etc.) and the pipeline halts on any failure — no partial loads.

## Verifying results

```bash
python -c "
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(host=os.environ['PG_HOST'], port=int(os.environ['PG_PORT']),
    user=os.environ['PG_USER'], password=os.environ['PG_PASSWORD'], dbname=os.environ['PG_DATABASE'])
cur = conn.cursor()
cur.execute('SELECT * FROM monthly_sales ORDER BY month, product_name LIMIT 20')
for row in cur.fetchall(): print(row)
"
```

## Tests

```bash
pytest
```

## Project files

| File | Responsibility |
|---|---|
| `extract.py` | MySQL query joining `orders`, `order_items`, `products` into a DataFrame |
| `load.py` | Bulk-inserts the DataFrame into `raw_order_items` on RDS |
| `transform.py` | Rebuilds `monthly_sales` from the staging table |
| `run_pipeline.py` | Orchestrates extract -> load -> transform |
| `docs/superpowers/` | Design spec and implementation plan |
