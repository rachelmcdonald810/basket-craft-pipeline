# Basket Craft Raw Extract-Load — Design Spec

**Date:** 2026-04-06
**Status:** Approved

## Overview

A standalone script that mirrors all raw tables from the Basket Craft MySQL database into the AWS RDS PostgreSQL instance, as-is with no transformations. Intended as a one-time or on-demand raw data load, independent of the existing monthly sales ELT pipeline.

---

## Architecture

```
extract_load_raw.py (manual trigger)
    │
    ├─ 1. Connect to MySQL, query information_schema for all tables + column definitions
    ├─ 2. For each table:
    │       a. Map MySQL column types → PostgreSQL equivalents
    │       b. CREATE TABLE IF NOT EXISTS in RDS with exact schema
    │       c. TRUNCATE the RDS table
    │       d. SELECT * FROM MySQL table → fetch all rows
    │       e. INSERT rows into RDS table via executemany
    └─ 3. Print per-table row count on success; print error and continue on failure
    └─ 4. Print final summary: X tables succeeded, Y failed
```

---

## Source

- **Database:** MySQL at `db.isba.co:3306`, database `basket_craft`
- **Credentials:** `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` from `.env`
- **Tables:** All tables discovered dynamically via `information_schema.columns`

---

## Destination

- **Database:** AWS RDS PostgreSQL at `basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com`
- **Credentials:** `RDS_HOST`, `RDS_PORT`, `RDS_USER`, `RDS_PASSWORD`, `RDS_DATABASE` from `.env`
- **Schema:** Tables created with exact column names and mapped PostgreSQL types
- **Load strategy:** Truncate and reload on every run (no incremental logic)

---

## .env Additions

```
RDS_HOST=basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com
RDS_PORT=5432
RDS_USER=student
RDS_PASSWORD=go_lions
RDS_DATABASE=basket_craft
```

---

## Type Mapping (MySQL → PostgreSQL)

| MySQL | PostgreSQL |
|-------|-----------|
| `INT`, `SMALLINT` | `INTEGER` |
| `BIGINT` | `BIGINT` |
| `VARCHAR(n)`, `CHAR(n)` | `VARCHAR(n)` |
| `TEXT`, `LONGTEXT`, `MEDIUMTEXT` | `TEXT` |
| `DECIMAL(p,s)` | `NUMERIC(p,s)` |
| `FLOAT` | `REAL` |
| `DOUBLE` | `DOUBLE PRECISION` |
| `DATE` | `DATE` |
| `DATETIME`, `TIMESTAMP` | `TIMESTAMP` |
| `TINYINT(1)` | `BOOLEAN` |
| anything else | `TEXT` (safe fallback) |

---

## Components

| File | Responsibility |
|------|---------------|
| `extract_load_raw.py` | Discovers MySQL tables, maps types, creates/truncates/loads each table in RDS |
| `.env` | MySQL credentials (existing) + RDS credentials (new) |

No new dependencies required — `pymysql`, `psycopg2-binary`, and `python-dotenv` are already in `requirements.txt`.

---

## Error Handling

- Per-table try/except: if a table fails, print the error and continue to the next table
- Final summary line: `[done] X/Y tables loaded successfully`
- No partial-load protection within a single table — if insert fails mid-table, that table is counted as failed

---

## Running the Script

```bash
python extract_load_raw.py
```

---

## Verification

```bash
psql -h basket-craft-pipeline.c3wa24q6an93.us-east-2.rds.amazonaws.com \
     -U student -d basket_craft \
     -c "\dt"
```

Expected: all MySQL source tables present in RDS.
