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
try:  # Allow running as module or direct script
    from .utils import (
        log_step,
        get_feature_toggle,
        ensure_directory_exists,
        update_batch_status,
        get_files_by_status,
        retry,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (  # type: ignore
        log_step,
        get_feature_toggle,
        ensure_directory_exists,
        update_batch_status,
        get_files_by_status,
        retry,
    )

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".mpe",
    ".mp2",
    ".mpv",
    ".avi",
    ".mkv",
    ".webm",
}


def get_files_in_bridge(bridge_dir):
    """Get all video files in bridge directory (no numbered batch folders)"""
    if not os.path.exists(bridge_dir):
        return [], []

    video_files = []
    skipped_files = []

    for item in os.listdir(bridge_dir):
        item_path = os.path.join(bridge_dir, item)
        if not os.path.isfile(item_path):
            continue

        if Path(item_path).suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(item_path)
        else:
            skipped_files.append(item_path)

    video_files.sort()
    skipped_files.sort()
    return video_files, skipped_files

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
def upload_files_to_icloud(bridge_dir, interactive=False, inspect_upload=False):
    """Upload all files from bridge directory to iCloud using Puppeteer"""
    try:
        log_step("upload_icloud", f"Starting upload from {bridge_dir}", "info")
        
        # Build command
        cmd = ["node", "scripts/upload_icloud.js", "--dir", bridge_dir]
        
        if interactive:
            cmd.append("--interactive")

        if inspect_upload:
            cmd.append("--inspect-upload")
        
        # Run upload script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            log_step("upload_icloud", f"Successfully uploaded files from {bridge_dir}", "success")
            return True
        else:
            log_step("upload_icloud", f"Upload failed from {bridge_dir}: {result.stderr}", "error")
            return False
            
    except subprocess.TimeoutExpired:
        log_step("upload_icloud", f"Upload timeout for {bridge_dir}", "error")
        return False
    except Exception as e:
        log_step("upload_icloud", f"Error uploading from {bridge_dir}: {e}", "error")
        return False

def upload_to_icloud(bridge_dir, interactive=False, inspect_upload=False):
    """Upload all files from bridge directory to iCloud"""
    if not get_feature_toggle("ENABLE_ICLOUD_UPLOAD"):
        log_step("upload_icloud", "iCloud upload is disabled, skipping", "info")
        return True
    
    # Validate environment
    if not validate_node_environment():
        log_step("upload_icloud", "Node.js environment validation failed", "error")
        return False
    
    # Validate bridge directory
    if not os.path.exists(bridge_dir):
        log_step("upload_icloud", f"Bridge directory {bridge_dir} does not exist", "error")
        return False
    
    # Check if there are files to upload
    files, skipped = get_files_in_bridge(bridge_dir)

    if skipped:
        preview = ", ".join(Path(path).name for path in skipped[:5])
        log_step(
            "upload_icloud",
            f"Skipping {len(skipped)} non-video files in bridge directory: {preview}",
            "warning",
        )
    if not files:
        if inspect_upload:
            log_step(
                "upload_icloud",
                "Inspection mode active — no files required for selector diagnostics",
                "info",
            )
            return upload_files_to_icloud(bridge_dir, interactive, inspect_upload)

        log_step("upload_icloud", "No files found to upload", "info")
        return True

    log_step("upload_icloud", f"Found {len(files)} files to upload from {bridge_dir}", "info")
    
    # Upload all files
    if upload_files_to_icloud(bridge_dir, interactive, inspect_upload):
        if inspect_upload:
            log_step(
                "upload_icloud",
                "Selector diagnostics completed. Re-run without ICLOUD_INSPECT_UPLOAD to perform uploads.",
                "success",
            )
        else:
            log_step("upload_icloud", "iCloud upload completed successfully", "success")
        return True
    else:
        log_step("upload_icloud", "iCloud upload failed", "error")
        return False

def main():
    """Main iCloud upload function"""
    # Get configuration
    bridge_dir = os.getenv("BRIDGE_ICLOUD_DIR", "bridge/icloud")
    interactive = os.getenv("ICLOUD_INTERACTIVE", "false").lower() == "true"
    inspect_upload = os.getenv("ICLOUD_INSPECT_UPLOAD", "false").lower() == "true"
    
    # Run upload
    success = upload_to_icloud(bridge_dir, interactive, inspect_upload)
    
    if success:
        if inspect_upload:
            log_step(
                "upload_icloud",
                "iCloud upload diagnostics finished",
                "success",
            )
        else:
            log_step("upload_icloud", "iCloud upload completed successfully", "success")
    else:
        log_step("upload_icloud", "iCloud upload failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
