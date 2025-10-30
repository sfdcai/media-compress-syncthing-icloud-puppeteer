#!/bin/bash
# Media Pipeline Comprehensive Installation Script
# Enhanced installation with external service setup and stability features

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PIPELINE_DIR="/opt/media-pipeline"
USER_NAME="media-pipeline"
SERVICE_NAME="media-pipeline"

# Remember where the installer lives so we can reliably copy files later
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Installation tracking
INSTALLATION_STEPS=()
FAILED_STEPS=()
WARNINGS=()

# Helper functions
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            INSTALLATION_STEPS+=("✓ $message")
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            WARNINGS+=("⚠ $message")
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            FAILED_STEPS+=("✗ $message")
            ;;
    esac
}

print_header() {
    echo
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Media Pipeline Installation & Setup${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

print_section() {
    echo
    echo -e "${BLUE}=== $1 ===${NC}"
    echo
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_system_requirements() {
    print_section "System Requirements Check"
    
    # Check Ubuntu version
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" == "ubuntu" ]]; then
            print_status "SUCCESS" "Ubuntu detected: $VERSION"
        else
            print_status "WARNING" "Non-Ubuntu system detected: $ID $VERSION"
            print_status "INFO" "This script is optimized for Ubuntu 22.04+"
        fi
    else
        print_status "WARNING" "Cannot determine OS version"
    fi
    
    # Check available disk space
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local available_gb=$((available_space / 1024 / 1024))
    
    if [ $available_gb -gt 20 ]; then
        print_status "SUCCESS" "Available disk space: ${available_gb}GB"
    else
        print_status "WARNING" "Low disk space: ${available_gb}GB (recommended: 20GB+)"
    fi
    
    # Check memory
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    if [ $total_mem -gt 2048 ]; then
        print_status "SUCCESS" "Total memory: ${total_mem}MB"
    else
        print_status "WARNING" "Low memory: ${total_mem}MB (recommended: 4GB+)"
    fi
}

install_system_packages() {
    print_section "System Package Installation"
    
    print_status "INFO" "Updating package lists..."
    apt update
    
    print_status "INFO" "Installing system packages..."
    local packages=(
        "python3"
        "python3-venv" 
        "python3-pip"
        "ffmpeg"
        "exiftool"
        "rsync"
        "parallel"
        "pv"
        "curl"
        "wget"
        "unzip"
        "git"
        "net-tools"
        "htop"
        "nano"
        "ufw"
    )
    
    for package in "${packages[@]}"; do
        if dpkg -l | grep -q "^ii  $package "; then
            print_status "SUCCESS" "Package $package already installed"
        else
            print_status "INFO" "Installing $package..."
            if apt install -y "$package"; then
                print_status "SUCCESS" "Package $package installed"
            else
                print_status "ERROR" "Failed to install $package"
                return 1
            fi
        fi
    done
    
    # Special handling for exiftool
    if ! command -v exiftool >/dev/null 2>&1; then
        print_status "INFO" "Installing exiftool via libimage-exiftool-perl..."
        apt install -y libimage-exiftool-perl
    fi
    
    # Install Chrome dependencies for Puppeteer
    print_status "INFO" "Installing Chrome dependencies for Puppeteer..."
    apt install -y \
        libnspr4 \
        libnss3 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libxss1 \
        libasound2 \
        libx11-xcb1 \
        libxcb-dri3-0 \
        libxcb1 \
        libxcb-xfixes0 \
        libxcb-xkb1 \
        libxcb-randr0 \
        libxcb-shape0 \
        libxcb-glx0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-render-util0 \
        libxcb-render0 \
        libxcb-shm0 \
        libxcb-sync1 \
        libxcb-util1 \
        libxcb-xinerama0
}

install_nodejs() {
    print_section "Node.js Installation"
    
    # Check if Node.js is already installed
    if command -v node >/dev/null 2>&1; then
        local node_version=$(node --version | sed 's/v//')
        local major_version=$(echo $node_version | cut -d. -f1)
        
        if [ "$major_version" -ge 18 ]; then
            print_status "SUCCESS" "Node.js $node_version is already installed and compatible"
            return 0
        else
            print_status "WARNING" "Node.js $node_version is too old (requires 18+)"
        fi
    fi
    
    print_status "INFO" "Installing Node.js 18+ from NodeSource..."
    
    # Add NodeSource repository
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    
    # Install Node.js
    if apt install -y nodejs; then
        local node_version=$(node --version)
        local npm_version=$(npm --version)
        print_status "SUCCESS" "Node.js $node_version and npm $npm_version installed"
    else
        print_status "ERROR" "Failed to install Node.js"
        return 1
    fi
}

install_syncthing() {
    print_section "Syncthing Installation"
    
    if command -v syncthing >/dev/null 2>&1; then
        local syncthing_version=$(syncthing --version | head -n1 | awk '{print $2}')
        print_status "SUCCESS" "Syncthing $syncthing_version is already installed"
        return 0
    fi
    
    print_status "INFO" "Installing Syncthing from official repository..."
    
    # Add Syncthing repository
    mkdir -p /etc/apt/keyrings
    curl -L -o /etc/apt/keyrings/syncthing-archive-keyring.gpg https://syncthing.net/release-key.gpg
    echo "deb [signed-by=/etc/apt/keyrings/syncthing-archive-keyring.gpg] https://apt.syncthing.net/ syncthing stable-v2" | tee /etc/apt/sources.list.d/syncthing.list
    
    # Update and install
    apt update
    if apt install -y syncthing; then
        local syncthing_version=$(syncthing --version | head -n1 | awk '{print $2}')
        print_status "SUCCESS" "Syncthing $syncthing_version installed"
        
        # Enable Syncthing service
        systemctl enable syncthing@root
        print_status "SUCCESS" "Syncthing service enabled"
    else
        print_status "ERROR" "Failed to install Syncthing"
        return 1
    fi
}

create_user_and_directories() {
    print_section "User and Directory Setup"
    
    # Create user and group
    if id "$USER_NAME" >/dev/null 2>&1; then
        print_status "SUCCESS" "User $USER_NAME already exists"
    else
        print_status "INFO" "Creating user $USER_NAME..."
        groupadd -r "$USER_NAME" || true
        useradd -r -g "$USER_NAME" -d "$PIPELINE_DIR" -s /bin/bash "$USER_NAME" || true
        print_status "SUCCESS" "User $USER_NAME created"
    fi
    
    # Create directory structure
    print_status "INFO" "Creating directory structure..."
    local directories=(
        "$PIPELINE_DIR"
        "$PIPELINE_DIR/originals"
        "$PIPELINE_DIR/compressed"
        "$PIPELINE_DIR/bridge"
        "$PIPELINE_DIR/bridge/icloud"
        "$PIPELINE_DIR/bridge/pixel"
        "$PIPELINE_DIR/uploaded"
        "$PIPELINE_DIR/uploaded/icloud"
        "$PIPELINE_DIR/uploaded/pixel"
        "$PIPELINE_DIR/sorted"
        "$PIPELINE_DIR/sorted/icloud"
        "$PIPELINE_DIR/sorted/pixel"
        "$PIPELINE_DIR/logs"
        "$PIPELINE_DIR/temp"
        "$PIPELINE_DIR/cleanup"
        "/mnt/nas/photos"
        "/mnt/syncthing/pixel"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
    done
    
    # Set ownership and permissions
    chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
    chown -R "$USER_NAME:$USER_NAME" /mnt/nas 2>/dev/null || true
    chown -R "$USER_NAME:$USER_NAME" /mnt/syncthing 2>/dev/null || true
    chmod -R 755 "$PIPELINE_DIR"
    chmod -R 755 /mnt/nas 2>/dev/null || true
    chmod -R 755 /mnt/syncthing 2>/dev/null || true
    
    print_status "SUCCESS" "Directory structure created with proper permissions"
}

setup_python_environment() {
    print_section "Python Environment Setup"
    
    print_status "INFO" "Creating Python virtual environment..."
    sudo -u "$USER_NAME" python3 -m venv "$PIPELINE_DIR/venv"
    sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install --upgrade pip
    
    print_status "INFO" "Installing Python dependencies..."
    local python_packages=(
        "icloudpd"
        "pillow"
        "ffmpeg-python"
        "python-dotenv"
        "supabase"
        "psutil"
        "requests"
        "cryptography"
    )
    
    for package in "${python_packages[@]}"; do
        print_status "INFO" "Installing $package..."
        if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install "$package"; then
            print_status "SUCCESS" "Python package $package installed"
        else
            print_status "ERROR" "Failed to install Python package $package"
            return 1
        fi
    done
    
    # Verify icloudpd installation
    if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/icloudpd" --version >/dev/null 2>&1; then
        local icloudpd_version=$(sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/icloudpd" --version 2>/dev/null | head -n1 || echo "unknown")
        print_status "SUCCESS" "icloudpd installed: $icloudpd_version"
    else
        print_status "WARNING" "icloudpd installation verification failed"
        print_status "INFO" "This may be normal - will be verified during pipeline execution"
    fi
}

setup_nodejs_dependencies() {
    print_section "Node.js Dependencies Setup"

    if [ ! -d "$PIPELINE_DIR" ]; then
        print_status "ERROR" "Pipeline directory $PIPELINE_DIR does not exist"
        return 1
    fi

    if [ ! -f "$PIPELINE_DIR/package.json" ]; then
        print_status "WARNING" "No package.json found in $PIPELINE_DIR; skipping Node.js dependency installation"
        return 0
    fi

    print_status "INFO" "Installing Node.js dependencies from package.json..."

    (
        cd "$PIPELINE_DIR" || exit 1

        if sudo -u "$USER_NAME" npm install; then
            print_status "SUCCESS" "Node.js dependencies installed"

            # Address known vulnerabilities when possible without failing the installer
            if command -v npm >/dev/null 2>&1; then
                print_status "INFO" "Running npm audit fix (non-fatal)..."
                sudo -u "$USER_NAME" npm audit fix --force 2>/dev/null || true
            fi
        else
            print_status "ERROR" "npm install failed"
            exit 1
        fi
    ) || return 1
}

copy_pipeline_files() {
    print_section "Pipeline Files Setup"

    if [ ! -d "$SCRIPT_DIR" ]; then
        print_status "ERROR" "Unable to locate installer source directory"
        return 1
    fi

    print_status "INFO" "Copying pipeline files from $SCRIPT_DIR to $PIPELINE_DIR..."

    rsync -a \
        --exclude 'venv/' \
        --exclude 'node_modules/' \
        --exclude '.git/' \
        --exclude '__pycache__/' \
        "$SCRIPT_DIR"/ "$PIPELINE_DIR"/

    chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
    print_status "SUCCESS" "Pipeline files copied successfully"

    # Create log file with correct permissions
    touch "$PIPELINE_DIR/logs/pipeline.log"
    chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs/pipeline.log"
    chmod 644 "$PIPELINE_DIR/logs/pipeline.log"
    print_status "SUCCESS" "Log file created with correct permissions"
}

setup_systemd_service() {
    print_section "Systemd Service Setup"
    
    print_status "INFO" "Creating systemd service..."
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
    print_status "SUCCESS" "Systemd service created and enabled"
}

setup_log_rotation() {
    print_section "Log Rotation Setup"
    
    print_status "INFO" "Setting up log rotation..."
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
    
    print_status "SUCCESS" "Log rotation configured"
}

setup_cron_job() {
    print_section "Cron Job Setup"
    
    print_status "INFO" "Setting up cron job..."
    cat > "/etc/cron.d/$SERVICE_NAME" << EOF
# Run media pipeline daily at 2 AM
0 2 * * * $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py >> $PIPELINE_DIR/logs/cron.log 2>&1
EOF
    
    print_status "SUCCESS" "Cron job configured for daily execution at 2 AM"
}

configure_firewall() {
    print_section "Firewall Configuration"
    
    if command -v ufw >/dev/null 2>&1; then
        print_status "INFO" "Configuring UFW firewall..."
        
        # Enable UFW if not already enabled
        if ! ufw status | grep -q "Status: active"; then
            ufw --force enable
        fi
        
        # Allow SSH
        ufw allow ssh
        
        # Allow Syncthing ports
        ufw allow 8384/tcp comment "Syncthing Web UI"
        ufw allow 22000/tcp comment "Syncthing Sync"
        ufw allow 21027/udp comment "Syncthing Discovery"
        
        print_status "SUCCESS" "Firewall configured for Syncthing ports"
    else
        print_status "WARNING" "UFW not available, skipping firewall configuration"
    fi
}

setup_initial_config() {
    print_section "Initial Configuration Setup"
    
    if [ -f "$PIPELINE_DIR/config/settings.env" ]; then
        print_status "SUCCESS" "Configuration file exists"
        
        # Check if credentials are configured
        if grep -q "ICLOUD_USERNAME=" "$PIPELINE_DIR/config/settings.env" && grep -q "ICLOUD_PASSWORD=" "$PIPELINE_DIR/config/settings.env"; then
            local username=$(grep "ICLOUD_USERNAME=" "$PIPELINE_DIR/config/settings.env" | cut -d'=' -f2)
            if [ -n "$username" ] && [ "$username" != "your@email.com" ]; then
                print_status "SUCCESS" "iCloud credentials appear to be configured"
            else
                print_status "WARNING" "iCloud credentials need to be configured"
                print_status "INFO" "Edit $PIPELINE_DIR/config/settings.env and set ICLOUD_USERNAME and ICLOUD_PASSWORD"
            fi
        else
            print_status "WARNING" "iCloud credentials not found in configuration"
        fi
    else
        print_status "WARNING" "Configuration file not found"
        print_status "INFO" "Please create $PIPELINE_DIR/config/settings.env with your settings"
    fi
}

run_health_check() {
    print_section "Post-Installation Health Check"
    
    if [ -f "$PIPELINE_DIR/scripts/check_and_fix.sh" ]; then
        print_status "INFO" "Running comprehensive health check..."
        chmod +x "$PIPELINE_DIR/scripts/check_and_fix.sh"
        
        # Run health check in non-interactive mode (skip prompts)
        if "$PIPELINE_DIR/scripts/check_and_fix.sh" --non-interactive 2>/dev/null; then
            print_status "SUCCESS" "Health check passed"
        else
            print_status "WARNING" "Health check found issues - run manually to fix"
            print_status "INFO" "Run: sudo $PIPELINE_DIR/scripts/check_and_fix.sh"
        fi
    else
        print_status "WARNING" "Health check script not found"
    fi
}

show_installation_summary() {
    print_section "Installation Summary"
    
    echo -e "${GREEN}Installation completed successfully!${NC}"
    echo
    
    echo -e "${BLUE}Completed Steps:${NC}"
    for step in "${INSTALLATION_STEPS[@]}"; do
        echo "  $step"
    done
    
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo
        echo -e "${YELLOW}Warnings:${NC}"
        for warning in "${WARNINGS[@]}"; do
            echo "  $warning"
        done
    fi
    
    if [ ${#FAILED_STEPS[@]} -gt 0 ]; then
        echo
        echo -e "${RED}Failed Steps:${NC}"
        for failure in "${FAILED_STEPS[@]}"; do
            echo "  $failure"
        done
    fi
    
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Configure iCloud credentials:"
    echo "   nano $PIPELINE_DIR/config/settings.env"
    echo
    echo "2. Run health check:"
    echo "   sudo $PIPELINE_DIR/scripts/check_and_fix.sh"
    echo
    echo "3. Test the pipeline:"
    echo "   sudo -u $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py"
    echo
    echo "4. Start the service:"
    echo "   sudo systemctl start $SERVICE_NAME"
    echo
    echo -e "${BLUE}Access Information:${NC}"
    local primary_ip=$(ip route get 8.8.8.8 | awk '{print $7; exit}' 2>/dev/null || echo "YOUR_IP")
    echo "• System IP: $primary_ip"
    echo "• SSH Access: ssh root@$primary_ip"
    echo "• Syncthing Web UI: http://$primary_ip:8384"
    echo "• Pipeline Logs: $PIPELINE_DIR/logs/"
    echo
    echo -e "${GREEN}Installation complete! 🎉${NC}"
}

# Main installation process
main() {
    print_header
    
    check_root
    check_system_requirements
    
    # Installation steps
    install_system_packages || exit 1
    install_nodejs || exit 1
    install_syncthing || exit 1
    create_user_and_directories || exit 1
    copy_pipeline_files || exit 1
    setup_python_environment || exit 1
    setup_nodejs_dependencies || exit 1
    setup_systemd_service || exit 1
    setup_log_rotation || exit 1
    setup_cron_job || exit 1
    configure_firewall
    setup_initial_config
    run_health_check
    
    show_installation_summary
}

# Run main function
main "$@"
