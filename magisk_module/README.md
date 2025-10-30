# Google Photos Uploader Magisk Module

A Magisk module that automatically uploads photos to Google Photos without storing them on NAND storage. Integrates seamlessly with your media pipeline system.

## Features

- 🚀 **Automatic Upload**: Monitors camera, screenshots, and downloads folders
- 💾 **NAND-Free**: No permanent storage on device
- 🔄 **Auto-Delete**: Optional automatic deletion after successful upload
- 📱 **Telegram Integration**: Real-time notifications
- 🛡️ **Robust Error Handling**: Retry logic and state persistence
- ⚡ **Production Ready**: Optimized for reliability and performance

## Installation

### Prerequisites

1. **Rooted Android device** with Magisk installed
2. **Python 3** installed on device
3. **Google Photos API** credentials
4. **Telegram Bot** (optional, for notifications)

### Step 1: Get Google Photos API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Photos Library API**
4. Create OAuth 2.0 credentials
5. Add redirect URI: `http://localhost:8080`
6. Download credentials JSON file

### Step 2: Generate Refresh Token

Use the provided script to get refresh token:

```bash
cd /opt/media-pipeline
python3 scripts/google_photos_auth_manual.py
```

### Step 3: Configure Module

1. Edit `config.json` with your credentials:
   ```json
   {
     "google_photos": {
       "client_id": "your_client_id",
       "client_secret": "your_client_secret", 
       "refresh_token": "your_refresh_token"
     },
     "telegram": {
       "bot_token": "your_bot_token",
       "chat_id": "your_chat_id"
     }
   }
   ```

### Step 4: Install Module

1. Package the module:
   ```bash
   cd /opt/media-pipeline/magisk_module
   zip -r google_photos_uploader.zip .
   ```

2. Install via Magisk Manager:
   - Open Magisk Manager
   - Go to Modules tab
   - Tap "+" button
   - Select `google_photos_uploader.zip`
   - Reboot device

## Configuration

### Upload Settings

```json
{
  "upload": {
    "enabled": true,                    // Enable/disable uploader
    "interval_seconds": 60,             // Scan interval
    "max_file_size_mb": 100,           // Max file size to upload
    "supported_formats": [".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"],
    "auto_delete_after_upload": false, // Auto-delete after upload
    "delete_delay_hours": 24           // Delay before deletion
  }
}
```

### Telegram Notifications

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID",
    "debug_mode": false
  }
}
```

### Directory Monitoring

```json
{
  "directories": {
    "camera": "/sdcard/DCIM/Camera",
    "screenshots": "/sdcard/Pictures/Screenshots", 
    "downloads": "/sdcard/Download"
  }
}
```

## Usage

### Manual Control

```bash
# Start uploader manually
python3 /data/adb/modules/google_photos_uploader/uploader.py

# Check logs
tail -f /data/adb/modules/google_photos_uploader/logs/uploader.log

# Check service status
cat /data/adb/modules/google_photos_uploader/logs/service.log
```

### Telegram Commands

Send these commands to your Telegram bot:

- `/status` - Check uploader status
- `/logs` - Get recent logs
- `/stats` - Upload statistics
- `/restart` - Restart uploader

## Verification

### Check Upload Status

1. **Logs**: Check `/data/adb/modules/google_photos_uploader/logs/uploader.log`
2. **State**: Check `/data/adb/modules/google_photos_uploader/state.json`
3. **Telegram**: Monitor notifications
4. **Google Photos**: Check your Google Photos library

### Debug Mode

Enable debug mode in config:

```json
{
  "telegram": {
    "debug_mode": true
  }
}
```

This will send detailed debug information to Telegram.

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check client_id and client_secret
   - Verify refresh_token is valid
   - Ensure Google Photos API is enabled

2. **Upload Failures**
   - Check file permissions
   - Verify network connectivity
   - Check file size limits

3. **Module Not Starting**
   - Check Magisk installation
   - Verify Python 3 is installed
   - Check service logs

### Logs

- **Service Log**: `/data/adb/modules/google_photos_uploader/logs/service.log`
- **Uploader Log**: `/data/adb/modules/google_photos_uploader/logs/uploader.log`
- **State File**: `/data/adb/modules/google_photos_uploader/state.json`

## Advanced Features

### AI-Driven Cleanup

Future enhancement for intelligent file management:

```python
def ai_cleanup_analysis(file_path: str) -> Dict:
    """Analyze file for cleanup decisions"""
    # Analyze file content, quality, duplicates
    # Make intelligent deletion recommendations
    pass
```

### Smart Retry Logic

```python
def smart_retry_upload(file_path: str, max_retries: int = 3) -> bool:
    """Smart retry with exponential backoff"""
    for attempt in range(max_retries):
        if upload_file(file_path):
            return True
        time.sleep(2 ** attempt)  # Exponential backoff
    return False
```

### Batch Processing

```python
def batch_upload(files: List[str], batch_size: int = 5) -> Dict:
    """Upload files in batches for efficiency"""
    results = {'success': [], 'failed': []}
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        # Process batch
    return results
```

## Security Considerations

1. **Credentials**: Store securely, never commit to version control
2. **Permissions**: Minimal required permissions
3. **Network**: Use HTTPS for all API calls
4. **Logs**: Avoid logging sensitive information

## Performance Optimization

1. **File Scanning**: Efficient directory traversal
2. **Memory Usage**: Stream large files
3. **Network**: Connection pooling and timeouts
4. **Storage**: Cleanup temporary files

## Future Enhancements

- 🤖 **AI-Driven Cleanup**: Intelligent duplicate detection and quality analysis
- 📊 **Analytics Dashboard**: Upload statistics and trends
- 🔄 **Smart Sync**: Bidirectional sync with media pipeline
- 🎯 **Selective Upload**: Upload only specific file types or quality
- 🌐 **Multi-Cloud**: Support for other cloud providers
- 📱 **Mobile App**: Companion app for configuration and monitoring

## Support

For issues and questions:

1. Check logs first
2. Review configuration
3. Test with debug mode
4. Check Google Photos API status
5. Verify network connectivity

## License

This module is part of the Media Pipeline System and follows the same license terms.