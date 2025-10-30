#!/usr/bin/env python3
"""
Backfill database with existing downloaded files that weren't tracked
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
try:  # Support both "python scripts/..." and "python -m scripts..."
    from .utils import (
        log_step,
        create_media_file_record,
        create_batch_record,
        calculate_file_hash,
        get_media_files_by_directory,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (  # type: ignore
        log_step,
        create_media_file_record,
        create_batch_record,
        calculate_file_hash,
        get_media_files_by_directory,
    )

# Load environment variables
load_dotenv("config/settings.env")

def backfill_originals_directory():
    """Backfill database with files from originals directory"""
    
    # Get directory paths
    originals_dir = os.getenv("ORIGINALS_DIR")
    if not originals_dir:
        nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline")
        originals_dir = os.path.join(nas_mount, "originals")
    
    print(f"Backfilling database for directory: {originals_dir}")
    
    if not os.path.exists(originals_dir):
        print(f"ERROR: Directory {originals_dir} does not exist")
        return False
    
    # Check what's already in database
    existing_files = get_media_files_by_directory(originals_dir)
    existing_paths = {f["file_path"] for f in existing_files}
    
    print(f"Found {len(existing_files)} files already tracked in database")
    
    # Find all media files in directory
    media_files = []
    for root, dirs, filenames in os.walk(originals_dir):
        for filename in filenames:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi')):
                file_path = os.path.join(root, filename)
                media_files.append(file_path)
    
    print(f"Found {len(media_files)} total media files in directory")
    
    # Filter out files already in database
    new_files = [f for f in media_files if f not in existing_paths]
    print(f"Need to track {len(new_files)} new files")
    
    if not new_files:
        print("No new files to track")
        return True
    
    # Create batch record for backfill
    total_size_gb = sum(os.path.getsize(f) for f in new_files if os.path.exists(f)) / (1024**3)
    batch_id = create_batch_record(
        batch_type="icloud_backfill",
        file_count=len(new_files),
        total_size_gb=total_size_gb
    )
    
    if not batch_id:
        print("ERROR: Failed to create batch record")
        return False
    
    # Track each new file
    tracked_count = 0
    error_count = 0
    
    for i, file_path in enumerate(new_files, 1):
        try:
            print(f"Processing {i}/{len(new_files)}: {os.path.basename(file_path)}")
            
            file_id = create_media_file_record(
                file_path=file_path,
                batch_id=batch_id,
                source_path="iCloud"
            )
            
            if file_id:
                tracked_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            print(f"ERROR processing {file_path}: {e}")
            error_count += 1
    
    print(f"\n=== Backfill Summary ===")
    print(f"Files processed: {len(new_files)}")
    print(f"Successfully tracked: {tracked_count}")
    print(f"Errors: {error_count}")
    
    if tracked_count > 0:
        log_step("database_backfill", f"Backfilled {tracked_count} files to database", "success")
        return True
    else:
        log_step("database_backfill", "No files were backfilled", "warning")
        return False

def main():
    """Main backfill function"""
    print("=== Database Backfill Script ===")
    
    try:
        success = backfill_originals_directory()
        
        if success:
            print("✓ Database backfill completed successfully")
            sys.exit(0)
        else:
            print("✗ Database backfill failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        log_step("database_backfill", f"Backfill failed: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
