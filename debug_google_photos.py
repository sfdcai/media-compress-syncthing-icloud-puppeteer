#!/usr/bin/env python3
"""
Debug Google Photos authorization
"""

import sys
import os
sys.path.append('/opt/media-pipeline/scripts')

from google_photos_sync_checker import GooglePhotosSyncChecker

def main():
    print("=== Google Photos Debug ===")
    
    checker = GooglePhotosSyncChecker()
    
    print(f"Client ID: {checker.client_id[:20]}..." if checker.client_id else "No client ID")
    print(f"Client Secret: {checker.client_secret[:10]}..." if checker.client_secret else "No client secret")
    
    print("\n--- Loading Credentials ---")
    creds_loaded = checker.load_credentials()
    print(f"Credentials loaded: {creds_loaded}")
    
    print("\n--- Loading Tokens ---")
    tokens_loaded = checker.load_tokens()
    print(f"Tokens loaded: {tokens_loaded}")
    
    if checker.access_token:
        print(f"Access token length: {len(checker.access_token)}")
        print(f"Access token starts with: {checker.access_token[:20]}...")
    else:
        print("No access token")
    
    if checker.refresh_token:
        print(f"Refresh token length: {len(checker.refresh_token)}")
        print(f"Refresh token starts with: {checker.refresh_token[:20]}...")
    else:
        print("No refresh token")
    
    print("\n--- Testing Token ---")
    token_valid = checker.test_token()
    print(f"Token valid: {token_valid}")
    
    print("\n--- Testing API Call ---")
    try:
        results = checker.search_media_items()
        print(f"API call successful: {len(results)} items found")
        if results:
            print(f"First item: {results[0]}")
    except Exception as e:
        print(f"API call failed: {e}")
    
    print("\n--- Testing Pixel Files ---")
    try:
        pixel_files = checker.check_pixel_uploaded_files('/mnt/syncthing/pixel')
        print(f"Pixel files found: {len(pixel_files) if pixel_files else 0}")
        if pixel_files:
            print(f"First few files: {[f['filename'] for f in pixel_files[:3]]}")
    except Exception as e:
        print(f"Pixel files check failed: {e}")

if __name__ == "__main__":
    main()