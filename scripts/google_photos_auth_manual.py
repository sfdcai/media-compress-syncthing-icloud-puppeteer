#!/usr/bin/env python3
"""
Google Photos Manual Authentication
Simplified authentication that works with the updated OAuth flow
"""

import os
import sys
import json
import webbrowser
from pathlib import Path

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')
sys.path.append('/opt/media-pipeline/scripts')

def get_authorization_url():
    """Get the Google Photos authorization URL"""
    try:
        credentials_file = '/opt/media-pipeline/config/google_photos_credentials.json'
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
        
        client_id = creds['client_id']
        
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            'client_id': client_id,
            'redirect_uri': 'http://localhost:8080',
            'scope': 'https://www.googleapis.com/auth/photoslibrary.readonly',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    except Exception as e:
        print(f"❌ Error generating authorization URL: {e}")
        return None

def exchange_code_for_tokens(auth_code):
    """Exchange authorization code for tokens"""
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        return checker.exchange_code_for_tokens(auth_code)
    except Exception as e:
        print(f"❌ Error exchanging code for tokens: {e}")
        return False

def complete_authentication():
    """Complete the Google Photos authentication process"""
    print("🔐 Google Photos API Authentication (Manual Method)")
    print("=" * 50)
    
    # Get authorization URL
    auth_url = get_authorization_url()
    if not auth_url:
        return False
    
    print("📋 Step 1: Authorization URL")
    print(f"🔗 {auth_url}")
    print()
    
    # Try to open browser automatically
    try:
        print("🌐 Attempting to open browser automatically...")
        webbrowser.open(auth_url)
        print("✅ Browser opened successfully")
    except Exception as e:
        print(f"⚠️ Could not open browser automatically: {e}")
        print("Please copy and paste the URL above into your browser")
    
    print()
    print("📋 Step 2: Complete OAuth Flow")
    print("1. Sign in to your Google account")
    print("2. Grant permission for the app to access your Google Photos")
    print("3. You will be redirected to localhost:8080")
    print("4. Look at the URL in your browser - it will contain 'code=' parameter")
    print("5. Copy the code value (everything after 'code=' and before '&')")
    print()
    print("Example: If the URL is http://localhost:8080/?code=4/0AX4XfWh...")
    print("         Copy: 4/0AX4XfWh...")
    print()
    
    # Get authorization code from user
    try:
        auth_code = input("Enter the authorization code: ").strip()
        if not auth_code:
            print("❌ No authorization code provided")
            return False
        
        print(f"✅ Authorization code received: {auth_code[:10]}...")
        
        # Exchange code for tokens
        print("\n🔄 Exchanging authorization code for tokens...")
        
        if exchange_code_for_tokens(auth_code):
            print("✅ Authentication completed successfully!")
            print("🎉 Google Photos API is now ready to use")
            return True
        else:
            print("❌ Failed to exchange authorization code for tokens")
            return False
            
    except KeyboardInterrupt:
        print("\n❌ Authentication cancelled by user")
        return False
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return False

def test_authentication():
    """Test the authentication"""
    print("\n🧪 Testing Authentication")
    print("=" * 30)
    
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        
        if not checker.load_credentials():
            print("❌ Failed to load credentials")
            return False
        
        if not checker.load_tokens():
            print("❌ Failed to load tokens")
            return False
        
        if not checker.ensure_valid_token():
            print("❌ Token validation failed")
            return False
        
        print("✅ Authentication test passed")
        
        # Test API connection
        print("🔍 Testing API connection...")
        media_items = checker.search_media_items()
        
        if media_items is not None:
            print(f"✅ API connection successful - Found {len(media_items)} media items")
            return True
        else:
            print("❌ API connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Google Photos API Authentication (Manual Method)")
    print("=" * 50)
    
    # Check if already authenticated
    token_file = '/opt/media-pipeline/config/google_photos_tokens.json'
    if os.path.exists(token_file):
        print("🔍 Checking existing authentication...")
        try:
            with open(token_file, 'r') as f:
                tokens = json.load(f)
            if tokens.get('access_token'):
                print("✅ Authentication already exists")
                
                # Test if tokens are still valid
                if test_authentication():
                    print("🎉 Google Photos API is already set up and working!")
                    return True
                else:
                    print("⚠️ Existing tokens are invalid, re-authenticating...")
        except Exception as e:
            print(f"⚠️ Error checking existing tokens: {e}")
    
    # Complete authentication
    if complete_authentication():
        # Test functionality
        if test_authentication():
            print("\n🎉 Google Photos API setup completed successfully!")
            print("✅ Ready to use in pipeline verification phase")
            return True
        else:
            print("\n⚠️ Authentication completed but API test failed")
            return False
    else:
        print("\n❌ Authentication failed")
        return False

if __name__ == "__main__":
    main()