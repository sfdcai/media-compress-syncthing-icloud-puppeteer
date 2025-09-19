#!/bin/bash
# Update Media Pipeline Packages Script
# Updates all packages to latest compatible versions

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
    echo -e "${BLUE}  Media Pipeline Package Update${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

update_system_packages() {
    print_status "INFO" "Updating system packages..."
    apt update
    apt upgrade -y
    print_status "SUCCESS" "System packages updated"
}

update_python_packages() {
    print_status "INFO" "Updating Python packages..."
    
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
        print_status "INFO" "Updating $package..."
        sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" install --upgrade "$package"
    done
    
    print_status "SUCCESS" "Python packages updated"
}

update_nodejs_packages() {
    print_status "INFO" "Updating Node.js packages..."
    
    cd "$PIPELINE_DIR"
    
    # Update package.json to latest Puppeteer version
    print_status "INFO" "Updating package.json with latest Puppeteer version..."
    sudo -u "$USER_NAME" npm install puppeteer@latest
    
    # Fix security vulnerabilities
    print_status "INFO" "Fixing npm security vulnerabilities..."
    sudo -u "$USER_NAME" npm audit fix --force 2>/dev/null || true
    
    print_status "SUCCESS" "Node.js packages updated"
}

verify_installations() {
    print_status "INFO" "Verifying installations..."
    
    # Check Python packages
    local python_packages=("icloudpd" "PIL" "ffmpeg" "dotenv" "supabase" "psutil")
    for package in "${python_packages[@]}"; do
        if sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/python" -c "import $package" 2>/dev/null; then
            print_status "SUCCESS" "Python module $package is available"
        else
            print_status "ERROR" "Python module $package is not available"
        fi
    done
    
    # Check Node.js packages
    cd "$PIPELINE_DIR"
    if sudo -u "$USER_NAME" node -e "require('puppeteer')" 2>/dev/null; then
        local puppeteer_version=$(sudo -u "$USER_NAME" node -e "console.log(require('puppeteer/package.json').version)" 2>/dev/null || echo "unknown")
        print_status "SUCCESS" "Puppeteer is available (v$puppeteer_version)"
    else
        print_status "ERROR" "Puppeteer is not available"
    fi
}

cleanup_old_packages() {
    print_status "INFO" "Cleaning up old packages..."
    
    # Clean npm cache
    cd "$PIPELINE_DIR"
    sudo -u "$USER_NAME" npm cache clean --force 2>/dev/null || true
    
    # Clean pip cache
    sudo -u "$USER_NAME" "$PIPELINE_DIR/venv/bin/pip" cache purge 2>/dev/null || true
    
    # Clean apt cache
    apt autoremove -y
    apt autoclean
    
    print_status "SUCCESS" "Cleanup completed"
}

show_summary() {
    echo
    echo -e "${GREEN}Package update completed!${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Run health check:"
    echo "   sudo $PIPELINE_DIR/scripts/check_and_fix.sh"
    echo
    echo "2. Test the pipeline:"
    echo "   sudo -u $USER_NAME $PIPELINE_DIR/venv/bin/python $PIPELINE_DIR/scripts/run_pipeline.py"
    echo
    echo "3. Restart services if needed:"
    echo "   sudo systemctl restart media-pipeline"
    echo
}

# Main execution
main() {
    print_header
    
    check_root
    
    update_system_packages
    update_python_packages
    update_nodejs_packages
    verify_installations
    cleanup_old_packages
    
    show_summary
}

# Run main function
main "$@"
