#!/usr/bin/env python3
"""
Deduplication script for media pipeline
Removes duplicate files and tracks them in Supabase database
"""

import os
import sys
import shutil
from pathlib import Path
from utils.utils import (
    log_step, calculate_file_hash, get_file_size_gb, 
    ensure_directory_exists, is_duplicate_file, 
    log_duplicate_file, get_feature_toggle, retry,
    create_media_file_record
)

def get_media_files(directory, extensions=None):
    """Get all media files from directory (excluding duplicates subdirectory)"""
    if extensions is None:
        extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv'}
    
    media_files = []
    for root, dirs, files in os.walk(directory):
        # Skip duplicates directory
        if 'duplicates' in dirs:
            dirs.remove('duplicates')
        
        for file in files:
            if Path(file).suffix.lower() in extensions:
                file_path = os.path.join(root, file)
                media_files.append(file_path)
    
    return media_files

@retry(max_attempts=3, delay=5)
def process_file_deduplication(file_path, duplicates_dir, hash_algorithm="md5"):
    """Process a single file for deduplication"""
    try:
        # Calculate file hash
        file_hash = calculate_file_hash(file_path, hash_algorithm)
        if not file_hash:
            log_step("deduplication", f"Failed to calculate hash for {file_path}", "error")
            return None
        
        # Check if file is duplicate
        if is_duplicate_file(file_hash):
            log_step("deduplication", f"Found duplicate: {file_path}", "info")
            
            # Move duplicate to duplicates directory
            filename = os.path.basename(file_path)
            duplicate_path = os.path.join(duplicates_dir, filename)
            
            # Handle filename conflicts
            counter = 1
            while os.path.exists(duplicate_path):
                name, ext = os.path.splitext(filename)
                duplicate_path = os.path.join(duplicates_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # Move file
            shutil.move(file_path, duplicate_path)
            log_step("deduplication", f"Moved duplicate to {duplicate_path}", "success")
            
            return {
                "file_path": file_path,
                "duplicate_path": duplicate_path,
                "hash": file_hash,
                "is_duplicate": True
            }
        else:
            # File is unique, log it
            log_step("deduplication", f"Unique file: {file_path}", "info")
            return {
                "file_path": file_path,
                "hash": file_hash,
                "is_duplicate": False
            }
            
    except Exception as e:
        log_step("deduplication", f"Error processing {file_path}: {e}", "error")
        return None

def deduplicate_directory(source_dir, duplicates_dir=None, hash_algorithm="md5", batch_size=1000):
    """Deduplicate files in a directory against database of previously processed files"""
    if not os.path.exists(source_dir):
        log_step("deduplication", f"Source directory {source_dir} does not exist", "error")
        return False
    
    # Create duplicates directory if not specified
    if duplicates_dir is None:
        duplicates_dir = os.path.join(source_dir, "duplicates")
    
    ensure_directory_exists(duplicates_dir)
    
    log_step("deduplication", f"Starting deduplication of {source_dir}", "info")
    
    # Get all media files
    media_files = get_media_files(source_dir)
    total_files = len(media_files)
    
    if total_files == 0:
        log_step("deduplication", "No media files found to process", "info")
        return True
    
    log_step("deduplication", f"Found {total_files} files to process", "info")
    
    # Track hashes within this directory AND check against database
    hash_to_file = {}  # hash -> first file path (within this directory)
    duplicates_found = 0
    errors = 0
    
    for i, file_path in enumerate(media_files):
        try:
            # Calculate file hash
            file_hash = calculate_file_hash(file_path, hash_algorithm)
            if not file_hash:
                log_step("deduplication", f"Failed to calculate hash for {file_path}", "error")
                errors += 1
                continue
            
            # Check if this file was already processed (database check)
            if is_duplicate_file(file_hash):
                log_step("deduplication", f"File already processed: {file_path} (hash: {file_hash[:8]}...)", "info")
                
                # Move to duplicates directory since it was already processed
                filename = os.path.basename(file_path)
                duplicate_path = os.path.join(duplicates_dir, filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(duplicate_path):
                    name, ext = os.path.splitext(filename)
                    duplicate_path = os.path.join(duplicates_dir, f"{name}_processed_{counter}{ext}")
                    counter += 1
                
                # Move the already-processed file
                shutil.move(file_path, duplicate_path)
                log_step("deduplication", f"Moved already-processed file to: {duplicate_path}", "info")
                
                # Log the duplicate file relationship
                log_duplicate_file(duplicate_path, f"already_processed_{file_hash[:8]}")
                duplicates_found += 1
                
            # Check if we've seen this hash before in this directory
            elif file_hash in hash_to_file:
                # This is a duplicate within this directory
                original_file = hash_to_file[file_hash]
                log_step("deduplication", f"Found duplicate: {file_path} (duplicate of {original_file})", "info")
                
                # Move duplicate to duplicates directory
                filename = os.path.basename(file_path)
                duplicate_path = os.path.join(duplicates_dir, filename)
                
                # Handle filename conflicts
                counter = 1
                while os.path.exists(duplicate_path):
                    name, ext = os.path.splitext(filename)
                    duplicate_path = os.path.join(duplicates_dir, f"{name}_dup_{counter}{ext}")
                    counter += 1
                
                # Move the duplicate file
                shutil.move(file_path, duplicate_path)
                log_step("deduplication", f"Moved duplicate to: {duplicate_path}", "info")
                
                # Log the duplicate file relationship
                log_duplicate_file(duplicate_path, original_file)
                duplicates_found += 1
                
            else:
                # First time seeing this hash, record it and log as unique
                hash_to_file[file_hash] = file_path
                log_step("deduplication", f"Unique file: {file_path} (hash: {file_hash[:8]}...)", "info")
                
                # Log this file to the database so it won't be reprocessed
                try:
                    file_size = os.path.getsize(file_path)
                    create_media_file_record(
                        file_path=file_path,
                        file_size=file_size,
                        file_hash=file_hash,
                        source_type="deduplication",
                        status="processed"
                    )
                except Exception as e:
                    log_step("deduplication", f"Failed to log unique file to database: {e}", "warning")
            
            # Progress update
            progress = (i + 1) / total_files * 100
            if (i + 1) % 10 == 0:  # Update every 10 files
                log_step("deduplication", f"Progress: {progress:.1f}% ({i + 1}/{total_files})", "info")
                
        except Exception as e:
            log_step("deduplication", f"Error processing {file_path}: {e}", "error")
            errors += 1
    
    # Summary
    processed = total_files - errors
    log_step("deduplication", f"Deduplication completed: {processed} processed, {duplicates_found} duplicates found, {errors} errors", "success")
    
    return True

def main():
    """Main deduplication function"""
    if not get_feature_toggle("ENABLE_DEDUPLICATION"):
        log_step("deduplication", "Deduplication is disabled, skipping", "info")
        return
    
    # Get configuration
    hash_algorithm = os.getenv("DEDUPLICATION_HASH_ALGORITHM", "md5")
    batch_size = int(os.getenv("DEDUPLICATION_BATCH_SIZE", "1000"))
    
    # Get directories to process
    directories_to_process = []
    
    # Add originals directory
    originals_dir = os.getenv("ORIGINALS_DIR", "/mnt/wd_all_pictures/sync/originals")
    if os.path.exists(originals_dir):
        directories_to_process.append(("originals", originals_dir))
    
    # Add uploaded directories
    uploaded_dirs = [
        ("uploaded_icloud", os.getenv("UPLOADED_ICLOUD_DIR", "/mnt/wd_all_pictures/sync/uploaded/icloud")),
        ("uploaded_pixel", os.getenv("UPLOADED_PIXEL_DIR", "/mnt/wd_all_pictures/sync/uploaded/pixel")),
        ("uploaded_folder", os.getenv("UPLOADED_FOLDER_DIR", "/mnt/wd_all_pictures/sync/uploaded/folder"))
    ]
    
    for dir_name, dir_path in uploaded_dirs:
        if os.path.exists(dir_path):
            directories_to_process.append((dir_name, dir_path))
    
    if not directories_to_process:
        log_step("deduplication", "No directories found to process", "warning")
        return
    
    log_step("deduplication", f"Processing {len(directories_to_process)} directories for deduplication", "info")
    
    # Run deduplication on each directory
    overall_success = True
    for dir_name, dir_path in directories_to_process:
        log_step("deduplication", f"Processing {dir_name} directory: {dir_path}", "info")
        
        success = deduplicate_directory(
            source_dir=dir_path,
            hash_algorithm=hash_algorithm,
            batch_size=batch_size
        )
        
        if not success:
            overall_success = False
            log_step("deduplication", f"Failed to deduplicate {dir_name} directory", "error")
        else:
            log_step("deduplication", f"Successfully deduplicated {dir_name} directory", "info")
    
    success = overall_success
    
    if success:
        log_step("deduplication", "Deduplication completed successfully", "success")
    else:
        log_step("deduplication", "Deduplication failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
