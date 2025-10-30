#!/bin/bash

# Pixel Backup Gang Setup Script
# Integrates with Pixel's built-in Google Photos backup system

set -e

echo "🚀 Pixel Backup Gang Setup"
echo "=========================="
echo ""

# Check if we're in the right directory
if [ ! -f "magisk_module_pixel_backup/module.prop" ]; then
    echo "❌ Error: Please run this script from the media-pipeline root directory"
    exit 1
fi

# Create the zip file
echo "📦 Creating Magisk module package..."
cd magisk_module_pixel_backup
zip -r ../pixel_backup_gang.zip . -x "*.git*" "*.DS_Store*"
cd ..

echo "✅ Module package created: pixel_backup_gang.zip"
echo ""

# Create deployment script
cat > deploy_pixel_backup.sh << 'EOF'
#!/bin/bash

# Deploy Pixel Backup Gang to Pixel device
# Usage: ./deploy_pixel_backup.sh <pixel_ip>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <pixel_ip>"
    echo "Example: $0 192.168.1.198"
    exit 1
fi

PIXEL_IP=$1
echo "🚀 Deploying Pixel Backup Gang to $PIXEL_IP"

# Check if device is reachable
echo "📡 Checking device connectivity..."
if ! ping -c 1 $PIXEL_IP > /dev/null 2>&1; then
    echo "❌ Cannot reach device at $PIXEL_IP"
    exit 1
fi

echo "✅ Device is reachable"

# Copy module files
echo "📦 Copying module files..."
scp pixel_backup_gang.zip root@$PIXEL_IP:/sdcard/
scp magisk_module_pixel_backup/credentials.json root@$PIXEL_IP:/sdcard/pixel_backup_config.json

echo "✅ Files copied to device"
echo ""
echo "📱 Next steps on your Pixel device:"
echo "1. Open Magisk Manager"
echo "2. Install pixel_backup_gang.zip"
echo "3. Copy pixel_backup_config.json to /data/adb/modules/pixel_backup_gang/credentials.json"
echo "4. Configure your Telegram credentials in the config file"
echo "5. Reboot device"
echo "6. Check logs: tail -f /data/adb/modules/pixel_backup_gang/logs/backup.log"
EOF

chmod +x deploy_pixel_backup.sh

echo "✅ Deployment script created: deploy_pixel_backup.sh"
echo ""

# Create verification script
cat > verify_pixel_backup.py << 'EOF'
#!/usr/bin/env python3
"""
Verify Pixel Backup Gang installation and configuration
"""

import os
import json
import subprocess
from datetime import datetime

