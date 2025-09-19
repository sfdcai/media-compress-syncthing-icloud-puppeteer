#!/usr/bin/env python3
"""
Python wrapper for iCloud upload via Puppeteer
Manages the Node.js upload script with proper error handling and logging
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from utils import (
    log_step, get_feature_toggle, ensure_directory_exists,
    update_batch_status, get_files_by_status, retry
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

def validate_node_environment():
    """Validate Node.js environment and dependencies"""
    try:
        # Check if Node.js is available
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
        log_step("upload_icloud", f"Node.js version: {result.stdout.strip()}", "info")
        
        # Check if upload script exists
        script_path = "scripts/upload_icloud.js"
        if not os.path.exists(script_path):
            log_step("upload_icloud", f"Upload script {script_path} not found", "error")
            return False
        
        # Check if puppeteer is installed
        try:
            subprocess.run(["node", "-e", "require('puppeteer')"], capture_output=True, check=True)
            log_step("upload_icloud", "Puppeteer is available", "info")
        except subprocess.CalledProcessError:
            log_step("upload_icloud", "Puppeteer not installed, installing...", "info")
            subprocess.run(["npm", "install", "puppeteer"], check=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        log_step("upload_icloud", f"Node.js validation failed: {e}", "error")
        return False
    except Exception as e:
        log_step("upload_icloud", f"Environment validation error: {e}", "error")
        return False

@retry(max_attempts=3, delay=30)
def upload_batch_to_icloud(batch_path, interactive=False):
    """Upload a single batch to iCloud using Puppeteer"""
    try:
        batch_name = os.path.basename(batch_path)
        log_step("upload_icloud", f"Starting upload for {batch_name}", "info")
        
        # Build command
        cmd = ["node", "scripts/upload_icloud.js", "--dir", batch_path]
        
        if interactive:
            cmd.append("--interactive")
        
        # Run upload script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            log_step("upload_icloud", f"Successfully uploaded {batch_name}", "success")
            return True
        else:
            log_step("upload_icloud", f"Upload failed for {batch_name}: {result.stderr}", "error")
            return False
            
    except subprocess.TimeoutExpired:
        log_step("upload_icloud", f"Upload timeout for {batch_name}", "error")
        return False
    except Exception as e:
        log_step("upload_icloud", f"Error uploading {batch_path}: {e}", "error")
        return False

def upload_to_icloud(batch_dir, interactive=False):
    """Upload all batches to iCloud"""
    if not get_feature_toggle("ENABLE_ICLOUD_UPLOAD"):
        log_step("upload_icloud", "iCloud upload is disabled, skipping", "info")
        return True
    
    # Validate environment
    if not validate_node_environment():
        log_step("upload_icloud", "Node.js environment validation failed", "error")
        return False
    
    # Validate batch directory
    if not os.path.exists(batch_dir):
        log_step("upload_icloud", f"Batch directory {batch_dir} does not exist", "error")
        return False
    
    log_step("upload_icloud", f"Starting iCloud upload from {batch_dir}", "info")
    
    # Get all batch directories
    batch_dirs = get_batch_directories(batch_dir)
    
    if not batch_dirs:
        log_step("upload_icloud", "No batches found to upload", "info")
        return True
    
    log_step("upload_icloud", f"Found {len(batch_dirs)} batches to upload", "info")
    
    # Upload each batch
    successful_uploads = 0
    failed_uploads = 0
    
    for batch_path in batch_dirs:
        batch_name = os.path.basename(batch_path)
        log_step("upload_icloud", f"Uploading {batch_name}", "info")
        
        if upload_batch_to_icloud(batch_path, interactive):
            successful_uploads += 1
            
            # Update batch status in database
            # Note: This would need batch_id from the database
            # For now, we'll just log the success
            
        else:
            failed_uploads += 1
    
    # Summary
    log_step("upload_icloud", f"iCloud upload completed: {successful_uploads} successful, {failed_uploads} failed", "success")
    return failed_uploads == 0

def main():
    """Main iCloud upload function"""
    # Get configuration
    batch_dir = os.getenv("BRIDGE_ICLOUD_DIR", "bridge/icloud")
    interactive = os.getenv("ICLOUD_INTERACTIVE", "false").lower() == "true"
    
    # Run upload
    success = upload_to_icloud(batch_dir, interactive)
    
    if success:
        log_step("upload_icloud", "iCloud upload completed successfully", "success")
    else:
        log_step("upload_icloud", "iCloud upload failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
