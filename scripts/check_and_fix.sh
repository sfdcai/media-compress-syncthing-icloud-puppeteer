#!/bin/bash
# Media Pipeline Status Check and Fix Script
# Comprehensive health check and repair tool for the media pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PIPELINE_DIR="/opt/media-pipeline"
SOURCE_DIR="$(pwd)"
SERVICE_NAME="media-pipeline"
USER_NAME="media-pipeline"

# Status tracking
ISSUES_FOUND=0
FIXES_APPLIED=0

# Helper functions
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠${NC} $message"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
    esac
}

ask_fix() {
    local message=$1
    echo -e "${YELLOW}Fix: $message${NC}"
    
    # Check if running in non-interactive mode
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        echo "Non-interactive mode: Skipping fix"
        return 1
    fi
    
    read -p "Apply this fix? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

apply_fix() {
    local fix_name=$1
    print_status "INFO" "Applying fix: $fix_name"
    FIXES_APPLIED=$((FIXES_APPLIED + 1))
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check for non-interactive mode
check_non_interactive() {
    if [[ "$1" == "--non-interactive" ]] || [[ "$NON_INTERACTIVE" == "true" ]]; then
        NON_INTERACTIVE="true"
        print_status "INFO" "Running in non-interactive mode"
    fi
}

# Fix permission issues
fix_permissions() {
    print_status "INFO" "Fixing permission issues..."
    
    # Stop the service first to prevent conflicts
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "INFO" "Stopping service to fix permissions..."
        systemctl stop "$SERVICE_NAME"
    fi
    
    # Fix directory permissions
    chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
    chmod -R 755 "$PIPELINE_DIR"
    
    # Fix logs directory specifically
    chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs"
    chmod -R 755 "$PIPELINE_DIR/logs"
    
    # Create and fix log file
    touch "$PIPELINE_DIR/logs/pipeline.log"
    chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs/pipeline.log"
    chmod 644 "$PIPELINE_DIR/logs/pipeline.log"
    
    # Fix any other log files
    find "$PIPELINE_DIR/logs" -name "*.log" -exec chown "$USER_NAME:$USER_NAME" {} \;
    find "$PIPELINE_DIR/logs" -name "*.log" -exec chmod 644 {} \;
    
    print_status "SUCCESS" "Permission issues fixed"
    
    # Try to start the service
    print_status "INFO" "Starting service after permission fix..."
    systemctl start "$SERVICE_NAME"
    sleep 3
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "SUCCESS" "Service started successfully after permission fix"
    else
        print_status "WARNING" "Service still not running - check logs for other issues"
        print_status "INFO" "Run: journalctl -u $SERVICE_NAME -f"
    fi
}

# Check system packages
check_packages() {
    print_status "INFO" "Checking system packages..."
    
    local packages=("python3" "ffmpeg" "rsync" "parallel" "pv" "curl" "wget" "unzip" "git")
    local missing_packages=()
    
    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            missing_packages+=("$package")
        fi
    done
    
    # Check for exiftool specifically (it might be installed as libimage-exiftool-perl)
    if ! command -v exiftool >/dev/null 2>&1; then
        if ! dpkg -l | grep -q "libimage-exiftool-perl"; then
            missing_packages+=("libimage-exiftool-perl")
        else
            print_status "OK" "exiftool is available via libimage-exiftool-perl"
        fi
    else
        print_status "OK" "exiftool is available"
    fi
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        print_status "OK" "All required packages are installed"
    else
        print_status "ERROR" "Missing packages: ${missing_packages[*]}"
        if ask_fix "Install missing packages"; then
            apply_fix "Installing missing packages"
            apt update
            apt install -y "${missing_packages[@]}"
            
            # Special handling for python3-venv
            if [[ " ${missing_packages[@]} " =~ " python3-venv " ]]; then
                print_status "INFO" "Installing python3-venv package..."
                apt install -y python3-venv
            fi
        fi
    fi
}

# Check Node.js version
check_nodejs() {
    print_status "INFO" "Checking Node.js version..."
    
    if command -v node >/dev/null 2>&1; then
        local node_version=$(node --version | sed 's/v//')
        local major_version=$(echo $node_version | cut -d. -f1)
        
        if [ "$major_version" -ge 18 ]; then
            print_status "OK" "Node.js version $node_version is compatible"
            
            # Check if npm is available
            if command -v npm >/dev/null 2>&1; then
                local npm_version=$(npm --version)
                print_status "OK" "npm version $npm_version is available"
            else
                print_status "ERROR" "npm is not available (should come with Node.js)"
                if ask_fix "Reinstall Node.js to get npm"; then
                    apply_fix "Reinstalling Node.js"
                    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
                    apt install -y nodejs
                fi
            fi
        else
            print_status "ERROR" "Node.js version $node_version is too old (requires 18+)"
            if ask_fix "Upgrade Node.js to version 18+"; then
                apply_fix "Upgrading Node.js"
                curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
                apt install -y nodejs
            fi
        fi
    else
        print_status "ERROR" "Node.js is not installed"
        if ask_fix "Install Node.js 18+"; then
            apply_fix "Installing Node.js"
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt install -y nodejs
        fi
    fi
}

# Check user and group
check_user_group() {
    print_status "INFO" "Checking user and group..."
    
    if id "$USER_NAME" >/dev/null 2>&1; then
        print_status "OK" "User $USER_NAME exists"
    else
        print_status "ERROR" "User $USER_NAME does not exist"
        if ask_fix "Create user $USER_NAME"; then
            apply_fix "Creating user and group"
            groupadd -r "$USER_NAME" || true
            useradd -r -g "$USER_NAME" -d "$PIPELINE_DIR" -s /bin/bash "$USER_NAME" || true
        fi
    fi
    
    if getent group "$USER_NAME" >/dev/null 2>&1; then
        print_status "OK" "Group $USER_NAME exists"
    else
        print_status "ERROR" "Group $USER_NAME does not exist"
        if ask_fix "Create group $USER_NAME"; then
            apply_fix "Creating group"
            groupadd -r "$USER_NAME"
        fi
    fi
}

# Check directory structure
check_directories() {
    print_status "INFO" "Checking directory structure..."
    
    local required_dirs=(
        "$PIPELINE_DIR"
        "$PIPELINE_DIR/originals"
        "$PIPELINE_DIR/compressed"
        "$PIPELINE_DIR/bridge"
        "$PIPELINE_DIR/uploaded"
        "$PIPELINE_DIR/logs"
        "$PIPELINE_DIR/temp"
        "$PIPELINE_DIR/cleanup"
        "$PIPELINE_DIR/bridge/icloud"
        "$PIPELINE_DIR/bridge/pixel"
        "$PIPELINE_DIR/uploaded/icloud"
        "$PIPELINE_DIR/uploaded/pixel"
        "$PIPELINE_DIR/sorted/icloud"
        "$PIPELINE_DIR/sorted/pixel"
        "/mnt/nas/photos"
        "/mnt/syncthing/pixel"
    )
    
    local missing_dirs=()
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [ ${#missing_dirs[@]} -eq 0 ]; then
        print_status "OK" "All required directories exist"
    else
        print_status "ERROR" "Missing directories: ${missing_dirs[*]}"
        if ask_fix "Create missing directories"; then
            apply_fix "Creating missing directories"
            for dir in "${missing_dirs[@]}"; do
                mkdir -p "$dir"
            done
        fi
    fi
}

# Check file permissions
check_permissions() {
    print_status "INFO" "Checking file permissions..."
    
    if [ -d "$PIPELINE_DIR" ]; then
        local owner=$(stat -c '%U:%G' "$PIPELINE_DIR")
        if [ "$owner" = "$USER_NAME:$USER_NAME" ]; then
            print_status "OK" "Pipeline directory ownership is correct"
        else
            print_status "WARN" "Pipeline directory ownership is $owner (should be $USER_NAME:$USER_NAME)"
            if ask_fix "Fix directory ownership"; then
                apply_fix "Fixing directory ownership"
                chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
                chown -R "$USER_NAME:$USER_NAME" /mnt/nas 2>/dev/null || true
                chown -R "$USER_NAME:$USER_NAME" /mnt/syncthing 2>/dev/null || true
            fi
        fi
        
        local perms=$(stat -c '%a' "$PIPELINE_DIR")
        if [ "$perms" = "755" ]; then
            print_status "OK" "Pipeline directory permissions are correct"
        else
            print_status "WARN" "Pipeline directory permissions are $perms (should be 755)"
            if ask_fix "Fix directory permissions"; then
                apply_fix "Fixing directory permissions"
                chmod -R 755 "$PIPELINE_DIR"
                chmod -R 755 /mnt/nas 2>/dev/null || true
                chmod -R 755 /mnt/syncthing 2>/dev/null || true
            fi
        fi
    fi
}

# Check if files are copied
check_files_copied() {
    print_status "INFO" "Checking if pipeline files are copied..."
    
    local required_files=(
        "$PIPELINE_DIR/scripts/run_pipeline.py"
        "$PIPELINE_DIR/scripts/compress_media.py"
        "$PIPELINE_DIR/scripts/deduplicate.py"
        "$PIPELINE_DIR/scripts/download_from_icloud.py"
        "$PIPELINE_DIR/scripts/upload_icloud.py"
        "$PIPELINE_DIR/scripts/upload_icloud.js"
        "$PIPELINE_DIR/scripts/utils.py"
        "$PIPELINE_DIR/config/settings.env"
        "$PIPELINE_DIR/requirements.txt"
        "$PIPELINE_DIR/package.json"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        print_status "OK" "All pipeline files are present"
    else
        print_status "ERROR" "Missing pipeline files: ${missing_files[*]}"
        if ask_fix "Copy pipeline files from $SOURCE_DIR to $PIPELINE_DIR"; then
            apply_fix "Copying pipeline files"
            
            # Copy all files and directories
            cp -r "$SOURCE_DIR"/* "$PIPELINE_DIR/" 2>/dev/null || true
            cp -r "$SOURCE_DIR"/.[^.]* "$PIPELINE_DIR/" 2>/dev/null || true
            
            # Ensure proper ownership
            chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
            
            # Create log file with correct permissions
            touch "$PIPELINE_DIR/logs/pipeline.log"
            chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs/pipeline.log"
            chmod 644 "$PIPELINE_DIR/logs/pipeline.log"
            
            print_status "OK" "Pipeline files copied successfully"
        fi
    fi
}

# Check Python virtual environment
check_python_venv() {
    print_status "INFO" "Checking Python virtual environment..."
    
    if [ -d "$PIPELINE_DIR/venv" ]; then
        print_status "OK" "Python virtual environment exists"
        
        # Check if packages are installed
        if [ -f "$PIPELINE_DIR/requirements.txt" ]; then
            local installed_packages=$(sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" list --format=freeze | cut -d= -f1)
            local required_packages=("icloudpd" "pillow" "ffmpeg-python" "python-dotenv" "supabase" "psutil")
            local missing=()
            
            for package in "${required_packages[@]}"; do
                if ! echo "$installed_packages" | grep -q "^$package$"; then
                    missing+=("$package")
                fi
            done
            
            if [ ${#missing[@]} -eq 0 ]; then
                print_status "OK" "All Python packages are installed"
            else
                print_status "WARN" "Missing Python packages: ${missing[*]}"
                if ask_fix "Install missing Python packages"; then
                    apply_fix "Installing Python packages"
                    sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install "${missing[@]}"
                fi
            fi
        fi
    else
        print_status "ERROR" "Python virtual environment does not exist"
        if ask_fix "Create Python virtual environment"; then
            apply_fix "Creating Python virtual environment"
            
            # First ensure python3-venv is installed
            if ! dpkg -l | grep -q "python3-venv"; then
                print_status "INFO" "Installing python3-venv package..."
                apt install -y python3-venv
            fi
            
            # Create virtual environment
            sudo -u "$USER_NAME" python3 -m venv "$PIPELINE_DIR/venv"
            
            # Upgrade pip
            sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install --upgrade pip
            
            # Install requirements if available
            if [ -f "$PIPELINE_DIR/requirements.txt" ]; then
                sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install -r "$PIPELINE_DIR/requirements.txt"
            fi
            
            print_status "OK" "Python virtual environment created successfully"
        fi
    fi
}

# Check Node.js packages
check_nodejs_packages() {
    print_status "INFO" "Checking Node.js packages..."
    
    if [ -f "$PIPELINE_DIR/package.json" ]; then
        if [ -d "$PIPELINE_DIR/node_modules" ]; then
            print_status "OK" "Node.js packages are installed"
        else
            print_status "WARN" "Node.js packages are not installed"
            if ask_fix "Install Node.js packages"; then
                apply_fix "Installing Node.js packages"
                cd "$PIPELINE_DIR"
                sudo -u "$USER_NAME" npm install
            fi
        fi
    else
        print_status "WARN" "package.json not found"
    fi
}

# Check systemd service
check_systemd_service() {
    print_status "INFO" "Checking systemd service..."
    
    if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
        print_status "OK" "Systemd service file exists"
        
        # Check service status and restart count
        local restart_count=$(systemctl show "$SERVICE_NAME" --property=ExecMainStatus --value 2>/dev/null || echo "0")
        local service_status=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "inactive")
        
        # Check for excessive restarts (indicates a problem)
        if systemctl show "$SERVICE_NAME" --property=RestartCount --value 2>/dev/null | grep -q "[0-9]"; then
            local restart_count=$(systemctl show "$SERVICE_NAME" --property=RestartCount --value 2>/dev/null)
            if [ "$restart_count" -gt 10 ]; then
                print_status "ERROR" "Service has restarted $restart_count times (indicates a problem)"
                if ask_fix "Stop the failing service to prevent continuous restarts"; then
                    apply_fix "Stopping failing service"
                    systemctl stop "$SERVICE_NAME"
                    systemctl disable "$SERVICE_NAME"
                    print_status "INFO" "Service stopped. Check logs and fix issues before restarting."
                fi
            fi
        fi
        
        # Check log file permissions
        local log_file="$PIPELINE_DIR/logs/pipeline.log"
        if [ -f "$log_file" ]; then
            local log_owner=$(stat -c '%U:%G' "$log_file" 2>/dev/null)
            if [ "$log_owner" != "$USER_NAME:$USER_NAME" ]; then
                print_status "WARN" "Log file ownership is $log_owner (should be $USER_NAME:$USER_NAME)"
                if ask_fix "Fix log file permissions"; then
                    apply_fix "Fixing log file permissions"
                    chown "$USER_NAME:$USER_NAME" "$log_file"
                    chmod 644 "$log_file"
                fi
            fi
        else
            # Create log file with correct permissions
            print_status "INFO" "Creating log file with correct permissions"
            touch "$log_file"
            chown "$USER_NAME:$USER_NAME" "$log_file"
            chmod 644 "$log_file"
        fi
        
        # Check logs directory permissions
        if [ -d "$PIPELINE_DIR/logs" ]; then
            local logs_owner=$(stat -c '%U:%G' "$PIPELINE_DIR/logs" 2>/dev/null)
            if [ "$logs_owner" != "$USER_NAME:$USER_NAME" ]; then
                print_status "WARN" "Logs directory ownership is $logs_owner (should be $USER_NAME:$USER_NAME)"
                if ask_fix "Fix logs directory permissions"; then
                    apply_fix "Fixing logs directory permissions"
                    chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs"
                    chmod -R 755 "$PIPELINE_DIR/logs"
                fi
            fi
        fi
        
        if systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
            print_status "OK" "Service is enabled"
        else
            print_status "WARN" "Service is not enabled"
            if ask_fix "Enable systemd service"; then
                apply_fix "Enabling systemd service"
                systemctl enable "$SERVICE_NAME"
            fi
        fi
        
        if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
            print_status "OK" "Service is running"
        else
            print_status "WARN" "Service is not running"
            
            # Check for excessive restart attempts
            local restart_count=$(journalctl -u "$SERVICE_NAME" --since "1 hour ago" | grep -c "Started Media Pipeline Service" || echo "0")
            if [ "$restart_count" -gt 10 ]; then
                print_status "WARN" "Service has restarted $restart_count times in the last hour"
                if ask_fix "Stop failing service to prevent resource exhaustion"; then
                    apply_fix "Stopping failing service"
                    systemctl stop "$SERVICE_NAME"
                    systemctl disable "$SERVICE_NAME"
                    print_status "INFO" "Service stopped. Fix issues before restarting."
                fi
            else
                if ask_fix "Start systemd service"; then
                    apply_fix "Starting systemd service"
                    systemctl start "$SERVICE_NAME"
                    sleep 3
                    if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
                        print_status "OK" "Service started successfully"
                    else
                        print_status "ERROR" "Service failed to start"
                        print_status "INFO" "Check logs with: journalctl -u $SERVICE_NAME -f"
                        
                        # Check for common startup issues
                        local log_error=$(journalctl -u "$SERVICE_NAME" --since "5 minutes ago" | tail -n 10)
                        if echo "$log_error" | grep -q "Permission denied"; then
                            print_status "INFO" "Permission error detected - fixing log file and directory permissions"
                            
                            # Fix logs directory permissions
                            chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs"
                            chmod -R 755 "$PIPELINE_DIR/logs"
                            
                            # Fix log file permissions
                            if [ -f "$PIPELINE_DIR/logs/pipeline.log" ]; then
                                chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs/pipeline.log"
                                chmod 644 "$PIPELINE_DIR/logs/pipeline.log"
                            else
                                # Create log file if it doesn't exist
                                touch "$PIPELINE_DIR/logs/pipeline.log"
                                chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs/pipeline.log"
                                chmod 644 "$PIPELINE_DIR/logs/pipeline.log"
                            fi
                            
                            # Also fix the entire pipeline directory permissions
                            chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
                            chmod -R 755 "$PIPELINE_DIR"
                            
                            print_status "OK" "Log file and directory permissions fixed"
                            
                            # Try to start the service again
                            print_status "INFO" "Attempting to restart service after permission fix"
                            systemctl start "$SERVICE_NAME"
                            sleep 2
                            if systemctl is-active --quiet "$SERVICE_NAME"; then
                                print_status "OK" "Service started successfully after permission fix"
                            else
                                print_status "ERROR" "Service still failing after permission fix"
                            fi
                        fi
                    fi
                fi
            fi
        fi
    else
        print_status "ERROR" "Systemd service file does not exist"
        if ask_fix "Create systemd service file"; then
            apply_fix "Creating systemd service"
            cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Media Pipeline Service
After=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PIPELINE_DIR
ExecStart=$PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py
Restart=always
RestartSec=10
Environment=PATH=$PIPELINE_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF
            systemctl daemon-reload
            systemctl enable "$SERVICE_NAME"
        fi
    fi
}

# Check log rotation
check_log_rotation() {
    print_status "INFO" "Checking log rotation..."
    
    if [ -f "/etc/logrotate.d/$SERVICE_NAME" ]; then
        print_status "OK" "Log rotation configuration exists"
    else
        print_status "WARN" "Log rotation configuration missing"
        if ask_fix "Create log rotation configuration"; then
            apply_fix "Creating log rotation configuration"
            cat > "/etc/logrotate.d/$SERVICE_NAME" << EOF
$PIPELINE_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER_NAME $USER_NAME
}
EOF
        fi
    fi
}

# Check cron job
check_cron_job() {
    print_status "INFO" "Checking cron job..."
    
    if [ -f "/etc/cron.d/$SERVICE_NAME" ]; then
        print_status "OK" "Cron job configuration exists"
    else
        print_status "WARN" "Cron job configuration missing"
        if ask_fix "Create cron job configuration"; then
            apply_fix "Creating cron job configuration"
            cat > "/etc/cron.d/$SERVICE_NAME" << EOF
# Run media pipeline daily at 2 AM
0 2 * * * $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py >> $PIPELINE_DIR/logs/cron.log 2>&1
EOF
        fi
    fi
}

# Check configuration file
check_config() {
    print_status "INFO" "Checking configuration file..."
    
    if [ -f "$PIPELINE_DIR/config/settings.env" ]; then
        print_status "OK" "Configuration file exists"
        
        # Check if it has content
        if [ -s "$PIPELINE_DIR/config/settings.env" ]; then
            print_status "OK" "Configuration file has content"
        else
            print_status "WARN" "Configuration file is empty"
            if ask_fix "Copy example configuration"; then
                apply_fix "Copying example configuration"
                if [ -f "$SOURCE_DIR/config/settings.env" ]; then
                    cp "$SOURCE_DIR/config/settings.env" "$PIPELINE_DIR/config/"
                    chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/config/settings.env"
                fi
            fi
        fi
    else
        print_status "ERROR" "Configuration file does not exist"
        if ask_fix "Create configuration file"; then
            apply_fix "Creating configuration file"
            mkdir -p "$PIPELINE_DIR/config"
            if [ -f "$SOURCE_DIR/config/settings.env" ]; then
                cp "$SOURCE_DIR/config/settings.env" "$PIPELINE_DIR/config/"
            else
                touch "$PIPELINE_DIR/config/settings.env"
            fi
            chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/config/settings.env"
        fi
    fi
}

# Check pipeline dependencies
check_pipeline_dependencies() {
    print_status "INFO" "Checking pipeline dependencies..."
    
    # Check icloudpd installation
    if command -v icloudpd >/dev/null 2>&1; then
        local icloudpd_version=$(icloudpd --version 2>/dev/null | head -n1 || echo "unknown")
        print_status "OK" "icloudpd is installed: $icloudpd_version"
    else
        print_status "ERROR" "icloudpd is not installed"
        if ask_fix "Install icloudpd"; then
            apply_fix "Installing icloudpd"
            sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install icloudpd
        fi
    fi
    
    # Check if icloudpd can be imported in Python
    if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/python" -c "import icloudpd" 2>/dev/null; then
        print_status "OK" "icloudpd Python module is available"
    else
        print_status "ERROR" "icloudpd Python module is not available"
        if ask_fix "Install icloudpd Python module"; then
            apply_fix "Installing icloudpd Python module"
            sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install icloudpd
        fi
    fi
    
    # Check other critical pipeline dependencies
    local critical_modules=("PIL" "ffmpeg" "dotenv" "supabase" "psutil")
    for module in "${critical_modules[@]}"; do
        if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/python" -c "import $module" 2>/dev/null; then
            print_status "OK" "Python module $module is available"
        else
            print_status "ERROR" "Python module $module is not available"
            if ask_fix "Install missing Python module $module"; then
                apply_fix "Installing Python module $module"
                case $module in
                    "PIL")
                        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install pillow
                        ;;
                    "ffmpeg")
                        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install ffmpeg-python
                        ;;
                    "dotenv")
                        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install python-dotenv
                        ;;
                    "supabase")
                        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install supabase
                        ;;
                    "psutil")
                        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install psutil
                        ;;
                esac
            fi
        fi
    done
    
    # Check Node.js dependencies
    if [ -f "$PIPELINE_DIR/package.json" ]; then
        cd "$PIPELINE_DIR"
        if sudo -u "$USER_NAME" node -e "require('puppeteer')" 2>/dev/null; then
            local puppeteer_version=$(sudo -u "$USER_NAME" node -e "console.log(require('puppeteer/package.json').version)" 2>/dev/null || echo "unknown")
            print_status "OK" "Puppeteer Node.js module is available (v$puppeteer_version)"
        else
            print_status "ERROR" "Puppeteer Node.js module is not available"
            if ask_fix "Install/Update Puppeteer Node.js module"; then
                apply_fix "Installing/Updating Puppeteer"
                cd "$PIPELINE_DIR"
                sudo -u "$USER_NAME" npm install puppeteer@latest
                sudo -u "$USER_NAME" npm audit fix --force
            fi
        fi
    fi
}

# Check iCloud configuration
check_icloud_config() {
    print_status "INFO" "Checking iCloud configuration..."
    
    if [ -f "$PIPELINE_DIR/config/settings.env" ]; then
        # Check if iCloud credentials are configured
        if grep -q "ICLOUD_USERNAME=" "$PIPELINE_DIR/config/settings.env" && grep -q "ICLOUD_PASSWORD=" "$PIPELINE_DIR/config/settings.env"; then
            local username=$(grep "ICLOUD_USERNAME=" "$PIPELINE_DIR/config/settings.env" | cut -d'=' -f2)
            if [ -n "$username" ] && [ "$username" != "your@email.com" ]; then
                print_status "OK" "iCloud username is configured"
            else
                print_status "WARN" "iCloud username is not properly configured"
                print_status "INFO" "Please edit $PIPELINE_DIR/config/settings.env and set ICLOUD_USERNAME"
            fi
            
            local password=$(grep "ICLOUD_PASSWORD=" "$PIPELINE_DIR/config/settings.env" | cut -d'=' -f2)
            if [ -n "$password" ] && [ "$password" != "your-app-password" ]; then
                print_status "OK" "iCloud password is configured"
            else
                print_status "WARN" "iCloud password is not properly configured"
                print_status "INFO" "Please edit $PIPELINE_DIR/config/settings.env and set ICLOUD_PASSWORD"
            fi
        else
            print_status "ERROR" "iCloud credentials are not configured"
            print_status "INFO" "Please edit $PIPELINE_DIR/config/settings.env and add ICLOUD_USERNAME and ICLOUD_PASSWORD"
        fi
    else
        print_status "ERROR" "Configuration file not found"
    fi
}

# Test pipeline execution
test_pipeline() {
    print_status "INFO" "Testing pipeline execution..."
    
    if [ -f "$PIPELINE_DIR/scripts/run_pipeline.py" ]; then
        print_status "OK" "Pipeline script exists"
        
        # Test syntax
        if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/python" -m py_compile "$PIPELINE_DIR/scripts/run_pipeline.py" 2>/dev/null; then
            print_status "OK" "Pipeline script syntax is valid"
        else
            print_status "ERROR" "Pipeline script has syntax errors"
        fi
        
        # Test individual script imports
        local scripts=("download_from_icloud.py" "compress_media.py" "upload_icloud.py" "utils.py")
        for script in "${scripts[@]}"; do
            if [ -f "$PIPELINE_DIR/scripts/$script" ]; then
                if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/python" -m py_compile "$PIPELINE_DIR/scripts/$script" 2>/dev/null; then
                    print_status "OK" "Script $script syntax is valid"
                else
                    print_status "ERROR" "Script $script has syntax errors"
                fi
            else
                print_status "ERROR" "Script $script is missing"
            fi
        done
    else
        print_status "ERROR" "Pipeline script does not exist"
    fi
}

# Check Syncthing installation and status
check_syncthing() {
    print_status "INFO" "Checking Syncthing installation and status..."
    
    # Check if Syncthing is installed
    if command -v syncthing >/dev/null 2>&1; then
        print_status "OK" "Syncthing is installed"
        
        # Check Syncthing version
        local syncthing_version=$(syncthing --version | head -n1 | awk '{print $2}')
        print_status "OK" "Syncthing version: $syncthing_version"
        
        # Check if Syncthing service is running
        if systemctl is-active syncthing@root >/dev/null 2>&1; then
            print_status "OK" "Syncthing service is running"
        elif systemctl is-active syncthing >/dev/null 2>&1; then
            print_status "OK" "Syncthing service is running"
        else
            print_status "WARN" "Syncthing service is not running"
            if ask_fix "Start Syncthing service"; then
                apply_fix "Starting Syncthing service"
                systemctl start syncthing@root || systemctl start syncthing
                systemctl enable syncthing@root || systemctl enable syncthing
                # Wait a moment for service to start
                sleep 3
                if systemctl is-active syncthing@root >/dev/null 2>&1 || systemctl is-active syncthing >/dev/null 2>&1; then
                    print_status "OK" "Syncthing service started successfully"
                else
                    print_status "ERROR" "Failed to start Syncthing service"
                    print_status "INFO" "Check logs with: journalctl -u syncthing@root -f"
                fi
            fi
        fi
        
        # Check Syncthing config file location
        local syncthing_config=""
        if [ -f "/root/.local/state/syncthing/config.xml" ]; then
            syncthing_config="/root/.local/state/syncthing/config.xml"
        elif [ -f "/root/.config/syncthing/config.xml" ]; then
            syncthing_config="/root/.config/syncthing/config.xml"
        fi
        
        if [ -n "$syncthing_config" ]; then
            print_status "OK" "Syncthing configuration exists at $syncthing_config"
            
            # Check Syncthing web interface port and binding
            local syncthing_port=$(grep -o 'address="[^"]*"' "$syncthing_config" 2>/dev/null | grep -o '[0-9]*' | head -1)
            local syncthing_address=$(grep -o 'address="[^"]*"' "$syncthing_config" 2>/dev/null | grep -o '[0-9.]*' | head -1)
            
            if [ -n "$syncthing_port" ]; then
                print_status "OK" "Syncthing web interface port: $syncthing_port"
                
                # Check if GUI is bound to localhost only
                if echo "$syncthing_address" | grep -q "127.0.0.1"; then
                    print_status "WARN" "Syncthing GUI is bound to localhost only (127.0.0.1:$syncthing_port)"
                    print_status "INFO" "This prevents external access to the web interface"
                    if ask_fix "Configure Syncthing GUI to accept external connections (0.0.0.0:$syncthing_port)"; then
                        apply_fix "Configuring Syncthing GUI for external access"
                        # Backup original config
                        cp "$syncthing_config" "$syncthing_config.backup"
                        # Update the GUI address to bind to all interfaces
                        sed -i 's/address="127.0.0.1:[0-9]*"/address="0.0.0.0:'$syncthing_port'"/g' "$syncthing_config"
                        # Restart Syncthing service
                        systemctl restart syncthing@root
                        sleep 3
                        print_status "OK" "Syncthing GUI configured for external access"
                        print_status "INFO" "Web interface should now be accessible at http://$(ip route get 8.8.8.8 | awk '{print $7; exit}'):$syncthing_port"
                    fi
                elif echo "$syncthing_address" | grep -q "0.0.0.0"; then
                    print_status "OK" "Syncthing GUI is configured for external access (0.0.0.0:$syncthing_port)"
                else
                    print_status "INFO" "Syncthing GUI address: $syncthing_address:$syncthing_port"
                fi
            else
                # Try to detect port from netstat if config parsing fails
                local detected_port=$(netstat -tlnp 2>/dev/null | grep syncthing | grep -o ':[0-9]*' | head -n1 | sed 's/://')
                if [ -n "$detected_port" ]; then
                    print_status "OK" "Syncthing web interface detected on port $detected_port"
                else
                    print_status "WARN" "Could not determine Syncthing web interface port"
                fi
            fi
        else
            print_status "WARN" "Syncthing configuration not found"
        fi
        
    else
        print_status "ERROR" "Syncthing is not installed"
        if ask_fix "Install Syncthing"; then
            apply_fix "Installing Syncthing"
            # Use the latest installation method from apt.syncthing.net
            mkdir -p /etc/apt/keyrings
            curl -L -o /etc/apt/keyrings/syncthing-archive-keyring.gpg https://syncthing.net/release-key.gpg
            echo "deb [signed-by=/etc/apt/keyrings/syncthing-archive-keyring.gpg] https://apt.syncthing.net/ syncthing stable-v2" | tee /etc/apt/sources.list.d/syncthing.list
            apt update
            apt install -y syncthing
            systemctl enable syncthing@root
        fi
    fi
}

# Check system information
check_system_info() {
    print_status "INFO" "Checking system information..."
    
    # Get system IP addresses
    local primary_ip=$(ip route get 8.8.8.8 | awk '{print $7; exit}' 2>/dev/null)
    local all_ips=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1')
    
    if [ -n "$primary_ip" ]; then
        print_status "OK" "Primary IP address: $primary_ip"
    else
        print_status "WARN" "Could not determine primary IP address"
    fi
    
    if [ -n "$all_ips" ]; then
        print_status "INFO" "All IP addresses: $(echo $all_ips | tr '\n' ' ')"
    fi
    
    # Check disk space
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        print_status "OK" "Disk usage: ${disk_usage}% (healthy)"
    elif [ "$disk_usage" -lt 90 ]; then
        print_status "WARN" "Disk usage: ${disk_usage}% (getting full)"
    else
        print_status "ERROR" "Disk usage: ${disk_usage}% (critical)"
    fi
    
    # Check memory usage
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_usage" -lt 80 ]; then
        print_status "OK" "Memory usage: ${memory_usage}% (healthy)"
    elif [ "$memory_usage" -lt 90 ]; then
        print_status "WARN" "Memory usage: ${memory_usage}% (high)"
    else
        print_status "ERROR" "Memory usage: ${memory_usage}% (critical)"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    print_status "INFO" "CPU load average: $cpu_load"
    
    # Check uptime
    local uptime_info=$(uptime -p)
    print_status "INFO" "System uptime: $uptime_info"
}

# Check SSH service
check_ssh_service() {
    print_status "INFO" "Checking SSH service..."
    
    if systemctl is-active ssh >/dev/null 2>&1; then
        print_status "OK" "SSH service is running"
    elif systemctl is-active sshd >/dev/null 2>&1; then
        print_status "OK" "SSH service is running (sshd)"
    else
        print_status "WARN" "SSH service is not running"
        if ask_fix "Start SSH service"; then
            apply_fix "Starting SSH service"
            systemctl start ssh || systemctl start sshd
            systemctl enable ssh || systemctl enable sshd
        fi
    fi
}

# Check network ports and services
check_network_services() {
    print_status "INFO" "Checking network services and ports..."
    
    # Check common ports
    local ports_to_check=("22" "80" "443" "8384" "22000")
    local port_names=("SSH" "HTTP" "HTTPS" "Syncthing Web" "Syncthing Sync")
    
    for i in "${!ports_to_check[@]}"; do
        local port="${ports_to_check[$i]}"
        local name="${port_names[$i]}"
        
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            print_status "OK" "$name (port $port) is listening"
        else
            print_status "INFO" "$name (port $port) is not listening"
        fi
    done
    
    # Check if firewall is active
    if command -v ufw >/dev/null 2>&1; then
        if ufw status | grep -q "Status: active"; then
            print_status "OK" "UFW firewall is active"
            local ufw_status=$(ufw status | grep -E "^\s*[0-9]" | wc -l)
            print_status "INFO" "UFW rules: $ufw_status active rules"
        else
            print_status "WARN" "UFW firewall is inactive"
        fi
    fi
}

# Check mount points
check_mount_points() {
    print_status "INFO" "Checking mount points..."
    
    local mount_points=("/mnt/nas" "/mnt/syncthing")
    
    for mount in "${mount_points[@]}"; do
        if mountpoint -q "$mount" 2>/dev/null; then
            print_status "OK" "$mount is mounted"
            local mount_info=$(df -h "$mount" | awk 'NR==2 {print $2 " total, " $4 " available"}')
            print_status "INFO" "$mount: $mount_info"
        else
            print_status "WARN" "$mount is not mounted"
        fi
    done
}

# Generate recommendations
generate_recommendations() {
    print_status "INFO" "Generating system recommendations..."
    
    echo
    echo -e "${BLUE}=== SYSTEM RECOMMENDATIONS ===${NC}"
    echo
    
    # Disk space recommendations
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 70 ]; then
        echo -e "${YELLOW}⚠ Disk Space:${NC} Consider cleaning up old files or expanding storage"
        echo "   - Check /opt/media-pipeline/logs for old log files"
        echo "   - Review /opt/media-pipeline/temp for temporary files"
        echo "   - Consider archiving old compressed media"
    fi
    
    # Memory recommendations
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_usage" -gt 80 ]; then
        echo -e "${YELLOW}⚠ Memory Usage:${NC} High memory usage detected"
        echo "   - Consider adding more RAM"
        echo "   - Check for memory leaks in running processes"
    fi
    
    # Security recommendations
    echo -e "${BLUE}🔒 Security:${NC}"
    echo "   - Ensure SSH keys are configured (disable password auth)"
    echo "   - Keep system packages updated regularly"
    echo "   - Configure UFW firewall rules for Syncthing ports"
    echo "   - Use strong passwords for all services"
    
    # Performance recommendations
    echo -e "${BLUE}⚡ Performance:${NC}"
    echo "   - Consider using SSD storage for better I/O performance"
    echo "   - Monitor CPU usage during media processing"
    echo "   - Optimize Syncthing settings for your network"
    
    # Backup recommendations
    echo -e "${BLUE}💾 Backup:${NC}"
    echo "   - Set up automated backups of configuration files"
    echo "   - Test restore procedures regularly"
    echo "   - Consider off-site backup for critical data"
    
    echo
}

# Main execution
main() {
    # Check for specific command line options
    if [[ "$1" == "--fix-permissions" ]]; then
        echo -e "${BLUE}Media Pipeline Permission Fix${NC}"
        echo "=================================="
        echo
        check_root
        fix_permissions
        exit 0
    fi
    
    echo -e "${BLUE}Media Pipeline Status Check and Fix Tool${NC}"
    echo "=============================================="
    echo
    
    check_root
    check_non_interactive "$@"
    
    echo "Starting comprehensive health check..."
    echo
    
    check_packages
    check_nodejs
    check_user_group
    check_directories
    check_permissions
    check_files_copied
    check_python_venv
    check_nodejs_packages
    check_systemd_service
    check_log_rotation
    check_cron_job
    check_config
    check_pipeline_dependencies
    check_icloud_config
    test_pipeline
    check_syncthing
    check_ssh_service
    check_system_info
    check_network_services
    check_mount_points
    check_nas_structure
    generate_recommendations
    
    echo
    echo "=============================================="
    echo -e "${BLUE}Health Check Summary${NC}"
    echo "=============================================="
    
    if [ $ISSUES_FOUND -eq 0 ]; then
        print_status "OK" "No issues found! System is healthy."
    else
        print_status "WARN" "$ISSUES_FOUND issue(s) found"
    fi
    
    if [ $FIXES_APPLIED -gt 0 ]; then
        print_status "INFO" "$FIXES_APPLIED fix(es) applied"
    fi
    
    echo
    echo -e "${BLUE}=== SYSTEM ACCESS INFORMATION ===${NC}"
    
    # Display system IP and ports
    local primary_ip=$(ip route get 8.8.8.8 | awk '{print $7; exit}' 2>/dev/null)
    local syncthing_config=""
    if [ -f "/root/.local/state/syncthing/config.xml" ]; then
        syncthing_config="/root/.local/state/syncthing/config.xml"
    elif [ -f "/root/.config/syncthing/config.xml" ]; then
        syncthing_config="/root/.config/syncthing/config.xml"
    fi
    local syncthing_port="8384"  # Default port
    if [ -n "$syncthing_config" ]; then
        syncthing_port=$(grep -o 'address="[^"]*"' "$syncthing_config" 2>/dev/null | grep -o '[0-9]*' | head -1)
        [ -z "$syncthing_port" ] && syncthing_port="8384"
    fi
    
    if [ -n "$primary_ip" ]; then
        echo "🌐 System IP Address: $primary_ip"
    fi
    
    if [ -n "$syncthing_port" ]; then
        echo "🔄 Syncthing Web Interface: http://$primary_ip:$syncthing_port"
    else
        echo "🔄 Syncthing Web Interface: http://$primary_ip:8384 (default)"
    fi
    
    echo "🔧 SSH Access: ssh root@$primary_ip"
    echo
    
    echo -e "${BLUE}=== SERVICE MANAGEMENT ===${NC}"
    echo "Media Pipeline Service:"
    echo "  Start:   systemctl start $SERVICE_NAME"
    echo "  Stop:    systemctl stop $SERVICE_NAME"
    echo "  Status:  systemctl status $SERVICE_NAME"
    echo "  Logs:    journalctl -u $SERVICE_NAME -f"
    echo
    echo "Syncthing Service:"
    echo "  Start:   systemctl start syncthing@root"
    echo "  Stop:    systemctl stop syncthing@root"
    echo "  Status:  systemctl status syncthing@root"
    echo "  Logs:    journalctl -u syncthing@root -f"
    echo
    echo -e "${BLUE}=== TESTING ===${NC}"
    echo "Manual pipeline test:"
    echo "  sudo -u $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py"
    echo
    echo "Check system health:"
    echo "  sudo ./scripts/check_and_fix.sh"
}

check_nas_structure() {
    echo -e "${BLUE}ℹ Checking NAS directory structure...${NC}"
    
    # Get NAS base directory from settings
    local nas_base=""
    if [ -f "$PIPELINE_DIR/config/settings.env" ]; then
        nas_base=$(grep "^NAS_MOUNT=" "$PIPELINE_DIR/config/settings.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    fi
    
    if [ -z "$nas_base" ]; then
        echo -e "${YELLOW}⚠ NAS_MOUNT not configured in settings.env${NC}"
        return 0
    fi
    
    # Required directories
    local required_dirs=(
        "$nas_base"
        "$nas_base/originals"
        "$nas_base/compressed"
        "$nas_base/bridge"
        "$nas_base/bridge/icloud"
        "$nas_base/bridge/pixel"
        "$nas_base/sorted"
        "$nas_base/temp"
        "$nas_base/cleanup"
        "$nas_base/logs"
    )
    
    local missing_dirs=()
    local existing_dirs=()
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            existing_dirs+=("$dir")
        else
            missing_dirs+=("$dir")
        fi
    done
    
    if [ ${#missing_dirs[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ All NAS directories exist${NC}"
        echo -e "${GREEN}✓ NAS structure is properly configured${NC}"
    else
        echo -e "${YELLOW}⚠ Missing NAS directories:${NC}"
        for dir in "${missing_dirs[@]}"; do
            echo -e "${YELLOW}  - $dir${NC}"
        done
        
        if ask_fix "Create missing NAS directories"; then
            echo -e "${BLUE}ℹ Creating missing NAS directories...${NC}"
            
            for dir in "${missing_dirs[@]}"; do
                mkdir -p "$dir"
                echo -e "${GREEN}✓ Created: $dir${NC}"
            done
            
            # Set proper ownership and permissions
            chown -R "$USER_NAME:$USER_NAME" "$nas_base"
            chmod -R 755 "$nas_base"
            chmod -R 644 "$nas_base/logs" 2>/dev/null || true
            
            echo -e "${GREEN}✓ NAS directory structure created successfully${NC}"
        fi
    fi
    
    # Check permissions
    local owner=$(stat -c '%U:%G' "$nas_base" 2>/dev/null || echo "unknown")
    if [[ "$owner" == "$USER_NAME:$USER_NAME" ]]; then
        echo -e "${GREEN}✓ NAS directory ownership is correct ($owner)${NC}"
    else
        echo -e "${YELLOW}⚠ NAS directory ownership is $owner (expected: $USER_NAME:$USER_NAME)${NC}"
        
        if ask_fix "Fix NAS directory ownership"; then
            chown -R "$USER_NAME:$USER_NAME" "$nas_base"
            echo -e "${GREEN}✓ Fixed NAS directory ownership${NC}"
        fi
    fi
}

# Run main function
main "$@"
