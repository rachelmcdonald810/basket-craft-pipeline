import os
import pymysql
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

QUERY = """
SELECT
    o.order_id,
    DATE_FORMAT(o.created_at, '%%Y-%%m') AS month,
    p.product_name,
    oi.price_usd
FROM order_items oi
JOIN orders o  ON oi.order_id  = o.order_id
JOIN products p ON oi.product_id = p.product_id
"""


def extract():
    conn = pymysql.connect(
        host=os.environ['MYSQL_HOST'],
        port=int(os.environ['MYSQL_PORT']),
        user=os.environ['MYSQL_USER'],
        password=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DATABASE'],
    )
    df = pd.read_sql(QUERY, conn)
    conn.close()
    print(f"[extract] {len(df)} rows extracted")
    return df
