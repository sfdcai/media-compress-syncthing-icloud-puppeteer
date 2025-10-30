#!/usr/bin/env python3
"""
Media Pipeline Web Dashboard Server
Provides REST API for the web interface
"""

import os
import sys
import json
import subprocess
import time
import threading
import re
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import psutil
import requests
from dotenv import load_dotenv

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(os.path.join(project_root, 'config', 'settings.env'))

# Import local database manager
try:
    from src.core.local_db_manager import get_db_manager
    db_manager = get_db_manager()
except Exception as e:
    print(f"Warning: Could not initialize database manager: {e}")
    db_manager = None

app = Flask(__name__)
CORS(app)

# Configuration
PIPELINE_DIR = "/opt/media-pipeline"
CONFIG_FILE = os.path.join(project_root, 'config', 'settings.env')
LOG_DIR = os.path.join(PIPELINE_DIR, 'logs')

class PipelineManager:
    def __init__(self):
        self.pipeline_process = None
        self.status_cache = {}
        self.cache_timeout = 30  # seconds
        
    def get_system_status(self):
        """Get comprehensive system status"""
        try:
            # Check if cache is still valid
            if 'timestamp' in self.status_cache:
                if time.time() - self.status_cache['timestamp'] < self.cache_timeout:
                    return self.status_cache
            
            status = {
                'timestamp': time.time(),
                'overall_status': 'healthy',
                'services': self.check_services(),
                'database': self.check_database(),
                'storage': self.check_storage(),
                'system': self.get_system_info()
            }
            
            # Determine overall status
            if (status['services']['media-pipeline'] != 'running' or 
                status['services']['syncthing@root'] != 'running' or
                not status['database']['connected'] or
                not status['storage']['mounted']):
                status['overall_status'] = 'unhealthy'
            
            self.status_cache = status
            return status
            
        except Exception as e:
            return {
                'timestamp': time.time(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    def check_services(self):
        """Check status of system services"""
        services = {}
        
        service_names = ['media-pipeline', 'syncthing@root']
        
        for service in service_names:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                services[service] = 'running' if result.returncode == 0 else 'stopped'
            except Exception:
                services[service] = 'unknown'
        
        return services
    
    def check_database(self):
        """Check both Supabase and localhost SQL database connections"""
        timestamp = datetime.now().isoformat()
        database_status = {
            'timestamp': timestamp,
            'supabase': {'connected': False, 'error': None, 'checked_at': timestamp},
            'localhost_sql': {'connected': False, 'error': None, 'checked_at': timestamp}
        }
        
        # Check Supabase connection
        try:
            from supabase import create_client, Client
            
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                database_status['supabase']['error'] = 'Missing Supabase credentials'
            else:
                supabase: Client = create_client(url, key)
                # Try a simple query
                result = supabase.table('media_files').select('id').limit(1).execute()
                database_status['supabase']['connected'] = True
                database_status['supabase']['tables'] = len(result.data)
                
        except Exception as e:
            database_status['supabase']['error'] = str(e)
        
        # Check localhost SQL connection
        try:
            import psycopg2
            
            # Try to connect to local PostgreSQL
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='media_pipeline',
                user='media_pipeline',
                password='media_pipeline_2024'
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            database_status['localhost_sql']['connected'] = True
            database_status['localhost_sql']['tables'] = count
            
        except Exception as e:
            database_status['localhost_sql']['error'] = str(e)
        
        # Overall database status
        database_status['connected'] = (
            database_status['supabase']['connected'] or 
            database_status['localhost_sql']['connected']
        )
        
        return database_status
    
    def check_storage(self):
        """Check storage mount status"""
        try:
            nas_mount = os.getenv('NAS_MOUNT', '/mnt/wd_all_pictures/sync')
            
            # Check if mount point exists and is accessible
            if os.path.exists(nas_mount) and os.access(nas_mount, os.R_OK):
                # Get disk usage
                usage = psutil.disk_usage(nas_mount)
                return {
                    'mounted': True,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
                }
            else:
                return {'mounted': False, 'error': 'Mount point not accessible'}
                
        except Exception as e:
            return {'mounted': False, 'error': str(e)}
    
    def get_system_info(self):
        """Get system resource information"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_pipeline_stats(self):
        """Get pipeline statistics"""
        try:
            stats = {
                'total_files': 0,
                'files_today': 0,
                'total_size': 0,
                'success_rate': 0
            }
            
            # Try to get stats from local database
            try:
                from src.core.local_db_manager import get_db_manager
                local_db = get_db_manager()
                
                # Get total files
                result = local_db._execute_query("SELECT COUNT(*) as count FROM media_files", fetch=True)
                if result and len(result) > 0:
                    stats['total_files'] = result[0]['count']
                
                # Get files processed today
                today = datetime.now().date()
                result = local_db._execute_query(
                    "SELECT COUNT(*) as count FROM media_files WHERE DATE(created_at) = %s", 
                    (today,), fetch=True
                )
                if result and len(result) > 0:
                    stats['files_today'] = result[0]['count']
                
                # Get success rate from recent pipeline executions
                result = local_db._execute_query(
                    "SELECT status FROM pipeline_executions ORDER BY created_at DESC LIMIT 100", 
                    fetch=True
                )
                if result:
                    total_executions = len(result)
                    successful_executions = len([r for r in result if r.get('status') == 'success'])
                    stats['success_rate'] = (successful_executions / total_executions) * 100 if total_executions > 0 else 0
                        
            except Exception as e:
                print(f"Error getting stats from local database: {e}")
                pass
            
            # Get file counts from directories
            try:
                nas_mount = os.getenv('NAS_MOUNT', '/mnt/wd_all_pictures/sync')
                originals_dir = os.path.join(nas_mount, 'originals')
                compressed_dir = os.path.join(nas_mount, 'compressed')
                
                if os.path.exists(originals_dir):
                    stats['total_files'] += len([f for f in os.listdir(originals_dir) if os.path.isfile(os.path.join(originals_dir, f))])
                
                if os.path.exists(compressed_dir):
                    stats['total_files'] += len([f for f in os.listdir(compressed_dir) if os.path.isfile(os.path.join(compressed_dir, f))])
                    
            except Exception:
                pass
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_recent_activity(self):
        """Get recent meaningful pipeline activity"""
        try:
            activities = []
            
            # Get meaningful activities from local database
            try:
                if db_manager:
                    conn = db_manager._get_connection()
                    cursor = conn.cursor()
                    
                    # 1. Recent media files added
                    cursor.execute('SELECT filename, created_at FROM media_files ORDER BY created_at DESC LIMIT 5')
                    media_files = cursor.fetchall()
                    for file in media_files:
                        activities.append({
                            'title': f'📁 New media file: {file[0]}',
                            'type': 'success',
                            'timestamp': file[1].isoformat()
                        })
                    
                    # 2. Recent batches created
                    cursor.execute('SELECT batch_type, file_count, created_at FROM batches ORDER BY created_at DESC LIMIT 3')
                    batches = cursor.fetchall()
                    for batch in batches:
                        activities.append({
                            'title': f'📦 Batch created: {batch[0]} ({batch[1]} files)',
                            'type': 'info',
                            'timestamp': batch[2].isoformat()
                        })
                    
                    # 3. Recent sync activities
                    cursor.execute('SELECT table_name, last_sync_timestamp FROM sync_status WHERE last_sync_timestamp IS NOT NULL ORDER BY last_sync_timestamp DESC LIMIT 3')
                    syncs = cursor.fetchall()
                    for sync in syncs:
                        activities.append({
                            'title': f'🔄 Sync completed: {sync[0]}',
                            'type': 'info',
                            'timestamp': sync[1].isoformat()
                        })
                    
                    # 4. Recent 2FA requests
                    cursor.execute('SELECT status, created_at FROM telegram_2fa_requests ORDER BY created_at DESC LIMIT 2')
                    twofa_requests = cursor.fetchall()
                    for request in twofa_requests:
                        activities.append({
                            'title': f'🔐 2FA request: {request[0]}',
                            'type': 'warning',
                            'timestamp': request[1].isoformat()
                        })
                    
                    cursor.close()
                    db_manager._return_connection(conn)
                    
            except Exception as e:
                print(f"Error getting activities from database: {e}")
            
            # Sort by timestamp (most recent first)
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Return top 10 most recent activities
            return activities[:10]
            
        except Exception as e:
            return [{'title': f'❌ Error loading activity: {str(e)}', 'type': 'danger', 'timestamp': datetime.now().isoformat()}]
    
    def get_configuration(self):
        """Get current configuration with helpful descriptions"""
        try:
            config = {}
            feature_toggles = {}
            
            # Configuration descriptions
            config_descriptions = {
                # ===== FEATURE TOGGLES - SOURCE CONTROL =====
                'ENABLE_ICLOUD_DOWNLOAD': 'Enable downloading photos and videos from iCloud Photos. Downloads media files from your iCloud Photos library.',
                'ENABLE_FOLDER_DOWNLOAD': 'Enable processing media files from a local folder. Scans specified folder for media files and processes them.',
                'ENABLE_ICLOUD_UPLOAD': 'Enable automatic upload of processed files to iCloud Photos. When enabled, files will be uploaded to your iCloud Photos library after processing.',
                'ENABLE_PIXEL_UPLOAD': 'Enable upload to Google Pixel. When enabled, files will be synced to Pixel device via Syncthing.',
                
                # ===== FEATURE TOGGLES - PROCESSING CONTROL =====
                'ENABLE_COMPRESSION': 'Enable overall compression system. Master toggle for all compression features.',
                'ENABLE_IMAGE_COMPRESSION': 'Enable image compression (JPEG, PNG, etc.). Reduces image file sizes with quality control.',
                'ENABLE_VIDEO_COMPRESSION': 'Enable video compression (MP4, MOV, etc.). Reduces video file sizes with resolution scaling.',
                'ENABLE_DEDUPLICATION': 'Enable duplicate file detection and removal. Scans files for duplicates using hash comparison.',
                'ENABLE_SORTING': 'Enable automatic file sorting by date/metadata. Organizes files into date-based folder structures.',
                'ENABLE_FILE_PREPARATION': 'Enable file preparation for uploads. Organizes files into batches and prepares them for upload.',
                'ENABLE_VERIFICATION': 'Enable verification and cleanup after processing. Verifies file integrity and cleans up temporary files.',
                
                # ===== ICLOUD CONFIGURATION =====
                'ICLOUD_USERNAME': 'Your iCloud email address (e.g., user@icloud.com). Used for authenticating with iCloud Photos.',
                'ICLOUD_PASSWORD': 'Your iCloud password (stored securely). Required for iCloud authentication.',
                
                # ===== SUPABASE CONFIGURATION =====
                'SUPABASE_URL': 'Supabase project URL (e.g., https://project.supabase.co). Your cloud database endpoint.',
                'SUPABASE_KEY': 'Supabase API key (anon/public key). Used for authenticating API requests to Supabase.',
                
                # ===== STORAGE PATHS =====
                'NAS_MOUNT': 'Base mount path for NAS storage (e.g., /mnt/wd_all_pictures/sync). Root directory for all media operations.',
                'ORIGINALS_DIR': 'Directory for original downloaded files (e.g., /mnt/wd_all_pictures/sync/originals). Where media files are stored.',
                'COMPRESSED_DIR': 'Directory for compressed files (e.g., /mnt/wd_all_pictures/sync/compressed). Where compressed versions are stored.',
                
                # ===== SOURCE CONFIGURATION =====
                'FOLDER_SOURCE_PATH': 'Path to local folder containing media files to process (e.g., /mnt/wd_all_pictures/sync/source_folder). Scanned for media files.',
                'FOLDER_SOURCE_PATTERNS': 'File patterns to match in source folder (e.g., *.jpg,*.mp4). Comma-separated list of file extensions.',
                
                # ===== BRIDGE DIRECTORIES =====
                'BRIDGE_ICLOUD_DIR': 'Bridge directory for iCloud uploads (e.g., /mnt/wd_all_pictures/sync/bridge/icloud). Temporary staging area.',
                'BRIDGE_PIXEL_DIR': 'Bridge directory for Pixel uploads (e.g., /mnt/wd_all_pictures/sync/bridge/pixel). Temporary staging area.',
                'BRIDGE_FOLDER_DIR': 'Bridge directory for folder source processing (e.g., /mnt/wd_all_pictures/sync/bridge/folder). Temporary staging area.',
                
                # ===== UPLOADED DIRECTORIES =====
                'UPLOADED_ICLOUD_DIR': 'Directory for successfully uploaded iCloud files (e.g., /mnt/wd_all_pictures/sync/uploaded/icloud). Archive location.',
                'UPLOADED_PIXEL_DIR': 'Directory for successfully uploaded Pixel files (e.g., /mnt/wd_all_pictures/sync/uploaded/pixel). Archive location.',
                'UPLOADED_FOLDER_DIR': 'Directory for successfully processed folder files (e.g., /mnt/wd_all_pictures/sync/uploaded/folder). Archive location.',
                
                # ===== SORTED DIRECTORIES =====
                'SORTED_DIR': 'Base directory for sorted files (e.g., /mnt/wd_all_pictures/sync/sorted). Final organized location.',
                'SORTED_ICLOUD_DIR': 'Directory for sorted iCloud files (e.g., /mnt/wd_all_pictures/sync/sorted/icloud). Organized by date/metadata.',
                'SORTED_PIXEL_DIR': 'Directory for sorted Pixel files (e.g., /mnt/wd_all_pictures/sync/sorted/pixel). Organized by date/metadata.',
                'SORTED_FOLDER_DIR': 'Directory for sorted folder files (e.g., /mnt/wd_all_pictures/sync/sorted/folder). Organized by date/metadata.',
                
                # ===== OTHER DIRECTORIES =====
                'CLEANUP_DIR': 'Directory for cleanup operations (e.g., /mnt/wd_all_pictures/sync/cleanup). Temporary files and cleanup.',
                'PIXEL_SYNC_FOLDER': 'Syncthing folder path for Pixel sync (e.g., /mnt/syncthing/pixel). Where Syncthing syncs files.',
                
                # ===== FILE PROCESSING SETTINGS =====
                'MAX_PROCESSING_SIZE_GB': 'Maximum total size in GB to process in one batch (e.g., 5). Prevents memory issues with large batches.',
                'MAX_PROCESSING_FILES': 'Maximum number of files to process in one batch (e.g., 500). Controls batch size for processing.',
                
                # ===== COMPRESSION SETTINGS =====
                'JPEG_QUALITY': 'JPEG compression quality (1-100, default: 85). Higher values = better quality but larger files.',
                'VIDEO_CRF': 'Video compression rate factor (0-51, default: 28). Lower values = better quality but larger files.',
                'VIDEO_PRESET': 'FFmpeg compression preset (ultrafast, fast, medium, slow, default: fast). Controls encoding speed vs efficiency.',
                
                # ===== DEDUPLICATION SETTINGS =====
                'DEDUPLICATION_HASH_ALGORITHM': 'Hash algorithm for duplicate detection (md5, sha1, sha256, default: md5). Used to identify duplicate files.',
                'DEDUPLICATION_BATCH_SIZE': 'Number of files to process in each deduplication batch (default: 1000). Controls memory usage.',
                
                # ===== SORTING SETTINGS =====
                'SORTING_USE_EXIF': 'Use EXIF metadata for file sorting (true/false, default: true). Uses photo metadata for accurate dating.',
                'SORTING_FALLBACK_TO_CREATION_DATE': 'Fallback to file creation date if EXIF unavailable (true/false, default: true). Ensures all files get sorted.',
                
                # ===== LOGGING SETTINGS =====
                'LOG_LEVEL': 'Logging verbosity level (DEBUG, INFO, WARNING, ERROR, default: INFO). Controls how much detail is logged.',
                
                # ===== LXC/PROXMOX SETTINGS =====
                'LXC_USER': 'System user for running the pipeline (default: media-pipeline). User account for service operations.',
                'LXC_GROUP': 'System group for the pipeline (default: media-pipeline). Group ownership for files.',
                'MOUNT_PERMISSIONS': 'File permissions for mounted directories (default: 755). Controls access permissions.',
                
                # ===== UPLOAD SETTINGS =====
                'ICLOUD_BATCH_SIZE': 'Number of files to upload to iCloud per batch (default: 50). Controls upload efficiency.',
                'PIXEL_SYNC_TIMEOUT': 'Timeout in seconds for Pixel sync operations (default: 300). How long to wait for sync completion.',
                'UPLOAD_RETRY_ATTEMPTS': 'Number of retry attempts for failed uploads (default: 3). Automatic retry on failures.',
                'UPLOAD_RETRY_DELAY': 'Delay in seconds between retry attempts (default: 30). Wait time before retrying.',
                
                # ===== SYNCTHING SETTINGS =====
                'SYNCTHING_URL': 'Syncthing web interface URL (default: http://localhost:8384). For monitoring and control.',
                'SYNCTHING_API_KEY': 'Syncthing API key for programmatic access. Required for automated operations.',
                'PIXEL_FOLDER_ID': 'Syncthing folder ID for Pixel sync. Identifies the specific folder to sync.',
                
                # ===== PROCESSING CONTROL SETTINGS =====
                'CLEAR_BRIDGE_BEFORE_PROCESSING': 'Clear bridge directories before processing (true/false, default: true). Ensures clean processing.',
                'ENABLE_FILENAME_CONFLICT_RESOLUTION': 'Enable automatic filename conflict resolution (true/false, default: true). Handles duplicate filenames.',
                
                # ===== TELEGRAM CONFIGURATION =====
                'TELEGRAM_BOT_TOKEN': 'Telegram bot token from @BotFather. Required for 2FA and notifications.',
                'TELEGRAM_CHAT_ID': 'Your Telegram chat ID for receiving notifications. Personal chat ID for bot communication.',
                
                # ===== BATCH MANAGER SETTINGS =====
                'BATCH_SIZE': 'Number of records to process in database batches (default: 100). Controls database operation efficiency.',
                'SYNC_INTERVAL': 'Interval in seconds between sync operations (default: 60). How often to sync to Supabase.',
                'CACHE_TTL': 'Cache time-to-live in seconds (default: 300). How long to cache data before refresh.',
                'MAX_RETRIES': 'Maximum retry attempts for failed operations (default: 3). Automatic retry limit.',
                'RETRY_DELAY': 'Delay in seconds between retry attempts (default: 5). Wait time before retrying.',
                
                # ===== TEST/DEBUG SETTINGS =====
                'TEST_KEY': 'Test configuration key for validation (default: test_value). Used for testing configuration loading.',
            }
            
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Handle feature toggles
                            if key.startswith('ENABLE_'):
                                feature_toggles[key] = {
                                    'value': value.lower() in ('true', '1', 'yes', 'on'),
                                    'description': config_descriptions.get(key, f'Enable/disable {key.replace("ENABLE_", "").replace("_", " ").lower()}'),
                                    'category': 'Feature Toggles'
                                }
                            else:
                                config[key] = {
                                    'value': value,
                                    'description': config_descriptions.get(key, f'Configuration option: {key.replace("_", " ").lower()}'),
                                    'category': self._get_config_category(key)
                                }
            
            return {
                'feature_toggles': feature_toggles,
                'settings': config,
                'editable': True  # Enable editing
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_config_category(self, key):
        """Get configuration category for grouping"""
        categories = {
            'Feature Toggles': ['ENABLE_', 'PIXEL_UPLOAD_ENABLED', 'TELEGRAM_ENABLED', 'SYNC_ENABLED'],
            'iCloud Settings': ['ICLOUD_'],
            'Google Pixel': ['PIXEL_'],
            'Compression': ['COMPRESSION_', 'MAX_RESOLUTION', 'AUDIO_BITRATE', 'VIDEO_BITRATE'],
            'Storage': ['SOURCE_DIR', 'PROCESSED_DIR', 'BACKUP_DIR', 'TEMP_DIR'],
            'Database': ['SUPABASE_', 'LOCAL_DB_'],
            'Telegram': ['TELEGRAM_'],
            'Sync': ['SYNC_', 'MAX_SYNC_', 'BATCH_SIZE'],
            'Processing': ['MAX_CONCURRENT_', 'FILE_SIZE_', 'SUPPORTED_FORMATS', 'SKIP_EXISTING'],
            'Logging': ['LOG_'],
            'Performance': ['CPU_LIMIT_', 'MEMORY_LIMIT_', 'DISK_SPACE_'],
            'Security': ['ENABLE_ENCRYPTION', 'ENCRYPTION_KEY', 'SECURE_DELETE'],
            'Notifications': ['EMAIL_'],
            'Advanced': ['CUSTOM_', 'PROCESSING_TIMEOUT', 'RETRY_FAILED_', 'CLEANUP_TEMP_']
        }
        
        for category, prefixes in categories.items():
            if any(key.startswith(prefix) for prefix in prefixes):
                return category
        
        return 'General'
    
    def update_feature_toggle(self, key, enabled):
        """Update a feature toggle in the configuration"""
        try:
            if not os.path.exists(CONFIG_FILE):
                return False, "Configuration file not found"
            
            # Read current config
            lines = []
            with open(CONFIG_FILE, 'r') as f:
                lines = f.readlines()
            
            # Update the toggle
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f'{key}='):
                    lines[i] = f'{key}={str(enabled).lower()}\n'
                    updated = True
                    break
            
            # If not found, add it
            if not updated:
                lines.append(f'{key}={str(enabled).lower()}\n')
            
            # Write back
            with open(CONFIG_FILE, 'w') as f:
                f.writelines(lines)
            
            return True, "Configuration updated"
            
        except Exception as e:
            return False, str(e)
    
    def update_config_value(self, key, value):
        """Update any configuration value"""
        try:
            if not os.path.exists(CONFIG_FILE):
                return False, "Configuration file not found"
            
            # Read current config
            lines = []
            with open(CONFIG_FILE, 'r') as f:
                lines = f.readlines()
            
            # Update the value
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f'{key}='):
                    lines[i] = f'{key}={value}\n'
                    updated = True
                    break
            
            # If not found, add it
            if not updated:
                lines.append(f'{key}={value}\n')
            
            # Write back
            with open(CONFIG_FILE, 'w') as f:
                f.writelines(lines)
            
            return True, f"Configuration updated: {key}={value}"
            
        except Exception as e:
            return False, str(e)
    
    def get_logs(self, log_type='pipeline', lines=100):
        """Get log content"""
        try:
            log_files = {
                'pipeline': os.path.join(LOG_DIR, 'pipeline.log'),
                'system': '/var/log/syslog',
                'syncthing': 'journalctl',  # Use journalctl for syncthing
                'error': os.path.join(LOG_DIR, 'error.log')
            }
            
            log_file = log_files.get(log_type, log_files['pipeline'])
            
            # Skip file existence check for journalctl
            if log_type != 'syncthing' and not os.path.exists(log_file):
                return {'content': f'Log file {log_file} not found'}
            
            # Get last N lines with proper permissions
            try:
                # For system logs, try different approaches
                if log_type == 'system':
                    # Try journalctl first (more reliable)
                    result = subprocess.run(
                        ['journalctl', '-n', str(lines), '--no-pager'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        # Fallback to sudo tail
                        result = subprocess.run(
                            ['sudo', 'tail', '-n', str(lines), log_file],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                elif log_type == 'syncthing':
                    # Try journalctl for syncthing
                    result = subprocess.run(
                        ['journalctl', '-u', 'syncthing@root', '-n', str(lines), '--no-pager'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        # Fallback to sudo tail
                        result = subprocess.run(
                            ['sudo', 'tail', '-n', str(lines), log_file],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                else:
                    result = subprocess.run(
                        ['tail', '-n', str(lines), log_file],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                
                if result.returncode == 0:
                    return {'content': result.stdout}
                else:
                    return {'content': f'Error reading log: {result.stderr}'}
                    
            except Exception as e:
                return {'content': f'Error reading log: {str(e)}'}
                
        except Exception as e:
            return {'content': f'Error: {str(e)}'}
    
    def run_pipeline_step(self, step):
        """Run a specific pipeline step"""
        try:
            step_scripts = {
                'download': 'download_from_icloud.py',
                'deduplicate': 'deduplicate.py',
                'compress': 'compress_media.py',
                'prepare': 'prepare_bridge_batch.py',
                'upload_icloud': 'upload_icloud.py',
                'upload_pixel': 'sync_to_pixel.py',
                'sort': 'sort_uploaded.py',
                'cleanup': 'verify_and_cleanup.py'
            }
            
            script = step_scripts.get(step)
            if not script:
                return False, f"Unknown step: {step}"
            
            script_path = os.path.join(PIPELINE_DIR, 'scripts', script)
            
            if not os.path.exists(script_path):
                return False, f"Script not found: {script_path}"
            
            # Run the script
            cmd = ['sudo', '-u', 'media-pipeline', 
                   os.path.join(PIPELINE_DIR, 'venv', 'bin', 'python'), 
                   script_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                return True, "Step completed successfully"
            else:
                return False, f"Step failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Step timed out"
        except Exception as e:
            return False, str(e)
    
    def run_full_pipeline(self):
        """Run the complete pipeline"""
        try:
            script_path = os.path.join(PIPELINE_DIR, 'scripts', 'run_pipeline.py')
            
            if not os.path.exists(script_path):
                return False, "Pipeline script not found"
            
            # Run the pipeline
            cmd = ['sudo', '-u', 'media-pipeline', 
                   os.path.join(PIPELINE_DIR, 'venv', 'bin', 'python'), 
                   script_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                return True, "Pipeline completed successfully"
            else:
                return False, f"Pipeline failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Pipeline timed out"
        except Exception as e:
            return False, str(e)
    
    def run_health_check(self):
        """Run the health check script"""
        try:
            script_path = os.path.join(PIPELINE_DIR, 'scripts', 'check_and_fix.sh')
            
            if not os.path.exists(script_path):
                return False, "Health check script not found"
            
            # Run health check
            cmd = ['sudo', script_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                return True, "Health check completed"
            else:
                return False, f"Health check found issues: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Health check timed out"
        except Exception as e:
            return False, str(e)
    
    def service_action(self, service, action):
        """Perform service action (start/stop/restart)"""
        try:
            # Use systemctl directly without sudo for systemd services
            cmd = ['systemctl', action, service]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, f"Service {service} {action} successful"
            else:
                # If direct systemctl fails, try with sudo
                cmd_sudo = ['sudo', '-n', 'systemctl', action, service]
                result_sudo = subprocess.run(
                    cmd_sudo,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result_sudo.returncode == 0:
                    return True, f"Service {service} {action} successful"
                else:
                    return False, f"Service {service} {action} failed: {result_sudo.stderr}"
                
        except Exception as e:
            return False, str(e)
    
    def run_diagnostic(self, diagnostic_type):
        """Run diagnostic checks"""
        try:
            if diagnostic_type == 'health':
                return self.run_health_check()
            elif diagnostic_type == 'permissions':
                # Check permissions
                cmd = ['sudo', 'ls', '-la', PIPELINE_DIR]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return True, "Permissions check completed"
                else:
                    return False, f"Permissions issue: {result.stderr}"
            elif diagnostic_type == 'services':
                # Check all services
                services = self.check_services()
                issues = [f"{service}: {status}" for service, status in services.items() if status != 'running']
                if issues:
                    return False, f"Service issues: {', '.join(issues)}"
                else:
                    return True, "All services running"
            elif diagnostic_type == 'dependencies':
                # Check Python dependencies
                cmd = [os.path.join(PIPELINE_DIR, 'venv', 'bin', 'pip'), 'list']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return True, "Dependencies check completed"
                else:
                    return False, f"Dependencies issue: {result.stderr}"
            else:
                return False, f"Unknown diagnostic type: {diagnostic_type}"
                
        except Exception as e:
            return False, str(e)
    
    def run_auto_fix(self, fix_type):
        """Run auto-fix tools"""
        try:
            if fix_type == 'all':
                return self.run_health_check()
            elif fix_type == 'permissions':
                cmd = ['sudo', 'chown', '-R', 'media-pipeline:media-pipeline', PIPELINE_DIR]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    return True, "Permissions fixed"
                else:
                    return False, f"Failed to fix permissions: {result.stderr}"
            elif fix_type == 'environment':
                script_path = os.path.join(PIPELINE_DIR, 'scripts', 'check_and_fix.sh')
                cmd = ['sudo', script_path, '--fix-environment']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    return True, "Environment fixed"
                else:
                    return False, f"Failed to fix environment: {result.stderr}"
            elif fix_type == 'services':
                # Restart services
                success = True
                errors = []
                
                for service in ['media-pipeline', 'syncthing@root']:
                    cmd = ['sudo', 'systemctl', 'restart', service]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode != 0:
                        success = False
                        errors.append(f"{service}: {result.stderr}")
                
                if success:
                    return True, "Services restarted"
                else:
                    return False, f"Failed to restart services: {', '.join(errors)}"
            else:
                return False, f"Unknown fix type: {fix_type}"
                
        except Exception as e:
            return False, str(e)

# Initialize pipeline manager
pipeline_manager = PipelineManager()

# API Routes
@app.route('/api/status')
def get_status():
    """Get system status"""
    status = pipeline_manager.get_system_status()
    return jsonify(status)

@app.route('/api/stats')
def get_stats():
    """Get pipeline statistics"""
    stats = pipeline_manager.get_pipeline_stats()
    return jsonify(stats)

@app.route('/api/activity')
def get_activity():
    """Get recent activity"""
    activity = pipeline_manager.get_recent_activity()
    return jsonify(activity)

@app.route('/api/config')
def get_config():
    """Get configuration"""
    config = pipeline_manager.get_configuration()
    return jsonify(config)

@app.route('/api/config/toggle', methods=['POST'])
def toggle_feature():
    """Toggle a feature"""
    data = request.get_json()
    key = data.get('key')
    enabled = data.get('enabled')
    
    if not key:
        return jsonify({'error': 'Missing key'}), 400
    
    success, message = pipeline_manager.update_feature_toggle(key, enabled)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/logs')
def get_logs():
    """Get log content"""
    log_type = request.args.get('type', 'pipeline')
    lines = int(request.args.get('lines', 100))
    
    logs = pipeline_manager.get_logs(log_type, lines)
    return jsonify(logs)

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear log file"""
    try:
        data = request.get_json()
        log_type = data.get('log_type', 'pipeline')
        
        if log_type == 'pipeline':
            log_file = os.path.join(LOG_DIR, 'pipeline.log')
            if os.path.exists(log_file):
                # Clear the log file
                with open(log_file, 'w') as f:
                    f.write(f"# Log cleared at {datetime.now().isoformat()}\n")
                return jsonify({'success': True, 'message': 'Pipeline log cleared successfully'})
            else:
                return jsonify({'success': False, 'message': 'Log file not found'})
        else:
            return jsonify({'success': False, 'message': 'Only pipeline logs can be cleared'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/pipeline/step', methods=['POST'])
def run_step():
    """Run a pipeline step"""
    data = request.get_json()
    step = data.get('step')
    
    if not step:
        return jsonify({'error': 'Missing step'}), 400
    
    success, message = pipeline_manager.run_pipeline_step(step)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/pipeline/run', methods=['POST'])
def run_pipeline():
    """Run full pipeline"""
    success, message = pipeline_manager.run_full_pipeline()
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/health-check', methods=['POST'])
def health_check():
    """Run health check"""
    success, message = pipeline_manager.run_health_check()
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'issues': message}), 200

@app.route('/api/service/<action>', methods=['POST'])
def service_action(action):
    """Service action"""
    data = request.get_json()
    service = data.get('service')
    
    if not service:
        return jsonify({'error': 'Missing service'}), 400
    
    success, message = pipeline_manager.service_action(service, action)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/diagnostic/<diagnostic_type>', methods=['POST'])
def run_diagnostic(diagnostic_type):
    """Run diagnostic"""
    success, message = pipeline_manager.run_diagnostic(diagnostic_type)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'issues': message}), 200

