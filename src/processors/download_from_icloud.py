#!/usr/bin/env python3
"""
Enhanced iCloud download script for media pipeline
Handles authentication, error reporting, and directory setup
"""

import os
import sys
import subprocess
from pathlib import Path
from utils.utils import log_step, ensure_directory_exists, create_media_file_record, create_batch_record, update_batch_status, calculate_file_hash

def check_icloudpd_installed():
    """Check if icloudpd is installed and accessible"""
    # Check virtual environment first
    venv_icloudpd = "/opt/media-pipeline/venv/bin/icloudpd"
    if os.path.exists(venv_icloudpd):
        log_step("download_from_icloud", f"icloudpd found in venv: {venv_icloudpd}", "info")
        return True
    
    # Fallback to system PATH
    try:
        result = subprocess.run(["which", "icloudpd"], capture_output=True, text=True)
        if result.returncode == 0:
            log_step("download_from_icloud", f"icloudpd found at: {result.stdout.strip()}", "info")
            return True
        else:
            log_step("download_from_icloud", "icloudpd not found in PATH", "error")
            return False
    except Exception as e:
        log_step("download_from_icloud", f"Error checking icloudpd: {e}", "error")
        return False

def validate_config():
    """Validate required configuration"""
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_PASSWORD")
    
    # Use ORIGINALS_DIR if set, otherwise fall back to NAS_MOUNT/originals
    originals_dir = os.getenv("ORIGINALS_DIR")
    if not originals_dir:
        nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline")
        originals_dir = os.path.join(nas_mount, "originals")
    
    print(f"  Username: {username}")
    print(f"  Password: {'SET' if password else 'NOT SET'}")
    print(f"  Target directory: {originals_dir}")
    
    if not username:
        print("  ERROR: ICLOUD_USERNAME not set in environment")
        log_step("download_from_icloud", "ICLOUD_USERNAME not set in environment", "error")
        return False
    
    if not password:
        print("  ERROR: ICLOUD_PASSWORD not set in environment")
        log_step("download_from_icloud", "ICLOUD_PASSWORD not set in environment", "error")
        return False
    
    log_step("download_from_icloud", f"Using username: {username}", "info")
    log_step("download_from_icloud", f"Target directory: {originals_dir}", "info")
    
    return True

def setup_download_directory():
    """Ensure download directory exists"""
    # Use ORIGINALS_DIR if set, otherwise fall back to NAS_MOUNT/originals
    originals_dir = os.getenv("ORIGINALS_DIR")
    if not originals_dir:
        nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline")
        originals_dir = os.path.join(nas_mount, "originals")
    
    try:
        ensure_directory_exists(originals_dir)
        log_step("download_from_icloud", f"Download directory ready: {originals_dir}", "success")
        return True
    except Exception as e:
        log_step("download_from_icloud", f"Failed to setup directory {originals_dir}: {e}", "error")
        return False

def run_icloud_download():
    """Run the actual iCloud download with proper error handling"""
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_PASSWORD")
    
    # Use ORIGINALS_DIR if set, otherwise fall back to NAS_MOUNT/originals
    originals_dir = os.getenv("ORIGINALS_DIR")
    if not originals_dir:
        nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline")
        originals_dir = os.path.join(nas_mount, "originals")
    
    # Use virtual environment icloudpd
    icloudpd_path = "/opt/media-pipeline/venv/bin/icloudpd"
    
    # Build command with all necessary parameters
    cmd = [
        icloudpd_path,
        "--directory", originals_dir,
        "--username", username,
        "--password", password,
        "--size", "original",  # Download original quality
        "--recent", "1000",    # Download recent 1000 photos
        "--file-match-policy", "name-size-dedup-with-suffix",  # Proper duplicate detection
        "--no-progress-bar",   # Disable progress bar for logging
        "--log-level", "info"  # Set log level
    ]
    
    log_step("download_from_icloud", f"Running command: {' '.join(cmd[:6])}...", "info")
    
    try:
        # Run icloudpd directly (without 2FA wrapper for now)
        log_step("download_from_icloud", f"Running icloudpd directly: {' '.join(cmd[:6])}...", "info")
        
        # Run with timeout and capture output
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=3600,  # 1 hour timeout
            check=True
        )
        
        # Log successful output
        if result.stdout:
            log_step("download_from_icloud", f"Download output: {result.stdout[:500]}", "info")
        
        log_step("download_from_icloud", "iCloud download completed successfully", "success")
        return True
        
    except subprocess.TimeoutExpired:
        log_step("download_from_icloud", "Download timed out after 1 hour", "error")
        return False
    except subprocess.CalledProcessError as e:
        log_step("download_from_icloud", f"Download failed with return code {e.returncode}", "error")
        if e.stdout:
            log_step("download_from_icloud", f"STDOUT: {e.stdout}", "error")
        if e.stderr:
            log_step("download_from_icloud", f"STDERR: {e.stderr}", "error")
        return False
    except Exception as e:
        log_step("download_from_icloud", f"Unexpected error during download: {e}", "error")
        return False

