#!/usr/bin/env python3
"""
Fix Google Photos authentication issues
"""

import sys
import os
import json
import requests
from datetime import datetime

# Add the project root to Python path
sys.path.append('/opt/media-pipeline')

def check_google_photos_setup():
    """Check Google Photos API setup and provide guidance"""
    print("=== Google Photos API Setup Check ===")
    
    # Check credentials file
    creds_file = '/opt/media-pipeline/config/google_photos_credentials.json'
    if not os.path.exists(creds_file):
        print("❌ Google Photos credentials file not found")
        print("   Please create: /opt/media-pipeline/config/google_photos_credentials.json")
        print("   With content:")
        print("   {")
        print("     \"client_id\": \"your_client_id\",")
        print("     \"client_secret\": \"your_client_secret\"")
        print("   }")
        return False
    
    with open(creds_file, 'r') as f:
        creds = json.load(f)
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    
    if not client_id or not client_secret:
        print("❌ Google Photos credentials incomplete")
        return False
    
    print(f"✅ Credentials found: {client_id[:20]}...")
    
    # Check tokens file
    token_file = '/opt/media-pipeline/config/google_photos_tokens.json'
    if not os.path.exists(token_file):
        print("❌ Google Photos tokens file not found")
        print("   You need to complete the OAuth flow first")
        return False
    
    with open(token_file, 'r') as f:
        tokens = json.load(f)
    
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')
    
    if not access_token:
        print("❌ No access token found")
        return False
    
    print(f"✅ Tokens found: access_token={len(access_token)} chars, refresh_token={len(refresh_token)} chars")
    
    # Test the token
    print("\n--- Testing Access Token ---")
    try:
        url = "https://photoslibrary.googleapis.com/v1/mediaItems"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Access token is valid")
            return True
        elif response.status_code == 400:
            print("✅ Access token is valid (no media items)")
            return True
        elif response.status_code == 403:
            print("❌ 403 Forbidden - This usually means:")
            print("   1. Google Photos Library API is not enabled")
            print("   2. OAuth consent screen is not properly configured")
            print("   3. The app is not verified (if in production)")
            print("\n   To fix this:")
            print("   1. Go to Google Cloud Console")
            print("   2. Enable Google Photos Library API")
            print("   3. Configure OAuth consent screen")
            print("   4. Add your redirect URI: http://192.168.1.7:8080")
            return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing token: {e}")
        return False

def create_authorization_url():
    """Create a proper authorization URL"""
    creds_file = '/opt/media-pipeline/config/google_photos_credentials.json'
    if not os.path.exists(creds_file):
        print("❌ Credentials file not found")
        return None
    
    with open(creds_file, 'r') as f:
        creds = json.load(f)
    
    client_id = creds.get('client_id')
    if not client_id:
        print("❌ No client ID found")
        return None
    
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        'client_id': client_id,
        'redirect_uri': 'http://192.168.1.7:8080',
        'scope': 'https://www.googleapis.com/auth/photoslibrary.readonly',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{base_url}?{param_string}"
    
    print(f"\n=== Authorization URL ===")
    print(auth_url)
    print("\nCopy this URL and open it in your browser to authorize the app.")
    print("After authorization, you'll be redirected to a URL with a 'code' parameter.")
    print("Copy that code and use it to complete the setup.")
    
    return auth_url

def main():
    print("Google Photos Authentication Fix Tool")
    print("=" * 50)
    
    # Check current setup
    if check_google_photos_setup():
        print("\n✅ Google Photos is properly configured!")
        return
    
    print("\n--- Creating Authorization URL ---")
    auth_url = create_authorization_url()
    
    if auth_url:
        print("\n--- Next Steps ---")
        print("1. Open the authorization URL above in your browser")
        print("2. Sign in to your Google account")
        print("3. Authorize the application")
        print("4. Copy the 'code' parameter from the redirect URL")
        print("5. Use the web dashboard to enter the code")

if __name__ == "__main__":
    main()