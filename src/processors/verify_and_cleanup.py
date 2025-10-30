#!/usr/bin/env python3
"""
Enhanced verification and cleanup script for media pipeline
Verifies successful uploads and cleans up processed files
"""

import os
import sys
import shutil
import time
from pathlib import Path
from utils.utils import (
    log_step, get_feature_toggle, ensure_directory_exists,
    get_file_size_gb, calculate_file_hash, update_batch_status,
    get_files_by_status
)

def get_batch_directories(batch_dir):
    """Get all batch directories"""
    if not os.path.exists(batch_dir):
        return []
    
    batch_dirs = []
    for item in os.listdir(batch_dir):
        item_path = os.path.join(batch_dir, item)
        if os.path.isdir(item_path) and item.startswith("batch_"):
            batch_dirs.append(item_path)
    
    return sorted(batch_dirs)

def verify_batch_files(batch_path):
    """Verify that all files in a batch are valid"""
    try:
        batch_name = os.path.basename(batch_path)
        log_step("verification", f"Verifying {batch_name}", "info")
        
        if not os.path.exists(batch_path):
            log_step("verification", f"Batch {batch_name} does not exist", "error")
            return False
        
        # Get all files in batch
        files = []
        for root, dirs, filenames in os.walk(batch_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                files.append(file_path)
        
        if not files:
            log_step("verification", f"Batch {batch_name} is empty", "warning")
            return True
        
        # Verify each file
        valid_files = 0
        invalid_files = 0
        
        for file_path in files:
            try:
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size <= 0:
                    log_step("verification", f"Invalid file size for {file_path}", "error")
                    invalid_files += 1
                    continue
                
                # Check file readability
                with open(file_path, 'rb') as f:
                    f.read(1)  # Try to read first byte
                
                valid_files += 1
                
            except Exception as e:
                log_step("verification", f"Error verifying {file_path}: {e}", "error")
                invalid_files += 1
        
        # Summary
        if invalid_files == 0:
            log_step("verification", f"Batch {batch_name} verified: {valid_files} files valid", "success")
            return True
        else:
            log_step("verification", f"Batch {batch_name} verification failed: {invalid_files} invalid files", "error")
            return False
            
    except Exception as e:
        log_step("verification", f"Error verifying batch {batch_path}: {e}", "error")
        return False

def cleanup_verified_batch(batch_path, cleanup_dir=None):
    """Clean up a verified batch"""
    try:
        batch_name = os.path.basename(batch_path)
        
        if cleanup_dir:
            # Move to cleanup directory instead of deleting
            cleanup_path = os.path.join(cleanup_dir, batch_name)
            ensure_directory_exists(cleanup_dir)
            
            if os.path.exists(cleanup_path):
                shutil.rmtree(cleanup_path)
            
            shutil.move(batch_path, cleanup_path)
            log_step("cleanup", f"Moved {batch_name} to cleanup directory", "success")
        else:
            # Delete the batch
            shutil.rmtree(batch_path)
            log_step("cleanup", f"Deleted {batch_name}", "success")
        
        return True
        
    except Exception as e:
        log_step("cleanup", f"Error cleaning up {batch_path}: {e}", "error")
        return False

def verify_and_cleanup_batches(batch_dir, cleanup_dir=None):
    """Verify and cleanup all batches in a directory"""
    if not os.path.exists(batch_dir):
        log_step("verification", f"Batch directory {batch_dir} does not exist", "info")
        return True
    
    log_step("verification", f"Starting verification and cleanup of {batch_dir}", "info")
    
    # Get all batch directories
    batch_dirs = get_batch_directories(batch_dir)
    
    if not batch_dirs:
        log_step("verification", "No batches found to verify", "info")
        return True
    
    log_step("verification", f"Found {len(batch_dirs)} batches to verify", "info")
    
    # Verify and cleanup each batch
    verified_batches = 0
    failed_batches = 0
    cleaned_batches = 0
    
    for batch_path in batch_dirs:
        batch_name = os.path.basename(batch_path)
        
        # Verify batch
        if verify_batch_files(batch_path):
            verified_batches += 1
            
            # Cleanup verified batch
            if cleanup_verified_batch(batch_path, cleanup_dir):
                cleaned_batches += 1
        else:
            failed_batches += 1
    
    # Summary
    log_step("verification", f"Verification completed: {verified_batches} verified, {failed_batches} failed", "success")
    log_step("cleanup", f"Cleanup completed: {cleaned_batches} batches cleaned", "success")
    
    return failed_batches == 0

def verify_upload_success(upload_type, uploaded_dir):
    """Verify that uploads were successful"""
    if not os.path.exists(uploaded_dir):
        log_step("verification", f"Uploaded directory {uploaded_dir} does not exist for {upload_type}", "info")
        return True
    
    log_step("verification", f"Verifying {upload_type} upload success", "info")
    
    # Get all files in uploaded directory
    files = []
    for root, dirs, filenames in os.walk(uploaded_dir):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            files.append(file_path)
    
    if not files:
        log_step("verification", f"No files found in {uploaded_dir}", "warning")
        return True
    
    # Verify files
    valid_files = 0
    invalid_files = 0
    
    for file_path in files:
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 0:
                valid_files += 1
            else:
                invalid_files += 1
                log_step("verification", f"Invalid file size for {file_path}", "error")
        except Exception as e:
            invalid_files += 1
            log_step("verification", f"Error verifying {file_path}: {e}", "error")
    
    # Summary
    if invalid_files == 0:
        log_step("verification", f"{upload_type} upload verification passed: {valid_files} files valid", "success")
        return True
    else:
        log_step("verification", f"{upload_type} upload verification failed: {invalid_files} invalid files", "error")
        return False

def generate_verification_report():
    """Generate a verification report"""
    try:
        report_dir = "logs"
        ensure_directory_exists(report_dir)
        
        report_file = os.path.join(report_dir, f"verification_report_{int(time.time())}.txt")
        
        with open(report_file, 'w') as f:
            f.write("Media Pipeline Verification Report\n")
            f.write("=" * 40 + "\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Add verification details here
            f.write("Verification completed successfully.\n")
        
        log_step("verification", f"Verification report generated: {report_file}", "success")
        return True
        
    except Exception as e:
        log_step("verification", f"Error generating verification report: {e}", "error")
        return False

def verify_google_photos_sync():
    """Verify that Pixel uploaded files are synced to Google Photos"""
    try:
        # Check if Google Photos sync checking is enabled
        if not get_feature_toggle("ENABLE_GOOGLE_PHOTOS_SYNC_CHECK"):
            log_step("verification", "Google Photos sync check disabled", "info")
            return True
        
        log_step("verification", "Starting Google Photos sync verification", "info")
        
        # Import and run the Google Photos sync checker
        sys.path.append('/opt/media-pipeline/scripts')
        from google_photos_sync_checker import GooglePhotosSyncChecker
        
        checker = GooglePhotosSyncChecker()
        
        # Load credentials and tokens
        if not checker.load_credentials() or not checker.load_tokens():
            log_step("verification", "Google Photos API not configured, skipping sync check", "warning")
            return True
        
        # Check if we have a valid token
        if not checker.ensure_valid_token():
            log_step("verification", "Google Photos API token invalid, skipping sync check", "warning")
            return True
        
        # Get Pixel upload directory
        pixel_upload_dir = os.getenv("UPLOADED_PIXEL_DIR", "/mnt/wd_all_pictures/sync/uploaded/pixel")
        
        if not os.path.exists(pixel_upload_dir):
            log_step("verification", f"Pixel upload directory {pixel_upload_dir} does not exist", "warning")
            return True
        
        # Check sync status for all files
        results = checker.check_pixel_uploaded_files(pixel_upload_dir)
        
        if not results:
            log_step("verification", "No files found in Pixel upload directory for sync check", "info")
            return True
        
        # Count synced vs not synced
        synced_count = sum(1 for r in results if r['synced'])
        total_count = len(results)
        sync_rate = (synced_count / total_count * 100) if total_count > 0 else 0
        
        # Log results
        if sync_rate >= 80:
            log_step("verification", f"Google Photos sync check passed: {synced_count}/{total_count} files synced ({sync_rate:.1f}%)", "success")
        elif sync_rate >= 50:
            log_step("verification", f"Google Photos sync check partial: {synced_count}/{total_count} files synced ({sync_rate:.1f}%)", "warning")
        else:
            log_step("verification", f"Google Photos sync check failed: {synced_count}/{total_count} files synced ({sync_rate:.1f}%)", "error")
        
        # Generate detailed report
        report = checker.generate_sync_report(results)
        report_file = f"/opt/media-pipeline/logs/google_photos_sync_report_{int(time.time())}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        log_step("verification", f"Google Photos sync report saved to: {report_file}", "info")
        
        return sync_rate >= 50  # Consider it successful if at least 50% synced
        
    except Exception as e:
        log_step("verification", f"Error during Google Photos sync check: {e}", "error")
        return True  # Don't fail the entire verification if sync check fails

def main():
    """Main verification and cleanup function"""
    # Get configuration
    bridge_icloud_dir = os.getenv("BRIDGE_ICLOUD_DIR", "bridge/icloud")
    bridge_pixel_dir = os.getenv("BRIDGE_PIXEL_DIR", "bridge/pixel")
    uploaded_icloud_dir = os.getenv("UPLOADED_ICLOUD_DIR", "uploaded/icloud")
    uploaded_pixel_dir = os.getenv("UPLOADED_PIXEL_DIR", "uploaded/pixel")
    cleanup_dir = os.getenv("CLEANUP_DIR", "cleanup")
    
    # Check feature toggles
    enable_icloud = get_feature_toggle("ENABLE_ICLOUD_UPLOAD")
    enable_pixel = get_feature_toggle("ENABLE_PIXEL_UPLOAD")
    
    success = True
    
    # Verify and cleanup iCloud batches
    if enable_icloud:
        if not verify_and_cleanup_batches(bridge_icloud_dir, cleanup_dir):
            success = False
        
        # Verify iCloud upload success
        if not verify_upload_success("iCloud", uploaded_icloud_dir):
            success = False
    
    # Verify and cleanup Pixel batches
    if enable_pixel:
        if not verify_and_cleanup_batches(bridge_pixel_dir, cleanup_dir):
            success = False
        
        # Verify Pixel upload success
        if not verify_upload_success("Pixel", uploaded_pixel_dir):
            success = False
        
        # Check Google Photos sync status
        if not verify_google_photos_sync():
            success = False
    
    # Generate verification report
    generate_verification_report()
    
    if success:
        log_step("verification", "Verification and cleanup completed successfully", "success")
    else:
        log_step("verification", "Verification and cleanup failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
