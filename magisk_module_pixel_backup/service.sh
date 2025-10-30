#!/system/bin/sh

# Pixel Backup Gang Service
# Manages Google Photos backup and monitoring

MODID=pixel_backup_gang
MODULE_DIR="/data/adb/modules/$MODID"
LOG_DIR="$MODULE_DIR/logs"
BACKUP_SCRIPT="$MODULE_DIR/backup_script.sh"
CONFIG_FILE="$MODULE_DIR/credentials.json"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_DIR/service.log"
}

# Check if module is enabled
if [ ! -f "$BACKUP_SCRIPT" ]; then
    log "ERROR: Backup script not found"
    exit 1
fi

# Wait for system to be ready
sleep 30

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    log "ERROR: Config file not found"
    exit 1
fi

# Start the backup manager
log "Starting Pixel Backup Gang service"
cd "$MODULE_DIR"

# Run in background with nohup
nohup sh "$BACKUP_SCRIPT" > "$LOG_DIR/backup.log" 2>&1 &

# Store PID
echo $! > "$LOG_DIR/backup.pid"
log "Pixel Backup Gang started with PID: $!"

exit 0