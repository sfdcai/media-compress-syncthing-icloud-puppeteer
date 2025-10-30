#!/system/bin/sh

# Pixel Backup Gang - Main Backup Script
# Leverages Pixel's built-in Google Photos backup system

MODULE_DIR="/data/adb/modules/pixel_backup_gang"
LOG_DIR="$MODULE_DIR/logs"
CONFIG_FILE="$MODULE_DIR/credentials.json"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_DIR/backup.log"
}

# Load configuration
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        # Extract values using simple parsing
        BACKUP_ENABLED=$(grep -o '"enabled": *true' "$CONFIG_FILE" | wc -l)
        INTERVAL=$(grep -o '"interval_seconds": *[0-9]*' "$CONFIG_FILE" | grep -o '[0-9]*')
        WIFI_ONLY=$(grep -o '"wifi_only": *true' "$CONFIG_FILE" | wc -l)
    else
        BACKUP_ENABLED=1
        INTERVAL=60
        WIFI_ONLY=0
    fi
}

# Check if backup is enabled
is_backup_enabled() {
    if [ "$BACKUP_ENABLED" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Check network connectivity
check_network() {
    if [ "$WIFI_ONLY" -gt 0 ]; then
        # Check if connected to WiFi
        WIFI_STATE=$(dumpsys wifi | grep "mWifiInfo" | grep -c "SSID")
        if [ "$WIFI_STATE" -gt 0 ]; then
            return 0
        else
            return 1
        fi
    else
        # Check any network connectivity
        ping -c 1 8.8.8.8 > /dev/null 2>&1
        return $?
    fi
}

# Enable Google Photos backup
enable_google_photos_backup() {
    log "Enabling Google Photos backup..."
    
    # Enable backup for photos
    settings put global backup_photos_enabled 1
    settings put global backup_videos_enabled 1
    
    # Set backup to Google Photos
    settings put global backup_transport com.google.android.gms/.backup.BackupTransportService
    
    # Enable auto backup
    settings put global auto_backup_enabled 1
    
    # Set backup frequency to daily
    settings put global backup_frequency 86400000  # 24 hours in milliseconds
    
    log "Google Photos backup enabled"
}

# Check Google Photos backup status
check_backup_status() {
    BACKUP_PHOTOS=$(settings get global backup_photos_enabled)
    BACKUP_VIDEOS=$(settings get global backup_videos_enabled)
    AUTO_BACKUP=$(settings get global auto_backup_enabled)
    
    log "Backup status - Photos: $BACKUP_PHOTOS, Videos: $BACKUP_VIDEOS, Auto: $AUTO_BACKUP"
    
    if [ "$BACKUP_PHOTOS" = "1" ] && [ "$BACKUP_VIDEOS" = "1" ] && [ "$AUTO_BACKUP" = "1" ]; then
        return 0
    else
        return 1
    fi
}

# Force backup sync
force_backup_sync() {
    log "Forcing backup sync..."
    
    # Trigger backup sync
    bmgr backupnow --all
    
    # Wait a bit for sync to start
    sleep 5
    
    # Check if backup is running
    BACKUP_RUNNING=$(bmgr list | grep -c "Backup")
    if [ "$BACKUP_RUNNING" -gt 0 ]; then
        log "Backup sync started successfully"
        return 0
    else
        log "Failed to start backup sync"
        return 1
    fi
}

# Monitor backup progress
monitor_backup_progress() {
    log "Monitoring backup progress..."
    
    # Get backup status
    BACKUP_STATUS=$(bmgr list)
    log "Backup status: $BACKUP_STATUS"
    
    # Check for any pending backups
    PENDING_BACKUPS=$(echo "$BACKUP_STATUS" | grep -c "Pending")
    if [ "$PENDING_BACKUPS" -gt 0 ]; then
        log "Found $PENDING_BACKUPS pending backups"
        return 1
    else
        log "No pending backups"
        return 0
    fi
}

# Scan for new files
scan_new_files() {
    log "Scanning for new files..."
    
    # Directories to monitor
    DIRS="/sdcard/DCIM/Camera /sdcard/Pictures/Screenshots /sdcard/Download"
    
    NEW_FILES=0
    for dir in $DIRS; do
        if [ -d "$dir" ]; then
            # Count files modified in the last hour
            COUNT=$(find "$dir" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.heic" -o -name "*.mov" -o -name "*.mp4" \) -mmin -60 | wc -l)
            NEW_FILES=$((NEW_FILES + COUNT))
            log "Directory $dir: $COUNT new files"
        fi
    done
    
    log "Total new files found: $NEW_FILES"
    echo "$NEW_FILES"
}

# Send notification (if Telegram is configured)
send_notification() {
    local message="$1"
    log "Notification: $message"
    
    # This would integrate with your Telegram bot
    # For now, just log the message
    echo "NOTIFICATION: $message" >> "$LOG_DIR/notifications.log"
}

# Main backup loop
main_backup_loop() {
    log "Starting Pixel Backup Gang main loop"
    
    # Load configuration
    load_config
    
    # Check if backup is enabled
    if ! is_backup_enabled; then
        log "Backup is disabled in configuration"
        exit 0
    fi
    
    # Enable Google Photos backup
    enable_google_photos_backup
    
    # Main loop
    while true; do
        # Check network connectivity
        if ! check_network; then
            log "No network connectivity, skipping backup"
            sleep $INTERVAL
            continue
        fi
        
        # Check backup status
        if ! check_backup_status; then
            log "Backup not properly configured, re-enabling..."
            enable_google_photos_backup
        fi
        
        # Scan for new files
        NEW_FILES=$(scan_new_files)
        
        if [ "$NEW_FILES" -gt 0 ]; then
            log "Found $NEW_FILES new files, triggering backup..."
            send_notification "Found $NEW_FILES new files, starting backup"
            
            # Force backup sync
            if force_backup_sync; then
                # Monitor backup progress
                sleep 30
                if monitor_backup_progress; then
                    log "Backup completed successfully"
                    send_notification "Backup completed successfully"
                else
                    log "Backup still in progress"
                fi
            else
                log "Failed to start backup"
                send_notification "Failed to start backup"
            fi
        else
            log "No new files to backup"
        fi
        
        # Wait for next check
        sleep $INTERVAL
    done
}

# Start the main loop
main_backup_loop