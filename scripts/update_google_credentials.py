#!/usr/bin/env python3
"""
Update Google Cloud Console Credentials
Instructions for updating OAuth credentials to support localhost redirect
"""

def print_instructions():
    """Print instructions for updating Google Cloud Console credentials"""
    print("""
🔧 Google Cloud Console Credentials Update Required
==================================================

The OAuth flow has been updated to use localhost redirect instead of the deprecated OOB flow.
You need to update your Google Cloud Console credentials to support this.

📋 Steps to Update Credentials:

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Select your project
3. Go to "APIs & Services" > "Credentials"
4. Find your OAuth 2.0 Client ID (the one you're using)
5. Click on it to edit
6. In the "Authorized redirect URIs" section, add:
   http://localhost:8080
7. Save the changes

📋 Alternative: Create New Credentials

If you prefer to create new credentials:

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application"
4. Give it a name (e.g., "Media Pipeline Sync Checker Localhost")
5. In "Authorized redirect URIs", add:
   http://localhost:8080
6. Click "Create"
7. Download the JSON file and update your credentials file

📋 Update Credentials File

After updating the credentials in Google Cloud Console, update your local credentials file:

/opt/media-pipeline/config/google_photos_credentials.json

Make sure it contains:
{
  "client_id": "your_new_client_id.apps.googleusercontent.com",
  "client_secret": "your_new_client_secret"
}

📋 Then Run Authentication

After updating the credentials, run:
python3 scripts/google_photos_auth_localhost.py

This will use the new localhost redirect method instead of the deprecated OOB flow.
""")

def main():
    print_instructions()

if __name__ == "__main__":
    main()