#!/usr/bin/env python3
"""
Prepare files for Pixel sync - move files from originals to bridge/pixel folder
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv
from utils import (
    log_step, ensure_directory_exists, get_media_files_by_directory,
    update_file_status, create_batch_record, update_batch_status
)

# Load environment variables
load_dotenv("config/settings.env")

def get_files_for_pixel_sync(originals_dir, max_files=None):
    """Get files from originals directory for Pixel sync"""
    try:
        # Get files from database that are in 'downloaded' status
        db_files = get_media_files_by_directory(originals_dir)
        downloaded_files = [f for f in db_files if f.get('status') == 'downloaded']
        
        # Sort by creation date (oldest first)
        downloaded_files.sort(key=lambda x: x.get('created_at', ''))
        
        # Limit number of files if specified
        if max_files and len(downloaded_files) > max_files:
            downloaded_files = downloaded_files[:max_files]
        
        log_step("prepare_pixel_sync", f"Found {len(downloaded_files)} files ready for Pixel sync", "info")
        return downloaded_files
        
    except Exception as e:
        log_step("prepare_pixel_sync", f"Error getting files for sync: {e}", "error")
        return []

def copy_files_to_pixel_bridge(files, bridge_dir):
    """Copy files to Pixel bridge directory"""
    try:
        # Ensure bridge directory exists
        ensure_directory_exists(bridge_dir)
        
        copied_files = []
        total_size_gb = 0
        
        for file_info in files:
            file_path = file_info['file_path']
            filename = file_info['filename']
            
            if not os.path.exists(file_path):
                log_step("prepare_pixel_sync", f"File not found: {file_path}", "warning")
                continue
            
            try:
                # Create destination path
                dest_path = os.path.join(bridge_dir, filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(bridge_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                # Copy file
                shutil.copy2(file_path, dest_path)
                
                # Update file info
                file_info['bridge_path'] = dest_path
                file_info['file_size'] = os.path.getsize(dest_path)
                copied_files.append(file_info)
                total_size_gb += file_info['file_size'] / (1024**3)
                
                log_step("prepare_pixel_sync", f"Copied {filename} to bridge", "info")
                
            except Exception as e:
                log_step("prepare_pixel_sync", f"Failed to copy {filename}: {e}", "error")
                continue
        
        log_step("prepare_pixel_sync", f"Copied {len(copied_files)} files to bridge ({total_size_gb:.2f} GB)", "success")
        return copied_files, total_size_gb
        
    except Exception as e:
        log_step("prepare_pixel_sync", f"Error copying files to bridge: {e}", "error")
        return [], 0

def update_file_statuses(files, status):
    """Update file statuses in database"""
    try:
        updated_count = 0
        
        for file_info in files:
            file_id = file_info['id']
            try:
                update_file_status(file_id, status, bridge_path=file_info.get('bridge_path'))
                updated_count += 1
            except Exception as e:
                log_step("prepare_pixel_sync", f"Failed to update status for file {file_id}: {e}", "error")
        
        log_step("prepare_pixel_sync", f"Updated status for {updated_count} files to '{status}'", "success")
        return updated_count
        
    except Exception as e:
        log_step("prepare_pixel_sync", f"Error updating file statuses: {e}", "error")
        return 0

def prepare_pixel_sync():
    """Main function to prepare files for Pixel sync"""
    print("=== Preparing Files for Pixel Sync ===")
    
    # Get configuration
    originals_dir = os.getenv("ORIGINALS_DIR", "/mnt/wd_all_pictures/sync/originals")
    bridge_dir = os.getenv("BRIDGE_PIXEL_DIR", "/mnt/wd_all_pictures/sync/bridge/pixel")
    max_files = int(os.getenv("MAX_PROCESSING_FILES", "50"))
    
    print(f"Originals directory: {originals_dir}")
    print(f"Bridge directory: {bridge_dir}")
    print(f"Max files to process: {max_files}")
    
    # Step 1: Get files ready for sync
    print("\nStep 1: Getting files ready for Pixel sync...")
    files = get_files_for_pixel_sync(originals_dir, max_files)
    
    if not files:
        print("No files ready for Pixel sync")
        return False
    
    print(f"✓ Found {len(files)} files ready for sync")
    
    # Step 2: Create batch record
    print("\nStep 2: Creating batch record...")
    batch_id = create_batch_record(
        batch_type="pixel",
        file_count=len(files),
        total_size_gb=sum(f.get('file_size', 0) for f in files) / (1024**3)
    )
    
    if not batch_id:
        print("✗ Failed to create batch record")
        return False
    
    print(f"✓ Created batch record: {batch_id}")
    
    # Step 3: Copy files to bridge directory
    print("\nStep 3: Copying files to bridge directory...")
    copied_files, total_size_gb = copy_files_to_pixel_bridge(files, bridge_dir)
    
    if not copied_files:
        print("✗ No files were copied to bridge directory")
        return False
    
    print(f"✓ Copied {len(copied_files)} files to bridge directory")
    
    # Step 4: Update file statuses to 'batched'
    print("\nStep 4: Updating file statuses...")
    updated_count = update_file_statuses(copied_files, "batched")
    
    if updated_count != len(copied_files):
        print(f"⚠ Updated {updated_count}/{len(copied_files)} file statuses")
    else:
        print(f"✓ Updated all {updated_count} file statuses")
    
    # Step 5: Update batch status
    print("\nStep 5: Updating batch status...")
    update_batch_status(batch_id, "created", file_count=len(copied_files), total_size_gb=total_size_gb)
    
    print(f"✓ Batch {batch_id} ready for Pixel sync")
    
    print(f"\n=== Pixel Sync Preparation Complete ===")
    print(f"Files prepared: {len(copied_files)}")
    print(f"Total size: {total_size_gb:.2f} GB")
    print(f"Bridge directory: {bridge_dir}")
    print(f"Batch ID: {batch_id}")
    
    return True

def main():
    """Main function"""
    try:
        success = prepare_pixel_sync()
        
        if success:
            print("\n✓ Pixel sync preparation completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Pixel sync preparation failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        log_step("prepare_pixel_sync", f"Preparation failed: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
