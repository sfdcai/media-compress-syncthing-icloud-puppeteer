#!/usr/bin/env python3
"""
Deduplication script for media pipeline
Removes duplicate files and tracks them in Supabase database
"""

import os
import sys
import shutil
from pathlib import Path
from utils import (
    log_step, calculate_file_hash, get_file_size_gb,
    ensure_directory_exists, is_duplicate_file,
    log_duplicate_file, get_feature_toggle, retry,
    create_media_file_record
)

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
            record_id = create_media_file_record(
                file_path=file_path,
                file_hash=file_hash,
                source_path=file_path,
            )

            if not record_id:
                log_step(
                    "deduplication",
                    f"Failed to record unique file in database: {file_path}",
                    "warning",
                )
            return {
                "file_path": file_path,
                "hash": file_hash,
                "is_duplicate": False
            }
            
    except Exception as e:
        log_step("deduplication", f"Error processing {file_path}: {e}", "error")
        return None

def deduplicate_directory(source_dir, duplicates_dir=None, hash_algorithm="md5", batch_size=1000):
    """Deduplicate files in a directory"""
    if not os.path.exists(source_dir):
        log_step("deduplication", f"Source directory {source_dir} does not exist", "error")
        return False
    
    # Create duplicates directory if not specified
    if duplicates_dir is None:
        duplicates_dir = os.path.join(source_dir, "duplicates")
    
    if not ensure_directory_exists(duplicates_dir):
        log_step(
            "deduplication",
            f"Failed to ensure duplicates directory exists at {duplicates_dir}",
            "error",
        )
        return False
    
    log_step("deduplication", f"Starting deduplication of {source_dir}", "info")
    
    # Get all media files
    media_files = get_media_files(source_dir)
    total_files = len(media_files)
    
    if total_files == 0:
        log_step("deduplication", "No media files found to process", "info")
        return True
    
    log_step("deduplication", f"Found {total_files} files to process", "info")
    
    # Process files in batches
    processed = 0
    duplicates_found = 0
    errors = 0
    
    for i in range(0, total_files, batch_size):
        batch = media_files[i:i + batch_size]
        log_step("deduplication", f"Processing batch {i//batch_size + 1} ({len(batch)} files)", "info")
        
        for file_path in batch:
            result = process_file_deduplication(file_path, duplicates_dir, hash_algorithm)
            if result:
                processed += 1
                if result.get("is_duplicate"):
                    duplicates_found += 1
            else:
                errors += 1
        
        # Log progress
        progress = (processed + errors) / total_files * 100
        log_step("deduplication", f"Progress: {progress:.1f}% ({processed + errors}/{total_files})", "info")
    
    # Summary
    log_step("deduplication", f"Deduplication completed: {processed} processed, {duplicates_found} duplicates found, {errors} errors", "success")
    
    return True

def main():
    """Main deduplication function"""
    if not get_feature_toggle("ENABLE_DEDUPLICATION"):
        log_step("deduplication", "Deduplication is disabled, skipping", "info")
        return
    
    # Get configuration
    source_dir = os.getenv("ORIGINALS_DIR", "originals")
    hash_algorithm = os.getenv("DEDUPLICATION_HASH_ALGORITHM", "md5")
    batch_size = int(os.getenv("DEDUPLICATION_BATCH_SIZE", "1000"))
    
    # Validate source directory
    if not os.path.exists(source_dir):
        log_step("deduplication", f"Source directory {source_dir} does not exist", "error")
        return
    
    # Run deduplication
    success = deduplicate_directory(
        source_dir=source_dir,
        hash_algorithm=hash_algorithm,
        batch_size=batch_size
    )
    
    if success:
        log_step("deduplication", "Deduplication completed successfully", "success")
    else:
        log_step("deduplication", "Deduplication failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
