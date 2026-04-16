import os
from unittest.mock import patch, MagicMock
from transform import transform


def _pg_env():
    return {
        'PG_HOST': 'localhost', 'PG_PORT': '5432',
        'PG_USER': 'u', 'PG_PASSWORD': 'p', 'PG_DATABASE': 'db',
    }


def test_transform_truncates_monthly_sales():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch.dict(os.environ, _pg_env()), \
         patch('transform.psycopg2.connect', return_value=mock_conn):
        transform()

    executed = [c.args[0] for c in mock_cur.execute.call_args_list]
    assert any('TRUNCATE' in sql and 'monthly_sales' in sql for sql in executed)


def test_transform_inserts_aggregated_data():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    with patch.dict(os.environ, _pg_env()), \
         patch('transform.psycopg2.connect', return_value=mock_conn):
        transform()

    executed = [c.args[0] for c in mock_cur.execute.call_args_list]
    assert any('INSERT INTO monthly_sales' in sql for sql in executed)
    insert_sql = next(sql for sql in executed if 'INSERT INTO monthly_sales' in sql)
    assert 'SUM(price_usd)' in insert_sql
    assert 'COUNT(DISTINCT order_id)' in insert_sql
    assert 'GROUP BY' in insert_sql
