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

# Check if files exist
if [ ! -f "pixel_backup_gang.zip" ]; then
    echo "❌ pixel_backup_gang.zip not found"
    exit 1
fi

if [ ! -f "magisk_module_pixel_backup/credentials.json" ]; then
    echo "❌ credentials.json not found"
    exit 1
fi

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