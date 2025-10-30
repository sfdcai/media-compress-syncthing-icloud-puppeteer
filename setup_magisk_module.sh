#!/bin/bash

# Google Photos Uploader Magisk Module Setup Script
# This script helps set up the Magisk module for your Pixel device

set -e

echo "🚀 Google Photos Uploader Magisk Module Setup"
echo "=============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "magisk_module/module.prop" ]; then
    echo "❌ Error: Please run this script from the media-pipeline root directory"
    exit 1
fi

# Create the zip file
echo "📦 Creating Magisk module package..."
cd magisk_module
zip -r ../google_photos_uploader.zip . -x "*.git*" "*.DS_Store*"
cd ..

echo "✅ Module package created: google_photos_uploader.zip"
echo ""

# Generate configuration template
echo "⚙️  Generating configuration template..."
cat > magisk_module_config_template.json << 'EOF'
{
  "google_photos": {
    "client_id": "YOUR_GOOGLE_CLIENT_ID_HERE",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET_HERE", 
    "refresh_token": "YOUR_REFRESH_TOKEN_HERE"
  },
  "upload": {
    "enabled": true,
    "interval_seconds": 60,
    "max_file_size_mb": 100,
    "supported_formats": [".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"],
    "auto_delete_after_upload": false,
    "delete_delay_hours": 24
  },
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID_HERE",
    "debug_mode": false
  },
  "directories": {
    "camera": "/sdcard/DCIM/Camera",
    "screenshots": "/sdcard/Pictures/Screenshots",
    "downloads": "/sdcard/Download"
  }
}
EOF

echo "✅ Configuration template created: magisk_module_config_template.json"
echo ""

# Create setup instructions
cat > MAGISK_MODULE_SETUP.md << 'EOF'
# Magisk Module Setup Instructions

## Prerequisites

1. **Rooted Pixel device** with Magisk installed
2. **Python 3** installed on device (via Termux or similar)
3. **Google Photos API** credentials
4. **Telegram Bot** (optional, for notifications)

## Step 1: Get Google Photos API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Photos Library API**
4. Create OAuth 2.0 credentials
5. Add redirect URI: `http://localhost:8080`
6. Note down your Client ID and Client Secret

## Step 2: Generate Refresh Token

Run this command on your server to get the refresh token:

```bash
cd /opt/media-pipeline
python3 scripts/google_photos_auth_manual.py
```

Follow the instructions to get the refresh token.

## Step 3: Configure the Module

1. Copy `magisk_module_config_template.json` to your Pixel device
2. Edit the file with your credentials:
   - Replace `YOUR_GOOGLE_CLIENT_ID_HERE` with your Client ID
   - Replace `YOUR_GOOGLE_CLIENT_SECRET_HERE` with your Client Secret
   - Replace `YOUR_REFRESH_TOKEN_HERE` with your refresh token
   - Replace `YOUR_TELEGRAM_BOT_TOKEN_HERE` with your bot token (optional)
   - Replace `YOUR_TELEGRAM_CHAT_ID_HERE` with your chat ID (optional)

3. Rename the file to `config.json`

## Step 4: Install the Module

1. Copy `google_photos_uploader.zip` to your Pixel device
2. Open Magisk Manager
3. Go to Modules tab
4. Tap the "+" button
5. Select `google_photos_uploader.zip`
6. Wait for installation to complete
7. Reboot your device

## Step 5: Configure the Module

1. After reboot, copy your `config.json` to:
   `/data/adb/modules/google_photos_uploader/config.json`

2. Set proper permissions:
   ```bash
   chmod 644 /data/adb/modules/google_photos_uploader/config.json
   ```

3. Restart the service:
   ```bash
   /data/adb/service.d/99_google_photos_uploader.sh
   ```

## Step 6: Verify Installation

1. Check logs:
   ```bash
   tail -f /data/adb/modules/google_photos_uploader/logs/uploader.log
   ```

2. Check service status:
   ```bash
   cat /data/adb/modules/google_photos_uploader/logs/service.log
   ```

3. Test by taking a photo and checking if it uploads

## Troubleshooting

### Common Issues

1. **Module not starting**
   - Check if Python 3 is installed
   - Verify config.json is in the right location
   - Check service logs

2. **Upload failures**
   - Verify Google Photos API credentials
   - Check network connectivity
   - Review uploader logs

3. **Permission errors**
   - Ensure proper file permissions
   - Check if device is properly rooted

### Logs Location

- Service log: `/data/adb/modules/google_photos_uploader/logs/service.log`
- Uploader log: `/data/adb/modules/google_photos_uploader/logs/uploader.log`
- State file: `/data/adb/modules/google_photos_uploader/state.json`

## Features

- ✅ Automatic photo upload to Google Photos
- ✅ No permanent storage on device (NAND-free)
- ✅ Optional auto-deletion after upload
- ✅ Telegram notifications
- ✅ Robust error handling and retry logic
- ✅ Production-ready and optimized

## Security Notes

- Store credentials securely
- Use HTTPS for all API calls
- Avoid logging sensitive information
- Regular security updates recommended
EOF

echo "✅ Setup instructions created: MAGISK_MODULE_SETUP.md"
echo ""

# Create verification script
cat > verify_magisk_module.py << 'EOF'
#!/usr/bin/env python3
"""
Verify Magisk module installation and configuration
"""

import os
import json
import requests
from datetime import datetime

