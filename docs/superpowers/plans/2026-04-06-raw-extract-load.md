# Raw Extract-Load Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone script that mirrors all raw tables from the Basket Craft MySQL database into AWS RDS PostgreSQL, preserving exact column types, truncating and reloading on each run.

**Architecture:** `extract_load_raw.py` connects to MySQL, queries `information_schema` to discover all tables and their column definitions, maps MySQL types to PostgreSQL equivalents, then creates/truncates/inserts each table in RDS. Per-table error handling ensures one failed table doesn't abort the run.

**Tech Stack:** Python 3, pymysql, psycopg2-binary, python-dotenv (all already in `requirements.txt`)

---

### Task 1: Add RDS credentials to .env

**Files:**
- Modify: `.env`

- [ ] **Step 1: Append RDS credentials to `.env`**

Open `.env` and append the following lines:

```
RDS_HOST=basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com
RDS_PORT=5432
RDS_USER=student
RDS_PASSWORD=go_lions
RDS_DATABASE=basket_craft
```

The full `.env` should now read:

```
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_USER=analyst
MYSQL_PASSWORD=go_lions
MYSQL_DATABASE=basket_craft

RDS_HOST=basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com
RDS_PORT=5432
RDS_USER=student
RDS_PASSWORD=go_lions
RDS_DATABASE=basket_craft
```

- [ ] **Step 2: Commit**

```bash
git add .env
git commit -m "feat: add RDS credentials to .env"
```

---

### Task 2: Type mapping function

**Files:**
- Create: `extract_load_raw.py`
- Create: `tests/test_extract_load_raw.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_extract_load_raw.py`:

```python
import pytest
from extract_load_raw import mysql_type_to_pg


def test_int_maps_to_integer():
    assert mysql_type_to_pg('int', 'int(11)', None, None, None) == 'INTEGER'


def test_smallint_maps_to_integer():
    assert mysql_type_to_pg('smallint', 'smallint(6)', None, None, None) == 'INTEGER'


def test_bigint_maps_to_bigint():
    assert mysql_type_to_pg('bigint', 'bigint(20)', None, None, None) == 'BIGINT'


def test_tinyint1_maps_to_boolean():
    assert mysql_type_to_pg('tinyint', 'tinyint(1)', None, None, None) == 'BOOLEAN'


def test_tinyint_non1_maps_to_integer():
    assert mysql_type_to_pg('tinyint', 'tinyint(4)', None, None, None) == 'INTEGER'


def test_varchar_maps_with_length():
    assert mysql_type_to_pg('varchar', 'varchar(50)', 50, None, None) == 'VARCHAR(50)'


def test_char_maps_with_length():
    assert mysql_type_to_pg('char', 'char(10)', 10, None, None) == 'VARCHAR(10)'


def test_text_maps_to_text():
    assert mysql_type_to_pg('text', 'text', None, None, None) == 'TEXT'


def test_longtext_maps_to_text():
    assert mysql_type_to_pg('longtext', 'longtext', None, None, None) == 'TEXT'


def test_decimal_maps_to_numeric_with_precision():
    assert mysql_type_to_pg('decimal', 'decimal(10,2)', None, 10, 2) == 'NUMERIC(10,2)'


def test_float_maps_to_real():
    assert mysql_type_to_pg('float', 'float', None, None, None) == 'REAL'


def test_double_maps_to_double_precision():
    assert mysql_type_to_pg('double', 'double', None, None, None) == 'DOUBLE PRECISION'


def test_date_maps_to_date():
    assert mysql_type_to_pg('date', 'date', None, None, None) == 'DATE'


def test_datetime_maps_to_timestamp():
    assert mysql_type_to_pg('datetime', 'datetime', None, None, None) == 'TIMESTAMP'


def test_timestamp_maps_to_timestamp():
    assert mysql_type_to_pg('timestamp', 'timestamp', None, None, None) == 'TIMESTAMP'


def test_unknown_type_maps_to_text():
    assert mysql_type_to_pg('enum', 'enum("a","b")', None, None, None) == 'TEXT'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extract_load_raw.py -v
```

Expected: `ModuleNotFoundError: No module named 'extract_load_raw'`

- [ ] **Step 3: Write `extract_load_raw.py` with just the type mapping function**

