#!/system/bin/sh

# Google Photos Uploader Service
# Starts the uploader service on boot

MODID=google_photos_uploader
MODULE_DIR="/data/adb/modules/$MODID"
LOG_DIR="$MODULE_DIR/logs"
UPLOADER_SCRIPT="$MODULE_DIR/uploader.py"
CONFIG_FILE="$MODULE_DIR/config.json"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_DIR/service.log"
}

# Check if module is enabled
if [ ! -f "$UPLOADER_SCRIPT" ]; then
    log "ERROR: Uploader script not found"
    exit 1
fi

# Wait for system to be ready
sleep 30

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    log "ERROR: Python3 not found"
    exit 1
fi

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    log "ERROR: Config file not found"
    exit 1
fi

# Start the uploader
log "Starting Google Photos Uploader service"
cd "$MODULE_DIR"

# Run in background with nohup
nohup python3 "$UPLOADER_SCRIPT" > "$LOG_DIR/uploader.log" 2>&1 &

# Store PID
echo $! > "$LOG_DIR/uploader.pid"
log "Google Photos Uploader started with PID: $!"

exit 0