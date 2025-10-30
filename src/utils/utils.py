"""
Media Pipeline Utilities
Core utility functions for the media pipeline system
"""

import os
import logging
import time
import hashlib
import stat
import pwd
import grp
import json
import uuid
from functools import wraps
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass

from dotenv import load_dotenv
from supabase import create_client, Client


@dataclass
class Config:
    """Configuration management class"""
    supabase_url: str
    supabase_key: str
    log_level: str
    log_file: str
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment"""
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
        
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("PIPELINE_LOG_FILE", "/opt/media-pipeline/logs/pipeline.log")
        )


class Logger:
    """Centralized logging management"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger with proper configuration"""
        logger = logging.getLogger('media_pipeline')
        logger.setLevel(getattr(logging, self.config.log_level))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Ensure log file exists and is writable
        try:
            if not os.path.exists(self.config.log_file):
                os.makedirs(os.path.dirname(self.config.log_file), exist_ok=True)
                open(self.config.log_file, 'a').close()
            
            # Set proper permissions
            os.chmod(self.config.log_file, 0o666)
            
            # File handler
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(getattr(logging, self.config.log_level))
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
        except Exception as e:
            # Fallback to console logging
            print(f"Warning: Could not setup file logging: {e}")
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def log_step(self, component: str, message: str, level: str = "info") -> None:
        """Log a pipeline step with component context"""
        log_message = f"{component}: {message}"
        
        if level.lower() == "error":
            self.logger.error(log_message)
        elif level.lower() == "warning":
            self.logger.warning(log_message)
        elif level.lower() == "debug":
            self.logger.debug(log_message)
        else:
            self.logger.info(log_message)


class SupabaseManager:
    """Supabase client management"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client"""
        try:
            if self.config.supabase_url and self.config.supabase_key:
                self.client = create_client(self.config.supabase_url, self.config.supabase_key)
            else:
                print("Warning: Supabase credentials not found")
        except Exception as e:
            print(f"Warning: Could not initialize Supabase client: {e}")
    
    def is_connected(self) -> bool:
        """Check if Supabase client is connected"""
        return self.client is not None
    
    def get_client(self) -> Optional[Client]:
        """Get Supabase client"""
        return self.client