Create `extract_load_raw.py`:

```python
import os
import pymysql
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def mysql_type_to_pg(data_type, column_type, char_max_len, num_precision, num_scale):
    dt = data_type.upper()
    if dt in ('INT', 'INTEGER', 'MEDIUMINT', 'SMALLINT'):
        return 'INTEGER'
    if dt == 'BIGINT':
        return 'BIGINT'
    if dt == 'TINYINT':
        return 'BOOLEAN' if 'tinyint(1)' in column_type.lower() else 'INTEGER'
    if dt in ('VARCHAR', 'CHAR'):
        return f'VARCHAR({char_max_len})'
    if dt in ('TEXT', 'TINYTEXT', 'MEDIUMTEXT', 'LONGTEXT'):
        return 'TEXT'
    if dt == 'DECIMAL':
        return f'NUMERIC({num_precision},{num_scale})'
    if dt == 'FLOAT':
        return 'REAL'
    if dt in ('DOUBLE', 'DOUBLE PRECISION'):
        return 'DOUBLE PRECISION'
    if dt == 'DATE':
        return 'DATE'
    if dt in ('DATETIME', 'TIMESTAMP'):
        return 'TIMESTAMP'
    return 'TEXT'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract_load_raw.py -v
```

Expected: all 16 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add extract_load_raw.py tests/test_extract_load_raw.py
git commit -m "feat: add mysql_type_to_pg type mapping"
```

---

### Task 3: Table discovery functions

**Files:**
- Modify: `extract_load_raw.py`
- Modify: `tests/test_extract_load_raw.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_extract_load_raw.py`:

```python
from unittest.mock import MagicMock, patch
from extract_load_raw import get_table_names, get_columns


def test_get_table_names_returns_list():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = [('orders',), ('products',), ('order_items',)]

    result = get_table_names(mock_conn, 'basket_craft')

    mock_cur.execute.assert_called_once()
    sql = mock_cur.execute.call_args[0][0]
    assert 'information_schema.tables' in sql
    assert result == ['orders', 'products', 'order_items']


def test_get_columns_returns_column_defs():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = [
        ('order_id', 'int', 'int(11)', None, None, None),
        ('created_at', 'datetime', 'datetime', None, None, None),
    ]

    result = get_columns(mock_conn, 'basket_craft', 'orders')

    assert len(result) == 2
    assert result[0] == ('order_id', 'int', 'int(11)', None, None, None)
    assert result[1] == ('created_at', 'datetime', 'datetime', None, None, None)
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
pytest tests/test_extract_load_raw.py::test_get_table_names_returns_list tests/test_extract_load_raw.py::test_get_columns_returns_column_defs -v
```

Expected: `ImportError: cannot import name 'get_table_names'`

- [ ] **Step 3: Add `get_table_names` and `get_columns` to `extract_load_raw.py`**

Append to `extract_load_raw.py` (after `mysql_type_to_pg`):

```python
def get_table_names(mysql_conn, db_name):
    cur = mysql_conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
        "ORDER BY table_name",
        (db_name,)
    )
    rows = cur.fetchall()
    cur.close()
    return [row[0] for row in rows]


def get_columns(mysql_conn, db_name, table_name):
    cur = mysql_conn.cursor()
    cur.execute(
        "SELECT column_name, data_type, column_type, "
        "character_maximum_length, numeric_precision, numeric_scale "
        "FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s "
        "ORDER BY ordinal_position",
        (db_name, table_name)
    )
    rows = cur.fetchall()
    cur.close()
    return rows
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/test_extract_load_raw.py -v
```

Expected: all 18 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add extract_load_raw.py tests/test_extract_load_raw.py
git commit -m "feat: add table discovery functions"
```

---

### Task 4: copy_table function

**Files:**
- Modify: `extract_load_raw.py`
- Modify: `tests/test_extract_load_raw.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_extract_load_raw.py`:

