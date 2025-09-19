#!/usr/bin/env python3
"""
Move iCloud downloaded files from root folder to originals folder
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from utils import log_step

# Load environment variables
load_dotenv("config/settings.env")

def move_files_to_originals():
    """Move files from root folder to originals folder"""
    
    # Get directory paths
    nas_mount = os.getenv("NAS_MOUNT", "/mnt/wd_all_pictures/sync")
    originals_dir = os.getenv("ORIGINALS_DIR", os.path.join(nas_mount, "originals"))
    
    print(f"Source directory: {nas_mount}")
    print(f"Target directory: {originals_dir}")
    
    # Ensure originals directory exists
    os.makedirs(originals_dir, exist_ok=True)
    
    # Media file extensions
    media_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv'}
    
    moved_count = 0
    error_count = 0
    
    # Find media files in root directory
    for root, dirs, files in os.walk(nas_mount):
        # Skip if we're already in a subdirectory (like originals, compressed, etc.)
        if root != nas_mount:
            continue
            
        for filename in files:
            file_path = os.path.join(root, filename)
            file_ext = Path(filename).suffix.lower()
            
            if file_ext in media_extensions:
                target_path = os.path.join(originals_dir, filename)
                
                try:
                    # Check if target file already exists
                    if os.path.exists(target_path):
                        # Create unique filename
                        base_name = Path(filename).stem
                        counter = 1
                        while os.path.exists(target_path):
                            new_filename = f"{base_name}_{counter}{file_ext}"
                            target_path = os.path.join(originals_dir, new_filename)
                            counter += 1
                    
                    # Move file
                    shutil.move(file_path, target_path)
                    print(f"Moved: {filename} -> {os.path.basename(target_path)}")
                    moved_count += 1
                    
                except Exception as e:
                    print(f"Error moving {filename}: {e}")
                    error_count += 1
    
    print(f"\n=== Move Summary ===")
    print(f"Files moved: {moved_count}")
    print(f"Errors: {error_count}")
    
    if moved_count > 0:
        log_step("file_organization", f"Moved {moved_count} files to originals directory", "success")
    
    if error_count > 0:
        log_step("file_organization", f"Encountered {error_count} errors during file move", "warning")
    
    return moved_count > 0

if __name__ == "__main__":
    print("=== Moving iCloud Files to Originals Directory ===")
    move_files_to_originals()
