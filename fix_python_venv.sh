#!/bin/bash
# Fix Python Virtual Environment Script
# Comprehensive fix for Python virtual environment issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo -e "${BLUE}  Python Virtual Environment Fix${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

# Configuration
PIPELINE_DIR="/opt/media-pipeline"
USER_NAME="media-pipeline"
VENV_DIR="$PIPELINE_DIR/venv"

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_python3_venv() {
    print_status "INFO" "Checking python3-venv package..."
    
    if dpkg -l | grep -q "python3-venv"; then
        print_status "SUCCESS" "python3-venv is installed"
        return 0
    else
        print_status "WARNING" "python3-venv is not installed"
        print_status "INFO" "Installing python3-venv..."
        apt update
        apt install -y python3-venv
        print_status "SUCCESS" "python3-venv installed"
        return 1
    fi
}

check_virtual_environment() {
    print_status "INFO" "Checking virtual environment..."
    
    if [ -d "$VENV_DIR" ]; then
        print_status "SUCCESS" "Virtual environment directory exists"
        
        if [ -f "$VENV_DIR/bin/python" ]; then
            print_status "SUCCESS" "Virtual environment Python executable exists"
            return 0
        else
            print_status "WARNING" "Virtual environment Python executable missing"
            return 1
        fi
    else
        print_status "WARNING" "Virtual environment directory does not exist"
        return 1
    fi
}

recreate_virtual_environment() {
    print_status "INFO" "Recreating virtual environment..."
    
    # Remove existing virtual environment if it exists
    if [ -d "$VENV_DIR" ]; then
        print_status "INFO" "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment
    print_status "INFO" "Creating new virtual environment..."
    sudo -u "$USER_NAME" python3 -m venv "$VENV_DIR"
    
    if [ -f "$VENV_DIR/bin/python" ]; then
        print_status "SUCCESS" "Virtual environment created successfully"
        return 0
    else
        print_status "ERROR" "Failed to create virtual environment"
        return 1
    fi
}

upgrade_pip() {
    print_status "INFO" "Upgrading pip in virtual environment..."
    
    sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" install --upgrade pip
    
    if [ $? -eq 0 ]; then
        print_status "SUCCESS" "Pip upgraded successfully"
        return 0
    else
        print_status "ERROR" "Failed to upgrade pip"
        return 1
    fi
}

install_requirements() {
    print_status "INFO" "Installing Python requirements..."
    
    if [ -f "$PIPELINE_DIR/requirements.txt" ]; then
        print_status "INFO" "Found requirements.txt, installing packages..."
        sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" install -r "$PIPELINE_DIR/requirements.txt"
        
        if [ $? -eq 0 ]; then
            print_status "SUCCESS" "Requirements installed successfully"
            return 0
        else
            print_status "ERROR" "Failed to install requirements"
            return 1
        fi
    else
        print_status "WARNING" "requirements.txt not found"
        return 1
    fi
}

install_critical_packages() {
    print_status "INFO" "Installing critical Python packages..."
    
    local critical_packages=("icloudpd" "pillow" "ffmpeg-python" "python-dotenv" "supabase" "psutil")
    
    for package in "${critical_packages[@]}"; do
        print_status "INFO" "Installing $package..."
        sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" install "$package"
        
        if [ $? -eq 0 ]; then
            print_status "SUCCESS" "$package installed successfully"
        else
            print_status "ERROR" "Failed to install $package"
        fi
    done
}

test_virtual_environment() {
    print_status "INFO" "Testing virtual environment..."
    
    # Test Python
    if sudo -u "$USER_NAME" "$VENV_DIR/bin/python" --version; then
        print_status "SUCCESS" "Python is working in virtual environment"
    else
        print_status "ERROR" "Python test failed"
        return 1
    fi
    
    # Test pip
    if sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" --version; then
        print_status "SUCCESS" "Pip is working in virtual environment"
    else
        print_status "ERROR" "Pip test failed"
        return 1
    fi
    
    # Test icloudpd
    if sudo -u "$USER_NAME" "$VENV_DIR/bin/icloudpd" --help >/dev/null 2>&1; then
        print_status "SUCCESS" "icloudpd is working in virtual environment"
    else
        print_status "WARNING" "icloudpd test failed (may need credentials)"
    fi
    
    # Test supabase
    if sudo -u "$USER_NAME" "$VENV_DIR/bin/python" -c "import supabase" 2>/dev/null; then
        print_status "SUCCESS" "Supabase package is available"
    else
        print_status "WARNING" "Supabase package test failed"
    fi
    
    return 0
}

show_virtual_environment_info() {
    print_status "INFO" "Virtual environment information:"
    echo "  Location: $VENV_DIR"
    echo "  Python: $(sudo -u "$USER_NAME" "$VENV_DIR/bin/python" --version 2>/dev/null || echo 'Not available')"
    echo "  Pip: $(sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" --version 2>/dev/null || echo 'Not available')"
    echo "  Installed packages:"
    sudo -u "$USER_NAME" "$VENV_DIR/bin/pip" list --format=freeze | head -10
    echo "  ... (showing first 10 packages)"
}

main() {
    print_header
    
    check_root
    
    # Step 1: Check python3-venv
    check_python3_venv
    
    # Step 2: Check virtual environment
    if ! check_virtual_environment; then
        print_status "INFO" "Virtual environment needs to be recreated"
        recreate_virtual_environment
    fi
    
    # Step 3: Upgrade pip
    upgrade_pip
    
    # Step 4: Install requirements
    if ! install_requirements; then
        print_status "WARNING" "Requirements installation failed, installing critical packages individually"
        install_critical_packages
    fi
    
    # Step 5: Test virtual environment
    test_virtual_environment
    
    # Step 6: Show information
    show_virtual_environment_info
    
    echo
    print_status "SUCCESS" "Python virtual environment fix completed!"
    echo
    print_status "INFO" "You can now test with:"
    echo "  sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --help"
    echo "  sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase.py"
}

main "$@"