```python
from extract_load_raw import copy_table


def test_copy_table_creates_truncates_and_inserts():
    mysql_conn = MagicMock()
    pg_conn = MagicMock()
    mysql_cur = MagicMock()
    pg_cur = MagicMock()
    mysql_conn.cursor.return_value = mysql_cur
    pg_conn.cursor.return_value = pg_cur

    columns = [
        ('order_id', 'int', 'int(11)', None, None, None),
        ('product_name', 'varchar', 'varchar(50)', 50, None, None),
    ]
    mysql_cur.fetchall.return_value = [(1, 'Woven Tote'), (2, 'Market Basket')]

    copy_table(mysql_conn, pg_conn, 'products', columns)

    pg_executed = [c.args[0] for c in pg_cur.execute.call_args_list]
    assert any('CREATE TABLE IF NOT EXISTS' in sql and 'products' in sql for sql in pg_executed)
    assert any('TRUNCATE TABLE products' in sql for sql in pg_executed)
    pg_conn.commit.assert_called_once()
    pg_cur.executemany.assert_called_once()
    rows_inserted = pg_cur.executemany.call_args[0][1]
    assert len(rows_inserted) == 2


def test_copy_table_uses_correct_column_types():
    mysql_conn = MagicMock()
    pg_conn = MagicMock()
    mysql_cur = MagicMock()
    pg_cur = MagicMock()
    mysql_conn.cursor.return_value = mysql_cur
    pg_conn.cursor.return_value = pg_cur
    mysql_cur.fetchall.return_value = []

    columns = [
        ('id', 'int', 'int(11)', None, None, None),
        ('amount', 'decimal', 'decimal(10,2)', None, 10, 2),
    ]

    copy_table(mysql_conn, pg_conn, 'payments', columns)

    pg_executed = [c.args[0] for c in pg_cur.execute.call_args_list]
    create_sql = next(sql for sql in pg_executed if 'CREATE TABLE IF NOT EXISTS' in sql)
    assert 'INTEGER' in create_sql
    assert 'NUMERIC(10,2)' in create_sql
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
pytest tests/test_extract_load_raw.py::test_copy_table_creates_truncates_and_inserts tests/test_extract_load_raw.py::test_copy_table_uses_correct_column_types -v
```

Expected: `ImportError: cannot import name 'copy_table'`

- [ ] **Step 3: Add `copy_table` to `extract_load_raw.py`**

Append to `extract_load_raw.py` (after `get_columns`):

```python
def copy_table(mysql_conn, pg_conn, table_name, columns):
    col_defs = ', '.join(
        f'{col_name} {mysql_type_to_pg(data_type, column_type, char_max_len, num_precision, num_scale)}'
        for col_name, data_type, column_type, char_max_len, num_precision, num_scale in columns
    )
    col_names = ', '.join(col[0] for col in columns)
    placeholders = ', '.join(['%s'] * len(columns))

    pg_cur = pg_conn.cursor()
    pg_cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})')
    pg_cur.execute(f'TRUNCATE TABLE {table_name}')

    mysql_cur = mysql_conn.cursor()
    mysql_cur.execute(f'SELECT {col_names} FROM {table_name}')
    rows = mysql_cur.fetchall()
    mysql_cur.close()

    pg_cur.executemany(
        f'INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})',
        rows,
    )
    pg_conn.commit()
    pg_cur.close()
    return len(rows)
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/test_extract_load_raw.py -v
```

Expected: all 20 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add extract_load_raw.py tests/test_extract_load_raw.py
git commit -m "feat: add copy_table function"
```

---

### Task 5: Main extract_load_raw function

**Files:**
- Modify: `extract_load_raw.py`
- Modify: `tests/test_extract_load_raw.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_extract_load_raw.py`:

```python
import os
from extract_load_raw import extract_load_raw


def _env():
    return {
        'MYSQL_HOST': 'localhost', 'MYSQL_PORT': '3306',
        'MYSQL_USER': 'u', 'MYSQL_PASSWORD': 'p', 'MYSQL_DATABASE': 'mydb',
        'RDS_HOST': 'localhost', 'RDS_PORT': '5432',
        'RDS_USER': 'u', 'RDS_PASSWORD': 'p', 'RDS_DATABASE': 'rdsdb',
    }


