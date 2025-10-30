#!/usr/bin/env python3
"""
Test Google Photos Sync Checker
Tests the sync checker functionality without requiring full authentication
"""

import os
import sys
import json
from pathlib import Path

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')

def test_sync_checker_basic():
    """Test basic sync checker functionality"""
    print("🧪 Testing Google Photos Sync Checker - Basic Functionality")
    print("=" * 60)
    
    try:
        # Import the sync checker
        sys.path.append('/opt/media-pipeline/scripts')
        from google_photos_sync_checker import GooglePhotosSyncChecker
        
        checker = GooglePhotosSyncChecker()
        print("✅ GooglePhotosSyncChecker imported successfully")
        
        # Test credential loading
        if checker.load_credentials():
            print("✅ Credentials loaded successfully")
            print(f"   Client ID: {checker.client_id[:20]}...")
            print(f"   Client Secret: {checker.client_secret[:10]}...")
        else:
            print("❌ Failed to load credentials")
            return False
        
        # Test token loading (may not exist yet)
        if checker.load_tokens():
            print("✅ Tokens loaded successfully")
            print(f"   Access Token: {checker.access_token[:20] if checker.access_token else 'None'}...")
            print(f"   Refresh Token: {checker.refresh_token[:20] if checker.refresh_token else 'None'}...")
        else:
            print("ℹ️ No tokens found (authentication not completed yet)")
        
        # Test authorization URL generation
        auth_url = checker.get_authorization_url()
        if auth_url:
            print("✅ Authorization URL generated successfully")
            print(f"   URL: {auth_url[:80]}...")
        else:
            print("❌ Failed to generate authorization URL")
            return False
        
        # Test configuration loading
        from utils.utils import get_config_value
        
        enable_sync_check = get_config_value('ENABLE_GOOGLE_PHOTOS_SYNC_CHECK', 'false')
        print(f"✅ Configuration loaded: ENABLE_GOOGLE_PHOTOS_SYNC_CHECK = {enable_sync_check}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing sync checker: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pipeline_integration():
    """Test pipeline integration"""
    print("\n🔗 Testing Pipeline Integration")
    print("=" * 35)
    
    try:
        # Test if verification processor can be imported
        sys.path.append('/opt/media-pipeline/src/processors')
        from verify_and_cleanup import verify_google_photos_sync
        
        print("✅ verify_google_photos_sync function imported successfully")
        
        # Test configuration check
        from utils.utils import get_feature_toggle
        
        enable_sync_check = get_feature_toggle("ENABLE_GOOGLE_PHOTOS_SYNC_CHECK")
        print(f"✅ Feature toggle check: ENABLE_GOOGLE_PHOTOS_SYNC_CHECK = {enable_sync_check}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing pipeline integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_structure():
    """Test file structure and permissions"""
    print("\n📁 Testing File Structure")
    print("=" * 25)
    
    files_to_check = [
        '/opt/media-pipeline/scripts/google_photos_sync_checker.py',
        '/opt/media-pipeline/scripts/setup_google_photos_api.py',
        '/opt/media-pipeline/scripts/complete_google_photos_auth.py',
        '/opt/media-pipeline/config/google_photos_credentials.json',
        '/opt/media-pipeline/config/google_photos_credentials.json.template',
        '/opt/media-pipeline/GOOGLE_PHOTOS_SYNC_CHECKER.md',
        '/opt/media-pipeline/src/processors/verify_and_cleanup.py'
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_exist = False
    
    return all_exist

def test_configuration():
    """Test configuration settings"""
    print("\n⚙️ Testing Configuration")
    print("=" * 25)
    
    try:
        # Check settings.env
        settings_file = '/opt/media-pipeline/config/settings.env'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                content = f.read()
            
            checks = [
                ('ENABLE_GOOGLE_PHOTOS_SYNC_CHECK=true', 'Google Photos sync check enabled'),
                ('GOOGLE_PHOTOS_CLIENT_ID=1026727790585', 'Client ID configured'),
                ('GOOGLE_PHOTOS_CLIENT_SECRET=GOCSPX-', 'Client secret configured')
            ]
            
            all_configured = True
            for check, description in checks:
                if check in content:
                    print(f"✅ {description}")
                else:
                    print(f"❌ {description}")
                    all_configured = False
            
            return all_configured
        else:
            print("❌ Settings file not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking configuration: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Google Photos Sync Checker - Comprehensive Test")
    print("=" * 55)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Configuration", test_configuration),
        ("Sync Checker Basic", test_sync_checker_basic),
        ("Pipeline Integration", test_pipeline_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Google Photos sync checker is ready.")
        print("\n📋 Next steps to complete setup:")
        print("1. Run: python3 scripts/complete_google_photos_auth.py")
        print("2. Follow the OAuth flow to get authorization code")
        print("3. Test sync functionality with real files")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main()