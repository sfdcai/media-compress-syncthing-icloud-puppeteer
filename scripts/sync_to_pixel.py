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

def get_batch_directories(batch_dir):
    """Get all batch directories"""
    if not os.path.exists(batch_dir):
        return []
    
    batch_dirs = []
    for item in os.listdir(batch_dir):
        item_path = os.path.join(batch_dir, item)
        if os.path.isdir(item_path) and item.startswith("batch_"):
            batch_dirs.append(item_path)
    
    return sorted(batch_dirs)

@retry(max_attempts=3, delay=10)
def sync_batch_to_pixel(batch_path, sync_folder):
    """Sync a single batch to Pixel Syncthing folder"""
    try:
        batch_name = os.path.basename(batch_path)
        sync_batch_path = os.path.join(sync_folder, batch_name)
        
        # Check if batch already exists in sync folder
        if os.path.exists(sync_batch_path):
            log_step("sync_to_pixel", f"Batch {batch_name} already exists in sync folder", "info")
            return True
        
        # Move batch to sync folder
        shutil.move(batch_path, sync_batch_path)
        
        # Ensure proper permissions
        ensure_directory_exists(sync_batch_path)
        
        log_step("sync_to_pixel", f"Successfully synced {batch_name} to Pixel folder", "success")
        return True
        
    except Exception as e:
        log_step("sync_to_pixel", f"Failed to sync batch {batch_path}: {e}", "error")
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

def sync_to_pixel(batch_dir, sync_folder):
    """Sync all batches to Pixel Syncthing folder"""
    if not get_feature_toggle("ENABLE_PIXEL_UPLOAD"):
        log_step("sync_to_pixel", "Pixel upload is disabled, skipping", "info")
        return True
    
    # Validate directories
    if not os.path.exists(batch_dir):
        log_step("sync_to_pixel", f"Batch directory {batch_dir} does not exist", "error")
        return False
    
    if not os.path.exists(sync_folder):
        log_step("sync_to_pixel", f"Sync folder {sync_folder} does not exist", "error")
        return False
    
    log_step("sync_to_pixel", f"Starting Pixel sync from {batch_dir} to {sync_folder}", "info")
    
    # Get all batch directories
    batch_dirs = get_batch_directories(batch_dir)
    
    if not batch_dirs:
        log_step("sync_to_pixel", "No batches found to sync", "info")
        return True
    
    log_step("sync_to_pixel", f"Found {len(batch_dirs)} batches to sync", "info")
    
    # Sync each batch
    successful_syncs = 0
    failed_syncs = 0
    
    for batch_path in batch_dirs:
        batch_name = os.path.basename(batch_path)
        log_step("sync_to_pixel", f"Syncing {batch_name}", "info")
        
        if sync_batch_to_pixel(batch_path, sync_folder):
            successful_syncs += 1
            
            # Update batch status in database
            # Note: This would need batch_id from the database
            # For now, we'll just log the success
            
        else:
            failed_syncs += 1
    
    # Wait for Syncthing to process files
    if successful_syncs > 0:
        sync_timeout = int(os.getenv("PIXEL_SYNC_TIMEOUT", "300"))
        wait_for_syncthing_sync(sync_folder, sync_timeout)
    
    # Summary
    log_step("sync_to_pixel", f"Pixel sync completed: {successful_syncs} successful, {failed_syncs} failed", "success")
    return failed_syncs == 0

def main():
    """Main Pixel sync function"""
    # Get configuration
    batch_dir = os.getenv("BRIDGE_PIXEL_DIR", "bridge/pixel")
    sync_folder = os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel")
    
    # Run sync
    success = sync_to_pixel(batch_dir, sync_folder)
    
    if success:
        log_step("sync_to_pixel", "Pixel sync completed successfully", "success")
    else:
        log_step("sync_to_pixel", "Pixel sync failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
