#!/usr/bin/env python3
"""
Setup Google Photos OAuth for headless server
"""

import sys
import os
import json
import webbrowser
from urllib.parse import urlparse, parse_qs

# Add the project root to Python path
sys.path.append('/opt/media-pipeline')

def setup_google_photos_oauth():
    """Setup Google Photos OAuth with proper redirect URI"""
    print("=== Google Photos OAuth Setup for Headless Server ===")
    print()
    
    # Check credentials
    creds_file = '/opt/media-pipeline/config/google_photos_credentials.json'
    if not os.path.exists(creds_file):
        print("❌ Google Photos credentials file not found")
        print("Please create: /opt/media-pipeline/config/google_photos_credentials.json")
        return False
    
    with open(creds_file, 'r') as f:
        creds = json.load(f)
    
    client_id = creds.get('client_id')
    if not client_id:
        print("❌ No client_id found in credentials")
        return False
    
    print("✅ Credentials loaded")
    print(f"Client ID: {client_id[:20]}...")
    print()
    
    # Create authorization URL with localhost redirect
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    redirect_uri = 'http://localhost:8080'
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'https://www.googleapis.com/auth/photoslibrary.readonly',
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{base_url}?{param_string}"
    
    print("🔧 IMPORTANT: Google Cloud Console Configuration Required")
    print("=" * 60)
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Navigate to: APIs & Services > OAuth consent screen")
    print("3. Add this redirect URI: http://localhost:8080")
    print("4. Make sure Google Photos Library API is enabled")
    print()
    print("📋 Authorization URL:")
    print(auth_url)
    print()
    
    # Try to open the URL
    try:
        print("🌐 Opening authorization URL in your default browser...")
        webbrowser.open(auth_url)
        print("✅ URL opened in browser")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print("Please copy and paste the URL above into your browser")
    
    print()
    print("📝 Instructions:")
    print("1. Complete the authorization in your browser")
    print("2. You'll be redirected to: http://localhost:8080?code=YOUR_CODE")
    print("3. Copy the code from the URL (the part after 'code=')")
    print("4. Paste the code in the web dashboard")
    print()
    
    # Wait for user input
    code = input("Enter the authorization code (or press Enter to skip): ").strip()
    
    if code:
        print(f"✅ Code received: {code[:20]}...")
        
        # Exchange code for tokens
        try:
            from scripts.google_photos_sync_checker import GooglePhotosSyncChecker
            checker = GooglePhotosSyncChecker()
            
            if checker.exchange_code_for_tokens(code):
                print("✅ Authorization successful! Tokens saved.")
                
                # Test the token
                if checker.test_token():
                    print("✅ Token test passed! Google Photos API is working.")
                else:
                    print("⚠️  Token test failed. Please check your Google Cloud Console setup.")
            else:
                print("❌ Failed to exchange code for tokens")
                
        except Exception as e:
            print(f"❌ Error exchanging code: {e}")
    else:
        print("⏭️  Skipping code exchange. You can complete this later via the web dashboard.")
    
    print()
    print("🎯 Next Steps:")
    print("1. If you haven't already, add http://localhost:8080 to your OAuth redirect URIs")
    print("2. Complete the authorization process")
    print("3. Test the connection in the web dashboard")

if __name__ == "__main__":
    setup_google_photos_oauth()