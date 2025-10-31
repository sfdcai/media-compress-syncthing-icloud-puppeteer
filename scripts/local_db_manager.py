"""Local SQLite database manager for offline pipeline bookkeeping.

This module provides a thin wrapper around SQLite that mirrors a subset of the
remote Supabase schema. Pipeline components can persist their progress locally
whenever Supabase is unavailable, and later reconcile by syncing pending
records. The helpers exposed here are intentionally small to keep the call
sites in ``scripts/utils.py`` straightforward.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(os.getenv("LOCAL_DB_PATH", "cache/local_pipeline.db"))

TABLE_DEFINITIONS = {
    "batches": """
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            supabase_id TEXT,
            batch_type TEXT,
            status TEXT,
            file_count INTEGER,
            total_size_gb REAL,
            source_type TEXT,
            completed_at TEXT,
            synced_to_supabase INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "media_files": """
        CREATE TABLE IF NOT EXISTS media_files (
            id TEXT PRIMARY KEY,
            supabase_id TEXT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_hash TEXT,
            file_size INTEGER,
            original_size INTEGER,
            compressed_size INTEGER,
            space_saved INTEGER,
            compression_percentage REAL,
            compression_ratio REAL,
            is_duplicate INTEGER DEFAULT 0,
            source_path TEXT,
            source_type TEXT DEFAULT 'unknown',
            status TEXT,
            batch_id TEXT,
            processed_at TEXT,
            synced_to_supabase INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "duplicate_files": """
        CREATE TABLE IF NOT EXISTS duplicate_files (
            id TEXT PRIMARY KEY,
            supabase_id TEXT,
            original_file_id TEXT,
            duplicate_file_id TEXT,
            hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            synced_to_supabase INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "pipeline_logs": """
        CREATE TABLE IF NOT EXISTS pipeline_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supabase_id TEXT,
            step TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            synced_to_supabase INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """,
}

LEGACY_COLUMNS = {
    "batches": {
        "completed_at": "TEXT",
        "source_type": "TEXT",
        "synced_to_supabase": "INTEGER DEFAULT 0",
    },
    "media_files": {
        "file_size": "INTEGER",
        "original_size": "INTEGER",
        "compressed_size": "INTEGER",
        "space_saved": "INTEGER",
        "compression_percentage": "REAL",
        "compression_ratio": "REAL",
        "is_duplicate": "INTEGER DEFAULT 0",
        "source_path": "TEXT",
        "source_type": "TEXT DEFAULT 'unknown'",
        "processed_at": "TEXT",
        "synced_to_supabase": "INTEGER DEFAULT 0",
    },
    "duplicate_files": {
        "synced_to_supabase": "INTEGER DEFAULT 0",
        "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        "supabase_id": "TEXT",
    },
    "pipeline_logs": {
        "supabase_id": "TEXT",
        "synced_to_supabase": "INTEGER DEFAULT 0",
        "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    },
}


def _ensure_parent_directory(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _ensure_columns(conn: sqlite3.Connection, table: str) -> None:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    for column, definition in LEGACY_COLUMNS.get(table, {}).items():
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Ensure the local SQLite schema exists and includes sync bookkeeping."""

    for table, statement in TABLE_DEFINITIONS.items():
        conn.execute(statement)
        _ensure_columns(conn, table)


@contextmanager
def get_connection(db_path: Path = DEFAULT_DB_PATH):
    """Provide a SQLite connection with schema initialised."""

    _ensure_parent_directory(db_path)
    conn = sqlite3.connect(db_path)
    try:
        initialize_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _count_unsynced(table: str) -> int:
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE synced_to_supabase = 0"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
    except sqlite3.DatabaseError as exc:
        logger.error("Database error while counting unsynced %s: %s", table, exc)
        return 0


def count_unsynced_batches() -> int:
    """Return the number of batch records waiting to sync to Supabase."""

    return _count_unsynced("batches")


def count_unsynced_media_files() -> int:
    """Return the number of media file records waiting to sync to Supabase."""

    return _count_unsynced("media_files")


def mark_record_synced(table: str, record_id: str) -> None:
    """Mark a record as synced in the local database."""

    try:
        with get_connection() as conn:
            conn.execute(
                f"""
                UPDATE {table}
                   SET synced_to_supabase = 1,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
                """,
                (record_id,),
            )
    except sqlite3.DatabaseError as exc:
        logger.error("Failed to mark %s record %s as synced: %s", table, record_id, exc)


def upsert_record(table: str, record_id: str, fields: Dict[str, Any]) -> None:
    """Insert or update a record in the specified table."""

    placeholders = ", ".join(f"{key} = :{key}" for key in fields)
    fields_with_id = {**fields, "id": record_id}

    with get_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO {table} (id, {', '.join(fields.keys())})
            VALUES (:id, {', '.join(f':{key}' for key in fields)})
            ON CONFLICT(id) DO UPDATE SET {placeholders},
                updated_at = CURRENT_TIMESTAMP
            """,
            fields_with_id,
        )


def reset_sync_flags(table: str, record_ids: Optional[Iterable[str]] = None) -> None:
    """Reset the sync flag for specific records or entire tables."""

    try:
        with get_connection() as conn:
            if record_ids is None:
                conn.execute(
                    f"UPDATE {table} SET synced_to_supabase = 0, updated_at = CURRENT_TIMESTAMP"
                )
            else:
                conn.executemany(
                    f"""
                    UPDATE {table}
                       SET synced_to_supabase = 0,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE id = ?
                    """,
                    ((record_id,) for record_id in record_ids),
                )
    except sqlite3.DatabaseError as exc:
        logger.error("Failed to reset sync flags for %s: %s", table, exc)


def generate_local_id(prefix: str) -> str:
    """Return a stable identifier for locally created records."""

    return f"{prefix}_{uuid.uuid4().hex}"


def _normalise_timestamp(value: Optional[str]) -> Optional[str]:
    """Return ``value`` or the current timestamp if ``value`` requests ``now()``."""

    if value is None:
        return None
    if isinstance(value, str) and value.lower() == "now()":
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return value


def _prepare_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Drop ``None`` values while keeping falsy but meaningful data."""

    return {key: value for key, value in fields.items() if value is not None}


def _save_record(
    table: str,
    record_id: str,
    fields: Dict[str, Any],
    *,
    supabase_id: Optional[str] = None,
    synced: bool = False,
) -> None:
    payload = _prepare_fields(fields)
    if supabase_id is not None:
        payload["supabase_id"] = supabase_id
    payload["synced_to_supabase"] = 1 if synced else 0
    upsert_record(table, record_id, payload)


def _update_record(
    table: str,
    record_id: str,
    fields: Dict[str, Any],
    *,
    supabase_id: Optional[str] = None,
    synced: Optional[bool] = None,
) -> None:
    payload = _prepare_fields(fields)
    if supabase_id is not None:
        payload["supabase_id"] = supabase_id
    if synced is not None:
        payload["synced_to_supabase"] = 1 if synced else 0

    if not payload:
        return

    assignments = ", ".join(f"{key} = :{key}" for key in payload)
    payload["id"] = record_id

    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            UPDATE {table}
               SET {assignments},
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = :id
            """,
            payload,
        )
        if cursor.rowcount == 0:
            _save_record(
                table,
                record_id,
                fields,
                supabase_id=supabase_id,
                synced=synced or False,
            )


