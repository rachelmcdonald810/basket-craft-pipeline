import os
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CREATE_RAW = """
CREATE TABLE IF NOT EXISTS raw_order_items (
    order_id     INT,
    month        VARCHAR(7),
    product_name VARCHAR(50),
    price_usd    DECIMAL(6,2)
)
"""


def load(df: pd.DataFrame) -> None:
    conn = psycopg2.connect(
        host=os.environ['PG_HOST'],
        port=int(os.environ['PG_PORT']),
        user=os.environ['PG_USER'],
        password=os.environ['PG_PASSWORD'],
        dbname=os.environ['PG_DATABASE'],
    )
    cur = conn.cursor()
    cur.execute(CREATE_RAW)
    cur.execute("TRUNCATE TABLE raw_order_items")
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
    execute_values(
        cur,
        "INSERT INTO raw_order_items (order_id, month, product_name, price_usd) VALUES %s",
        rows,
        page_size=1000,
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"[load] {len(df)} rows loaded to raw_order_items")
