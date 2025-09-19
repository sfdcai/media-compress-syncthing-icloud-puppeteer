#!/usr/bin/env python3
"""
Enhanced Pixel sync script for media pipeline
Moves batches to Syncthing folder for Google Photos sync
"""

import os
import sys
import shutil
import time
from pathlib import Path
from utils import (
    log_step, get_feature_toggle, ensure_directory_exists,
    update_batch_status, get_files_by_status, retry
)

def get_files_in_bridge(bridge_dir):
    """Get all files in bridge directory (no numbered batch folders)"""
    if not os.path.exists(bridge_dir):
        return []
    
    files = []
    for item in os.listdir(bridge_dir):
        item_path = os.path.join(bridge_dir, item)
        if os.path.isfile(item_path):
            files.append(item_path)
    
    return sorted(files)

@retry(max_attempts=3, delay=10)
def sync_files_to_pixel(bridge_dir, sync_folder):
    """Sync all files from bridge directory to Pixel Syncthing folder"""
    try:
        # Get all files in bridge directory
        files = get_files_in_bridge(bridge_dir)
        
        if not files:
            log_step("sync_to_pixel", "No files found in bridge directory", "info")
            return True
        
        # Ensure sync folder exists
        ensure_directory_exists(sync_folder)
        
        # Copy files to sync folder
        copied_files = 0
        for file_path in files:
            try:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(sync_folder, filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(sync_folder, f"{name}_{counter}{ext}")
                    counter += 1
                
                # Copy file
                shutil.copy2(file_path, dest_path)
                copied_files += 1
                
            except Exception as e:
                log_step("sync_to_pixel", f"Failed to copy {file_path}: {e}", "error")
                continue
        
        log_step("sync_to_pixel", f"Successfully synced {copied_files} files to Pixel folder", "success")
        return True
        
    except Exception as e:
        log_step("sync_to_pixel", f"Failed to sync files from {bridge_dir}: {e}", "error")
        return False

def wait_for_syncthing_sync(sync_folder, timeout=300):
    """Wait for Syncthing to process the files"""
    log_step("sync_to_pixel", f"Waiting for Syncthing to process files (timeout: {timeout}s)", "info")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check if files are being processed by Syncthing
        # This is a simple check - in production you might want to check Syncthing API
        time.sleep(10)
        
        # For now, just wait the full timeout
        # In a real implementation, you'd check Syncthing status
        
    log_step("sync_to_pixel", "Syncthing sync timeout reached", "warning")
    return True

def sync_to_pixel(bridge_dir, sync_folder):
    """Sync all files from bridge directory to Pixel Syncthing folder"""
    if not get_feature_toggle("ENABLE_PIXEL_UPLOAD"):
        log_step("sync_to_pixel", "Pixel upload is disabled, skipping", "info")
        return True
    
    # Validate directories
    if not os.path.exists(bridge_dir):
        log_step("sync_to_pixel", f"Bridge directory {bridge_dir} does not exist", "error")
        return False
    
    log_step("sync_to_pixel", f"Starting Pixel sync from {bridge_dir} to {sync_folder}", "info")
    
    # Sync all files from bridge directory
    if sync_files_to_pixel(bridge_dir, sync_folder):
        # Wait for Syncthing to process files
        sync_timeout = int(os.getenv("PIXEL_SYNC_TIMEOUT", "300"))
        wait_for_syncthing_sync(sync_folder, sync_timeout)
        
        log_step("sync_to_pixel", "Pixel sync completed successfully", "success")
        return True
    else:
        log_step("sync_to_pixel", "Pixel sync failed", "error")
        return False

def main():
    """Main Pixel sync function"""
    # Get configuration
    bridge_dir = os.getenv("BRIDGE_PIXEL_DIR", "bridge/pixel")
    sync_folder = os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel")
    
    # Run sync
    success = sync_to_pixel(bridge_dir, sync_folder)
    
    if success:
        log_step("sync_to_pixel", "Pixel sync completed successfully", "success")
    else:
        log_step("sync_to_pixel", "Pixel sync failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
