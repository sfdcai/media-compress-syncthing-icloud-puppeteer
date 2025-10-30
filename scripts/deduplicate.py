#!/usr/bin/env python3
"""
Deduplication script for media pipeline
Removes duplicate files and tracks them in Supabase database
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import List, Tuple
try:  # Allow execution both as module and standalone script
    from .utils import (
        log_step,
        calculate_file_hash,
        get_file_size_gb,
        ensure_directory_exists,
        is_duplicate_file,
        log_duplicate_file,
        get_feature_toggle,
        retry,
        create_media_file_record,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (  # type: ignore
        log_step,
        calculate_file_hash,
        get_file_size_gb,
        ensure_directory_exists,
        is_duplicate_file,
        log_duplicate_file,
        get_feature_toggle,
        retry,
        create_media_file_record,
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
                source_type="deduplication",
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
        log_step(
            "deduplication",
            f"Source directory {source_dir} does not exist; skipping",
            "info",
        )
        return True
    
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


def _derive_label(path: Path, fallback_index: int) -> str:
    """Create a human-friendly label for a deduplication directory."""

    name = path.name.strip()
    if name:
        return name

    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", path.as_posix().strip("/"))
    if sanitized:
        return sanitized.strip("_")

    return f"custom_{fallback_index}"


def get_deduplication_targets() -> List[Tuple[str, str]]:
    """Return labeled directories that should run through deduplication."""

    targets: List[Tuple[str, str]] = []

    defaults = [
        ("originals", os.getenv("ORIGINALS_DIR", "originals")),
        ("uploaded_icloud", os.getenv("UPLOADED_ICLOUD_DIR")),
        ("uploaded_pixel", os.getenv("UPLOADED_PIXEL_DIR")),
    ]

    seen_paths = set()
    for label, directory in defaults:
        if not directory:
            continue
        normalized = str(Path(directory).expanduser())
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        targets.append((label, normalized))

    custom_paths = os.getenv("DEDUPLICATION_DIRECTORIES", "")
    if custom_paths:
        raw_entries = re.split(r"[\n,]", custom_paths)
        index = 1
        for entry in raw_entries:
            directory = entry.strip()
            if not directory:
                continue
            normalized = str(Path(directory).expanduser())
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)
            label = _derive_label(Path(normalized), index)
            targets.append((label, normalized))
            index += 1

    return targets

def main():
    """Main deduplication function"""
    if not get_feature_toggle("ENABLE_DEDUPLICATION"):
        log_step("deduplication", "Deduplication is disabled, skipping", "info")
        return

    # Get configuration
    hash_algorithm = os.getenv("DEDUPLICATION_HASH_ALGORITHM", "md5")
    batch_size = int(os.getenv("DEDUPLICATION_BATCH_SIZE", "1000"))

    targets = get_deduplication_targets()
    if not targets:
        log_step(
            "deduplication",
            "No directories configured for deduplication; nothing to do",
            "warning",
        )
        return

    overall_success = True
    for label, directory in targets:
        log_step(
            "deduplication",
            f"Processing {label} directory: {directory}",
            "info",
        )
        success = deduplicate_directory(
            source_dir=directory,
            hash_algorithm=hash_algorithm,
            batch_size=batch_size,
        )
        if success:
            log_step(
                "deduplication",
                f"Successfully deduplicated {label} directory",
                "success",
            )
        else:
            log_step(
                "deduplication",
                f"Failed to deduplicate {label} directory",
                "error",
            )
            overall_success = False

    if overall_success:
        log_step("deduplication", "Deduplication completed successfully", "success")
    else:
        log_step("deduplication", "Deduplication encountered errors", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
