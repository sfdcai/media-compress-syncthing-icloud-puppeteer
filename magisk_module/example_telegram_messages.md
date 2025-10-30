# Example Telegram Messages

## Info Mode Messages

### Startup
```
📱 Google Photos Uploader
🚀 Google Photos Uploader started
```

### Successful Upload
```
📱 Google Photos Uploader
✅ Uploaded: IMG_20241005_143022.jpg
```

### Batch Upload
```
📱 Google Photos Uploader
✅ Uploaded: IMG_20241005_143022.jpg
✅ Uploaded: IMG_20241005_143045.heic
✅ Uploaded: Screenshot_20241005_143100.png
```

### Auto-Delete
```
📱 Google Photos Uploader
🗑️ Deleted: IMG_20241005_143022.jpg
```

### Service Stop
```
📱 Google Photos Uploader
🛑 Google Photos Uploader stopped
```

## Debug Mode Messages

### Authentication
```
📱 Google Photos Uploader [DEBUG]
🔐 Authenticating with Google Photos API...
✅ Authentication successful
```

### File Discovery
```
📱 Google Photos Uploader [DEBUG]
🔍 Scanning directories...
📁 Camera: 5 new files
📁 Screenshots: 2 new files
📁 Downloads: 0 new files
📊 Total: 7 files to upload
```

### Upload Process
```
📱 Google Photos Uploader [DEBUG]
📤 Uploading: IMG_20241005_143022.jpg (2.3 MB)
⏳ Uploading raw bytes...
✅ Raw bytes uploaded successfully
⏳ Creating media item...
✅ Media item created successfully
✅ Upload completed in 3.2s
```

### Error Handling
```
📱 Google Photos Uploader [DEBUG]
❌ Upload failed: IMG_20241005_143022.jpg
🔍 Error: Network timeout
🔄 Retrying in 30 seconds...
```

### Configuration
```
📱 Google Photos Uploader [DEBUG]
⚙️ Configuration loaded:
  - Upload enabled: true
  - Interval: 60s
  - Max file size: 100MB
  - Auto-delete: false
  - Telegram notifications: true
```

### State Management
```
📱 Google Photos Uploader [DEBUG]
💾 State updated:
  - Uploaded files: 1,234
  - Failed files: 12
  - Last scan: 2024-10-05 14:30:22
```

### Network Status
```
📱 Google Photos Uploader [DEBUG]
🌐 Network check:
  - Google Photos API: ✅ Online
  - Telegram API: ✅ Online
  - Upload speed: 2.1 MB/s
```

### File Analysis
```
📱 Google Photos Uploader [DEBUG]
📊 File analysis:
  - Format: HEIC
  - Size: 3.2 MB
  - Resolution: 3024x4032
  - Quality: High
  - Duplicate check: ✅ Unique
```

### Performance Metrics
```
📱 Google Photos Uploader [DEBUG]
📈 Performance metrics:
  - Uploads today: 45
  - Success rate: 98.2%
  - Average upload time: 2.8s
  - Storage saved: 145.6 MB
```

### System Status
```
📱 Google Photos Uploader [DEBUG]
🖥️ System status:
  - CPU usage: 12%
  - Memory usage: 45 MB
  - Storage free: 8.2 GB
  - Battery level: 78%
```

## Error Messages

### Authentication Errors
```
📱 Google Photos Uploader
❌ Authentication failed: Invalid refresh token
🔧 Please check your Google Photos API credentials
```

### Upload Errors
```
📱 Google Photos Uploader
❌ Upload failed: IMG_20241005_143022.jpg
🔍 Error: File too large (150 MB > 100 MB limit)
```

### Network Errors
```
📱 Google Photos Uploader
❌ Network error: Connection timeout
🔄 Retrying in 60 seconds...
```

### Configuration Errors
```
📱 Google Photos Uploader
❌ Configuration error: Missing client_id
🔧 Please update your config.json file
```

### Permission Errors
```
📱 Google Photos Uploader
❌ Permission denied: Cannot access /sdcard/DCIM/Camera
🔧 Please check file permissions
```

## Status Commands

### /status
```
📱 Google Photos Uploader Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 Status: Running
📊 Uploads today: 23
✅ Success rate: 100%
⏱️ Last upload: 2 minutes ago
📁 Files in queue: 0
💾 Storage saved: 67.3 MB
```

### /logs
```
📱 Google Photos Uploader Logs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[14:30:22] INFO: Starting scan...
[14:30:23] INFO: Found 3 new files
[14:30:24] INFO: Uploading IMG_001.jpg
[14:30:27] INFO: Upload successful
[14:30:28] INFO: Uploading IMG_002.heic
[14:30:31] INFO: Upload successful
```

### /stats
```
📱 Google Photos Uploader Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total uploads: 1,234
📈 Success rate: 98.2%
💾 Storage saved: 2.3 GB
📅 Last 24h: 45 uploads
📅 Last 7 days: 312 uploads
📅 Last 30 days: 1,189 uploads
```

## Configuration Examples

### Basic Configuration
```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "123456789",
    "debug_mode": false
  }
}
```

### Debug Configuration
```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "123456789",
    "debug_mode": true
  }
}
```

### Minimal Configuration
```json
{
  "telegram": {
    "enabled": false
  }
}
```