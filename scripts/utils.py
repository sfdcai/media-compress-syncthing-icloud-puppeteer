import os
import logging
import time
import hashlib
import stat
import pwd
import grp
from functools import wraps
from dotenv import load_dotenv
from supabase import create_client

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

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    filename="logs/pipeline.log", 
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log_step(step, message, status="info"):
    """Log a step to both file and Supabase"""
    logging.info(f"{step}: {message}")
    try:
        supabase.table("pipeline_logs").insert({
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
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log_step(func.__name__, f"Attempt {attempt} failed: {e}", "error")
                    if attempt == max_attempts:
                        raise
                    time.sleep(delay * (2 ** (attempt - 1)))  # Exponential backoff
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
    """Validate NAS and Syncthing mount points"""
    mount_points = [
        os.getenv("NAS_MOUNT", "/mnt/nas/photos"),
        os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel")
    ]
    
    for mount_point in mount_points:
        if not os.path.exists(mount_point):
            log_step("mount_validation", f"Mount point {mount_point} does not exist", "error")
            return False
        
        if not os.access(mount_point, os.W_OK):
            log_step("mount_validation", f"Mount point {mount_point} is not writable", "error")
            return False
    
    return True

def validate_config():
    """Validate all configuration settings and feature toggles"""
    required_settings = [
        'SUPABASE_URL', 'SUPABASE_KEY', 'NAS_MOUNT', 'PIXEL_SYNC_FOLDER'
    ]
    
    feature_toggles = [
        'ENABLE_ICLOUD_UPLOAD', 'ENABLE_PIXEL_UPLOAD', 
        'ENABLE_COMPRESSION', 'ENABLE_DEDUPLICATION', 'ENABLE_SORTING'
    ]
    
    # Validate required settings
    for setting in required_settings:
        if not os.getenv(setting):
            log_step("config_validation", f"Required setting {setting} is missing", "error")
            return False
    
    # Validate feature toggles
    for toggle in feature_toggles:
        value = os.getenv(toggle, "true").lower()
        if value not in ["true", "false"]:
            log_step("config_validation", f"Invalid value for {toggle}: {value}", "error")
            return False
    
    # Validate mount points
    if not validate_mount_points():
        return False
    
    log_step("config_validation", "Configuration validation passed", "success")
    return True

def get_feature_toggle(toggle_name, default=True):
    """Get feature toggle value"""
    value = os.getenv(toggle_name, str(default)).lower()
    return value == "true"

def update_file_status(file_id, status, **kwargs):
    """Update file status in database"""
    try:
        update_data = {"status": status, "updated_at": "now()"}
        update_data.update(kwargs)
        
        supabase.table("media_files").update(update_data).eq("id", file_id).execute()
        log_step("file_status_update", f"Updated file {file_id} status to {status}", "success")
    except Exception as e:
        log_step("file_status_update", f"Failed to update file {file_id}: {e}", "error")

def create_batch_record(batch_type, file_count=0, total_size_gb=0):
    """Create a new batch record in database"""
    try:
        batch_data = {
            "batch_type": batch_type,
            "status": "created",
            "file_count": file_count,
            "total_size_gb": total_size_gb
        }
        
        result = supabase.table("batches").insert(batch_data).execute()
        batch_id = result.data[0]["id"]
        log_step("batch_creation", f"Created batch {batch_id} for {batch_type}", "success")
        return batch_id
    except Exception as e:
        log_step("batch_creation", f"Failed to create batch: {e}", "error")
        return None

def update_batch_status(batch_id, status, **kwargs):
    """Update batch status in database"""
    try:
        update_data = {"status": status}
        if status == "completed":
            update_data["completed_at"] = "now()"
        update_data.update(kwargs)
        
        supabase.table("batches").update(update_data).eq("id", batch_id).execute()
        log_step("batch_status_update", f"Updated batch {batch_id} status to {status}", "success")
    except Exception as e:
        log_step("batch_status_update", f"Failed to update batch {batch_id}: {e}", "error")

def get_files_by_status(status):
    """Get files by status from database"""
    try:
        result = supabase.table("media_files").select("*").eq("status", status).execute()
        return result.data
    except Exception as e:
        log_step("file_query", f"Failed to get files with status {status}: {e}", "error")
        return []

def is_duplicate_file(file_hash):
    """Check if file hash already exists in database"""
    try:
        result = supabase.table("media_files").select("id").eq("file_hash", file_hash).execute()
        return len(result.data) > 0
    except Exception as e:
        log_step("duplicate_check", f"Failed to check duplicate for hash {file_hash}: {e}", "error")
        return False

def log_duplicate_file(original_file_id, duplicate_file_id, file_hash):
    """Log duplicate file relationship"""
    try:
        duplicate_data = {
            "original_file_id": original_file_id,
            "duplicate_file_id": duplicate_file_id,
            "hash": file_hash
        }
        
        supabase.table("duplicate_files").insert(duplicate_data).execute()
        log_step("duplicate_logging", f"Logged duplicate relationship for hash {file_hash}", "success")
    except Exception as e:
        log_step("duplicate_logging", f"Failed to log duplicate: {e}", "error")

def create_media_file_record(file_path, file_hash=None, batch_id=None, source_path=None):
    """Create a new media file record in database"""
    try:
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Calculate file hash if not provided
        if not file_hash:
            file_hash = calculate_file_hash(file_path)
        
        media_data = {
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_hash": file_hash,
            "status": "downloaded",
            "source_path": source_path or file_path,
            "batch_id": batch_id,
            "processed_at": "now()"
        }
        
        result = supabase.table("media_files").insert(media_data).execute()
        file_id = result.data[0]["id"]
        log_step("media_file_creation", f"Created media file record {file_id} for {filename}", "success")
        return file_id
        
    except Exception as e:
        log_step("media_file_creation", f"Failed to create media file record for {file_path}: {e}", "error")
        return None

def get_media_files_by_directory(directory):
    """Get all media files from a directory"""
    try:
        result = supabase.table("media_files").select("*").ilike("file_path", f"{directory}%").execute()
        return result.data
    except Exception as e:
        log_step("file_query", f"Failed to get files from directory {directory}: {e}", "error")
        return []