def track_downloaded_files_in_database(originals_dir, batch_id=None):
    """Track downloaded files in the database"""
    try:
        if not os.path.exists(originals_dir):
            log_step("download_from_icloud", f"Download directory {originals_dir} does not exist", "error")
            return 0
        
        # Find all media files in directory (excluding duplicates subdirectory)
        media_files = []
        for root, dirs, filenames in os.walk(originals_dir):
            # Skip duplicates directory
            if 'duplicates' in dirs:
                dirs.remove('duplicates')
            
            for filename in filenames:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi')):
                    file_path = os.path.join(root, filename)
                    media_files.append(file_path)
        
        if not media_files:
            log_step("download_from_icloud", "No media files found to track", "warning")
            return 0
        
        # Create batch record if not provided
        if not batch_id:
            batch_id = create_batch_record(
                source_type="icloud",
                file_count=len(media_files),
                total_size=sum(os.path.getsize(f) for f in media_files if os.path.exists(f))
            )
        
        # Track each file in database
        tracked_count = 0
        for file_path in media_files:
            try:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                file_id = create_media_file_record(
                    file_path=file_path,
                    file_size=file_size,
                    source_type="icloud",
                    batch_id=batch_id
                )
                if file_id:
                    tracked_count += 1
            except Exception as e:
                log_step("download_from_icloud", f"Failed to track file {file_path}: {e}", "error")
        
        log_step("download_from_icloud", f"Tracked {tracked_count}/{len(media_files)} files in database", "success")
        return tracked_count
        
    except Exception as e:
        log_step("download_from_icloud", f"Error tracking files in database: {e}", "error")
        return 0

def check_download_results():
    """Check if any files were downloaded and track them in database"""
    # Use ORIGINALS_DIR if set, otherwise fall back to NAS_MOUNT/originals
    originals_dir = os.getenv("ORIGINALS_DIR")
    if not originals_dir:
        nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline")
        originals_dir = os.path.join(nas_mount, "originals")
    
    try:
        if not os.path.exists(originals_dir):
            log_step("download_from_icloud", f"Download directory {originals_dir} does not exist", "error")
            return False
        
        # Count files in directory
        files = []
        for root, dirs, filenames in os.walk(originals_dir):
            for filename in filenames:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi')):
                    files.append(os.path.join(root, filename))
        
        if files:
            log_step("download_from_icloud", f"Downloaded {len(files)} media files to {originals_dir}", "success")
            
            # Track files in database
            tracked_count = track_downloaded_files_in_database(originals_dir)
            
            if tracked_count > 0:
                log_step("download_from_icloud", f"Successfully tracked {tracked_count} files in database", "success")
                return True
            else:
                log_step("download_from_icloud", "Files downloaded but database tracking failed", "warning")
                return False
        else:
            log_step("download_from_icloud", "No media files found after download", "warning")
            return False
            
    except Exception as e:
        log_step("download_from_icloud", f"Error checking download results: {e}", "error")
        return False

def main():
    """Main download function with comprehensive error handling"""
    print("=== iCloud Download Script Starting ===")
    log_step("download_from_icloud", "Starting iCloud download process", "info")
    
    # Step 1: Check if icloudpd is installed
    print("Step 1: Checking icloudpd installation...")
    if not check_icloudpd_installed():
        print("ERROR: icloudpd not found!")
        log_step("download_from_icloud", "Please install icloudpd: pip install icloudpd", "error")
        sys.exit(1)
    print("✓ icloudpd found")
    
    # Step 2: Validate configuration
    print("Step 2: Validating configuration...")
    if not validate_config():
        print("ERROR: Configuration validation failed!")
        log_step("download_from_icloud", "Configuration validation failed", "error")
        sys.exit(1)
    print("✓ Configuration valid")
    
    # Step 3: Setup download directory
    print("Step 3: Setting up download directory...")
    if not setup_download_directory():
        print("ERROR: Directory setup failed!")
        log_step("download_from_icloud", "Directory setup failed", "error")
        sys.exit(1)
    print("✓ Download directory ready")
    
    # Step 4: Run download
    print("Step 4: Running iCloud download...")
    if not run_icloud_download():
        print("ERROR: Download process failed!")
        log_step("download_from_icloud", "Download process failed", "error")
        sys.exit(1)
    print("✓ Download completed")
    
    # Step 5: Verify results
    print("Step 5: Verifying download results...")
    if not check_download_results():
        print("WARNING: No files were downloaded!")
        log_step("download_from_icloud", "No files were downloaded - check credentials and iCloud account", "warning")
        sys.exit(1)
    print("✓ Files verified")
    
    print("=== iCloud Download Script Completed Successfully ===")
    log_step("download_from_icloud", "iCloud download process completed successfully", "success")
    return True

if __name__ == "__main__":
    main()
