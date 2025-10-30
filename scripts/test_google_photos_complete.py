#!/usr/bin/env python3
"""
Complete Google Photos Integration Test
Tests all aspects of the Google Photos integration and provides setup guidance
"""

import os
import sys
import json
import requests
from pathlib import Path

import pytest

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')
sys.path.append('/opt/media-pipeline/scripts')

RUN_PROD_TESTS = os.environ.get("RUN_PROD_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_PROD_TESTS,
    reason="Set RUN_PROD_TESTS=1 to enable Google Photos integration tests."
)

USING_PYTEST = "pytest" in sys.modules


def _test_result(success, failure_message="Test reported failure"):
    if USING_PYTEST:
        if not success:
            pytest.fail(failure_message)
        return None
    return success

def test_credentials_and_config():
    """Test credentials and configuration"""
    print("🔍 Testing Credentials and Configuration")
    print("=" * 45)
    
    try:
        # Test credentials file
        credentials_file = '/opt/media-pipeline/config/google_photos_credentials.json'
        if not os.path.exists(credentials_file):
            print("❌ Credentials file not found")
            return _test_result(False, "Google Photos credentials file not found")

        with open(credentials_file, 'r') as f:
            creds = json.load(f)

        if not creds.get('client_id') or not creds.get('client_secret'):
            print("❌ Credentials file incomplete")
            return _test_result(False, "Google Photos credentials file is incomplete")

        print("✅ Credentials file found and complete")

        # Test environment variables
        from utils.utils import get_config_value
        enable_sync = get_config_value('ENABLE_GOOGLE_PHOTOS_SYNC_CHECK', 'false')
        client_id = get_config_value('GOOGLE_PHOTOS_CLIENT_ID', '')
        client_secret = get_config_value('GOOGLE_PHOTOS_CLIENT_SECRET', '')

        if enable_sync.lower() != 'true':
            print("❌ Google Photos sync check not enabled")
            return _test_result(False, "Google Photos sync check is not enabled")

        if not client_id or not client_secret:
            print("❌ Google Photos credentials not configured in environment")
            return _test_result(False, "Google Photos credentials environment variables are missing")

        print("✅ Environment configuration correct")
        return _test_result(True)

    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return _test_result(False, f"Error testing credentials: {e}")

def test_oauth_flow():
    """Test OAuth flow and token management"""
    print("\n🔐 Testing OAuth Flow and Token Management")
    print("=" * 50)
    
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        
        # Test credential loading
        if not checker.load_credentials():
            print("❌ Failed to load credentials")
            return _test_result(False, "Failed to load Google Photos credentials")
        print("✅ Credentials loaded successfully")
        
        # Test token loading
        has_tokens = checker.load_tokens()
        if has_tokens:
            print("✅ Tokens loaded successfully")
            print(f"   Access Token: {checker.access_token[:20] if checker.access_token else 'None'}...")
            print(f"   Refresh Token: {checker.refresh_token[:20] if checker.refresh_token else 'None'}...")
        else:
            print("ℹ️ No tokens found - authentication needed")
            return _test_result(False, "No Google Photos tokens found; authentication required")
        
        # Test token validity
        if checker.ensure_valid_token():
            print("✅ Access token is valid")
        else:
            print("❌ Access token is invalid")
            return _test_result(False, "Google Photos access token is invalid")

        return _test_result(True)

    except Exception as e:
        print(f"❌ Error testing OAuth flow: {e}")
        return _test_result(False, f"Error testing OAuth flow: {e}")

