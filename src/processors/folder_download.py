#!/usr/bin/env python3
"""
Folder Download Script for Media Pipeline
Handles downloading/processing media files from local folders
"""

import os
import sys
import shutil
import glob
from pathlib import Path
from datetime import datetime
from utils.utils import (
    log_step, validate_config, get_config_value,
    ensure_directory_exists, create_media_file_record
)

def get_file_patterns():
    """Get file patterns from configuration"""
    patterns_str = get_config_value("FOLDER_SOURCE_PATTERNS", "*.jpg,*.jpeg,*.png,*.gif,*.bmp,*.tiff,*.mp4,*.mov,*.avi,*.mkv,*.webm")
    return [pattern.strip() for pattern in patterns_str.split(",")]

def scan_source_folder():
    """Scan the source folder for media files"""
    source_path = get_config_value("FOLDER_SOURCE_PATH", "/mnt/wd_all_pictures/sync/source_folder")
    
    if not os.path.exists(source_path):
        log_step("folder_download", f"Source folder does not exist: {source_path}", "error")
        return []
    
    log_step("folder_download", f"Scanning source folder: {source_path}", "info")
    
    patterns = get_file_patterns()
    media_files = []
    
    # Scan for files matching patterns
    for pattern in patterns:
        search_pattern = os.path.join(source_path, "**", pattern)
        files = glob.glob(search_pattern, recursive=True)
        media_files.extend(files)
    
    # Remove duplicates and sort
    media_files = list(set(media_files))
    media_files.sort()
    
    log_step("folder_download", f"Found {len(media_files)} media files", "info")
    return media_files

def copy_file_to_originals(source_file, destination_dir):
    """Copy file to originals directory with proper naming"""
    try:
        # Ensure destination directory exists
        ensure_directory_exists(destination_dir)
        
        # Get file info
        source_path = Path(source_file)
        filename = source_path.name
        file_size = source_path.stat().st_size
        file_extension = source_path.suffix.lower()
        
        # Create destination path
        dest_path = os.path.join(destination_dir, filename)
        
        # Handle filename conflicts
        counter = 1
        original_dest = dest_path
        while os.path.exists(dest_path):
            name_part = source_path.stem
            dest_path = os.path.join(destination_dir, f"{name_part}_{counter}{file_extension}")
            counter += 1
        
        # Copy file using sudo (for CIFS mount compatibility)
        import subprocess
        try:
            subprocess.run(['sudo', 'cp', source_file, dest_path], check=True)
            # Try to set permissions, but don't fail if it doesn't work (CIFS mount issue)
            try:
                subprocess.run(['sudo', 'chmod', '644', dest_path], check=True)
            except subprocess.CalledProcessError:
                log_step("folder_download", f"Could not set permissions for {dest_path} (CIFS mount)", "warning")
        except subprocess.CalledProcessError as e:
            log_step("folder_download", f"Sudo copy failed for {source_file}: {e}", "error")
            return None
        
        # Get file modification time
        mod_time = datetime.fromtimestamp(source_path.stat().st_mtime)
        
        # Create database record
        create_media_file_record(
            file_path=dest_path,
            file_hash=None,
            batch_id=None,
            source_path=source_file
        )
        
        log_step("folder_download", f"Copied {filename} to originals", "success")
        return dest_path
        
    except Exception as e:
        log_step("folder_download", f"Error copying {source_file}: {e}", "error")
        return None

def process_folder_files():
    """Process all files from the source folder"""
    log_step("folder_download", "Starting folder download process", "info")
    
    # Get configuration
    originals_dir = get_config_value("ORIGINALS_DIR", "/mnt/wd_all_pictures/sync/originals")
    
    # Scan for media files
    media_files = scan_source_folder()
    
    if not media_files:
        log_step("folder_download", "No media files found in source folder", "info")
        return True
    
    # Process each file
    processed_count = 0
    failed_count = 0
    
    for file_path in media_files:
        try:
            result = copy_file_to_originals(file_path, originals_dir)
            if result:
                processed_count += 1
            else:
                failed_count += 1
        except Exception as e:
            log_step("folder_download", f"Error processing {file_path}: {e}", "error")
            failed_count += 1
    
    log_step("folder_download", f"Folder download completed: {processed_count} processed, {failed_count} failed", "success")
    return failed_count == 0

def cleanup_source_files():
    """Optionally clean up source files after processing"""
    cleanup_enabled = get_config_value("CLEANUP_SOURCE_FILES", "false").lower() == "true"
    
    if not cleanup_enabled:
        log_step("folder_download", "Source file cleanup is disabled", "info")
        return True
    
    log_step("folder_download", "Cleaning up source files", "info")
    
    try:
        source_path = get_config_value("FOLDER_SOURCE_PATH", "/mnt/wd_all_pictures/sync/source_folder")
        
        # Get all processed files from database
        from local_db_manager import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_path FROM media_files 
            WHERE source_type = 'folder' AND processed = true
        """)
        
        processed_files = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Remove processed files
        removed_count = 0
        for file_path in processed_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1
            except Exception as e:
                log_step("folder_download", f"Error removing {file_path}: {e}", "error")
        
        log_step("folder_download", f"Cleaned up {removed_count} source files", "success")
        return True
        
    except Exception as e:
        log_step("folder_download", f"Error during cleanup: {e}", "error")
        return False

def main():
    """Main function for folder download"""
    log_step("folder_download", "Starting folder download script", "info")
    
    # Validate configuration
    if not validate_config():
        log_step("folder_download", "Configuration validation failed", "error")
        sys.exit(1)
    
    try:
        # Process folder files
        success = process_folder_files()
        
        if success:
            # Optionally cleanup source files
            cleanup_source_files()
            log_step("folder_download", "Folder download completed successfully", "success")
            return True
        else:
            log_step("folder_download", "Folder download completed with errors", "error")
            return False
            
    except Exception as e:
        log_step("folder_download", f"Unexpected error: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()