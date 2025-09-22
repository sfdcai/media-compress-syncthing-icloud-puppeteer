#!/usr/bin/env python3
"""
Debug version of prepare_pixel_sync to see what's happening
"""

import os
import sys
import shutil
from pathlib import Path

# Ensure we can find the config file
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
config_path = os.path.join(project_root, "config", "settings.env")

# Load environment variables before importing utils
from dotenv import load_dotenv
load_dotenv(config_path)

# Now import utils
from utils import (
    log_step, ensure_directory_exists, get_media_files_by_directory,
    update_file_status, create_batch_record, update_batch_status
)

def debug_pixel_sync():
    """Debug version to see what's happening"""
    print("=== Debug Pixel Sync ===")
    
    # Get configuration
    originals_dir = os.getenv("ORIGINALS_DIR", "/mnt/wd_all_pictures/sync/originals")
    bridge_dir = os.getenv("BRIDGE_PIXEL_DIR", "/mnt/wd_all_pictures/sync/bridge/pixel")
    max_files = int(os.getenv("MAX_PROCESSING_FILES", "50"))
    
    print(f"Originals directory: {originals_dir}")
    print(f"Bridge directory: {bridge_dir}")
    print(f"Max files to process: {max_files}")
    
    # Check if directories exist
    print(f"\nOriginals directory exists: {os.path.exists(originals_dir)}")
    print(f"Bridge directory exists: {os.path.exists(bridge_dir)}")
    
    if os.path.exists(bridge_dir):
        bridge_files = os.listdir(bridge_dir)
        print(f"Files already in bridge directory: {len(bridge_files)}")
        if bridge_files:
            print(f"Sample bridge files: {bridge_files[:5]}")
    
    # Get files from database
    print(f"\nGetting files from database...")
    db_files = get_media_files_by_directory(originals_dir)
    downloaded_files = [f for f in db_files if f.get('status') == 'downloaded']
    
    print(f"Total files in database: {len(db_files)}")
    print(f"Files with 'downloaded' status: {len(downloaded_files)}")
    
    if downloaded_files:
        print(f"Sample downloaded files:")
        for i, f in enumerate(downloaded_files[:5]):
            print(f"  {i+1}. {f['filename']} - {f['file_path']} - Status: {f.get('status')}")
    
    # Check if files exist on disk
    print(f"\nChecking if files exist on disk...")
    existing_files = []
    missing_files = []
    
    for file_info in downloaded_files[:10]:  # Check first 10
        file_path = file_info['file_path']
        if os.path.exists(file_path):
            existing_files.append(file_info)
        else:
            missing_files.append(file_info)
    
    print(f"Files that exist on disk: {len(existing_files)}")
    print(f"Files missing from disk: {len(missing_files)}")
    
    if missing_files:
        print(f"Missing files:")
        for f in missing_files[:3]:
            print(f"  - {f['filename']}: {f['file_path']}")
    
    # Check what would happen during copy
    print(f"\nSimulating copy process...")
    if existing_files:
        sample_file = existing_files[0]
        file_path = sample_file['file_path']
        filename = sample_file['filename']
        dest_path = os.path.join(bridge_dir, filename)
        
        print(f"Sample file: {filename}")
        print(f"Source: {file_path}")
        print(f"Destination: {dest_path}")
        print(f"Source exists: {os.path.exists(file_path)}")
        print(f"Destination exists: {os.path.exists(dest_path)}")
        
        if os.path.exists(dest_path):
            print(f"⚠ File already exists in bridge directory!")
            print(f"This might be why the copy is being skipped.")

def main():
    """Main debug function"""
    try:
        debug_pixel_sync()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
