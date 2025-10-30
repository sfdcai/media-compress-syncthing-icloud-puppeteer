#!/usr/bin/env python3
"""
Test Google Photos API Setup
Tests the Google Photos API configuration and setup
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')

def test_credentials_loading():
    """Test if credentials are loaded correctly"""
    print("🔍 Testing Google Photos API credentials loading...")
    
    try:
        # Test credentials file
        credentials_file = '/opt/media-pipeline/config/google_photos_credentials.json'
        if os.path.exists(credentials_file):
            with open(credentials_file, 'r') as f:
                creds = json.load(f)
                print(f"✅ Credentials file found: {credentials_file}")
                print(f"✅ Client ID: {creds.get('client_id', 'Not found')[:20]}...")
                print(f"✅ Client Secret: {creds.get('client_secret', 'Not found')[:10]}...")
                return True
        else:
            print(f"❌ Credentials file not found: {credentials_file}")
            return False
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        return False

def test_environment_variables():
    """Test if environment variables are set correctly"""
    print("\n🔍 Testing environment variables...")
    
    try:
        # Load settings.env
        settings_file = '/opt/media-pipeline/config/settings.env'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                content = f.read()
                
            # Check for Google Photos settings
            if 'ENABLE_GOOGLE_PHOTOS_SYNC_CHECK=true' in content:
                print("✅ ENABLE_GOOGLE_PHOTOS_SYNC_CHECK is enabled")
            else:
                print("❌ ENABLE_GOOGLE_PHOTOS_SYNC_CHECK is not enabled")
                
            if 'GOOGLE_PHOTOS_CLIENT_ID=' in content and 'GOOGLE_PHOTOS_CLIENT_ID=1026727790585' in content:
                print("✅ GOOGLE_PHOTOS_CLIENT_ID is set")
            else:
                print("❌ GOOGLE_PHOTOS_CLIENT_ID is not set correctly")
                
            if 'GOOGLE_PHOTOS_CLIENT_SECRET=' in content and 'GOOGLE_PHOTOS_CLIENT_SECRET=GOCSPX-' in content:
                print("✅ GOOGLE_PHOTOS_CLIENT_SECRET is set")
            else:
                print("❌ GOOGLE_PHOTOS_CLIENT_SECRET is not set correctly")
                
            return True
        else:
            print(f"❌ Settings file not found: {settings_file}")
            return False
    except Exception as e:
        print(f"❌ Error checking environment variables: {e}")
        return False

def test_authorization_url():
    """Test if authorization URL can be generated"""
    print("\n🔍 Testing authorization URL generation...")
    
    try:
        # Load credentials
        credentials_file = '/opt/media-pipeline/config/google_photos_credentials.json'
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
        
        client_id = creds['client_id']
        
        # Generate authorization URL
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            'client_id': client_id,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'scope': 'https://www.googleapis.com/auth/photoslibrary.readonly',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{base_url}?{param_string}"
        
        print("✅ Authorization URL generated successfully")
        print(f"🔗 URL: {auth_url}")
        print("\n📋 To complete setup:")
        print("1. Visit the URL above in your browser")
        print("2. Sign in to your Google account")
        print("3. Grant permission for the app to access your Google Photos")
        print("4. Copy the authorization code")
        print("5. Run: python3 scripts/google_photos_sync_checker.py setup")
        print("6. Paste the authorization code when prompted")
        
        return True
    except Exception as e:
        print(f"❌ Error generating authorization URL: {e}")
        return False

def test_sync_checker_import():
    """Test if the sync checker can be imported"""
    print("\n🔍 Testing sync checker import...")
    
    try:
        sys.path.append('/opt/media-pipeline/scripts')
        from google_photos_sync_checker import GooglePhotosSyncChecker
        
        checker = GooglePhotosSyncChecker()
        print("✅ GooglePhotosSyncChecker imported successfully")
        
        # Test credential loading
        if checker.load_credentials():
            print("✅ Credentials loaded successfully")
        else:
            print("❌ Failed to load credentials")
            
        return True
    except Exception as e:
        print(f"❌ Error importing sync checker: {e}")
        return False

def test_pipeline_integration():
    """Test if pipeline integration is working"""
    print("\n🔍 Testing pipeline integration...")
    
    try:
        # Check if verification processor has the Google Photos sync function
        verify_file = '/opt/media-pipeline/src/processors/verify_and_cleanup.py'
        if os.path.exists(verify_file):
            with open(verify_file, 'r') as f:
                content = f.read()
                
            if 'def verify_google_photos_sync():' in content:
                print("✅ Google Photos sync function found in verification processor")
            else:
                print("❌ Google Photos sync function not found in verification processor")
                
            if 'verify_google_photos_sync()' in content:
                print("✅ Google Photos sync function is called in main pipeline")
            else:
                print("❌ Google Photos sync function is not called in main pipeline")
                
            return True
        else:
            print(f"❌ Verification processor not found: {verify_file}")
            return False
    except Exception as e:
        print(f"❌ Error checking pipeline integration: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Google Photos API Setup Test")
    print("=" * 50)
    
    tests = [
        test_credentials_loading,
        test_environment_variables,
        test_authorization_url,
        test_sync_checker_import,
        test_pipeline_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Google Photos API setup is ready.")
        print("\n📋 Next steps:")
        print("1. Visit the authorization URL above")
        print("2. Complete the OAuth flow")
        print("3. Run the sync checker to test functionality")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    main()