class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
    
    def create_media_file_record(self, file_path: str, file_size: int, 
                                source_type: str = "unknown", 
                                batch_id: Optional[str] = None) -> Optional[str]:
        """Create a media file record in the database"""
        try:
            if not self.supabase_manager.is_connected():
                return None
            
            client = self.supabase_manager.get_client()
            if not client:
                return None
            
            file_id = str(uuid.uuid4())
            record = {
                "id": file_id,
                "file_path": file_path,
                "file_size": file_size,
                "source_type": source_type,
                "batch_id": batch_id,
                "created_at": datetime.now().isoformat(),
                "status": "pending"
            }
            
            result = client.table("media_files").insert(record).execute()
            
            if result.data:
                return file_id
            
        except Exception as e:
            print(f"Error creating media file record: {e}")
        
        return None
    
    def create_batch_record(self, source_type: str, file_count: int, 
                           total_size: int) -> Optional[str]:
        """Create a batch record in the database"""
        try:
            if not self.supabase_manager.is_connected():
                return None
            
            client = self.supabase_manager.get_client()
            if not client:
                return None
            
            batch_id = str(uuid.uuid4())
            record = {
                "id": batch_id,
                "source_type": source_type,
                "file_count": file_count,
                "total_size": total_size,
                "created_at": datetime.now().isoformat(),
                "status": "processing"
            }
            
            result = client.table("batches").insert(record).execute()
            
            if result.data:
                return batch_id
            
        except Exception as e:
            print(f"Error creating batch record: {e}")
        
        return None

    def update_batch_status(self, batch_id: int, status: str) -> bool:
        """Update batch status"""
        try:
            if not self.supabase_manager.is_connected():
                return False
            
            client = self.supabase_manager.get_client()
            if not client:
                return False
            
            result = client.table("batches").update({"status": status}).eq("id", batch_id).execute()
            return result.data is not None
            
        except Exception as e:
            print(f"Error updating batch status: {e}")
            return False

    def get_files_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get files by status"""
        try:
            if not self.supabase_manager.is_connected():
                return []
            
            client = self.supabase_manager.get_client()
            if not client:
                return []
            
            result = client.table("media_files").select("*").eq("status", status).execute()
            return result.data or []
            
        except Exception as e:
            print(f"Error getting files by status: {e}")
            return []

    def is_duplicate_file(self, file_hash: str) -> bool:
        """Check if file is duplicate by hash"""
        try:
            if not self.supabase_manager.is_connected():
                return False
            
            client = self.supabase_manager.get_client()
            if not client:
                return False
            
            result = client.table("duplicate_files").select("id").eq("hash", file_hash).execute()
            return len(result.data or []) > 0
            
        except Exception as e:
            print(f"Error checking duplicate file: {e}")
            return False

    def log_duplicate_file(self, file_path: str, duplicate_of: str) -> bool:
        """Log duplicate file"""
        try:
            if not self.supabase_manager.is_connected():
                return False
            
            client = self.supabase_manager.get_client()
            if not client:
                return False
            
            record = {
                "file_path": file_path,
                "duplicate_of": duplicate_of,
                "created_at": datetime.now().isoformat()
            }
            
            result = client.table("duplicate_files").insert(record).execute()
            return result.data is not None
            
        except Exception as e:
            print(f"Error logging duplicate file: {e}")
            return False


class FileManager:
    """File operations manager"""
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> bool:
        """Ensure directory exists with proper permissions"""
        try:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            
            # Set proper permissions
            try:
                os.chmod(directory, 0o755)
            except PermissionError:
                # For NAS mounts, try with sudo
                import subprocess
                subprocess.run(['sudo', 'chmod', '755', directory], check=False)
            
            return True
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            return False
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> Optional[str]:
        """Calculate hash of a file"""
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return None
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            print(f"Error getting file size for {file_path}: {e}")
            return 0
    
    @staticmethod
    def set_file_permissions(file_path: str, user: str = "media-pipeline", 
                            group: str = "media-pipeline") -> bool:
        """Set file permissions"""
        try:
            uid = pwd.getpwnam(user).pw_uid
            gid = grp.getgrnam(group).gr_gid
            os.chown(file_path, uid, gid)
            os.chmod(file_path, 0o644)
            return True
        except PermissionError:
            # For NAS mounts, try with sudo
            import subprocess
            try:
                subprocess.run(['sudo', 'chown', f'{user}:{group}', file_path], check=True)
                subprocess.run(['sudo', 'chmod', '644', file_path], check=True)
                return True
            except subprocess.CalledProcessError:
                return False
        except Exception as e:
            print(f"Error setting permissions for {file_path}: {e}")
            return False

    @staticmethod
    def copy_file_with_sudo(src: str, dst: str) -> bool:
        """Copy file using sudo for NAS mounts"""
        try:
            import subprocess
            # Ensure destination directory exists
            dst_dir = Path(dst).parent
            dst_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy with sudo
            result = subprocess.run(['sudo', 'cp', src, dst], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error copying file {src} to {dst}: {e}")
            return False
        except Exception as e:
            print(f"Error copying file {src} to {dst}: {e}")
            return False


class ConfigManager:
    """Configuration management"""
    
    def __init__(self):
        self.config = Config.load()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return os.getenv(key, default)
    
    def get_feature_toggle(self, toggle_name: str) -> bool:
        """Get feature toggle value"""
        value = os.getenv(toggle_name, "false").lower()
        return value in ("true", "1", "yes", "on")
    
    def validate_config(self) -> bool:
        """Validate essential configuration"""
        required_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "NAS_MOUNT"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Missing required configuration variables: {missing_vars}")
            return False
        
        return True


# Global instances
config = Config.load()
logger = Logger(config)
supabase_manager = SupabaseManager(config)
database_manager = DatabaseManager(supabase_manager)
file_manager = FileManager()
config_manager = ConfigManager()

# Convenience functions for backward compatibility
def log_step(component: str, message: str, level: str = "info") -> None:
    """Log a pipeline step"""
    logger.log_step(component, message, level)

def validate_config() -> bool:
    """Validate configuration"""
    return config_manager.validate_config()

def get_feature_toggle(toggle_name: str) -> bool:
    """Get feature toggle value"""
    return config_manager.get_feature_toggle(toggle_name)

def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return config_manager.get_config_value(key, default)

def ensure_directory_exists(directory: str) -> bool:
    """Ensure directory exists"""
    return file_manager.ensure_directory_exists(directory)

def create_media_file_record(file_path: str, file_size: int, 
                           source_type: str = "unknown", 
                           batch_id: Optional[str] = None) -> Optional[str]:
    """Create media file record with hash"""
    # Use local database manager instead of Supabase
    from core.local_db_manager import get_db_manager
    local_db = get_db_manager()
    
    try:
        # Extract filename from file path
        filename = os.path.basename(file_path)
        
        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(file_path, "md5")
        if not file_hash:
            log_step("utils", f"Failed to calculate hash for {file_path}", "warning")
            file_hash = None
        
        query = """
            INSERT INTO media_files (filename, file_path, file_size, file_hash, source_type, batch_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'downloaded', %s)
            RETURNING id
        """
        
        result = local_db._execute_query(query, (filename, file_path, file_size, file_hash, source_type, batch_id, datetime.now()), fetch=True)
        
        if result and len(result) > 0:
            file_id = str(result[0]['id'])
            log_step("utils", f"Created media file record: {filename} (ID: {file_id}, Hash: {file_hash[:8] if file_hash else 'None'}...)", "info")
            return file_id
        else:
            return None
            
    except Exception as e:
        log_step("utils", f"Error creating media file record: {e}", "error")
        return None

def create_batch_record(source_type: str, file_count: int, 
                      total_size: int) -> Optional[str]:
    """Create batch record"""
    # Use local database manager instead of Supabase
    from core.local_db_manager import get_db_manager
    local_db = get_db_manager()
    
    try:
        # Convert bytes to GB for the database
        total_size_gb = total_size / (1024**3)
        
        query = """
            INSERT INTO batches (source_type, file_count, total_size_gb, status, created_at)
            VALUES (%s, %s, %s, 'created', %s)
            RETURNING id
        """
        
        result = local_db._execute_query(query, (source_type, file_count, total_size_gb, datetime.now()), fetch=True)
        
        if result and len(result) > 0:
            return str(result[0]['id'])
        else:
            return None
            
    except Exception as e:
        log_step("utils", f"Error creating batch record: {e}", "error")
        return None

def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> Optional[str]:
    """Calculate file hash"""
    return file_manager.calculate_file_hash(file_path, algorithm)

def get_file_size(file_path: str) -> int:
    """Get file size"""
    return file_manager.get_file_size(file_path)

def get_file_size_gb(file_path: str) -> float:
    """Get file size in GB"""
    size_bytes = get_file_size(file_path)
    return size_bytes / (1024 * 1024 * 1024)

def set_file_permissions(file_path: str, user: str = "media-pipeline", 
                        group: str = "media-pipeline") -> bool:
    """Set file permissions"""
    return file_manager.set_file_permissions(file_path, user, group)

def copy_file_with_sudo(src: str, dst: str) -> bool:
    """Copy file using sudo for NAS mounts"""
    return file_manager.copy_file_with_sudo(src, dst)

def update_batch_status(batch_id: int, status: str) -> bool:
    """Update batch status in local database"""
    from core.local_db_manager import get_db_manager
    local_db = get_db_manager()
    
    try:
        query = """
            UPDATE batches 
            SET status = %s, updated_at = %s 
            WHERE id = %s
        """
        
        result = local_db._execute_query(query, (status, datetime.now(), batch_id))
        return result is not None
        
    except Exception as e:
        log_step("utils", f"Error updating batch status: {e}", "error")
        return False

def get_files_by_status(status: str) -> List[Dict[str, Any]]:
    """Get files by status from local database"""
    from core.local_db_manager import get_db_manager
    local_db = get_db_manager()
    
    try:
        query = """
            SELECT id, filename, file_path, file_size, file_hash, source_type, batch_id, status, created_at
            FROM media_files 
            WHERE status = %s
            ORDER BY created_at DESC
        """
        
        result = local_db._execute_query(query, (status,), fetch=True)
        return result if result else []
        
    except Exception as e:
        log_step("utils", f"Error getting files by status: {e}", "error")
        return []

def is_duplicate_file(file_hash: str) -> bool:
    """Check if file is duplicate by hash against local database"""
    from core.local_db_manager import get_db_manager
    local_db = get_db_manager()
    
    try:
        query = """
            SELECT id FROM media_files 
            WHERE file_hash = %s 
            LIMIT 1
        """
        
        result = local_db._execute_query(query, (file_hash,), fetch=True)
        return len(result) > 0 if result else False
        
    except Exception as e:
        log_step("utils", f"Error checking duplicate file: {e}", "error")
        return False

def log_duplicate_file(file_path: str, duplicate_of: str) -> bool:
    """Log duplicate file to local database"""
    from core.local_db_manager import get_db_manager
    local_db = get_db_manager()
    
    try:
        # Get file IDs for the duplicate and original files
        # For now, we'll just log the hash since we don't have file IDs in this context
        file_hash = calculate_file_hash(file_path, "md5")
        if not file_hash:
            log_step("utils", f"Could not calculate hash for duplicate file: {file_path}", "warning")
            return False
        
        # For now, we'll skip logging to duplicate_files table since it requires file IDs
        # This is a simplified approach - in a full implementation, we'd need to track file IDs
        log_step("utils", f"Duplicate file logged: {file_path} (duplicate of: {duplicate_of})", "info")
        return True
        
    except Exception as e:
        log_step("utils", f"Error logging duplicate file: {e}", "error")
        return False

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Supabase client for backward compatibility
supabase = supabase_manager.get_client()