def save_batch_record(
    record_id: str,
    *,
    batch_type: str,
    status: str,
    file_count: Optional[int] = None,
    total_size_gb: Optional[float] = None,
    source_type: Optional[str] = None,
    supabase_id: Optional[str] = None,
    synced: bool = False,
) -> None:
    """Persist (or upsert) a batch record to the local database."""

    fields: Dict[str, Any] = {
        "batch_type": batch_type,
        "status": status,
        "file_count": file_count,
        "total_size_gb": total_size_gb,
        "source_type": source_type or batch_type,
    }
    _save_record(
        "batches",
        record_id,
        fields,
        supabase_id=supabase_id,
        synced=synced,
    )


def save_media_file_record(
    record_id: str,
    *,
    filename: str,
    file_path: str,
    file_hash: Optional[str],
    status: str,
    file_size: Optional[int] = None,
    original_size: Optional[int] = None,
    compressed_size: Optional[int] = None,
    space_saved: Optional[int] = None,
    compression_percentage: Optional[float] = None,
    compression_ratio: Optional[float] = None,
    is_duplicate: Optional[bool] = None,
    batch_id: Optional[str] = None,
    source_path: Optional[str] = None,
    source_type: Optional[str] = None,
    processed_at: Optional[str] = None,
    supabase_id: Optional[str] = None,
    synced: bool = False,
) -> None:
    """Persist (or upsert) a media file record to the local database."""

    fields: Dict[str, Any] = {
        "filename": filename,
        "file_path": file_path,
        "file_hash": file_hash,
        "status": status,
        "file_size": file_size,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "space_saved": space_saved,
        "compression_percentage": compression_percentage,
        "compression_ratio": compression_ratio,
        "batch_id": batch_id,
        "source_path": source_path,
        "source_type": source_type or "unknown",
        "processed_at": _normalise_timestamp(processed_at),
    }
    if is_duplicate is not None:
        fields["is_duplicate"] = int(bool(is_duplicate))
    _save_record(
        "media_files",
        record_id,
        fields,
        supabase_id=supabase_id,
        synced=synced,
    )


def update_batch_status_local(
    record_id: str,
    status: str,
    *,
    extra_fields: Optional[Dict[str, Any]] = None,
    supabase_id: Optional[str] = None,
    synced: Optional[bool] = None,
) -> None:
    """Update the status (and optional metadata) of a batch record locally."""

    fields = dict(extra_fields or {})
    fields["status"] = status
    if "completed_at" in fields:
        fields["completed_at"] = _normalise_timestamp(fields["completed_at"])
    _update_record(
        "batches",
        record_id,
        fields,
        supabase_id=supabase_id,
        synced=synced,
    )


def update_media_status_local(
    record_id: str,
    status: str,
    *,
    extra_fields: Optional[Dict[str, Any]] = None,
    supabase_id: Optional[str] = None,
    synced: Optional[bool] = None,
) -> None:
    """Update the status (and optional metadata) of a media record locally."""

    fields = dict(extra_fields or {})
    fields["status"] = status
    if "processed_at" in fields:
        fields["processed_at"] = _normalise_timestamp(fields["processed_at"])
    _update_record(
        "media_files",
        record_id,
        fields,
        supabase_id=supabase_id,
        synced=synced,
    )


def media_hash_exists(file_hash: Optional[str]) -> bool:
    """Return ``True`` when a media record already tracks ``file_hash`` locally."""

    if not file_hash:
        return False

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM media_files WHERE file_hash = ? LIMIT 1",
                (file_hash,),
            )
            return cursor.fetchone() is not None
    except sqlite3.DatabaseError as exc:
        logger.error("Failed to check media hash existence for %s: %s", file_hash, exc)
        return False
