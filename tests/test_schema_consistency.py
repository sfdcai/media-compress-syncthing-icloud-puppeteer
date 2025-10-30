"""Tests ensuring the local cache schema stays aligned with Supabase."""

from __future__ import annotations

import importlib.util
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Set

def _extract_column_names(lines: Iterable[str]) -> Set[str]:
    columns: Set[str] = set()
    for raw_line in lines:
        line = raw_line.strip().strip(",")
        if not line or line.startswith("--"):
            continue
        upper = line.upper()
        if upper.startswith("CREATE TABLE") or line == ");":
            continue
        column_name = line.split()[0]
        columns.add(column_name)
    return columns


CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)", re.IGNORECASE)


def _parse_sql_tables(sql_text: str) -> Dict[str, Set[str]]:
    tables: Dict[str, Set[str]] = {}
    current_lines: list[str] = []
    current_table: str | None = None

    for raw_line in sql_text.splitlines():
        line = raw_line.strip()
        match = CREATE_TABLE_RE.match(line)
        if match:
            table_name = match.group(1).rstrip("(")
            current_table = table_name.lower()
            current_lines = []
            continue

        if current_table is None:
            continue

        current_lines.append(line)
        if line == ");":
            tables[current_table] = _extract_column_names(current_lines)
            current_table = None

    return tables


def _load_local_db_manager_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "local_db_manager.py"
    spec = importlib.util.spec_from_file_location("_local_db_manager", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:  # pragma: no cover - defensive guard
        raise ImportError("Unable to load local_db_manager module")
    spec.loader.exec_module(module)
    return module


def _load_supabase_schema_module():
    module_path = Path(__file__).resolve().parents[1] / "supabase_schema" / "__init__.py"
    spec = importlib.util.spec_from_file_location("_supabase_schema", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:  # pragma: no cover - defensive guard
        raise ImportError("Unable to load supabase schema definitions")
    spec.loader.exec_module(module)
    return module


local_db_manager = _load_local_db_manager_module()
supabase_schema = _load_supabase_schema_module()


def test_supabase_schema_sql_matches_module_definitions():
    schema_path = Path("supabase/schema.sql")
    file_tables = _parse_sql_tables(schema_path.read_text())
    module_tables = {
        name: _extract_column_names(sql.splitlines())
        for name, sql in supabase_schema.TABLES.items()
    }
    assert file_tables == module_tables


def test_local_sqlite_schema_covers_supabase_columns():
    module_tables = {
        name: _extract_column_names(sql.splitlines())
        for name, sql in supabase_schema.TABLES.items()
    }

    with sqlite3.connect(":memory:") as conn:
        for statement in local_db_manager.TABLE_DEFINITIONS.values():
            conn.execute(statement)

        local_tables = {
            table: {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for table in local_db_manager.TABLE_DEFINITIONS
        }

    for table, columns in module_tables.items():
        assert table in local_tables
        assert columns <= local_tables[table]
