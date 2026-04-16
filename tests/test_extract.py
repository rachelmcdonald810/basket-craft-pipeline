import os
import pandas as pd
from unittest.mock import patch
from extract import extract


def test_extract_returns_expected_columns():
    expected = pd.DataFrame({
        'order_id': [1, 2],
        'month': ['2025-01', '2025-01'],
        'product_name': ['Woven Tote', 'Market Basket'],
        'price_usd': [48.00, 62.00],
    })
    env = {
        'MYSQL_HOST': 'localhost', 'MYSQL_PORT': '3306',
        'MYSQL_USER': 'u', 'MYSQL_PASSWORD': 'p', 'MYSQL_DATABASE': 'db',
    }
    with patch.dict(os.environ, env), \
         patch('extract.pymysql.connect'), \
         patch('extract.pd.read_sql', return_value=expected):
        result = extract()

    assert list(result.columns) == ['order_id', 'month', 'product_name', 'price_usd']
    assert len(result) == 2


def test_extract_passes_correct_query():
    expected = pd.DataFrame({
        'order_id': [1], 'month': ['2025-01'],
        'product_name': ['Woven Tote'], 'price_usd': [48.00],
    })
    env = {
        'MYSQL_HOST': 'localhost', 'MYSQL_PORT': '3306',
        'MYSQL_USER': 'u', 'MYSQL_PASSWORD': 'p', 'MYSQL_DATABASE': 'db',
    }
    with patch.dict(os.environ, env), \
         patch('extract.pymysql.connect'), \
         patch('extract.pd.read_sql', return_value=expected) as mock_read_sql:
        extract()

    query_used = mock_read_sql.call_args[0][0]
    assert 'order_items' in query_used
    assert 'orders' in query_used
    assert 'products' in query_used
    assert 'price_usd' in query_used
