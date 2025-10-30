#!/system/bin/sh

# Google Photos Monitor Service
# Monitors Google Photos app activity and provides notifications

MODID=google_photos_monitor
MODULE_DIR="/data/adb/modules/$MODID"
LOG_DIR="$MODULE_DIR/logs"
MONITOR_SCRIPT="$MODULE_DIR/monitor.py"
CONFIG_FILE="$MODULE_DIR/credentials.json"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_DIR/service.log"
}

# Check if module is enabled
if [ ! -f "$MONITOR_SCRIPT" ]; then
    log "ERROR: Monitor script not found"
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

# Start the monitor
log "Starting Google Photos Monitor service"
cd "$MODULE_DIR"

# Run in background with nohup
nohup python3 "$MONITOR_SCRIPT" > "$LOG_DIR/monitor.log" 2>&1 &

# Store PID
echo $! > "$LOG_DIR/monitor.pid"
log "Google Photos Monitor started with PID: $!"

exit 0