@app.route('/api/auto-fix/<fix_type>', methods=['POST'])
def run_auto_fix(fix_type):
    """Run auto-fix"""
    success, message = pipeline_manager.run_auto_fix(fix_type)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/config/reload', methods=['POST'])
def reload_config():
    """Reload configuration"""
    # Clear cache to force reload
    pipeline_manager.status_cache = {}
    return jsonify({'success': True, 'message': 'Configuration reloaded'})

@app.route('/api/config/edit', methods=['POST'])
def edit_config():
    """Edit configuration file"""
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    
    if not key:
        return jsonify({'error': 'Missing key'}), 400
    
    success, message = pipeline_manager.update_config_value(key, value)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/telegram/test', methods=['POST'])
def test_telegram():
    """Test Telegram bot configuration"""
    try:
        data = request.get_json()
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')
        
        if not bot_token or not chat_id:
            return jsonify({'success': False, 'message': 'Bot token and chat ID are required'})
        
        # Test bot token
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                # Test sending message
                send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                send_data = {
                    'chat_id': chat_id,
                    'text': '🤖 Enhanced Media Pipeline Telegram bot test successful!\n\n✅ Bot is working correctly\n🔐 2FA notifications enabled\n📊 Status updates available\n❌ Error alerts active',
                    'parse_mode': 'HTML'
                }
                
                send_response = requests.post(send_url, data=send_data, timeout=10)
                
                if send_response.status_code == 200:
                    return jsonify({
                        'success': True, 
                        'message': f'Bot "{bot_info["result"]["first_name"]}" is working! Test message sent.'
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'message': 'Bot token is valid but failed to send message. Check chat ID.'
                    })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Invalid bot token'
                })
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to connect to Telegram API'
            })
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error testing Telegram: {str(e)}'
        })

