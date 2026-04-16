import os
import pandas as pd
from unittest.mock import patch, MagicMock, call
from load import load


def _sample_df():
    return pd.DataFrame({
        'order_id': [1, 2],
        'month': ['2025-01', '2025-01'],
        'product_name': ['Woven Tote', 'Market Basket'],
        'price_usd': [48.00, 62.00],
    })


def _pg_env():
    return {
        'PG_HOST': 'localhost', 'PG_PORT': '5432',
        'PG_USER': 'u', 'PG_PASSWORD': 'p', 'PG_DATABASE': 'db',
    }


def test_load_truncates_raw_order_items():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch.dict(os.environ, _pg_env()), \
         patch('load.psycopg2.connect', return_value=mock_conn):
        load(_sample_df())

    executed = [c.args[0] for c in mock_cur.execute.call_args_list]
    assert any('TRUNCATE' in sql and 'raw_order_items' in sql for sql in executed)


def test_load_inserts_all_rows():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch.dict(os.environ, _pg_env()), \
         patch('load.psycopg2.connect', return_value=mock_conn):
        load(_sample_df())

    mock_cur.executemany.assert_called_once()
    rows = mock_cur.executemany.call_args[0][1]
    assert len(rows) == 2
    assert rows[0] == (1, '2025-01', 'Woven Tote', 48.00)
    assert rows[1] == (2, '2025-01', 'Market Basket', 62.00)
