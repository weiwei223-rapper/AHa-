#!/usr/bin/env python3
"""Schema migration helper for backend SQLite/PostgreSQL databases."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import sqltypes

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aha_app.db")

USE_SQLITE = DATABASE_URL.startswith("sqlite")
ENGINE_KWARGS = {"connect_args": {"check_same_thread": False}} if USE_SQLITE else {}
engine = create_engine(DATABASE_URL, **ENGINE_KWARGS)

from models import Base


def compile_column_type(column):
    try:
        return column.type.compile(dialect=engine.dialect)
    except Exception:
        return str(column.type)


def build_column_sql(column):
    col_type = compile_column_type(column)
    nullable = column.nullable
    default = None

    if column.server_default is not None:
        default = str(column.server_default.arg)
    elif column.default is not None and hasattr(column.default, "arg"):
        default = column.default.arg

    if default is None:
        if isinstance(column.type, sqltypes.Integer):
            default = 0
        elif isinstance(column.type, (sqltypes.String, sqltypes.Text)):
            default = None
        elif isinstance(column.type, (sqltypes.DateTime, sqltypes.TIMESTAMP)):
            default = "CURRENT_TIMESTAMP"

    parts = [f"{column.name} {col_type}"]
    if not nullable:
        parts.append("NOT NULL")

    if default is not None:
        if isinstance(default, str) and default.upper() == "CURRENT_TIMESTAMP":
            parts.append("DEFAULT CURRENT_TIMESTAMP")
        elif isinstance(default, str):
            parts.append(f"DEFAULT '{default}'")
        else:
            parts.append(f"DEFAULT {default}")

    return " ".join(parts)


def add_missing_columns():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue

                ddl = build_column_sql(column)
                if USE_SQLITE:
                    statement = f"ALTER TABLE {table_name} ADD COLUMN {ddl}"
                else:
                    statement = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {ddl}"

                print(f"Adding missing column {column.name} to {table_name}: {statement}")
                try:
                    conn.execute(text(statement))
                except SQLAlchemyError as err:
                    print(f"Failed to add column {column.name} to {table_name}: {err}")


def migrate():
    print(f"Connecting to database: {DATABASE_URL}")
    print("Creating missing tables...")
    Base.metadata.create_all(bind=engine)

    print("Checking existing tables for missing columns...")
    add_missing_columns()

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
