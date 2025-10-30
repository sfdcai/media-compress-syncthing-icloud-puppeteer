# Manual Deployment Guide for Pixel Backup Gang

## 🚀 **Quick Manual Deployment**

Since you're getting "file not found" errors, here's how to manually deploy the Pixel Backup Gang module:

### **Step 1: Download Files to Your Computer**

**Files you need:**
- `pixel_backup_gang.zip` - The Magisk module
- `magisk_module_pixel_backup/credentials.json` - Configuration file

### **Step 2: Transfer to Pixel Device**

**Option A: USB Transfer**
1. Connect Pixel to computer via USB
2. Copy `pixel_backup_gang.zip` to Pixel's Downloads folder
3. Copy `credentials.json` to Pixel's Downloads folder

**Option B: Cloud Transfer**
1. Upload `pixel_backup_gang.zip` to Google Drive/Dropbox
2. Download on Pixel device
3. Upload `credentials.json` to cloud storage
4. Download on Pixel device

### **Step 3: Install via Magisk Manager**

1. **Open Magisk Manager** on your Pixel
2. **Go to Modules tab**
3. **Tap the "+" button** (Install module)
4. **Navigate to Downloads folder**
5. **Select `pixel_backup_gang.zip`**
6. **Install the module**
7. **Reboot device**

### **Step 4: Configure Module**

1. **After reboot, open a file manager** (or use ADB)
2. **Navigate to `/data/adb/modules/pixel_backup_gang/`**
3. **Copy `credentials.json` to this directory**
4. **Edit the file** with your Telegram credentials:

```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID",
    "enabled": true
  }
}
```

### **Step 5: Test Installation**

**Check if module is working:**
```bash
# Connect via ADB or use terminal app
adb shell
su
ls -la /data/adb/modules/pixel_backup_gang/
```

**Check logs:**
```bash
tail -f /data/adb/modules/pixel_backup_gang/logs/backup.log
```

## 🔧 **Alternative: Direct File Transfer**

If you have SSH access to your Pixel:

```bash
# From your media-pipeline server
scp pixel_backup_gang.zip root@192.168.1.198:/sdcard/
scp magisk_module_pixel_backup/credentials.json root@192.168.1.198:/sdcard/
```

## 📱 **Verification Steps**

1. **Check module installation:**
   - Module should appear in Magisk Manager
   - Files should be in `/data/adb/modules/pixel_backup_gang/`

2. **Check Google Photos backup:**
   - Go to Settings > Google > Backup
   - Verify Photos backup is enabled

3. **Test file detection:**
   - Take a photo with camera
   - Check logs for detection message

4. **Check Telegram notifications:**
   - Should receive notifications about new files
   - Should receive backup status updates

## 🚨 **Troubleshooting**

### **Module Not Installing**
- Check if Magisk is properly installed
- Ensure module zip file is not corrupted
- Try installing from internal storage instead of SD card

### **Files Not Detected**
- Check file permissions in monitored directories
- Verify module is running: `ps aux | grep backup`
- Check logs for errors

### **Backup Not Working**
- Verify Google Photos backup is enabled in settings
- Check network connectivity
- Ensure Google account is signed in

### **No Telegram Notifications**
- Verify bot token and chat ID are correct
- Check if Telegram bot is working
- Look for errors in logs

## 📋 **Quick Commands**

**Check module status:**
```bash
adb shell
su
ls -la /data/adb/modules/pixel_backup_gang/
cat /data/adb/modules/pixel_backup_gang/logs/backup.log
```

**Force backup:**
```bash
adb shell
su
settings put global backup_photos_enabled 1
settings put global auto_backup_enabled 1
bmgr backupnow --all
```

**Check backup status:**
```bash
adb shell
su
settings get global backup_photos_enabled
settings get global backup_videos_enabled
bmgr list
```

---

**This manual approach should work even if the automated deployment script has issues!** 🎉