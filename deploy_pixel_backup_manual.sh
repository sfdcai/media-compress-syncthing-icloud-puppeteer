#!/bin/bash

# Manual Pixel Backup Gang Deployment
# This script prepares files for manual transfer

echo "🚀 Pixel Backup Gang - Manual Deployment Preparation"
echo "=================================================="
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

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p pixel_backup_deployment
cp pixel_backup_gang.zip pixel_backup_deployment/
cp magisk_module_pixel_backup/credentials.json pixel_backup_deployment/
cp README.md pixel_backup_deployment/

# Create a simple transfer script
cat > pixel_backup_deployment/transfer_to_pixel.sh << 'EOF'
#!/bin/bash
# Simple transfer script for Pixel device

echo "📱 Pixel Backup Gang - File Transfer"
echo "===================================="
echo ""

echo "Files to transfer:"
echo "1. pixel_backup_gang.zip - Magisk module"
echo "2. credentials.json - Configuration file"
echo ""

echo "Transfer methods:"
echo "1. USB Transfer:"
echo "   - Connect Pixel to computer via USB"
echo "   - Copy files to Pixel's Downloads folder"
echo ""
echo "2. Cloud Transfer:"
echo "   - Upload files to Google Drive/Dropbox"
echo "   - Download on Pixel device"
echo ""
echo "3. ADB Transfer (if ADB is set up):"
echo "   adb push pixel_backup_gang.zip /sdcard/Download/"
echo "   adb push credentials.json /sdcard/Download/"
echo ""

echo "After transfer, follow the Pixel backup instructions in README.md (see Pipeline Operations ➔ Upload Automation)."
EOF

chmod +x pixel_backup_deployment/transfer_to_pixel.sh

echo "✅ Deployment package created in: pixel_backup_deployment/"
echo ""

# Show file sizes
echo "📊 File sizes:"
ls -lh pixel_backup_deployment/
echo ""

# Create QR code for easy access (if qrencode is available)
if command -v qrencode >/dev/null 2>&1; then
    echo "📱 Creating QR code for easy access..."
    echo "http://192.168.1.7:5000/pixel-backup-download" | qrencode -t ANSI
    echo ""
fi

echo "🎯 Next steps:"
echo "1. Copy the entire 'pixel_backup_deployment' folder to your computer"
echo "2. Transfer files to your Pixel device (USB, cloud, or ADB)"
echo "3. Install pixel_backup_gang.zip via Magisk Manager"
echo "4. Copy credentials.json to /data/adb/modules/pixel_backup_gang/"
echo "5. Edit credentials.json with your Telegram details"
echo "6. Reboot your Pixel device"
echo ""

echo "📋 Alternative: Use web interface at http://192.168.1.7:5000/pixel-backup-download"
echo ""

# Create a simple HTTP server for easy download
echo "🌐 Starting temporary web server for easy download..."
echo "Files available at:"
echo "  - http://192.168.1.7:5000/pixel-backup-download (web interface)"
echo "  - http://192.168.1.7:5000/api/download/pixel_backup_gang.zip (direct download)"
echo "  - http://192.168.1.7:5000/api/download/credentials.json (config download)"
echo ""
echo "Press Ctrl+C to stop the web server"
echo ""

# Start a simple HTTP server in the deployment directory
cd pixel_backup_deployment
python3 -m http.server 8080