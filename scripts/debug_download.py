#!/usr/bin/env python3
"""
Debug script to test iCloud download configuration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/settings.env")

def debug_config():
    """Debug configuration and environment"""
    print("=== Configuration Debug ===")
    print(f"ICLOUD_USERNAME: {os.getenv('ICLOUD_USERNAME')}")
    print(f"ICLOUD_PASSWORD: {'SET' if os.getenv('ICLOUD_PASSWORD') else 'NOT SET'}")
    print(f"NAS_MOUNT: {os.getenv('NAS_MOUNT')}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.executable}")
    
    # Check if directories exist
    nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline/originals")
    print(f"Target directory exists: {os.path.exists(nas_mount)}")
    if os.path.exists(nas_mount):
        print(f"Target directory contents: {os.listdir(nas_mount)}")
    
    print("\n=== Testing icloudpd ===")
    import subprocess
    try:
        result = subprocess.run(["which", "icloudpd"], capture_output=True, text=True)
        print(f"icloudpd location: {result.stdout.strip()}")
        
        # Test icloudpd help
        result = subprocess.run(["/opt/media-pipeline/venv/bin/icloudpd", "--help"], 
                              capture_output=True, text=True, timeout=10)
        print(f"icloudpd help return code: {result.returncode}")
        if result.stderr:
            print(f"icloudpd stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"Error testing icloudpd: {e}")

def test_manual_download():
    """Test manual download with verbose output"""
    print("\n=== Manual Download Test ===")
    
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_PASSWORD")
    nas_mount = os.getenv("NAS_MOUNT", "/opt/media-pipeline/originals")
    
    if not username or not password:
        print("ERROR: Missing credentials")
        return
    
    # Create test directory
    os.makedirs(nas_mount, exist_ok=True)
    
    # Test command
    cmd = [
        "/opt/media-pipeline/venv/bin/icloudpd",
        "--directory", nas_mount,
        "--username", username,
        "--password", password,
        "--size", "original",
        "--recent", "5",  # Just download 5 recent photos for testing
        "--log-level", "debug",
        "--no-progress-bar"
    ]
    
    print(f"Running command: {' '.join(cmd[:6])}...")
    
    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        # Check results
        files = []
        for root, dirs, filenames in os.walk(nas_mount):
            for filename in filenames:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov')):
                    files.append(filename)
        
        print(f"Files downloaded: {len(files)}")
        if files:
            print(f"Sample files: {files[:3]}")
            
    except subprocess.TimeoutExpired:
        print("Download timed out")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_config()
    test_manual_download()
