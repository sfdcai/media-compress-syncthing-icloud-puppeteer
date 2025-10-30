import os
import logging
import time
import hashlib
import stat
import pwd
import grp
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Optional, Set

from dotenv import load_dotenv
from supabase import create_client

try:  # Support both package and script execution
    from .local_db_manager import (
        generate_local_id,
        media_hash_exists,
        save_batch_record,
        save_media_file_record,
        update_batch_status_local,
        update_media_status_local,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from local_db_manager import (  # type: ignore
        generate_local_id,
        media_hash_exists,
        save_batch_record,
        save_media_file_record,
        update_batch_status_local,
        update_media_status_local,
    )

# Load environment variables
# Try multiple paths to find the config file
config_paths = [
    "config/settings.env",  # Relative to current directory
    "../config/settings.env",  # Relative to scripts directory
    "/opt/media-pipeline/config/settings.env"  # Absolute path
]

config_loaded = False
for config_path in config_paths:
    if os.path.exists(config_path):
        load_dotenv(config_path)
        config_loaded = True
        break

if not config_loaded:
    print(f"Warning: Could not find config file. Tried: {config_paths}")

# Supabase configuration (initial values refreshed lazily in get_supabase_client)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_supabase_client = None
_supabase_init_attempted = False
_supabase_unavailable_messages: Set[str] = set()


def get_supabase_client(force_refresh: bool = False):
    """Lazily instantiate the Supabase client."""
    global _supabase_client, _supabase_init_attempted, SUPABASE_URL, SUPABASE_KEY

    if force_refresh:
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        _supabase_init_attempted = False
        _supabase_client = None

    if _supabase_client is not None:
        return _supabase_client

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if _supabase_init_attempted:
        return _supabase_client

    _supabase_init_attempted = True

    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.warning(
            "Supabase credentials are missing. Remote logging and syncing will be skipped."
        )
        return None

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:  # pragma: no cover - defensive: network/auth failures
        logging.error(f"Failed to initialize Supabase client: {exc}")
        _supabase_client = None

    return _supabase_client


def _log_supabase_unavailable(operation: str):
    """Log once per operation when Supabase is unavailable."""

    if operation in _supabase_unavailable_messages:
        return

    logging.warning(
        "Skipping Supabase %s because the client is unavailable.",
        operation,
    )
    _supabase_unavailable_messages.add(operation)

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = Path(os.getenv("LOG_FILE", "logs/pipeline.log"))

try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
except OSError as exc:  # pragma: no cover - defensive logging configuration
    print(f"Warning: Could not create log directory {LOG_FILE.parent}: {exc}")

logging.basicConfig(
    filename=str(LOG_FILE),
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def _current_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _store_local_batch(
    batch_id: str,
    batch_type: str,
    status: str,
    file_count: int,
    total_size_gb: float,
    *,
    supabase_id: Optional[str],
    synced: bool,
) -> None:
    try:
        save_batch_record(
            batch_id,
            batch_type=batch_type,
            status=status,
            file_count=file_count,
            total_size_gb=total_size_gb,
            supabase_id=supabase_id,
            synced=synced,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.error("Failed to persist local batch record %s: %s", batch_id, exc)


def _store_local_media(
    media_id: str,
    filename: str,
    file_path: str,
    file_hash: str,
    status: str,
    file_size: int,
    batch_id: Optional[str],
    source_path: Optional[str],
    processed_at: Optional[str],
    *,
    supabase_id: Optional[str],
    synced: bool,
) -> None:
    try:
        save_media_file_record(
            media_id,
            filename=filename,
            file_path=file_path,
            file_hash=file_hash,
            status=status,
            file_size=file_size,
            batch_id=batch_id,
            source_path=source_path,
            processed_at=processed_at,
            supabase_id=supabase_id,
            synced=synced,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.error("Failed to persist local media record %s: %s", media_id, exc)

def log_step(step, message, status="info"):
    """Log a step to both file and Supabase"""
    logging.info(f"{step}: {message}")

    client = get_supabase_client()
    if not client:
        _log_supabase_unavailable("pipeline log insert")
        return

    try:
        client.table("pipeline_logs").insert({
            "step": step,
            "message": message,
            "status": status
        }).execute()
    except Exception as e:
        logging.error(f"Supabase log failed: {e}")

def retry(max_attempts=3, delay=5):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # pragma: no cover - behaviour verified via tests
                    last_exception = e
                    log_step(func.__name__, f"Attempt {attempt} failed: {e}", "error")
                    if attempt == max_attempts:
                        break
                    time.sleep(delay * (2 ** (attempt - 1)))  # Exponential backoff

            if last_exception is not None:
                raise last_exception

        return wrapper

    return decorator

def calculate_file_hash(file_path, algorithm="md5", chunk_size=8192):
    """Calculate hash of a file efficiently"""
    hash_obj = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        log_step("hash_calculation", f"Failed to calculate hash for {file_path}: {e}", "error")
        return None

def get_file_size_gb(file_path):
    """Get file size in GB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 ** 3)
    except Exception as e:
        log_step("file_size", f"Failed to get size for {file_path}: {e}", "error")
        return 0

def ensure_directory_exists(directory_path):
    """Ensure directory exists with proper permissions"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        ensure_proper_permissions(directory_path)
        return True
    except Exception as e:
        log_step("directory_creation", f"Failed to create directory {directory_path}: {e}", "error")
        return False

def ensure_proper_permissions(file_path, user="media-pipeline", group="media-pipeline"):
    """Ensure files have proper permissions for LXC container"""
    try:
        media_user = pwd.getpwnam(user)
        media_group = grp.getgrnam(group)
        os.chown(file_path, media_user.pw_uid, media_group.gr_gid)
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
    except Exception as e:
        log_step("permissions", f"Failed to set permissions for {file_path}: {e}", "error")

def validate_mount_points():
    """Validate NAS and Syncthing mount points."""

    success = True
    mount_points = [
        os.getenv("NAS_MOUNT", "/mnt/nas/photos"),
        os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel"),
    ]

    for mount_point in mount_points:
        if not mount_point:
            continue

        if not os.path.exists(mount_point):
            log_step(
                "mount_validation",
                f"Mount point {mount_point} does not exist; it will be created if needed",
                "warning",
            )
            continue

        if not os.access(mount_point, os.W_OK):
            log_step(
                "mount_validation",
                f"Mount point {mount_point} is not writable",
                "error",
            )
            success = False

    return success

def validate_config():
    """Validate configuration settings, tolerating optional dependencies."""

    success = True

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        log_step(
            "config_validation",
            "Supabase credentials are not set; operating in offline mode",
            "warning",
        )
    else:
        log_step("config_validation", "Supabase credentials detected", "info")

    defaults = {
        "NAS_MOUNT": "/opt/media-pipeline",
        "PIXEL_SYNC_FOLDER": "/mnt/syncthing/pixel",
    }
    for setting, default_value in defaults.items():
        if not os.getenv(setting):
            log_step(
                "config_validation",
                f"{setting} not set; defaulting to {default_value}",
                "warning",
            )

    feature_toggles = [
        "ENABLE_ICLOUD_UPLOAD",
        "ENABLE_PIXEL_UPLOAD",
        "ENABLE_COMPRESSION",
        "ENABLE_DEDUPLICATION",
        "ENABLE_SORTING",
    ]

    # Validate feature toggles
    for toggle in feature_toggles:
        value = os.getenv(toggle, "true").lower()
        if value not in ["true", "false"]:
            log_step(
                "config_validation",
                f"Invalid value for {toggle}: {value}",
                "error",
            )
            success = False

    # Validate mount points (warnings already emitted inside the helper)
    if not validate_mount_points():
        success = False

    if success:
        log_step("config_validation", "Configuration validation passed", "success")
    else:
        log_step(
            "config_validation",
            "Configuration validation completed with warnings or errors",
            "warning",
        )

    return success

def get_feature_toggle(toggle_name, default=True):
    """Get feature toggle value"""
    value = os.getenv(toggle_name, str(default)).lower()
    return value == "true"

def update_file_status(file_id, status, **kwargs):
    """Update a media file status in Supabase and mirror it locally."""

    client = get_supabase_client()
    supabase_success = False
    update_data = {"status": status, "updated_at": "now()"}
    update_data.update(kwargs)

    if client:
        try:
            client.table("media_files").update(update_data).eq("id", file_id).execute()
            log_step(
                "file_status_update",
                f"Updated file {file_id} status to {status}",
                "success",
            )
            supabase_success = True
        except Exception as e:
            log_step(
                "file_status_update",
                f"Failed to update file {file_id}: {e}",
                "error",
            )
    else:
        _log_supabase_unavailable("media file status update")

    local_fields = dict(update_data)
    if local_fields.get("processed_at") == "now()":
        local_fields["processed_at"] = _current_timestamp()
    if local_fields.get("updated_at") == "now()":
        local_fields["updated_at"] = _current_timestamp()
    local_fields.pop("status", None)

    update_media_status_local(
        file_id,
        status,
        extra_fields=local_fields,
        synced=supabase_success,
    )

def create_batch_record(batch_type, file_count=0, total_size_gb=0):
    """Create a new batch record, falling back to the local cache when required."""

    client = get_supabase_client()
    batch_data = {
        "batch_type": batch_type,
        "status": "created",
        "file_count": file_count,
        "total_size_gb": total_size_gb,
    }

    if client:
        try:
            result = client.table("batches").insert(batch_data).execute()
            data = getattr(result, "data", None)
            batch_id = data[0]["id"] if data else None
            if batch_id:
                log_step(
                    "batch_creation",
                    f"Created batch {batch_id} for {batch_type}",
                    "success",
                )
                _store_local_batch(
                    batch_id,
                    batch_type=batch_type,
                    status="created",
                    file_count=file_count,
                    total_size_gb=total_size_gb,
                    supabase_id=batch_id,
                    synced=True,
                )
                return batch_id

            log_step(
                "batch_creation",
                f"Supabase insert for {batch_type} returned no data; using local cache",
                "warning",
            )
        except Exception as e:
            log_step("batch_creation", f"Failed to create batch: {e}", "error")
    else:
        _log_supabase_unavailable("batch creation")

    local_batch_id = generate_local_id("batch")
    _store_local_batch(
        local_batch_id,
        batch_type=batch_type,
        status="created",
        file_count=file_count,
        total_size_gb=total_size_gb,
        supabase_id=None,
        synced=False,
    )
    log_step(
        "batch_creation",
        f"Created local batch {local_batch_id} for {batch_type}; pending Supabase sync",
        "warning",
    )
    return local_batch_id

def update_batch_status(batch_id, status, **kwargs):
    """Update batch status in Supabase and mirror it in the local cache."""

    client = get_supabase_client()
    supabase_success = False
    update_data = {"status": status}
    update_data.update(kwargs)
    if status == "completed" and "completed_at" not in update_data:
        update_data["completed_at"] = "now()"

    if client:
        try:
            client.table("batches").update(update_data).eq("id", batch_id).execute()
            log_step(
                "batch_status_update",
                f"Updated batch {batch_id} status to {status}",
                "success",
            )
            supabase_success = True
        except Exception as e:
            log_step(
                "batch_status_update",
                f"Failed to update batch {batch_id}: {e}",
                "error",
            )
    else:
        _log_supabase_unavailable("batch status update")

    local_fields = dict(update_data)
    if local_fields.get("completed_at") == "now()":
        local_fields["completed_at"] = _current_timestamp()
    local_fields.pop("status", None)

    update_batch_status_local(
        batch_id,
        status,
        extra_fields=local_fields,
        synced=supabase_success,
    )

def get_files_by_status(status):
    """Get files by status from database"""
    client = get_supabase_client()
    if not client:
        _log_supabase_unavailable("media file query by status")
        logging.debug(
            "Supabase unavailable when querying media files with status %s",
            status,
        )
        return []

    try:
        result = client.table("media_files").select("*").eq("status", status).execute()
        return result.data
    except Exception as e:
        log_step("file_query", f"Failed to get files with status {status}: {e}", "error")
        return []

def is_duplicate_file(file_hash):
    """Check if file hash already exists in Supabase or the local cache."""

    if not file_hash:
        return False

    client = get_supabase_client()
    if client:
        try:
            result = (
                client.table("media_files")
                .select("id")
                .eq("file_hash", file_hash)
                .execute()
            )
            if len(result.data) > 0:
                return True
        except Exception as e:
            log_step(
                "duplicate_check",
                f"Failed to check duplicate for hash {file_hash}: {e}",
                "error",
            )
    else:
        _log_supabase_unavailable("duplicate check")

    exists_locally = media_hash_exists(file_hash)
    if exists_locally:
        logging.debug("Local cache reports existing hash %s", file_hash)
    return exists_locally

def log_duplicate_file(original_file_id, duplicate_file_id, file_hash):
    """Log duplicate file relationship"""
    client = get_supabase_client()
    if not client:
        _log_supabase_unavailable("duplicate logging")
        logging.debug(
            "Supabase unavailable when logging duplicate relationship for hash %s",
            file_hash,
        )
        return

    try:
        duplicate_data = {
            "original_file_id": original_file_id,
            "duplicate_file_id": duplicate_file_id,
            "hash": file_hash
        }

        client.table("duplicate_files").insert(duplicate_data).execute()
        log_step("duplicate_logging", f"Logged duplicate relationship for hash {file_hash}", "success")
    except Exception as e:
        log_step("duplicate_logging", f"Failed to log duplicate: {e}", "error")

def create_media_file_record(file_path, file_hash=None, batch_id=None, source_path=None):
    """Create a new media file record, with an offline-safe fallback."""

    filename = os.path.basename(file_path)
    try:
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    except OSError as exc:
        log_step(
            "media_file_creation",
            f"Unable to determine size for {file_path}: {exc}",
            "warning",
        )
        file_size = 0

    if not file_hash:
        file_hash = calculate_file_hash(file_path)

    if not file_hash:
        log_step(
            "media_file_creation",
            f"Unable to determine hash for {file_path}; skipping record creation",
            "error",
        )
        return None

    client = get_supabase_client()
    processed_at = _current_timestamp()

    if client:
        try:
            media_data = {
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "file_hash": file_hash,
                "status": "downloaded",
                "source_path": source_path or file_path,
                "batch_id": batch_id,
                "processed_at": "now()",
            }

            result = client.table("media_files").insert(media_data).execute()
            data = getattr(result, "data", None)

            if data:
                payload = data[0]
                file_id = payload.get("id") if isinstance(payload, dict) else None
                if file_id:
                    log_step(
                        "media_file_creation",
                        f"Created media file record {file_id} for {filename}",
                        "success",
                    )
                    _store_local_media(
                        file_id,
                        filename=filename,
                        file_path=file_path,
                        file_hash=file_hash,
                        status="downloaded",
                        file_size=file_size,
                        batch_id=batch_id,
                        source_path=source_path or file_path,
                        processed_at=processed_at,
                        supabase_id=file_id,
                        synced=True,
                    )
                    return file_id

            log_step(
                "media_file_creation",
                f"Supabase insert for {file_path} returned no data; storing locally",
                "warning",
            )
        except Exception as e:
            log_step(
                "media_file_creation",
                f"Failed to create media file record for {file_path}: {e}",
                "error",
            )
    else:
        _log_supabase_unavailable("media file creation")

    local_file_id = generate_local_id("media")
    _store_local_media(
        local_file_id,
        filename=filename,
        file_path=file_path,
        file_hash=file_hash,
        status="downloaded",
        file_size=file_size,
        batch_id=batch_id,
        source_path=source_path or file_path,
        processed_at=processed_at,
        supabase_id=None,
        synced=False,
    )
    log_step(
        "media_file_creation",
        f"Created local media record {local_file_id} for {filename}; pending Supabase sync",
        "warning",
    )
    return local_file_id

def get_media_files_by_directory(directory):
    """Get all media files from a directory"""
    client = get_supabase_client()
    if not client:
        _log_supabase_unavailable("media file directory query")
        logging.debug(
            "Supabase unavailable when querying media files for directory %s",
            directory,
        )
        return []

    try:
        result = client.table("media_files").select("*").ilike("file_path", f"{directory}%").execute()
        return result.data
    except Exception as e:
        log_step("file_query", f"Failed to get files from directory {directory}: {e}", "error")
        return []