def test_extract_load_raw_copies_all_tables():
    mock_mysql_conn = MagicMock()
    mock_pg_conn = MagicMock()

    with patch.dict(os.environ, _env()), \
         patch('extract_load_raw.pymysql.connect', return_value=mock_mysql_conn), \
         patch('extract_load_raw.psycopg2.connect', return_value=mock_pg_conn), \
         patch('extract_load_raw.get_table_names', return_value=['orders', 'products']), \
         patch('extract_load_raw.get_columns', return_value=[('id', 'int', 'int(11)', None, None, None)]), \
         patch('extract_load_raw.copy_table', return_value=5) as mock_copy:
        extract_load_raw()

    assert mock_copy.call_count == 2
    tables_copied = [c.args[2] for c in mock_copy.call_args_list]
    assert 'orders' in tables_copied
    assert 'products' in tables_copied


def test_extract_load_raw_continues_after_table_failure():
    mock_mysql_conn = MagicMock()
    mock_pg_conn = MagicMock()

    def fail_on_orders(mysql_conn, pg_conn, table_name, columns):
        if table_name == 'orders':
            raise Exception("connection error")
        return 3

    with patch.dict(os.environ, _env()), \
         patch('extract_load_raw.pymysql.connect', return_value=mock_mysql_conn), \
         patch('extract_load_raw.psycopg2.connect', return_value=mock_pg_conn), \
         patch('extract_load_raw.get_table_names', return_value=['orders', 'products']), \
         patch('extract_load_raw.get_columns', return_value=[('id', 'int', 'int(11)', None, None, None)]), \
         patch('extract_load_raw.copy_table', side_effect=fail_on_orders):
        # should not raise
        extract_load_raw()
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
pytest tests/test_extract_load_raw.py::test_extract_load_raw_copies_all_tables tests/test_extract_load_raw.py::test_extract_load_raw_continues_after_table_failure -v
```

Expected: `ImportError: cannot import name 'extract_load_raw'`

- [ ] **Step 3: Add `extract_load_raw` function and `__main__` block to `extract_load_raw.py`**

Append to `extract_load_raw.py` (after `copy_table`):

```python
def extract_load_raw():
    mysql_conn = pymysql.connect(
        host=os.environ['MYSQL_HOST'],
        port=int(os.environ['MYSQL_PORT']),
        user=os.environ['MYSQL_USER'],
        password=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DATABASE'],
    )
    pg_conn = psycopg2.connect(
        host=os.environ['RDS_HOST'],
        port=int(os.environ['RDS_PORT']),
        user=os.environ['RDS_USER'],
        password=os.environ['RDS_PASSWORD'],
        dbname=os.environ['RDS_DATABASE'],
    )

    db_name = os.environ['MYSQL_DATABASE']
    tables = get_table_names(mysql_conn, db_name)
    succeeded = 0
    failed = 0

    for table in tables:
        try:
            columns = get_columns(mysql_conn, db_name, table)
            row_count = copy_table(mysql_conn, pg_conn, table, columns)
            print(f'[ok] {table}: {row_count} rows loaded')
            succeeded += 1
        except Exception as e:
            print(f'[error] {table}: {e}')
            failed += 1

    mysql_conn.close()
    pg_conn.close()
    print(f'[done] {succeeded}/{succeeded + failed} tables loaded successfully')


if __name__ == '__main__':
    extract_load_raw()
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/test_extract_load_raw.py -v
```

Expected: all 22 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add extract_load_raw.py tests/test_extract_load_raw.py
git commit -m "feat: add extract_load_raw orchestrator"
```

---

### Task 6: End-to-end verification

**Files:** none

- [ ] **Step 1: Run the script**

```bash
python extract_load_raw.py
```

Expected output (table names will vary):
```
[ok] order_items: NNNN rows loaded
[ok] orders: NNNN rows loaded
[ok] products: NNNN rows loaded
[done] 3/3 tables loaded successfully
```

- [ ] **Step 2: Verify tables exist in RDS**

```bash
psql -h basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com \
     -U student -d basket_craft \
     -c "\dt"
```

Expected: one row per source MySQL table.

- [ ] **Step 3: Spot-check row counts**

```bash
psql -h basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com \
     -U student -d basket_craft \
     -c "SELECT 'order_items', COUNT(*) FROM order_items UNION ALL SELECT 'orders', COUNT(*) FROM orders UNION ALL SELECT 'products', COUNT(*) FROM products;"
```

Expected: row counts match what the script printed in Step 1.

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: raw extract-load verified end-to-end"
```
