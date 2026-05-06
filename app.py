import streamlit as st
import psycopg2
import pandas as pd
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

st.title("Basket Craft Pipeline Dashboard")


@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("RDS_HOST"),
        port=os.getenv("RDS_PORT"),
        user=os.getenv("RDS_USER"),
        password=os.getenv("RDS_PASSWORD"),
        database=os.getenv("RDS_DATABASE"),
    )


@st.cache_data(ttl=60)
def get_headline_metrics():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            month,
            SUM(revenue) AS total_revenue,
            SUM(order_count) AS total_orders,
            SUM(revenue) / NULLIF(SUM(order_count), 0) AS avg_order_value
        FROM monthly_sales
        GROUP BY month
        ORDER BY month DESC
        LIMIT 2
    """)
    rows = cur.fetchall()
    cur.execute("""
        SELECT month, COUNT(*) AS items_sold
        FROM raw_order_items
        GROUP BY month
        ORDER BY month DESC
        LIMIT 2
    """)
    item_rows = cur.fetchall()
    cur.close()
    return rows, item_rows


st.header("Headline Metrics")

sales_rows, item_rows = get_headline_metrics()

current = sales_rows[0]
prior = sales_rows[1]
current_items = item_rows[0][1]
prior_items = item_rows[1][1]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    label="Total Revenue",
    value=f"${current[1]:,.2f}",
    delta=f"${current[1] - prior[1]:,.2f}",
)
col2.metric(
    label="Total Orders",
    value=f"{current[2]:,}",
    delta=f"{current[2] - prior[2]:,}",
)
col3.metric(
    label="Avg Order Value",
    value=f"${current[3]:.2f}",
    delta=f"${current[3] - prior[3]:.2f}",
)
col4.metric(
    label="Items Sold",
    value=f"{current_items:,}",
    delta=f"{current_items - prior_items:,}",
)

st.caption(f"Current month: {current[0]} vs prior month: {prior[0]}")


@st.cache_data(ttl=60)
def get_revenue_trend():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT month, SUM(revenue) AS total_revenue
        FROM monthly_sales
        GROUP BY month
        ORDER BY month
    """)
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows, columns=["month", "revenue"])
    df["month"] = pd.to_datetime(df["month"])
    return df


st.header("Revenue Trend")

revenue_df = get_revenue_trend()

min_date = revenue_df["month"].min().date()
max_date = revenue_df["month"].max().date()

date_range = st.slider(
    "Date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="MMM YYYY",
)

filtered = revenue_df[
    (revenue_df["month"].dt.date >= date_range[0])
    & (revenue_df["month"].dt.date <= date_range[1])
]

st.line_chart(filtered, x="month", y="revenue")


@st.cache_data(ttl=60)
def get_product_revenue():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT month, product_name, revenue
        FROM monthly_sales
        ORDER BY month
    """)
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows, columns=["month", "product_name", "revenue"])
    df["month"] = pd.to_datetime(df["month"])
    return df


st.header("Top Products by Revenue")

product_df = get_product_revenue()

filtered_products = product_df[
    (product_df["month"].dt.date >= date_range[0])
    & (product_df["month"].dt.date <= date_range[1])
]

top_products = (
    filtered_products.groupby("product_name", as_index=False)["revenue"]
    .sum()
    .sort_values("revenue", ascending=True)
)

st.bar_chart(top_products, x="product_name", y="revenue", horizontal=True)


@st.cache_data(ttl=60)
def get_bundle_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            a.product_name AS selected_product,
            b.product_name AS paired_product,
            COUNT(DISTINCT a.order_id) AS shared_orders
        FROM raw_order_items a
        JOIN raw_order_items b
            ON a.order_id = b.order_id
            AND a.product_name <> b.product_name
        GROUP BY a.product_name, b.product_name
        ORDER BY a.product_name, shared_orders DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows, columns=["selected_product", "paired_product", "shared_orders"])


st.header("Bundle Finder")

bundle_df = get_bundle_data()
products = sorted(bundle_df["selected_product"].unique())

selected = st.selectbox("Pick a product", products)

pairs = (
    bundle_df[bundle_df["selected_product"] == selected]
    .sort_values("shared_orders", ascending=True)
)

st.bar_chart(pairs, x="paired_product", y="shared_orders", horizontal=True)
st.caption(f"Number of orders containing both {selected} and each other product.")
