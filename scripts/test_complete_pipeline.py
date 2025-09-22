#!/usr/bin/env python3
"""
Complete Pipeline Test Script
Tests all components of the media pipeline in sequence
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(f"Output: {result.stdout[:200]}...")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def check_file_exists(file_path, description):
    """Check if a file exists"""
    if os.path.exists(file_path):
        print(f"✅ {description} - File exists: {file_path}")
        return True
    else:
        print(f"❌ {description} - File missing: {file_path}")
        return False

def check_directory_contents(dir_path, description):
    """Check directory contents"""
    if os.path.exists(dir_path):
        files = os.listdir(dir_path)
        print(f"✅ {description} - Directory exists with {len(files)} items: {dir_path}")
        if files:
            print(f"   Sample files: {files[:3]}")
        return True
    else:
        print(f"❌ {description} - Directory missing: {dir_path}")
        return False

def test_system_requirements():
    """Test system requirements"""
    print("\n" + "="*60)
    print("🧪 TESTING SYSTEM REQUIREMENTS")
    print("="*60)
    
    tests = [
        ("python3 --version", "Python 3.10+"),
        ("node --version", "Node.js 18+"),
        ("npm --version", "NPM"),
        ("which icloudpd", "icloudpd installed"),
        ("which ffmpeg", "FFmpeg installed"),
        ("which exiftool", "ExifTool installed"),
    ]
    
    results = []
    for command, description in tests:
        results.append(run_command(command, description))
    
    return all(results)

def test_configuration():
    """Test configuration"""
    print("\n" + "="*60)
    print("🧪 TESTING CONFIGURATION")
    print("="*60)
    
    config_file = "/opt/media-pipeline/config/settings.env"
    if not check_file_exists(config_file, "Configuration file"):
        return False
    
    # Check for required environment variables
    required_vars = [
        "ICLOUD_USERNAME",
        "ICLOUD_PASSWORD", 
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "NAS_MOUNT"
    ]
    
    try:
        with open(config_file, 'r') as f:
            content = f.read()
            
        missing_vars = []
        for var in required_vars:
            if f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {missing_vars}")
            return False
        else:
            print("✅ All required environment variables present")
            return True
            
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("🧪 TESTING DATABASE CONNECTION")
    print("="*60)
    
    return run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/setup_supabase_tables.py",
        "Supabase database connection and table setup"
    )

def test_icloud_authentication():
    """Test iCloud authentication"""
    print("\n" + "="*60)
    print("🧪 TESTING iCLOUD AUTHENTICATION")
    print("="*60)
    
    return run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --username test@icloud.com --list-albums",
        "iCloud authentication test"
    )

def test_download_phase():
    """Test download phase"""
    print("\n" + "="*60)
    print("🧪 TESTING DOWNLOAD PHASE")
    print("="*60)
    
    success = run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py",
        "Download from iCloud"
    )
    
    if success:
        check_directory_contents("/mnt/wd_all_pictures/sync/originals", "Originals directory")
    
    return success

def test_compression_phase():
    """Test compression phase"""
    print("\n" + "="*60)
    print("🧪 TESTING COMPRESSION PHASE")
    print("="*60)
    
    success = run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py",
        "Media compression"
    )
    
    if success:
        check_directory_contents("/mnt/wd_all_pictures/sync/compressed", "Compressed directory")
    
    return success

def test_deduplication_phase():
    """Test deduplication phase"""
    print("\n" + "="*60)
    print("🧪 TESTING DEDUPLICATION PHASE")
    print("="*60)
    
    return run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/deduplicate.py",
        "Deduplication"
    )

def test_file_preparation():
    """Test file preparation"""
    print("\n" + "="*60)
    print("🧪 TESTING FILE PREPARATION")
    print("="*60)
    
    success = run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py",
        "File preparation for uploads"
    )
    
    if success:
        check_directory_contents("/mnt/wd_all_pictures/sync/bridge/icloud", "iCloud bridge directory")
        check_directory_contents("/mnt/wd_all_pictures/sync/bridge/pixel", "Pixel bridge directory")
    
    return success

def test_icloud_upload():
    """Test iCloud upload"""
    print("\n" + "="*60)
    print("🧪 TESTING iCLOUD UPLOAD")
    print("="*60)
    
    # Create a test file for upload
    test_dir = "/tmp/test_upload"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a simple test image
    test_file = os.path.join(test_dir, "test_image.jpg")
    if not os.path.exists(test_file):
        # Create a minimal JPEG file for testing
        with open(test_file, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9')
    
    success = run_command(
        f"sudo -u media-pipeline /opt/media-pipeline/venv/bin/node /opt/media-pipeline/scripts/upload_icloud_fixed.js --dir {test_dir} --interactive",
        "iCloud upload test"
    )
    
    return success

def test_pixel_sync():
    """Test Pixel sync"""
    print("\n" + "="*60)
    print("🧪 TESTING PIXEL SYNC")
    print("="*60)
    
    return run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sync_to_pixel.py",
        "Pixel sync via Syncthing"
    )

def test_sorting():
    """Test sorting"""
    print("\n" + "="*60)
    print("🧪 TESTING SORTING")
    print("="*60)
    
    success = run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sort_uploaded.py",
        "File sorting by date"
    )
    
    if success:
        check_directory_contents("/mnt/wd_all_pictures/sync/sorted", "Sorted directory")
    
    return success

def test_cleanup():
    """Test cleanup"""
    print("\n" + "="*60)
    print("🧪 TESTING CLEANUP")
    print("="*60)
    
    return run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/verify_and_cleanup.py",
        "Verification and cleanup"
    )

def test_complete_pipeline():
    """Test complete pipeline"""
    print("\n" + "="*60)
    print("🧪 TESTING COMPLETE PIPELINE")
    print("="*60)
    
    return run_command(
        "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py",
        "Complete pipeline execution"
    )

def main():
    """Main test function"""
    print("🚀 MEDIA PIPELINE COMPLETE TEST SUITE")
    print("="*60)
    print(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test phases
    test_phases = [
        ("System Requirements", test_system_requirements),
        ("Configuration", test_configuration),
        ("Database Connection", test_database_connection),
        ("iCloud Authentication", test_icloud_authentication),
        ("Download Phase", test_download_phase),
        ("Compression Phase", test_compression_phase),
        ("Deduplication Phase", test_deduplication_phase),
        ("File Preparation", test_file_preparation),
        ("iCloud Upload", test_icloud_upload),
        ("Pixel Sync", test_pixel_sync),
        ("Sorting", test_sorting),
        ("Cleanup", test_cleanup),
        ("Complete Pipeline", test_complete_pipeline),
    ]
    
    results = {}
    
    for phase_name, test_function in test_phases:
        try:
            success = test_function()
            results[phase_name] = success
            
            if not success:
                print(f"\n❌ {phase_name} failed. Stopping tests.")
                break
                
        except Exception as e:
            print(f"\n💥 {phase_name} exception: {e}")
            results[phase_name] = False
            break
    
    # Generate test report
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for phase_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{phase_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Pipeline is ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
