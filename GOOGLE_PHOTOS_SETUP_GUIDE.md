# Google Photos API Setup Guide

## ✅ **CURRENT STATUS: READY FOR AUTHENTICATION**

All components are properly configured and ready. You just need to complete the OAuth authentication.

## 🔐 **AUTHENTICATION STEPS**

### **Step 1: Get Authorization Code**

1. **Visit this URL in your browser:**
   ```
   https://accounts.google.com/o/oauth2/v2/auth?client_id=1026727790585-sfrt7quhss8a9jm442p0d7t8idnde1tv.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob&scope=https://www.googleapis.com/auth/photoslibrary.readonly&response_type=code&access_type=offline&prompt=consent
   ```

2. **Sign in to your Google account**

3. **Grant permission** for the app to access your Google Photos

4. **Copy the authorization code** from the page

### **Step 2: Complete Authentication**

Run this command and paste the authorization code when prompted:

```bash
cd /opt/media-pipeline
python3 scripts/google_photos_sync_checker.py setup
```

When prompted, paste the authorization code you copied from Step 1.

### **Step 3: Test the Setup**

After authentication, test the setup:

```bash
# Test basic functionality
python3 scripts/test_google_photos_sync.py

# Test sync checker with real files (if you have files in Pixel upload directory)
python3 scripts/google_photos_sync_checker.py
```

## 🎯 **WHAT'S ALREADY CONFIGURED**

### ✅ **Files Created:**
- `/opt/media-pipeline/scripts/google_photos_sync_checker.py` - Main sync checker
- `/opt/media-pipeline/scripts/setup_google_photos_api.py` - Setup script
- `/opt/media-pipeline/scripts/complete_google_photos_auth.py` - Authentication helper
- `/opt/media-pipeline/scripts/test_google_photos_sync.py` - Test script
- `/opt/media-pipeline/config/google_photos_credentials.json` - Your credentials
- `/opt/media-pipeline/GOOGLE_PHOTOS_SYNC_CHECKER.md` - Full documentation

### ✅ **Configuration Updated:**
- `ENABLE_GOOGLE_PHOTOS_SYNC_CHECK=true` - Feature enabled
- `GOOGLE_PHOTOS_CLIENT_ID` - Your client ID configured
- `GOOGLE_PHOTOS_CLIENT_SECRET` - Your client secret configured

### ✅ **Pipeline Integration:**
- Google Photos sync check added to verification phase
- Will run automatically when Pixel upload is enabled
- Non-blocking (won't fail pipeline if sync check fails)

## 🚀 **HOW IT WORKS**

1. **File Discovery**: Scans `/mnt/wd_all_pictures/sync/uploaded/pixel/` for media files
2. **Google Photos Search**: Uses API to search for files by filename and date
3. **Sync Verification**: Determines if files are synced to Google Photos
4. **Reporting**: Generates detailed sync status reports
5. **Pipeline Integration**: Runs automatically during verification phase

## 📊 **SYNC STATUS LEVELS**

- **✅ SYNCED (80%+)**: Most files synced successfully
- **⚠️ PARTIAL (50-79%)**: Some files synced, needs attention
- **❌ FAILED (<50%)**: Most files not synced, requires investigation

## 🔧 **TROUBLESHOOTING**

### **If authentication fails:**
1. Make sure you're using the correct Google account
2. Check that the Photos Library API is enabled in Google Cloud Console
3. Verify the client ID and secret are correct

### **If sync check fails:**
1. Check that files exist in the Pixel upload directory
2. Verify Google Photos sync is enabled on your Pixel device
3. Check the logs for detailed error messages

### **If pipeline integration fails:**
1. The sync check is non-blocking, so pipeline will continue
2. Check the verification phase logs for details
3. Ensure `ENABLE_GOOGLE_PHOTOS_SYNC_CHECK=true` is set

## 📋 **QUICK COMMANDS**

```bash
# Complete setup (interactive)
python3 scripts/complete_google_photos_auth.py

# Manual authentication
python3 scripts/google_photos_sync_checker.py setup

# Test everything
python3 scripts/test_google_photos_sync.py

# Run sync check manually
python3 scripts/google_photos_sync_checker.py

# Check configuration
grep -E "GOOGLE_PHOTOS|ENABLE_GOOGLE_PHOTOS" config/settings.env
```

## 🎉 **READY TO GO!**

Once you complete the OAuth authentication, the Google Photos sync checker will be fully operational and integrated into your media pipeline!