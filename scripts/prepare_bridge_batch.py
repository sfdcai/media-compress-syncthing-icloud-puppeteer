#!/usr/bin/env python3
"""
Enhanced batch preparation script for media pipeline
Creates batches for iCloud and Pixel uploads with database tracking
"""

import os
import sys
import shutil
from pathlib import Path
from utils import (
    log_step, get_file_size_gb, ensure_directory_exists, 
    get_feature_toggle, create_batch_record, update_batch_status,
    calculate_file_hash
)

# Configuration
MAX_BATCH_SIZE_GB = int(os.getenv("MAX_BATCH_SIZE_GB", 5))
MAX_BATCH_FILES = int(os.getenv("MAX_BATCH_FILES", 500))

def get_media_files(directory, extensions=None):
    """Get all media files from directory"""
    if extensions is None:
        extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv'}
    
    media_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in extensions:
                file_path = os.path.join(root, file)
                media_files.append(file_path)
    
    return media_files

def create_batch_from_files(files, batch_dir, batch_type, batch_number):
    """Create a batch from a list of files"""
    try:
        # Create batch directory
        batch_path = os.path.join(batch_dir, f"batch_{batch_number}")
        ensure_directory_exists(batch_path)
        
        # Copy files to batch directory
        copied_files = []
        total_size_gb = 0
        
        for file_path in files:
            try:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(batch_path, filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    dest_path = os.path.join(batch_path, f"{name}_{counter}{ext}")
                    counter += 1
                
                # Copy file
                shutil.copy2(file_path, dest_path)
                copied_files.append(dest_path)
                
                # Calculate size
                file_size_gb = get_file_size_gb(dest_path)
                total_size_gb += file_size_gb
                
            except Exception as e:
                log_step("batch_creation", f"Failed to copy {file_path}: {e}", "error")
                continue
        
        # Create batch record in database
        batch_id = create_batch_record(
            batch_type=batch_type,
            file_count=len(copied_files),
            total_size_gb=total_size_gb
        )
        
        if batch_id:
            log_step("batch_creation", f"Created batch_{batch_number} for {batch_type} with {len(copied_files)} files ({total_size_gb:.2f} GB)", "success")
            return batch_id, len(copied_files), total_size_gb
        else:
            log_step("batch_creation", f"Failed to create batch record for batch_{batch_number}", "error")
            return None, 0, 0
            
    except Exception as e:
        log_step("batch_creation", f"Error creating batch_{batch_number}: {e}", "error")
        return None, 0, 0

def prepare_batches_for_type(source_dir, batch_dir, batch_type, use_compressed=False):
    """Prepare batches for a specific upload type"""
    if not os.path.exists(source_dir):
        log_step("batch_preparation", f"Source directory {source_dir} does not exist", "error")
        return False
    
    # Ensure batch directory exists
    ensure_directory_exists(batch_dir)
    
    log_step("batch_preparation", f"Preparing batches for {batch_type} from {source_dir}", "info")
    
    # Get all media files
    media_files = get_media_files(source_dir)
    
    if not media_files:
        log_step("batch_preparation", f"No media files found in {source_dir}", "info")
        return True
    
    # Sort files by name for consistent batching
    media_files.sort()
    
    # Create batches
    current_batch = []
    current_size_gb = 0
    batch_number = 1
    total_batches = 0
    total_files = 0
    total_size_gb = 0
    
    for file_path in media_files:
        file_size_gb = get_file_size_gb(file_path)
        
        # Check if adding this file would exceed limits
        if (len(current_batch) >= MAX_BATCH_FILES or 
            current_size_gb + file_size_gb > MAX_BATCH_SIZE_GB):
            
            # Create batch from current files
            if current_batch:
                batch_id, file_count, batch_size = create_batch_from_files(
                    current_batch, batch_dir, batch_type, batch_number
                )
                
                if batch_id:
                    total_batches += 1
                    total_files += file_count
                    total_size_gb += batch_size
                    batch_number += 1
                
                # Reset for next batch
                current_batch = []
                current_size_gb = 0
        
        # Add file to current batch
        current_batch.append(file_path)
        current_size_gb += file_size_gb
    
    # Create final batch if there are remaining files
    if current_batch:
        batch_id, file_count, batch_size = create_batch_from_files(
            current_batch, batch_dir, batch_type, batch_number
        )
        
        if batch_id:
            total_batches += 1
            total_files += file_count
            total_size_gb += batch_size
    
    # Summary
    log_step("batch_preparation", f"Created {total_batches} batches for {batch_type}: {total_files} files, {total_size_gb:.2f} GB total", "success")
    return True

def main():
    """Main batch preparation function"""
    # Get configuration
    originals_dir = os.getenv("ORIGINALS_DIR", "originals")
    compressed_dir = os.getenv("COMPRESSED_DIR", "compressed")
    bridge_icloud_dir = os.getenv("BRIDGE_ICLOUD_DIR", "bridge/icloud")
    bridge_pixel_dir = os.getenv("BRIDGE_PIXEL_DIR", "bridge/pixel")
    
    # Check feature toggles
    enable_icloud = get_feature_toggle("ENABLE_ICLOUD_UPLOAD")
    enable_pixel = get_feature_toggle("ENABLE_PIXEL_UPLOAD")
    enable_compression = get_feature_toggle("ENABLE_COMPRESSION")
    
    if not enable_icloud and not enable_pixel:
        log_step("batch_preparation", "Both iCloud and Pixel uploads are disabled, skipping batch preparation", "info")
        return
    
    success = True
    
    # Prepare batches for iCloud (use compressed files if compression is enabled)
    if enable_icloud:
        if enable_compression and os.path.exists(compressed_dir):
            source_dir = compressed_dir
            log_step("batch_preparation", "Using compressed files for iCloud batches", "info")
        else:
            source_dir = originals_dir
            log_step("batch_preparation", "Using original files for iCloud batches", "info")
        
        if not prepare_batches_for_type(source_dir, bridge_icloud_dir, "icloud"):
            success = False
    
    # Prepare batches for Pixel (always use original files)
    if enable_pixel:
        if not prepare_batches_for_type(originals_dir, bridge_pixel_dir, "pixel"):
            success = False
    
    if success:
        log_step("batch_preparation", "Batch preparation completed successfully", "success")
    else:
        log_step("batch_preparation", "Batch preparation failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
