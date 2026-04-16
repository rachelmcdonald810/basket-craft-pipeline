import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CREATE_MONTHLY_SALES = """
CREATE TABLE IF NOT EXISTS monthly_sales (
    product_name    VARCHAR(50),
    month           VARCHAR(7),
    revenue         DECIMAL(10,2),
    order_count     INT,
    avg_order_value DECIMAL(10,2)
)
"""

TRANSFORM_SQL = """
INSERT INTO monthly_sales (product_name, month, revenue, order_count, avg_order_value)
SELECT
    product_name,
    month,
    SUM(price_usd)                            AS revenue,
    COUNT(DISTINCT order_id)                  AS order_count,
    SUM(price_usd) / COUNT(DISTINCT order_id) AS avg_order_value
FROM raw_order_items
GROUP BY product_name, month
"""


def transform() -> None:
    conn = psycopg2.connect(
        host=os.environ['PG_HOST'],
        port=int(os.environ['PG_PORT']),
        user=os.environ['PG_USER'],
        password=os.environ['PG_PASSWORD'],
        dbname=os.environ['PG_DATABASE'],
    )
    cur = conn.cursor()
    cur.execute(CREATE_MONTHLY_SALES)
    cur.execute("TRUNCATE TABLE monthly_sales")
    cur.execute(TRANSFORM_SQL)
    conn.commit()
    cur.close()
    conn.close()
    print("[transform] monthly_sales rebuilt")
