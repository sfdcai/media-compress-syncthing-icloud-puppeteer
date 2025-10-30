#!/bin/bash

# ADB-based Pixel Backup Gang Deployment
# Uses ADB instead of SSH for file transfer

PIXEL_IP="192.168.1.198"
ADB_PORT="5555"

echo "🚀 Pixel Backup Gang - ADB Deployment"
echo "====================================="
echo ""

# Check if ADB is available
if ! command -v adb >/dev/null 2>&1; then
    echo "❌ ADB not found. Please install Android SDK platform-tools"
    echo "   Ubuntu/Debian: sudo apt install android-tools-adb"
    echo "   Or download from: https://developer.android.com/studio/releases/platform-tools"
    exit 1
fi

echo "✅ ADB found"
echo ""

# Check if files exist
if [ ! -f "pixel_backup_gang.zip" ]; then
    echo "❌ pixel_backup_gang.zip not found"
    exit 1
fi

if [ ! -f "magisk_module_pixel_backup/credentials.json" ]; then
    echo "❌ credentials.json not found"
    exit 1
fi

echo "✅ All files found"
echo ""

# Connect to device via ADB
echo "📱 Connecting to Pixel device at $PIXEL_IP:$ADB_PORT..."
adb connect $PIXEL_IP:$ADB_PORT

# Check if device is connected
if ! adb devices | grep -q "$PIXEL_IP"; then
    echo "❌ Cannot connect to device. Make sure:"
    echo "   1. USB debugging is enabled on your Pixel"
    echo "   2. ADB over WiFi is enabled"
    echo "   3. Device is on the same network"
    echo "   4. IP address is correct: $PIXEL_IP"
    echo ""
    echo "To enable ADB over WiFi:"
    echo "   1. Connect via USB first: adb tcpip 5555"
    echo "   2. Then disconnect USB and run this script"
    exit 1
fi

echo "✅ Device connected"
echo ""

# Check if device is rooted
echo "🔍 Checking if device is rooted..."
if adb shell "su -c 'id'" 2>/dev/null | grep -q "uid=0"; then
    echo "✅ Device is rooted"
else
    echo "❌ Device is not rooted or su not available"
    echo "   This module requires root access via Magisk"
    exit 1
fi

# Transfer files
echo "📦 Transferring files to device..."

# Transfer module zip
echo "   - Transferring pixel_backup_gang.zip..."
adb push pixel_backup_gang.zip /sdcard/Download/
if [ $? -eq 0 ]; then
    echo "   ✅ Module transferred successfully"
else
    echo "   ❌ Failed to transfer module"
    exit 1
fi

# Transfer config file
echo "   - Transferring credentials.json..."
adb push magisk_module_pixel_backup/credentials.json /sdcard/Download/
if [ $? -eq 0 ]; then
    echo "   ✅ Config transferred successfully"
else
    echo "   ❌ Failed to transfer config"
    exit 1
fi

echo ""
echo "✅ All files transferred successfully!"
echo ""

# Show next steps
echo "📱 Next steps on your Pixel device:"
echo "1. Open Magisk Manager"
echo "2. Go to Modules tab"
echo "3. Tap '+' button to install module"
echo "4. Navigate to Downloads folder"
echo "5. Select pixel_backup_gang.zip"
echo "6. Install and reboot"
echo "7. After reboot, copy credentials.json to /data/adb/modules/pixel_backup_gang/"
echo "8. Edit credentials.json with your Telegram details"
echo ""

# Optional: Try to install module automatically
read -p "🤖 Try to install module automatically? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Attempting automatic installation..."
    
    # Check if Magisk is installed
    if adb shell "pm list packages | grep -q magisk"; then
        echo "✅ Magisk found"
        
        # Try to install module via Magisk
        echo "📦 Installing module..."
        adb shell "su -c 'magisk --install-module /sdcard/Download/pixel_backup_gang.zip'"
        
        if [ $? -eq 0 ]; then
            echo "✅ Module installed successfully!"
            echo "🔄 Reboot your device to activate the module"
        else
            echo "❌ Automatic installation failed. Please install manually via Magisk Manager"
        fi
    else
        echo "❌ Magisk not found. Please install manually via Magisk Manager"
    fi
fi

echo ""
echo "🎉 Deployment complete!"
echo "📋 Check logs after reboot: adb shell 'su -c \"tail -f /data/adb/modules/pixel_backup_gang/logs/backup.log\"'"