@app.route('/api/telegram/config', methods=['POST'])
def save_telegram_config():
    """Save Telegram bot configuration"""
    try:
        data = request.get_json()
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')
        
        if not bot_token or not chat_id:
            return jsonify({'success': False, 'message': 'Bot token and chat ID are required'})
        
        # Save to configuration file
        success, message = pipeline_manager.update_config_value('TELEGRAM_BOT_TOKEN', bot_token)
        if not success:
            return jsonify({'success': False, 'message': f'Failed to save bot token: {message}'})
        
        success, message = pipeline_manager.update_config_value('TELEGRAM_CHAT_ID', chat_id)
        if not success:
            return jsonify({'success': False, 'message': f'Failed to save chat ID: {message}'})
        
        return jsonify({'success': True, 'message': 'Telegram configuration saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/icloudpd/2fa', methods=['POST'])
def icloudpd_2fa():
    """Handle icloudpd 2FA web interface"""
    try:
        data = request.get_json()
        code = data.get('code')
        request_id = data.get('request_id')
        
        if not code or not request_id:
            return jsonify({'success': False, 'message': 'Code and request ID are required'})
        
        # Update 2FA request in local database
        try:
            from src.core.local_db_manager import get_db_manager
            local_db = get_db_manager()
            
            # Update the 2FA request
            query = """
                UPDATE twofa_requests 
                SET code = %s, status = 'completed', completed_at = %s 
                WHERE request_id = %s
            """
            
            result = local_db._execute_query(query, (code, datetime.now(), request_id))
            
            if result:
                return jsonify({'success': True, 'message': '2FA code submitted successfully'})
            else:
                return jsonify({'success': False, 'message': 'Request not found or expired'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/icloudpd/status', methods=['GET'])
def icloudpd_status():
    """Get icloudpd 2FA status"""
    try:
        request_id = request.args.get('request_id')
        
        if not request_id:
            return jsonify({'success': False, 'message': 'Request ID is required'})
        
        # Check 2FA request status in local database
        try:
            from src.core.local_db_manager import get_db_manager
            local_db = get_db_manager()
            
            query = """
                SELECT status, code, expires_at 
                FROM twofa_requests 
                WHERE request_id = %s
            """
            
            result = local_db._execute_query(query, (request_id,), fetch=True)
            
            if result and len(result) > 0:
                request_data = result[0]
                return jsonify({
                    'success': True,
                    'status': request_data.get('status', 'pending'),
                    'code': request_data.get('code'),
                    'expires_at': request_data.get('expires_at')
                })
            else:
                return jsonify({'success': False, 'message': 'Request not found'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/open-editor', methods=['POST'])
def open_config_editor():
    """Open configuration editor"""
    try:
        # Use the manage_config.sh script to open editor
        result = subprocess.run(
            ['sudo', '-u', 'media-pipeline', '/opt/media-pipeline/manage_config.sh', 'edit'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Configuration editor opened'})
        else:
            return jsonify({'error': f'Failed to open editor: {result.stderr}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/icloud', methods=['POST'])
def test_icloud_connection():
    """Test iCloud connection"""
    try:
        # Simple test - check if iCloud credentials are configured
        config = pipeline_manager.get_configuration()
        username = config.get('ICLOUD_USERNAME', '')
        password = config.get('ICLOUD_PASSWORD', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'iCloud credentials not configured'})
        
        # You could add more sophisticated testing here
        return jsonify({'success': True, 'message': 'iCloud credentials configured'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/readme')
def get_readme():
    """Get README content"""
    try:
        readme_file = os.path.join(project_root, 'web', 'README.md')
        
        if os.path.exists(readme_file):
            with open(readme_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Convert markdown to HTML (simple conversion)
            html_content = convert_markdown_to_html(content)
            
            return jsonify({'content': html_content})
        else:
            return jsonify({'content': '<p>README file not found</p>'})
            
    except Exception as e:
        return jsonify({'content': f'<p>Error loading README: {str(e)}</p>'})

@app.route('/api/telegram/status', methods=['GET'])
def get_telegram_status():
    """Get Telegram bot status and active 2FA requests"""
    try:
        # Check if Telegram service is running
        result = subprocess.run(['systemctl', 'is-active', 'media-pipeline-telegram'], 
                              capture_output=True, text=True)
        service_status = result.stdout.strip()
        
        # Get active 2FA requests (simplified)
        active_requests = 0  # This would be fetched from the handler in a real implementation
        
        return jsonify({
            'service_status': service_status,
            'active_2fa_requests': active_requests,
            'bot_configured': bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'))
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telegram/send-status', methods=['POST'])
def send_telegram_status():
    """Send pipeline status to Telegram"""
    try:
        # Import the enhanced bot
        sys.path.insert(0, str(project_root))
        from src.utils.enhanced_telegram_bot import EnhancedTelegramBot
        
        bot = EnhancedTelegramBot()
        success = bot.send_pipeline_status("manual", "Status update sent from web dashboard")
        
        if success:
            return jsonify({'success': True, 'message': 'Status update sent to Telegram'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send status update'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/telegram/send-summary', methods=['POST'])
def send_telegram_summary():
    """Send daily summary to Telegram"""
    try:
        # Import the enhanced bot
        sys.path.insert(0, str(project_root))
        from src.utils.enhanced_telegram_bot import EnhancedTelegramBot
        
        bot = EnhancedTelegramBot()
        success = bot.send_daily_summary()
        
        if success:
            return jsonify({'success': True, 'message': 'Daily summary sent to Telegram'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send daily summary'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get local database statistics"""
    try:
        from src.core.local_db_manager import get_db_manager
        
        db_manager = get_db_manager()
        stats = db_manager.get_database_stats()
        
        # Get recent cache metrics
        cache_metrics = db_manager.get_cache_metrics(limit=10)
        
        # Get sync timestamps
        sync_timestamps = {}
        try:
            conn = db_manager._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT table_name, last_sync_timestamp FROM sync_status ORDER BY last_sync_timestamp DESC")
            for row in cursor.fetchall():
                sync_timestamps[row[0]] = row[1].isoformat() if row[1] else None
            cursor.close()
            db_manager._return_connection(conn)
        except Exception as e:
            print(f"Error getting sync timestamps: {e}")
        
        return jsonify({
            'success': True,
            'stats': stats,
            'cache_metrics': cache_metrics,
            'sync_timestamps': sync_timestamps,
            'database_info': {
                'host': 'localhost',
                'port': 5432,
                'database': 'media_pipeline',
                'type': 'PostgreSQL'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear old synced records from local database"""
    try:
        from src.core.local_db_manager import get_db_manager
        
        db_manager = get_db_manager()
        db_manager.cleanup_old_records(days=7)  # Clean up records older than 7 days
        
        return jsonify({
            'success': True,
            'message': 'Old records cleaned up successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/cache/optimize', methods=['POST'])
def optimize_cache():
    """Force sync all tables to Supabase"""
    try:
        from supabase_sync import get_sync_instance
        
        sync_instance = get_sync_instance()
        
        # Sync all tables
        tables = ['pipeline_logs', 'telegram_2fa_requests', 'telegram_notifications', 
                 'cache_metrics', 'pipeline_metrics']
        
        results = []
        for table in tables:
            result = sync_instance.force_sync_table(table)
            results.append({
                'table': table,
                'success': result['success'],
                'records_synced': result['records_synced']
            })
        
        return jsonify({
            'success': True,
            'message': 'All tables synced to Supabase',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/batch/config', methods=['GET'])
def get_batch_config():
    """Get batch manager configuration"""
    try:
        if batch_manager:
            config = {
                'batch_size': batch_manager.batch_size,
                'sync_interval': batch_manager.sync_interval,
                'cache_ttl': batch_manager.cache_ttl,
                'max_retries': batch_manager.max_retries,
                'retry_delay': batch_manager.retry_delay
            }
            return jsonify({
                'success': True,
                'config': config
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Batch manager not available'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/batch/config', methods=['POST'])
def update_batch_config():
    """Update batch manager configuration"""
    try:
        if batch_manager:
            config = request.get_json()
            batch_manager.update_config(config)
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Batch manager not available'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/batch/sync', methods=['POST'])
def manual_sync():
    """Manually trigger batch sync"""
    try:
        if batch_manager:
            result = batch_manager.sync_batches()
            return jsonify({
                'success': True,
                'message': f'Manual sync completed: {result["total_synced"]} operations',
                'sync_result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Batch manager not available'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/database/stats', methods=['GET'])
def get_database_stats():
    """Get database statistics"""
    try:
        if not db_manager:
            return jsonify({'success': False, 'message': 'Database manager not available'}), 500
        
        stats = db_manager.get_database_stats()
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/database/tables', methods=['GET'])
def get_database_tables():
    """Get database table information"""
    try:
        if not db_manager:
            return jsonify({'success': False, 'message': 'Database manager not available'}), 500
        
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name, 'public' as table_owner, 'table' as table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = []
        for row in cursor.fetchall():
            tables.append({
                'table_name': row[0],
                'table_owner': row[1],
                'table_type': row[2]
            })
        
        cursor.close()
        db_manager._return_connection(conn)
        
        return jsonify({'success': True, 'tables': tables})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/database/query', methods=['POST'])
def execute_database_query():
    """Execute a database query"""
    try:
        if not db_manager:
            return jsonify({'success': False, 'message': 'Database manager not available'}), 500
        
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'success': False, 'message': 'No query provided'}), 400
        
        # Security check - only allow SELECT queries
        if not query.strip().upper().startswith('SELECT'):
            return jsonify({'success': False, 'message': 'Only SELECT queries are allowed'}), 400
        
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [desc[0] for desc in cursor.description]
        result_list = []
        for row in results:
            result_list.append(dict(zip(columns, row)))
        
        cursor.close()
        db_manager._return_connection(conn)
        
        return jsonify({'success': True, 'results': result_list})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/database/maintenance', methods=['POST'])
def execute_maintenance():
    """Execute database maintenance commands"""
    try:
        if not db_manager:
            return jsonify({'success': False, 'message': 'Database manager not available'}), 500
        
        data = request.get_json()
        command = data.get('command', '')
        
        if not command:
            return jsonify({'success': False, 'message': 'No command provided'}), 400
        
        # Security check - only allow specific maintenance commands
        allowed_commands = ['VACUUM ANALYZE', 'REINDEX DATABASE media_pipeline']
        if command not in allowed_commands:
            return jsonify({'success': False, 'message': 'Command not allowed'}), 400
        
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(command)
        conn.commit()
        
        cursor.close()
        db_manager._return_connection(conn)
        
        return jsonify({'success': True, 'message': f'Command executed successfully: {command}'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sources/status', methods=['GET'])
def get_sources_status():
    """Get status of all media sources"""
    try:
        if not db_manager:
            return jsonify({'error': 'Database manager not available'}), 500
        
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        # Get source statistics
        cursor.execute("""
            SELECT 
                source_type,
                COUNT(*) as file_count,
                COALESCE(SUM(file_size), 0) as total_size,
                COUNT(CASE WHEN status = 'verified' THEN 1 END) as processed_count,
                COUNT(CASE WHEN status != 'verified' THEN 1 END) as pending_count
            FROM media_files 
            GROUP BY source_type
        """)
        
        source_stats = {}
        for row in cursor.fetchall():
            source_type, file_count, total_size, processed_count, pending_count = row
            source_stats[source_type] = {
                'file_count': file_count,
                'total_size': total_size,
                'processed_count': processed_count,
                'pending_count': pending_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
        
        # Get enabled sources from configuration
        enabled_sources = []
        config = pipeline_manager.get_configuration()
        
        if config.get('feature_toggles', {}).get('ENABLE_ICLOUD_DOWNLOAD', {}).get('value'):
            enabled_sources.append('icloud')
        
        if config.get('feature_toggles', {}).get('ENABLE_FOLDER_DOWNLOAD', {}).get('value'):
            enabled_sources.append('folder')
        
        cursor.close()
        db_manager._return_connection(conn)
        
        return jsonify({
            'enabled_sources': enabled_sources,
            'source_stats': source_stats,
            'total_sources': len(enabled_sources)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def convert_markdown_to_html(markdown_text):
    """Simple markdown to HTML converter"""
    html = markdown_text
    
    # Headers
    html = re.sub(r'^# (.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # Code blocks
    html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    
    # Inline code
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # Lists
    html = re.sub(r'^- (.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    
    # Line breaks
    html = html.replace('\n', '<br>\n')
    
    return html

# Serve static files
# Google Photos API endpoints removed - functionality disabled

# Alternative Sync Verification Endpoints
@app.route('/api/alternative-sync/status', methods=['GET'])
def get_alternative_sync_status():
    """Get sync status using alternative methods"""
    try:
        from alternative_sync_endpoints import get_alternative_sync_status
        return jsonify(get_alternative_sync_status())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/alternative-sync/methods', methods=['GET'])
def get_verification_methods():
    """Get available verification methods"""
    try:
        from alternative_sync_endpoints import get_file_verification_methods
        return jsonify(get_file_verification_methods())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/alternative-sync/run-method/<method_name>', methods=['POST'])
def run_verification_method(method_name):
    """Run a specific verification method"""
    try:
        from alternative_sync_endpoints import run_verification_method
        return jsonify(run_verification_method(method_name))
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/alternative-sync/summary', methods=['GET'])
def get_sync_summary():
    """Get sync status summary"""
    try:
        from alternative_sync_endpoints import get_sync_summary
        return jsonify(get_sync_summary())
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/docs/list')
def list_documentation_files():
    """List all markdown documentation files"""
    try:
        docs_dir = Path(PIPELINE_DIR)
        md_files = []
        
        # Find all .md files in the project (excluding node_modules and venv)
        for md_file in docs_dir.rglob('*.md'):
            if 'node_modules' not in str(md_file) and 'venv' not in str(md_file):
                relative_path = md_file.relative_to(docs_dir)
                md_files.append({
                    'name': md_file.name,
                    'path': str(relative_path),
                    'size': md_file.stat().st_size,
                    'modified': datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
                })
        
        # Sort by modification time (newest first)
        md_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': md_files
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/docs/read/<path:filename>')
def read_documentation_file(filename):
    """Read a markdown documentation file"""
    try:
        # Security check - only allow .md files
        if not filename.endswith('.md'):
            return jsonify({'success': False, 'error': 'Only .md files are allowed'}), 400
        
        file_path = Path(PIPELINE_DIR) / filename
        
        # Security check - ensure file is within project directory
        if not str(file_path.resolve()).startswith(str(Path(PIPELINE_DIR).resolve())):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Check if file exists
        if not file_path.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'size': file_path.stat().st_size,
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Pixel Backup Gang download endpoints
@app.route('/api/download/pixel_backup_gang.zip')
def download_pixel_backup_module():
    """Download the Pixel Backup Gang Magisk module"""
    try:
        module_path = os.path.join(PIPELINE_DIR, 'pixel_backup_gang.zip')
        if os.path.exists(module_path):
            return send_from_directory(PIPELINE_DIR, 'pixel_backup_gang.zip', as_attachment=True)
        else:
            return jsonify({'error': 'Module file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/credentials.json')
def download_credentials():
    """Download the credentials configuration file"""
    try:
        config_path = os.path.join(PIPELINE_DIR, 'magisk_module_pixel_backup', 'credentials.json')
        if os.path.exists(config_path):
            return send_from_directory(os.path.join(PIPELINE_DIR, 'magisk_module_pixel_backup'), 'credentials.json', as_attachment=True)
        else:
            return jsonify({'error': 'Credentials file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pixel-backup-download')
def pixel_backup_download_page():
    """Serve the Pixel Backup Gang download page"""
    try:
        return send_from_directory(os.path.join(PIPELINE_DIR, 'web'), 'download_pixel_backup.html')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pixel-deployment')
def pixel_deployment_page():
    """Serve the Pixel Backup Gang deployment page"""
    try:
        return send_from_directory(os.path.join(PIPELINE_DIR, 'web'), 'pixel_deployment.html')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Run the server
    app.run(host='0.0.0.0', port=5000, debug=False)