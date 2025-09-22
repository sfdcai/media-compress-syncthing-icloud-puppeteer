#!/usr/bin/env python3
"""
Simple version of prepare_pixel_sync that doesn't require Supabase
Use this to test file operations without database dependency
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/settings.env")

def get_files_from_directory(originals_dir, max_files=None):
    """Get media files from directory (without database)"""
    try:
        if not os.path.exists(originals_dir):
            print(f"ERROR: Directory {originals_dir} does not exist")
            return []
        
        # Find media files
        media_files = []
        for root, dirs, filenames in os.walk(originals_dir):
            for filename in filenames:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi')):
                    file_path = os.path.join(root, filename)
                    file_size = os.path.getsize(file_path)
                    media_files.append({
                        'filename': filename,
                        'file_path': file_path,
                        'file_size': file_size
                    })
        
        # Sort by filename
        media_files.sort(key=lambda x: x['filename'])
        
        # Limit number of files
        if max_files and len(media_files) > max_files:
            media_files = media_files[:max_files]
        
        print(f"Found {len(media_files)} media files in {originals_dir}")
        return media_files
        
    except Exception as e:
        print(f"ERROR getting files: {e}")
        return []

def copy_files_to_bridge(files, bridge_dir):
    """Copy files to bridge directory"""
    try:
        # Ensure bridge directory exists
        os.makedirs(bridge_dir, exist_ok=True)
        
        copied_files = []
        total_size_gb = 0
        
        for file_info in files:
            file_path = file_info['file_path']
            filename = file_info['filename']
            
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
                
                file_size_gb = file_info['file_size'] / (1024**3)
                total_size_gb += file_size_gb
                copied_files.append({
                    'filename': filename,
                    'source_path': file_path,
                    'dest_path': dest_path,
                    'file_size_gb': file_size_gb
                })
                
                print(f"Copied: {filename} ({file_size_gb:.2f} GB)")
                
            except Exception as e:
                print(f"ERROR copying {filename}: {e}")
                continue
        
        print(f"\nCopied {len(copied_files)} files to {bridge_dir}")
        print(f"Total size: {total_size_gb:.2f} GB")
        return copied_files
        
    except Exception as e:
        print(f"ERROR copying files: {e}")
        return []

def prepare_pixel_sync_simple():
    """Simple version without database dependency"""
    print("=== Simple Pixel Sync Preparation (No Database) ===")
    
    # Get configuration
    originals_dir = os.getenv("ORIGINALS_DIR", "/mnt/wd_all_pictures/sync/originals")
    bridge_dir = os.getenv("BRIDGE_PIXEL_DIR", "/mnt/wd_all_pictures/sync/bridge/pixel")
    max_files = int(os.getenv("MAX_PROCESSING_FILES", "50"))
    
    print(f"Originals directory: {originals_dir}")
    print(f"Bridge directory: {bridge_dir}")
    print(f"Max files to process: {max_files}")
    
    # Step 1: Get files from directory
    print(f"\nStep 1: Getting files from {originals_dir}...")
    files = get_files_from_directory(originals_dir, max_files)
    
    if not files:
        print("No files found to process")
        return False
    
    print(f"✓ Found {len(files)} files to process")
    
    # Step 2: Copy files to bridge
    print(f"\nStep 2: Copying files to {bridge_dir}...")
    copied_files = copy_files_to_bridge(files, bridge_dir)
    
    if not copied_files:
        print("No files were copied")
        return False
    
    print(f"✓ Successfully copied {len(copied_files)} files")
    
    # Step 3: Summary
    print(f"\n=== Summary ===")
    print(f"Files processed: {len(copied_files)}")
    print(f"Source directory: {originals_dir}")
    print(f"Destination directory: {bridge_dir}")
    
    return True

def main():
    """Main function"""
    try:
        success = prepare_pixel_sync_simple()
        
        if success:
            print("\n✓ Simple Pixel sync preparation completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Simple Pixel sync preparation failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
