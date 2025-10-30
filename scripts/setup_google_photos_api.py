#!/usr/bin/env python3
"""
Google Photos API Setup Script
Helps configure Google Photos API for sync checking
"""

import os
import json
import webbrowser
from pathlib import Path

def create_google_cloud_project_instructions():
    """Print instructions for creating Google Cloud Project"""
    print("""
Google Photos API Setup Instructions
===================================

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable the Photos Library API:
   - Go to "APIs & Services" > "Library"
   - Search for "Photos Library API"
   - Click on it and press "Enable"

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application"
   - Give it a name (e.g., "Media Pipeline Sync Checker")
   - Click "Create"

5. Download the credentials JSON file
6. Copy the client_id and client_secret to the credentials file

The credentials file should be saved as:
/opt/media-pipeline/config/google_photos_credentials.json

Example format:
{
  "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
  "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz"
}
""")

def main():
    """Main setup function"""
    print("Google Photos API Setup for Media Pipeline")
    print("=" * 50)
    
    # Check if credentials already exist
    credentials_file = "/opt/media-pipeline/config/google_photos_credentials.json"
    
    if os.path.exists(credentials_file):
        print(f"✅ Credentials file already exists: {credentials_file}")
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
            if creds.get('client_id') and creds.get('client_secret'):
                print("✅ Credentials appear to be configured")
                print("\nTo authenticate, run:")
                print("python3 /opt/media-pipeline/scripts/google_photos_sync_checker.py setup")
                return
            else:
                print("⚠️  Credentials file exists but appears incomplete")
    
    # Create template file
    template_file = "/opt/media-pipeline/config/google_photos_credentials.json.template"
    if os.path.exists(template_file):
        print(f"📋 Template file found: {template_file}")
        print("Please copy it to the credentials file and fill in your values:")
        print(f"cp {template_file} {credentials_file}")
        print("Then edit the file with your actual client_id and client_secret")
    
    # Show instructions
    create_google_cloud_project_instructions()
    
    # Create directories
    os.makedirs("/opt/media-pipeline/config", exist_ok=True)
    os.makedirs("/opt/media-pipeline/logs", exist_ok=True)
    
    print(f"\n📁 Created directories: /opt/media-pipeline/config")
    print(f"📁 Created directories: /opt/media-pipeline/logs")

if __name__ == "__main__":
    main()