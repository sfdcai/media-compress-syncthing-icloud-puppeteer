#!/usr/bin/env python3
"""
Simple test to verify iCloud credentials and basic connectivity
"""

import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/settings.env")

def test_credentials():
    """Test iCloud credentials with a simple command"""
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_PASSWORD")
    
    print("=== iCloud Credentials Test ===")
    print(f"Username: {username}")
    print(f"Password: {'SET' if password else 'NOT SET'}")
    
    if not username or not password:
        print("ERROR: Missing credentials in config/settings.env")
        return False
    
    # Test with a simple icloudpd command that just checks authentication
    cmd = [
        "/opt/media-pipeline/venv/bin/icloudpd",
        "--username", username,
        "--password", password,
        "--list-albums"  # This just lists albums without downloading
    ]
    
    print(f"Testing command: {' '.join(cmd[:4])}...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✓ Authentication successful!")
            if result.stdout:
                print(f"Albums found: {len(result.stdout.splitlines())}")
            return True
        else:
            print("✗ Authentication failed!")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Command timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    test_credentials()
