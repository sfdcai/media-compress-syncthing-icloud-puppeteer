#!/usr/bin/env python3
"""
Simple Google Photos test
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append('/opt/media-pipeline')

def test_google_photos():
    print("=== Simple Google Photos Test ===")
    
    # Load tokens
    token_file = '/opt/media-pipeline/config/google_photos_tokens.json'
    if not os.path.exists(token_file):
        print("❌ Token file not found")
        return
    
    with open(token_file, 'r') as f:
        tokens = json.load(f)
    
    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')
    
    print(f"Access token length: {len(access_token) if access_token else 0}")
    print(f"Refresh token length: {len(refresh_token) if refresh_token else 0}")
    
    if not access_token:
        print("❌ No access token")
        return
    
    # Test 1: Simple API call
    print("\n--- Test 1: Simple API Call ---")
    try:
        url = "https://photoslibrary.googleapis.com/v1/mediaItems"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API call successful: {len(data.get('mediaItems', []))} items")
        elif response.status_code == 400:
            print("✅ API call successful (no media items)")
        else:
            print(f"❌ API call failed: {response.text}")
            
    except Exception as e:
        print(f"❌ API call error: {e}")
    
    # Test 2: Search API call
    print("\n--- Test 2: Search API Call ---")
    try:
        url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        search_request = {}
        response = requests.post(url, headers=headers, json=search_request, timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search API successful: {len(data.get('mediaItems', []))} items")
        else:
            print(f"❌ Search API failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Search API error: {e}")
    
    # Test 3: Albums API call
    print("\n--- Test 3: Albums API Call ---")
    try:
        url = "https://photoslibrary.googleapis.com/v1/albums"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Albums API successful: {len(data.get('albums', []))} albums")
        else:
            print(f"❌ Albums API failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Albums API error: {e}")

if __name__ == "__main__":
    test_google_photos()