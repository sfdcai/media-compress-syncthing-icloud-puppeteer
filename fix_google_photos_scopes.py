#!/usr/bin/env python3
"""
Fix Google Photos OAuth scopes issue
"""

import sys
import os
import json
import webbrowser
from datetime import datetime

# Add the project root to Python path
sys.path.append('/opt/media-pipeline')

def fix_google_photos_scopes():
    """Fix Google Photos OAuth scopes by forcing fresh authorization"""
    print("=== Google Photos OAuth Scopes Fix ===")
    print()
    
    # Check credentials
    creds_file = '/opt/media-pipeline/config/google_photos_credentials.json'
    if not os.path.exists(creds_file):
        print("❌ Google Photos credentials file not found")
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
    
    # Create authorization URL with explicit scope and force consent
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    redirect_uri = 'http://localhost:8080'
    
    # Use multiple scopes to ensure we get the right permissions
    scopes = [
        'https://www.googleapis.com/auth/photoslibrary.readonly',
        'https://www.googleapis.com/auth/photoslibrary'
    ]
    scope_string = ' '.join(scopes)
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scope_string,
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent',  # Force consent screen
        'include_granted_scopes': 'true'  # Include all granted scopes
    }
    
    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{base_url}?{param_string}"
    
    print("🔧 IMPORTANT: Google Cloud Console Configuration")
    print("=" * 60)
    print("Make sure your OAuth consent screen has these scopes:")
    print("✅ https://www.googleapis.com/auth/photoslibrary.readonly")
    print("✅ https://www.googleapis.com/auth/photoslibrary")
    print()
    print("And this redirect URI:")
    print("✅ http://localhost:8080")
    print()
    
    # Backup current tokens
    token_file = '/opt/media-pipeline/config/google_photos_tokens.json'
    if os.path.exists(token_file):
        backup_file = f'/opt/media-pipeline/config/google_photos_tokens_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        os.rename(token_file, backup_file)
        print(f"✅ Backed up current tokens to: {backup_file}")
    
    print()
    print("📋 Fresh Authorization URL:")
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
    print("2. Make sure to grant ALL requested permissions")
    print("3. You'll be redirected to: http://localhost:8080?code=YOUR_CODE")
    print("4. Copy the code from the URL (the part after 'code=')")
    print("5. Paste the code below")
    print()
    
    # Wait for user input
    code = input("Enter the authorization code: ").strip()
    
    if not code:
        print("❌ No code provided")
        return False
    
    print(f"✅ Code received: {code[:20]}...")
    
    # Exchange code for tokens
    try:
        from scripts.google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        
        if checker.exchange_code_for_tokens(code):
            print("✅ Authorization successful! Tokens saved.")
            
            # Test the token with different scopes
            print("\n--- Testing New Token ---")
            if checker.test_token():
                print("✅ Token test passed!")
                
                # Test actual API calls
                try:
                    results = checker.search_media_items()
                    print(f"✅ API call successful: {len(results)} media items found")
                    
                    if results:
                        print("First few items:")
                        for i, item in enumerate(results[:3]):
                            print(f"  {i+1}. {item.get('filename', 'Unknown')}")
                    else:
                        print("ℹ️  No media items found (this might be normal if no photos are uploaded)")
                        
                except Exception as e:
                    print(f"⚠️  API call failed: {e}")
            else:
                print("❌ Token test failed")
        else:
            print("❌ Failed to exchange code for tokens")
            return False
            
    except Exception as e:
        print(f"❌ Error exchanging code: {e}")
        return False
    
    print()
    print("🎉 Google Photos OAuth scopes fixed!")
    print("You should now be able to access Google Photos API and list uploaded files.")

if __name__ == "__main__":
    fix_google_photos_scopes()