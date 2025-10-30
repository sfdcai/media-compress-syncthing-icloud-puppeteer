# Google Photos OAuth Fix for Headless Server

## 🚨 Problem
Google OAuth doesn't allow private IP addresses (like `192.168.1.7:8080`) for redirect URIs. This causes the error:
```
device_id and device_name are required for private IP: http://192.168.1.7:8080
Error 400: invalid_request
```

## ✅ Solution

### Step 1: Update Google Cloud Console OAuth Settings

1. **Go to Google Cloud Console**:
   - Visit: https://console.cloud.google.com/
   - Select your project

2. **Navigate to OAuth Consent Screen**:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Click "Edit App"

3. **Add Redirect URI**:
   - Scroll down to "Authorized redirect URIs"
   - Click "Add URI"
   - Add: `http://localhost:8080`
   - Click "Save"

4. **Verify Google Photos Library API is Enabled**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Photos Library API"
   - Make sure it's enabled

### Step 2: Use the Fixed Authorization

The system now uses `http://localhost:8080` as the redirect URI, which Google accepts.

### Step 3: Complete Authorization

1. **Via Web Dashboard**:
   - Go to http://192.168.1.7:5000
   - Click "Configuration" tab
   - Find Google Photos section
   - Click "Authorize Google Photos"
   - Complete OAuth in browser
   - Copy code from redirect URL
   - Paste code in the input field

2. **Via Command Line**:
   ```bash
   cd /opt/media-pipeline
   python3 setup_google_photos_oauth.py
   ```

## 🔧 Technical Details

### What Changed
- Redirect URI changed from `http://192.168.1.7:8080` to `http://localhost:8080`
- Added better error handling and instructions
- Created setup script for easier configuration

### Why This Works
- Google OAuth accepts `localhost` redirects
- The authorization code is captured manually
- No need for a running web server on port 8080

## 🎯 Expected Result

After completing the setup:
- ✅ OAuth authorization will work
- ✅ Google Photos API will be accessible
- ✅ Sync status checker will function
- ✅ You can retrieve photo details

## 🚀 Quick Test

Run this to verify everything is working:
```bash
cd /opt/media-pipeline
python3 -c "
import sys
sys.path.append('.')
from scripts.google_photos_sync_checker import GooglePhotosSyncChecker
checker = GooglePhotosSyncChecker()
print('Token valid:', checker.test_token())
"
```

## 📝 Troubleshooting

If you still get errors:
1. Double-check the redirect URI in Google Cloud Console
2. Make sure Google Photos Library API is enabled
3. Verify your OAuth consent screen is configured
4. Check that the authorization code is copied correctly