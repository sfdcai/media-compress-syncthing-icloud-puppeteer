#!/usr/bin/env python3
"""
Google Photos Authentication with Localhost Redirect
Handles OAuth flow with localhost redirect instead of deprecated OOB flow
"""

import os
import sys
import json
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')
sys.path.append('/opt/media-pipeline/scripts')

class AuthHandler(BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback"""
    
    def do_GET(self):
        """Handle GET request from OAuth callback"""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
            <html>
            <head><title>Authentication Complete</title></head>
            <body>
                <h1>Authentication Complete!</h1>
                <p>You can close this window and return to the terminal.</p>
                <p>The authorization code has been captured.</p>
            </body>
            </html>
            ''')
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
            <html>
            <head><title>Authentication Error</title></head>
            <body>
                <h1>Authentication Error</h1>
                <p>No authorization code received. Please try again.</p>
            </body>
            </html>
            ''')
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def start_auth_server():
    """Start local HTTP server to capture OAuth callback"""
    server = HTTPServer(('localhost', 8080), AuthHandler)
    server.auth_code = None
    return server

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
    print("🔐 Google Photos API Authentication (Localhost Method)")
    print("=" * 55)
    
    # Get authorization URL
    auth_url = get_authorization_url()
    if not auth_url:
        return False
    
    print("📋 Step 1: Starting local server...")
    
    # Start local server
    server = start_auth_server()
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print("✅ Local server started on http://localhost:8080")
    
    print("\n📋 Step 2: Opening browser...")
    print(f"🔗 Authorization URL: {auth_url}")
    
    # Try to open browser automatically
    try:
        webbrowser.open(auth_url)
        print("✅ Browser opened successfully")
    except Exception as e:
        print(f"⚠️ Could not open browser automatically: {e}")
        print("Please copy and paste the URL above into your browser")
    
    print("\n📋 Step 3: Complete OAuth Flow")
    print("1. Sign in to your Google account")
    print("2. Grant permission for the app to access your Google Photos")
    print("3. You will be redirected to localhost:8080")
    print("4. The authorization code will be captured automatically")
    print("\n⏳ Waiting for authorization...")
    
    # Wait for authorization code
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    while server.auth_code is None:
        if time.time() - start_time > timeout:
            print("❌ Authentication timeout - no code received within 5 minutes")
            server.shutdown()
            return False
        time.sleep(1)
    
    auth_code = server.auth_code
    print(f"✅ Authorization code received: {auth_code[:10]}...")
    
    # Shutdown server
    server.shutdown()
    server_thread.join()
    
    # Exchange code for tokens
    print("\n🔄 Exchanging authorization code for tokens...")
    
    if exchange_code_for_tokens(auth_code):
        print("✅ Authentication completed successfully!")
        print("🎉 Google Photos API is now ready to use")
        return True
    else:
        print("❌ Failed to exchange authorization code for tokens")
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
    print("🚀 Google Photos API Authentication (Updated Method)")
    print("=" * 55)
    
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