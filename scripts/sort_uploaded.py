#!/usr/bin/env python3
"""
Post-upload sorting script for media pipeline
Organizes uploaded files into yyyy/mm/dd structure after successful uploads
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
try:  # Support both module and standalone execution modes
    from .utils import (
        log_step,
        get_feature_toggle,
        ensure_directory_exists,
        get_file_size_gb,
        calculate_file_hash,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (  # type: ignore
        log_step,
        get_feature_toggle,
        ensure_directory_exists,
        get_file_size_gb,
        calculate_file_hash,
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

def get_date_from_exif(file_path):
    """Get date from EXIF metadata using exiftool"""
    try:
        # Try to get DateTimeOriginal first
        cmd = ["exiftool", "-DateTimeOriginal", "-d", "%Y-%m-%d", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            date_str = result.stdout.split(": ")[1].strip()
            if date_str and date_str != "0000:00:00":
                return date_str
        
        # Fallback to CreateDate
        cmd = ["exiftool", "-CreateDate", "-d", "%Y-%m-%d", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            date_str = result.stdout.split(": ")[1].strip()
            if date_str and date_str != "0000:00:00":
                return date_str
        
        # Fallback to ModifyDate
        cmd = ["exiftool", "-ModifyDate", "-d", "%Y-%m-%d", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            date_str = result.stdout.split(": ")[1].strip()
            if date_str and date_str != "0000:00:00":
                return date_str
        
        return None
        
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        log_step("sorting", f"Error getting EXIF date for {file_path}: {e}", "error")
        return None

def get_date_from_file_creation(file_path):
    """Get date from file creation time"""
    try:
        import time
        file_stat = os.stat(file_path)
        creation_time = file_stat.st_ctime
        date_str = time.strftime("%Y-%m-%d", time.localtime(creation_time))
        return date_str
    except Exception as e:
        log_step("sorting", f"Error getting file creation date for {file_path}: {e}", "error")
        return None

def get_file_date(file_path, use_exif=True, fallback_to_creation=True):
    """Get date for file sorting"""
    if use_exif:
        date_str = get_date_from_exif(file_path)
        if date_str:
            return date_str
    
    if fallback_to_creation:
        date_str = get_date_from_file_creation(file_path)
        if date_str:
            return date_str
    
    return None

def create_sorted_directory_structure(base_dir, date_str):
    """Create yyyy/mm/dd directory structure"""
    try:
        year, month, day = date_str.split("-")
        sorted_dir = os.path.join(base_dir, year, month, day)
        ensure_directory_exists(sorted_dir)
        return sorted_dir
    except Exception as e:
        log_step("sorting", f"Error creating directory structure for {date_str}: {e}", "error")
        return None

def move_file_to_sorted_location(file_path, sorted_dir, filename):
    """Move file to sorted location with conflict handling"""
    try:
        dest_path = os.path.join(sorted_dir, filename)
        
        # Handle filename conflicts
        counter = 1
        while os.path.exists(dest_path):
            name, ext = os.path.splitext(filename)
            dest_path = os.path.join(sorted_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        # Move file
        shutil.move(file_path, dest_path)
        log_step("sorting", f"Moved {filename} to {dest_path}", "success")
        return dest_path
        
    except Exception as e:
        log_step("sorting", f"Error moving {filename}: {e}", "error")
        return None

def sort_uploaded_files(source_dir, sorted_base_dir, use_exif=True, fallback_to_creation=True):
    """Sort uploaded files into yyyy/mm/dd structure"""
    if not os.path.exists(source_dir):
        log_step("sorting", f"Source directory {source_dir} does not exist", "error")
        return False
    
    # Create sorted base directory
    ensure_directory_exists(sorted_base_dir)
    
    log_step("sorting", f"Starting sorting of {source_dir}", "info")
    
    # Get all media files
    media_files = get_media_files(source_dir)
    
    if not media_files:
        log_step("sorting", "No media files found to sort", "info")
        return True
    
    log_step("sorting", f"Found {len(media_files)} files to sort", "info")
    
    # Sort files
    sorted_files = 0
    unknown_files = 0
    errors = 0
    
    for file_path in media_files:
        filename = os.path.basename(file_path)
        
        # Get file date
        date_str = get_file_date(file_path, use_exif, fallback_to_creation)
        
        if date_str:
            # Create sorted directory structure
            sorted_dir = create_sorted_directory_structure(sorted_base_dir, date_str)
            
            if sorted_dir:
                # Move file to sorted location
                dest_path = move_file_to_sorted_location(file_path, sorted_dir, filename)
                
                if dest_path:
                    sorted_files += 1
                else:
                    errors += 1
            else:
                errors += 1
        else:
            # Move to unknown directory
            unknown_dir = os.path.join(sorted_base_dir, "unknown")
            ensure_directory_exists(unknown_dir)
            
            dest_path = move_file_to_sorted_location(file_path, unknown_dir, filename)
            
            if dest_path:
                unknown_files += 1
                log_step("sorting", f"Moved {filename} to unknown directory (no date found)", "warning")
            else:
                errors += 1
    
    # Summary
    log_step("sorting", f"Sorting completed: {sorted_files} sorted, {unknown_files} unknown, {errors} errors", "success")
    return True

def sort_uploaded_directory(upload_type, source_dir, sorted_base_dir):
    """Sort uploaded files for a specific upload type"""
    if not os.path.exists(source_dir):
        log_step("sorting", f"Source directory {source_dir} does not exist for {upload_type}", "info")
        return True
    
    log_step("sorting", f"Sorting {upload_type} uploaded files", "info")
    
    # Get configuration
    use_exif = os.getenv("SORTING_USE_EXIF", "true").lower() == "true"
    fallback_to_creation = os.getenv("SORTING_FALLBACK_TO_CREATION_DATE", "true").lower() == "true"
    
    # Create sorted directory for this upload type
    sorted_dir = os.path.join(sorted_base_dir, upload_type)
    
    return sort_uploaded_files(source_dir, sorted_dir, use_exif, fallback_to_creation)

def main():
    """Main sorting function"""
    if not get_feature_toggle("ENABLE_SORTING"):
        log_step("sorting", "Sorting is disabled, skipping", "info")
        return
    
    # Get configuration
    uploaded_base_dir = os.getenv("UPLOADED_BASE_DIR", "uploaded")
    sorted_base_dir = os.getenv("SORTED_BASE_DIR", "sorted")
    
    # Check if exiftool is available
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
        log_step("sorting", "exiftool is available", "info")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_step("sorting", "exiftool not found, will use file creation dates only", "warning")
    
    success = True
    
    # Sort iCloud uploaded files
    icloud_source = os.path.join(uploaded_base_dir, "icloud")
    if not sort_uploaded_directory("icloud", icloud_source, sorted_base_dir):
        success = False
    
    # Sort Pixel uploaded files
    pixel_source = os.path.join(uploaded_base_dir, "pixel")
    if not sort_uploaded_directory("pixel", pixel_source, sorted_base_dir):
        success = False
    
    if success:
        log_step("sorting", "Sorting completed successfully", "success")
    else:
        log_step("sorting", "Sorting failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
