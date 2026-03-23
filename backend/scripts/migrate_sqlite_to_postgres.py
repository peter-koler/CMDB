#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

ALEMBIC_HEAD_REVISION = "a7b8c9d0e1f3"

@dataclass
class TableStat:
    table: str
    sqlite_count: int
    pg_count: int


def normalize_pg_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg2://"):
        return "postgresql://" + dsn[len("postgresql+psycopg2://") :]
    if dsn.startswith("postgres+psycopg2://"):
        return "postgresql://" + dsn[len("postgres+psycopg2://") :]
    return dsn


def get_pg_table_set(pg_cur) -> set[str]:
    pg_cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
    )
    return {row[0] for row in pg_cur.fetchall()}


def get_pg_column_types(pg_cur) -> dict[str, dict[str, str]]:
    pg_cur.execute(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    out: dict[str, dict[str, str]] = {}
    for table_name, column_name, data_type in pg_cur.fetchall():
        out.setdefault(table_name, {})[column_name] = data_type
    return out


def get_sqlite_table_names(sqlite_conn: sqlite3.Connection) -> list[str]:
    cur = sqlite_conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [row[0] for row in cur.fetchall()]


def count_sqlite_rows(sqlite_conn: sqlite3.Connection, table: str) -> int:
    cur = sqlite_conn.execute(f'SELECT COUNT(*) FROM "{table}"')
    return int(cur.fetchone()[0])


def cast_value_for_pg(data_type: str | None, value):
    if value is None:
        return None
    if data_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        s = str(value).strip().lower()
        return s in {"1", "t", "true", "yes", "y", "on"}
    return value


def chunked_rows(rows: Iterable[tuple], size: int) -> Iterable[list[tuple]]:
    batch: list[tuple] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite data into PostgreSQL")
    parser.add_argument("--sqlite", required=True, help="Path to sqlite db file")
    parser.add_argument(
        "--pg-dsn",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL DSN, supports postgresql+psycopg2://",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    if not args.pg_dsn:
        raise SystemExit("Missing --pg-dsn or DATABASE_URL")

    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row

    pg_dsn = normalize_pg_dsn(args.pg_dsn)
    parsed = urlparse(pg_dsn)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise SystemExit(f"Unsupported pg dsn scheme: {parsed.scheme}")

    pg_conn = psycopg2.connect(pg_dsn)
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    try:
        sqlite_tables = get_sqlite_table_names(sqlite_conn)
        pg_tables = get_pg_table_set(pg_cur)
        pg_column_types = get_pg_column_types(pg_cur)
        common_tables = [t for t in sqlite_tables if t in pg_tables]

        pg_cur.execute("SET session_replication_role = 'replica'")
        for table in common_tables:
            pg_cur.execute(
                sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                    sql.Identifier(table)
                )
            )

        stats: list[TableStat] = []
        for table in common_tables:
            if table == "alembic_version":
                continue
            sqlite_cur = sqlite_conn.execute(f'SELECT * FROM "{table}"')
            columns = [d[0] for d in sqlite_cur.description]
            table_types = pg_column_types.get(table, {})
            rows_iter = (
                tuple(
                    cast_value_for_pg(table_types.get(col), row[col])
                    for col in columns
                )
                for row in sqlite_cur.fetchall()
            )
            inserted = 0
            for batch in chunked_rows(rows_iter, args.batch_size):
                query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                )
                execute_values(pg_cur, query.as_string(pg_conn), batch)
                inserted += len(batch)
            stats.append(TableStat(table=table, sqlite_count=count_sqlite_rows(sqlite_conn, table), pg_count=inserted))

        if "alembic_version" in pg_tables:
            pg_cur.execute("DELETE FROM alembic_version")
            pg_cur.execute(
                "INSERT INTO alembic_version(version_num) VALUES (%s)",
                (ALEMBIC_HEAD_REVISION,),
            )
            sqlite_alembic_count = 0
            if "alembic_version" in sqlite_tables:
                sqlite_alembic_count = count_sqlite_rows(sqlite_conn, "alembic_version")
            stats.append(
                TableStat(
                    table="alembic_version",
                    sqlite_count=sqlite_alembic_count,
                    pg_count=1,
                )
            )

        # realign sequences to max(id) when serial/bigserial exists
        pg_cur.execute(
            """
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.column_default LIKE 'nextval(%'
            """
        )
        for table_name, column_name in pg_cur.fetchall():
            pg_cur.execute(
                sql.SQL(
                    """
                    SELECT setval(
                        pg_get_serial_sequence(%s, %s),
                        COALESCE((SELECT MAX({col}) FROM {tbl}), 1),
                        COALESCE((SELECT MAX({col}) FROM {tbl}), 0) > 0
                    )
                    """
                ).format(
                    col=sql.Identifier(column_name),
                    tbl=sql.Identifier(table_name),
                ),
                (f"public.{table_name}", column_name),
            )

        pg_cur.execute("SET session_replication_role = 'origin'")
        pg_conn.commit()

        print("table\tsqlite_count\tinserted_count")
        for s in stats:
            print(f"{s.table}\t{s.sqlite_count}\t{s.pg_count}")

        missing_in_pg = [t for t in sqlite_tables if t not in pg_tables]
        if missing_in_pg:
            print("\n[warn] tables in sqlite but missing in postgres:")
            for t in missing_in_pg:
                print(f"- {t}")
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_cur.close()
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