def check_module_installation():
    """Check if module is properly installed"""
    print("🔍 Checking Magisk module installation...")
    
    module_dir = "/data/adb/modules/google_photos_uploader"
    required_files = [
        "uploader.py",
        "config.json",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(module_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def check_configuration():
    """Check module configuration"""
    print("\n⚙️  Checking configuration...")
    
    config_file = "/data/adb/modules/google_photos_uploader/config.json"
    if not os.path.exists(config_file):
        print("❌ Config file not found")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check required fields
        required_fields = [
            'google_photos.client_id',
            'google_photos.client_secret',
            'google_photos.refresh_token'
        ]
        
        missing_fields = []
        for field in required_fields:
            keys = field.split('.')
            value = config
            for key in keys:
                value = value.get(key, {})
            if not value or value == f"YOUR_{key.upper()}_HERE":
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing or invalid configuration: {missing_fields}")
            return False
        else:
            print("✅ Configuration looks good")
            return True
            
    except Exception as e:
        print(f"❌ Config file error: {e}")
        return False

def check_google_photos_auth():
    """Check Google Photos authentication"""
    print("\n🔐 Testing Google Photos authentication...")
    
    try:
        config_file = "/data/adb/modules/google_photos_uploader/config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Test refresh token
        url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': config['google_photos']['client_id'],
            'client_secret': config['google_photos']['client_secret'],
            'refresh_token': config['google_photos']['refresh_token'],
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("✅ Google Photos authentication successful")
            return True
        else:
            print(f"❌ Google Photos authentication failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test error: {e}")
        return False

def check_telegram_config():
    """Check Telegram configuration"""
    print("\n📱 Checking Telegram configuration...")
    
    try:
        config_file = "/data/adb/modules/google_photos_uploader/config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if not config['telegram']['enabled']:
            print("ℹ️  Telegram notifications disabled")
            return True
        
        bot_token = config['telegram']['bot_token']
        chat_id = config['telegram']['chat_id']
        
        if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            print("⚠️  Telegram bot token not configured")
            return False
        
        if not chat_id or chat_id == "YOUR_TELEGRAM_CHAT_ID_HERE":
            print("⚠️  Telegram chat ID not configured")
            return False
        
        # Test Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Telegram configuration valid")
            return True
        else:
            print(f"❌ Telegram API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram test error: {e}")
        return False

def check_logs():
    """Check module logs"""
    print("\n📋 Checking logs...")
    
    log_dir = "/data/adb/modules/google_photos_uploader/logs"
    if not os.path.exists(log_dir):
        print("❌ Log directory not found")
        return False
    
    log_files = [
        "service.log",
        "uploader.log"
    ]
    
    for log_file in log_files:
        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            print(f"✅ {log_file}: {size} bytes")
        else:
            print(f"⚠️  {log_file}: Not found")
    
    return True

def main():
    """Main verification function"""
    print("🔍 Google Photos Uploader Module Verification")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    checks = [
        check_module_installation,
        check_configuration,
        check_google_photos_auth,
        check_telegram_config,
        check_logs
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Verification Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("✅ All checks passed! Module is ready to use.")
    else:
        print(f"⚠️  {passed}/{total} checks passed. Please fix the issues above.")
    
    print(f"\nFor detailed logs, check: /data/adb/modules/google_photos_uploader/logs/")

if __name__ == "__main__":
    main()
EOF

chmod +x verify_magisk_module.py

echo "✅ Verification script created: verify_magisk_module.py"
echo ""

# Create deployment script for Pixel device
cat > deploy_to_pixel.sh << 'EOF'
#!/bin/bash

# Deploy Magisk module to Pixel device
# Usage: ./deploy_to_pixel.sh <pixel_ip>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <pixel_ip>"
    echo "Example: $0 192.168.1.198"
    exit 1
fi

PIXEL_IP=$1
echo "🚀 Deploying to Pixel device at $PIXEL_IP"

# Check if device is reachable
echo "📡 Checking device connectivity..."
if ! ping -c 1 $PIXEL_IP > /dev/null 2>&1; then
    echo "❌ Cannot reach device at $PIXEL_IP"
    exit 1
fi

echo "✅ Device is reachable"

# Copy module files
echo "📦 Copying module files..."
scp google_photos_uploader.zip root@$PIXEL_IP:/sdcard/
scp magisk_module_config_template.json root@$PIXEL_IP:/sdcard/
scp verify_magisk_module.py root@$PIXEL_IP:/sdcard/

echo "✅ Files copied to device"
echo ""
echo "📱 Next steps on your Pixel device:"
echo "1. Open Magisk Manager"
echo "2. Install google_photos_uploader.zip"
echo "3. Configure config.json with your credentials"
echo "4. Reboot device"
echo "5. Run: python3 /sdcard/verify_magisk_module.py"
EOF

chmod +x deploy_to_pixel.sh

echo "✅ Deployment script created: deploy_to_pixel.sh"
echo ""

echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review MAGISK_MODULE_SETUP.md for detailed instructions"
echo "2. Configure your Google Photos API credentials"
echo "3. Deploy to your Pixel device: ./deploy_to_pixel.sh 192.168.1.198"
echo "4. Install the module via Magisk Manager"
echo "5. Configure and test the module"
echo ""
echo "📁 Files created:"
echo "  - google_photos_uploader.zip (Magisk module package)"
echo "  - magisk_module_config_template.json (Configuration template)"
echo "  - MAGISK_MODULE_SETUP.md (Setup instructions)"
echo "  - verify_magisk_module.py (Verification script)"
echo "  - deploy_to_pixel.sh (Deployment script)"
echo ""
echo "🔧 For verification, run: python3 verify_magisk_module.py"