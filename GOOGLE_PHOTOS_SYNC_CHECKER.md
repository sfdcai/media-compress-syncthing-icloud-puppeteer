# Google Photos Sync Checker

This script checks if files uploaded to Pixel are synced to Google Photos cloud, providing verification that the complete sync process is working.

## Features

- **API Integration**: Uses Google Photos Library API to check file sync status
- **Filename Matching**: Searches for files by exact filename and similar names
- **Date Range Filtering**: Searches within upload date ranges for better accuracy
- **Detailed Reporting**: Generates comprehensive sync status reports
- **Pipeline Integration**: Automatically runs during verification phase
- **Configurable**: Can be enabled/disabled via configuration

## Setup Instructions

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Photos Library API:
   - Go to "APIs & Services" > "Library"
   - Search for "Photos Library API"
   - Click on it and press "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application"
4. Give it a name (e.g., "Media Pipeline Sync Checker")
5. Click "Create"
6. Download the credentials JSON file

### 3. Configure Credentials

```bash
# Copy the template file
cp /opt/media-pipeline/config/google_photos_credentials.json.template /opt/media-pipeline/config/google_photos_credentials.json

# Edit the file with your credentials
nano /opt/media-pipeline/config/google_photos_credentials.json
```

Example credentials file:
```json
{
  "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
  "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz"
}
```

### 4. Authenticate

```bash
# Run the setup script
python3 /opt/media-pipeline/scripts/setup_google_photos_api.py

# Authenticate with Google
python3 /opt/media-pipeline/scripts/google_photos_sync_checker.py setup
```

Follow the instructions to get the authorization code and complete authentication.

## Configuration

Add these settings to your `config/settings.env`:

```env
# Google Photos Sync Check Configuration
ENABLE_GOOGLE_PHOTOS_SYNC_CHECK=true
GOOGLE_PHOTOS_CLIENT_ID=your_client_id
GOOGLE_PHOTOS_CLIENT_SECRET=your_client_secret
```

## Usage

### Manual Sync Check

```bash
# Check sync status for all Pixel uploaded files
python3 /opt/media-pipeline/scripts/google_photos_sync_checker.py

# Setup authentication (first time only)
python3 /opt/media-pipeline/scripts/google_photos_sync_checker.py setup
```

### Automatic Pipeline Integration

The sync checker is automatically integrated into the pipeline verification phase when:
- `ENABLE_GOOGLE_PHOTOS_SYNC_CHECK=true`
- `ENABLE_PIXEL_UPLOAD=true`
- Google Photos API is properly configured

## How It Works

### 1. File Discovery
- Scans the Pixel upload directory (`UPLOADED_PIXEL_DIR`)
- Finds all media files (jpg, jpeg, png, heic, heif, mp4, mov, avi, mkv)

### 2. Google Photos Search
- Searches Google Photos for files uploaded around the same time (±1 day)
- Uses filename matching (exact and similar)
- Filters by date range for better accuracy

### 3. Sync Status Determination
- **Exact Match**: File found with identical filename
- **Similar Match**: File found with similar filename (base name matches)
- **Not Found**: No matching files found

### 4. Reporting
- Generates detailed sync status report
- Saves report to logs directory
- Logs results to pipeline logs

## Sync Status Levels

- **✅ SYNCED (80%+)**: Most files are synced successfully
- **⚠️ PARTIAL (50-79%)**: Some files are synced, needs attention
- **❌ FAILED (<50%)**: Most files not synced, requires investigation

## Report Format

```
Google Photos Sync Status Report
===============================
Generated: 2025-10-05 15:30:00

Summary:
- Total files checked: 25
- Successfully synced: 23
- Not synced: 2
- Sync rate: 92.0%

Detailed Results:

✅ SYNCED IMG_4878.JPG - Created: 2025-10-05T10:15:30Z
✅ SYNCED IMG_4875.MOV - Created: 2025-10-05T10:16:45Z
❌ NOT SYNCED IMG_4890.HEIC - Not found in Google Photos
```

## Troubleshooting

### Common Issues

1. **"Google Photos API not configured"**
   - Run the setup script: `python3 scripts/setup_google_photos_api.py`
   - Complete authentication: `python3 scripts/google_photos_sync_checker.py setup`

2. **"Access token invalid"**
   - The refresh token will automatically get a new access token
   - If this fails, re-run the setup process

3. **"No files found in Pixel upload directory"**
   - Check that `UPLOADED_PIXEL_DIR` is correctly configured
   - Ensure files have been uploaded to Pixel

4. **"Low sync rate"**
   - Check if Google Photos sync is enabled on the Pixel device
   - Verify internet connection on the Pixel device
   - Check if files are in the correct format for Google Photos

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

This will provide detailed information about the API calls and search process.

## Security Notes

- Credentials are stored in `/opt/media-pipeline/config/google_photos_credentials.json`
- Tokens are stored in `/opt/media-pipeline/config/google_photos_tokens.json`
- Both files should have restricted permissions (600)
- The script only has read-only access to Google Photos

## API Limits

- Google Photos API has rate limits
- The script includes proper error handling and retry logic
- Large file sets may take time to process

## Integration with Pipeline

The sync checker is integrated into the verification phase and will:
- Only run when Pixel upload is enabled
- Skip if Google Photos API is not configured
- Not fail the entire pipeline if sync check fails
- Generate reports in the logs directory
- Log results to the main pipeline log