def check_module_installation():
    """Check if module is properly installed"""
    print("🔍 Checking Pixel Backup Gang installation...")
    
    module_dir = "/data/adb/modules/pixel_backup_gang"
    required_files = [
        "backup_manager.py",
        "backup_script.sh",
        "credentials.json"
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

def check_google_photos_backup():
    """Check Google Photos backup status"""
    print("\n📱 Checking Google Photos backup status...")
    
    try:
        # Check backup settings
        result = subprocess.run(['settings', 'get', 'global', 'backup_photos_enabled'], 
                              capture_output=True, text=True)
        backup_photos = result.stdout.strip()
        
        result = subprocess.run(['settings', 'get', 'global', 'backup_videos_enabled'], 
                              capture_output=True, text=True)
        backup_videos = result.stdout.strip()
        
        result = subprocess.run(['settings', 'get', 'global', 'auto_backup_enabled'], 
                              capture_output=True, text=True)
        auto_backup = result.stdout.strip()
        
        print(f"Backup Photos: {backup_photos}")
        print(f"Backup Videos: {backup_videos}")
        print(f"Auto Backup: {auto_backup}")
        
        if backup_photos == '1' and backup_videos == '1' and auto_backup == '1':
            print("✅ Google Photos backup is properly configured")
            return True
        else:
            print("⚠️  Google Photos backup needs configuration")
            return False
            
    except Exception as e:
        print(f"❌ Error checking backup status: {e}")
        return False

def check_network_connectivity():
    """Check network connectivity"""
    print("\n🌐 Checking network connectivity...")
    
    try:
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                              capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ Network connectivity OK")
            return True
        else:
            print("❌ No network connectivity")
            return False
    except Exception as e:
        print(f"❌ Network check failed: {e}")
        return False

def check_logs():
    """Check module logs"""
    print("\n📋 Checking logs...")
    
    log_dir = "/data/adb/modules/pixel_backup_gang/logs"
    if not os.path.exists(log_dir):
        print("❌ Log directory not found")
        return False
    
    log_files = [
        "backup.log",
        "backup_manager.log",
        "service.log"
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
    print("🔍 Pixel Backup Gang Verification")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    checks = [
        check_module_installation,
        check_google_photos_backup,
        check_network_connectivity,
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
    
    print("\n" + "=" * 40)
    print("📊 Verification Summary")
    print("=" * 40)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("✅ All checks passed! Pixel Backup Gang is ready.")
    else:
        print(f"⚠️  {passed}/{total} checks passed. Please fix the issues above.")
    
    print(f"\nFor detailed logs, check: /data/adb/modules/pixel_backup_gang/logs/")

if __name__ == "__main__":
    main()
EOF

chmod +x verify_pixel_backup.py

echo "✅ Verification script created: verify_pixel_backup.py"
echo ""

# Create comprehensive guide
cat > PIXEL_BACKUP_GANG_GUIDE.md << 'EOF'
# Pixel Backup Gang - Complete Integration Guide

## 🎯 **Overview**

This solution leverages the **Pixel Backup Gang** approach, which uses the Pixel's built-in Google Photos backup system instead of custom API integration. This is much more reliable and doesn't require Google Photos API credentials.

## 🚀 **How It Works**

### **Built-in Google Photos Backup**
- Uses Pixel's native backup system
- No custom API integration needed
- Leverages existing Google Photos app
- Automatic sync to Google Photos cloud

### **Monitoring & Management**
- Monitors file changes in camera/screenshots folders
- Triggers backup when new files are detected
- Provides Telegram notifications
- Manages backup settings automatically

## 📦 **Installation**

### **Step 1: Deploy to Pixel Device**
```bash
# Deploy the module to your Pixel
./deploy_pixel_backup.sh 192.168.1.198
```

### **Step 2: Install via Magisk Manager**
1. Open Magisk Manager on your Pixel
2. Go to Modules tab
3. Tap "+" button
4. Select `pixel_backup_gang.zip`
5. Reboot device

### **Step 3: Configure**
1. Copy `pixel_backup_config.json` to `/data/adb/modules/pixel_backup_gang/credentials.json`
2. Edit the file with your Telegram credentials
3. Reboot device

## ⚙️ **Configuration**

### **Basic Configuration:**
```json
{
  "telegram": {
    "bot_token": "your_bot_token",
    "chat_id": "your_chat_id",
    "enabled": true
  },
  "backup_settings": {
    "enabled": true,
    "interval_seconds": 60,
    "wifi_only": false
  }
}
```

### **Advanced Settings:**
- **Backup Frequency**: How often to check for new files
- **WiFi Only**: Only backup when connected to WiFi
- **File Monitoring**: Which directories to monitor
- **Auto Cleanup**: Optional file cleanup after backup

## 🔍 **Verification**

### **Check Installation:**
```bash
# Run verification script
python3 verify_pixel_backup.py
```

### **Manual Checks:**
```bash
# Check backup status
settings get global backup_photos_enabled
settings get global backup_videos_enabled
settings get global auto_backup_enabled

# Check logs
tail -f /data/adb/modules/pixel_backup_gang/logs/backup.log
```

## 📱 **How It Leverages Pixel's Built-in System**

### **1. Native Backup Settings**
- Enables Google Photos backup in system settings
- Configures backup transport to Google
- Sets automatic backup frequency

### **2. File Monitoring**
- Monitors camera, screenshots, and download folders
- Detects new files automatically
- Triggers backup when files are found

### **3. Backup Management**
- Uses `bmgr` (Backup Manager) to control backups
- Forces backup sync when needed
- Monitors backup progress

### **4. Integration with Google Photos App**
- Works with existing Google Photos app
- No custom API calls needed
- Uses Pixel's native backup infrastructure

## 🎉 **Benefits Over Custom API**

### **Reliability:**
- ✅ Uses Pixel's proven backup system
- ✅ No API rate limits or restrictions
- ✅ No authentication token management
- ✅ Works with Google's infrastructure

### **Simplicity:**
- ✅ No Google Photos API credentials needed
- ✅ No custom upload implementation
- ✅ Leverages existing Google Photos app
- ✅ Automatic sync to cloud

### **Performance:**
- ✅ Optimized for Pixel devices
- ✅ Background processing
- ✅ Efficient file handling
- ✅ Native Android integration

## 📊 **Monitoring & Notifications**

### **Telegram Notifications:**
```
📱 Pixel Backup Gang
📸 Found 3 new files
⏳ Backup in progress...
✅ Backup completed
```

### **Log Monitoring:**
- Real-time backup status
- File detection logs
- Error reporting
- Performance metrics

## 🔧 **Troubleshooting**

### **Common Issues:**

#### **Backup Not Starting**
```bash
# Check backup settings
settings get global backup_photos_enabled
settings get global auto_backup_enabled

# Force enable backup
settings put global backup_photos_enabled 1
settings put global auto_backup_enabled 1
```

#### **Files Not Detected**
```bash
# Check file permissions
ls -la /sdcard/DCIM/Camera/

# Check monitoring directories
cat /data/adb/modules/pixel_backup_gang/credentials.json
```

#### **Network Issues**
```bash
# Check network connectivity
ping 8.8.8.8

# Check WiFi status
dumpsys wifi | grep mWifiInfo
```

## 🚀 **Advanced Features**

### **1. Smart Backup Triggers**
- File size monitoring
- Time-based triggers
- Network condition awareness
- Battery optimization

### **2. Backup Verification**
- Monitor backup progress
- Verify successful uploads
- Handle failed backups
- Retry mechanisms

### **3. File Management**
- Optional cleanup after backup
- Backup to server
- Duplicate detection
- Quality optimization

## 📋 **Complete Workflow**

1. **File Detection**: New photos/videos are taken
2. **Monitoring**: Pixel Backup Gang detects new files
3. **Backup Trigger**: Automatically enables Google Photos backup
4. **Sync Process**: Pixel's native backup system uploads to Google Photos
5. **Verification**: Monitor backup progress and completion
6. **Notification**: Send Telegram updates about backup status
7. **Cleanup**: Optional file cleanup after successful backup

## 🎯 **Success Criteria**

- ✅ Module installs without errors
- ✅ Google Photos backup is enabled
- ✅ New files are detected automatically
- ✅ Backup sync is triggered
- ✅ Files appear in Google Photos
- ✅ Telegram notifications work
- ✅ No custom API integration needed

---

**This approach is much simpler, more reliable, and leverages the Pixel's built-in capabilities instead of fighting against Google's API restrictions!** 🎉
EOF

echo "✅ Complete guide created: PIXEL_BACKUP_GANG_GUIDE.md"
echo ""

echo "🎉 Pixel Backup Gang setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review PIXEL_BACKUP_GANG_GUIDE.md for detailed instructions"
echo "2. Deploy to your Pixel device: ./deploy_pixel_backup.sh 192.168.1.198"
echo "3. Install the module via Magisk Manager"
echo "4. Configure your Telegram credentials"
echo "5. Test the backup functionality"
echo ""
echo "📁 Files created:"
echo "  - pixel_backup_gang.zip (Magisk module package)"
echo "  - deploy_pixel_backup.sh (Deployment script)"
echo "  - verify_pixel_backup.py (Verification script)"
echo "  - PIXEL_BACKUP_GANG_GUIDE.md (Complete guide)"
echo ""
echo "🔧 For verification, run: python3 verify_pixel_backup.py"