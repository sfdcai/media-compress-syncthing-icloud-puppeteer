#!/bin/bash
# Quick Fix Script for Media Pipeline Installation Issues
# Fixes common installation problems

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
SOURCE_DIR=$(pwd)

print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
    esac
}

print_header() {
    echo
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Media Pipeline Quick Fix${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_missing_packages() {
    print_status "INFO" "Installing missing system packages..."
    
    # Install python3-venv if missing
    if ! dpkg -l | grep -q "python3-venv"; then
        print_status "INFO" "Installing python3-venv..."
        apt update
        apt install -y python3-venv
        print_status "SUCCESS" "python3-venv installed"
    else
        print_status "SUCCESS" "python3-venv already installed"
    fi
    
    # Install other missing packages
    local packages=("python3" "python3-pip" "ffmpeg" "exiftool" "curl" "wget" "git")
    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            print_status "INFO" "Installing $package..."
            apt install -y "$package"
        fi
    done
    
    # Special handling for exiftool
    if ! command -v exiftool >/dev/null 2>&1; then
        print_status "INFO" "Installing exiftool via libimage-exiftool-perl..."
        apt install -y libimage-exiftool-perl
    fi
}

copy_pipeline_files() {
    print_status "INFO" "Copying pipeline files..."
    
    # Create directories if they don't exist
    mkdir -p "$PIPELINE_DIR"/{scripts,config,logs,originals,compressed,bridge,uploaded,sorted,temp,cleanup}
    
    # Copy all files from source directory
    if [ -d "$SOURCE_DIR" ]; then
        cp -r "$SOURCE_DIR"/* "$PIPELINE_DIR/" 2>/dev/null || true
        cp -r "$SOURCE_DIR"/.[^.]* "$PIPELINE_DIR/" 2>/dev/null || true
        
        # Ensure proper ownership
        chown -R "$USER_NAME:$USER_NAME" "$PIPELINE_DIR"
        
        # Create log file with correct permissions
        touch "$PIPELINE_DIR/logs/pipeline.log"
        chown "$USER_NAME:$USER_NAME" "$PIPELINE_DIR/logs/pipeline.log"
        chmod 644 "$PIPELINE_DIR/logs/pipeline.log"
        
        print_status "SUCCESS" "Pipeline files copied successfully"
    else
        print_status "ERROR" "Could not determine source directory"
        exit 1
    fi
}

create_python_venv() {
    print_status "INFO" "Creating Python virtual environment..."
    
    # Remove existing venv if it exists
    if [ -d "$PIPELINE_DIR/venv" ]; then
        print_status "INFO" "Removing existing virtual environment..."
        rm -rf "$PIPELINE_DIR/venv"
    fi
    
    # Create new virtual environment
    sudo -u "$USER_NAME" python3 -m venv "$PIPELINE_DIR/venv"
    
    # Upgrade pip
    sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install --upgrade pip
    
    # Install requirements
    if [ -f "$PIPELINE_DIR/requirements.txt" ]; then
        print_status "INFO" "Installing Python requirements..."
        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install -r "$PIPELINE_DIR/requirements.txt"
    fi
    
    print_status "SUCCESS" "Python virtual environment created successfully"
}

install_nodejs_dependencies() {
    print_status "INFO" "Installing Node.js dependencies..."
    
    cd "$PIPELINE_DIR"
    
    # Install Puppeteer
    if [ -f "package.json" ]; then
        sudo -u "$USER_NAME" npm install puppeteer@latest
        sudo -u "$USER_NAME" npm audit fix --force 2>/dev/null || true
        print_status "SUCCESS" "Node.js dependencies installed"
    else
        print_status "WARNING" "package.json not found, skipping Node.js dependencies"
    fi
}

verify_installation() {
    print_status "INFO" "Verifying installation..."
    
    # Check if files exist
    local required_files=(
        "$PIPELINE_DIR/scripts/run_pipeline.py"
        "$PIPELINE_DIR/scripts/utils.py"
        "$PIPELINE_DIR/config/settings.env"
        "$PIPELINE_DIR/requirements.txt"
        "$PIPELINE_DIR/package.json"
    )
    
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            print_status "SUCCESS" "File exists: $(basename "$file")"
        else
            print_status "ERROR" "File missing: $(basename "$file")"
        fi
    done
    
    # Check Python virtual environment
    if [ -d "$PIPELINE_DIR/venv" ]; then
        print_status "SUCCESS" "Python virtual environment exists"
    else
        print_status "ERROR" "Python virtual environment missing"
    fi
    
    # Check Node.js dependencies
    cd "$PIPELINE_DIR"
    if sudo -u "$USER_NAME" node -e "require('puppeteer')" 2>/dev/null; then
        local puppeteer_version=$(sudo -u "$USER_NAME" node -e "console.log(require('puppeteer/package.json').version)" 2>/dev/null || echo "unknown")
        print_status "SUCCESS" "Puppeteer is available (v$puppeteer_version)"
    else
        print_status "ERROR" "Puppeteer is not available"
    fi
}

show_next_steps() {
    echo
    echo -e "${GREEN}Quick fix completed!${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Run the health check:"
    echo "   sudo ./scripts/check_and_fix.sh"
    echo
    echo "2. Configure your settings:"
    echo "   nano $PIPELINE_DIR/config/settings.env"
    echo
    echo "3. Test the pipeline:"
    echo "   sudo -u $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py"
    echo
}

# Main execution
main() {
    print_header
    
    check_root
    
    install_missing_packages
    copy_pipeline_files
    create_python_venv
    install_nodejs_dependencies
    verify_installation
    
    show_next_steps
}

# Run main function
main "$@"
