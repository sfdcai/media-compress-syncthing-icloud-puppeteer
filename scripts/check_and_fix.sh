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

# Check system packages
check_packages() {
    print_status "INFO" "Checking system packages..."
    
    local packages=("python3" "ffmpeg" "exiftool" "rsync" "parallel" "pv" "curl" "wget" "unzip" "git")
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
        fi
    fi
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        print_status "OK" "All required packages are installed"
    else
        print_status "ERROR" "Missing packages: ${missing_packages[*]}"
        if ask_fix "Install missing packages"; then
            apply_fix "Installing missing packages"
            apt update
            apt install -y "${missing_packages[@]}"
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
            cp -r "$SOURCE_DIR"/* "$PIPELINE_DIR/"
            chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
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
            local missing_packages=$(sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" list --format=freeze | cut -d= -f1)
            local required_packages=("icloudpd" "pillow" "ffmpeg-python" "python-dotenv" "supabase" "psutil")
            local missing=()
            
            for package in "${required_packages[@]}"; do
                if ! echo "$missing_packages" | grep -q "^$package=="; then
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
            sudo -u "$USER_NAME" python3 -m venv "$PIPELINE_DIR/venv"
            sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install --upgrade pip
            if [ -f "$PIPELINE_DIR/requirements.txt" ]; then
                sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install -r "$PIPELINE_DIR/requirements.txt"
            fi
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
            if ask_fix "Start systemd service"; then
                apply_fix "Starting systemd service"
                systemctl start "$SERVICE_NAME"
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
    else
        print_status "ERROR" "Pipeline script does not exist"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}Media Pipeline Status Check and Fix Tool${NC}"
    echo "=============================================="
    echo
    
    check_root
    
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
    test_pipeline
    
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
    echo "Service management commands:"
    echo "  Start:   systemctl start $SERVICE_NAME"
    echo "  Stop:    systemctl stop $SERVICE_NAME"
    echo "  Status:  systemctl status $SERVICE_NAME"
    echo "  Logs:    journalctl -u $SERVICE_NAME -f"
    echo
    echo "Manual test:"
    echo "  sudo -u $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py"
}

# Run main function
main "$@"
