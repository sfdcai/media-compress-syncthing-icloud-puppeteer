#!/usr/bin/env python3
"""
Verify Pixel Backup Gang installation and configuration
"""

import os
import json
import subprocess
from datetime import datetime

def check_module_installation():
    """Check if module is properly installed"""
    print("🔍 Checking Pixel Backup Gang installation...")
    
    module_dir = "/data/adb/modules/pixel_backup_gang"
    required_files = [
        "backup_manager.py",
        "backup_script.sh",
        "credentials.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(module_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def check_google_photos_backup():
    """Check Google Photos backup status"""
    print("\n📱 Checking Google Photos backup status...")
    
    try:
        # Check backup settings
        result = subprocess.run(['settings', 'get', 'global', 'backup_photos_enabled'], 
                              capture_output=True, text=True)
        backup_photos = result.stdout.strip()
        
        result = subprocess.run(['settings', 'get', 'global', 'backup_videos_enabled'], 
                              capture_output=True, text=True)
        backup_videos = result.stdout.strip()
        
        result = subprocess.run(['settings', 'get', 'global', 'auto_backup_enabled'], 
                              capture_output=True, text=True)
        auto_backup = result.stdout.strip()
        
        print(f"Backup Photos: {backup_photos}")
        print(f"Backup Videos: {backup_videos}")
        print(f"Auto Backup: {auto_backup}")
        
        if backup_photos == '1' and backup_videos == '1' and auto_backup == '1':
            print("✅ Google Photos backup is properly configured")
            return True
        else:
            print("⚠️  Google Photos backup needs configuration")
            return False
            
    except Exception as e:
        print(f"❌ Error checking backup status: {e}")
        return False

def check_network_connectivity():
    """Check network connectivity"""
    print("\n🌐 Checking network connectivity...")
    
    try:
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                              capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ Network connectivity OK")
            return True
        else:
            print("❌ No network connectivity")
            return False
    except Exception as e:
        print(f"❌ Network check failed: {e}")
        return False

def check_logs():
    """Check module logs"""
    print("\n📋 Checking logs...")
    
    log_dir = "/data/adb/modules/pixel_backup_gang/logs"
    if not os.path.exists(log_dir):
        print("❌ Log directory not found")
        return False
    
    log_files = [
        "backup.log",
        "backup_manager.log",
        "service.log"
    ]
    
    for log_file in log_files:
        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            print(f"✅ {log_file}: {size} bytes")
        else:
            print(f"⚠️  {log_file}: Not found")
    
    return True

def main():
    """Main verification function"""
    print("🔍 Pixel Backup Gang Verification")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    checks = [
        check_module_installation,
        check_google_photos_backup,
        check_network_connectivity,
        check_logs
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    print("📊 Verification Summary")
    print("=" * 40)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("✅ All checks passed! Pixel Backup Gang is ready.")
    else:
        print(f"⚠️  {passed}/{total} checks passed. Please fix the issues above.")
    
    print(f"\nFor detailed logs, check: /data/adb/modules/pixel_backup_gang/logs/")

if __name__ == "__main__":
    main()