def test_api_permissions():
    """Test API permissions and scopes"""
    print("\n🔑 Testing API Permissions and Scopes")
    print("=" * 40)
    
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        checker.load_credentials()
        checker.load_tokens()
        checker.ensure_valid_token()
        
        # Check token scopes
        url = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
        params = {'access_token': checker.access_token}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            token_info = response.json()
            scope = token_info.get('scope', '')
            print(f"✅ Token scopes: {scope}")

            if 'photoslibrary.readonly' in scope:
                print("✅ Photos Library API scope is present")
            else:
                print("❌ Photos Library API scope is missing")
                return _test_result(False, "Photos Library API scope is missing from token")
        else:
            print(f"❌ Failed to get token info: {response.status_code}")
            return _test_result(False, "Failed to retrieve token info from Google OAuth endpoint")
        
        # Test API access
        print("\n🧪 Testing API Access...")
        
        # Test albums endpoint
        url = 'https://photoslibrary.googleapis.com/v1/albums'
        headers = {'Authorization': f'Bearer {checker.access_token}'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Albums API working - Found {len(data.get('albums', []))} albums")
            return _test_result(True)
        elif response.status_code == 403:
            error_data = response.json()
            if 'insufficient authentication scopes' in error_data.get('error', {}).get('message', ''):
                print("❌ Insufficient authentication scopes")
                print("   This usually means the Photos Library API is not enabled in Google Cloud Console")
                return _test_result(False, "Insufficient authentication scopes for Google Photos API")
            else:
                print(f"❌ API access denied: {error_data}")
                return _test_result(False, "Google Photos API access denied")
        else:
            print(f"❌ API test failed with status {response.status_code}")
            return _test_result(False, "Google Photos API albums request failed")

    except Exception as e:
        print(f"❌ Error testing API permissions: {e}")
        return _test_result(False, f"Error testing API permissions: {e}")

def test_sync_functionality():
    """Test sync functionality"""
    print("\n🔄 Testing Sync Functionality")
    print("=" * 30)
    
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        checker.load_credentials()
        checker.load_tokens()
        checker.ensure_valid_token()
        
        # Test search functionality
        print("🔍 Testing media search...")
        media_items = checker.search_media_items()
        
        if media_items is not None:
            print(f"✅ Media search working - Found {len(media_items)} items")
        else:
            print("❌ Media search failed")
            return _test_result(False, "Google Photos media search failed")
        
        # Test file sync check
        print("📁 Testing file sync check...")
        pixel_dir = '/mnt/wd_all_pictures/sync/uploaded/pixel'
        os.makedirs(pixel_dir, exist_ok=True)
        
        results = checker.check_pixel_uploaded_files(pixel_dir)
        print(f"✅ File sync check working - Checked {len(results)} files")
        
        return _test_result(True)

    except Exception as e:
        print(f"❌ Error testing sync functionality: {e}")
        return _test_result(False, f"Error testing sync functionality: {e}")

def test_pipeline_integration():
    """Test pipeline integration"""
    print("\n🔗 Testing Pipeline Integration")
    print("=" * 35)
    
    try:
        # Test verification processor import
        from processors.verify_and_cleanup import verify_google_photos_sync
        print("✅ Google Photos sync function imported successfully")

        # Test feature toggle
        from utils.utils import get_feature_toggle
        enable_sync = get_feature_toggle("ENABLE_GOOGLE_PHOTOS_SYNC_CHECK")
        print(f"✅ Feature toggle working: {enable_sync}")

        # Test the sync function (without actually running it)
        print("✅ Pipeline integration ready")
        return _test_result(True)

    except Exception as e:
        print(f"❌ Error testing pipeline integration: {e}")
        return _test_result(False, f"Error testing pipeline integration: {e}")

def provide_setup_guidance():
    """Provide setup guidance for common issues"""
    print("\n📋 Setup Guidance")
    print("=" * 20)
    
    print("""
If you're getting 403 errors with 'insufficient authentication scopes':

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Select your project (or create a new one)
3. Enable the Photos Library API:
   - Go to "APIs & Services" > "Library"
   - Search for "Photos Library API"
   - Click on it and press "Enable"
4. Configure OAuth consent screen:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in required fields (App name, User support email, etc.)
   - Add your email to test users
   - Add the scope: https://www.googleapis.com/auth/photoslibrary.readonly
5. Re-authenticate:
   - Delete the tokens file: rm /opt/media-pipeline/config/google_photos_tokens.json
   - Run: python3 scripts/complete_google_photos_auth.py
   - Follow the OAuth flow again

If you're getting other errors:
- Check that your Google account has photos
- Verify the OAuth consent screen is properly configured
- Ensure the Photos Library API is enabled
- Check that your credentials are correct
""")

def main():
    """Main test function"""
    print("🚀 Google Photos Integration - Complete Test")
    print("=" * 50)
    
    tests = [
        ("Credentials and Configuration", test_credentials_and_config),
        ("OAuth Flow and Token Management", test_oauth_flow),
        ("API Permissions and Scopes", test_api_permissions),
        ("Sync Functionality", test_sync_functionality),
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
        print("🎉 All tests passed! Google Photos integration is working perfectly.")
        print("\n✅ Ready for production use!")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        provide_setup_guidance()
    
    return passed == total

if __name__ == "__main__":
    main()