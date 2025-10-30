#!/bin/bash
# Test Setup Script
# Verifies all components are working correctly

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
    echo -e "${BLUE}  Media Pipeline Setup Test${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

test_script_executability() {
    print_status "INFO" "Testing script executability..."
    
    local scripts=(
        "install.sh"
        "scripts/setup_lxc.sh"
        "scripts/check_and_fix.sh"
        "setup_nas_structure.sh"
        "manage_config.sh"
        "cleanup_and_setup.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            if [ -x "$script" ]; then
                print_status "SUCCESS" "$script is executable"
            else
                print_status "WARNING" "$script exists but is not executable"
                chmod +x "$script"
                print_status "SUCCESS" "Made $script executable"
            fi
        else
            print_status "ERROR" "$script not found"
        fi
    done
}

test_configuration_files() {
    print_status "INFO" "Testing configuration files..."
    
    if [ -f "config/settings.env" ]; then
        print_status "SUCCESS" "config/settings.env exists"
        
        # Check for required variables
        local required_vars=(
            "NAS_MOUNT"
            "ORIGINALS_DIR"
            "COMPRESSED_DIR"
            "BRIDGE_ICLOUD_DIR"
            "BRIDGE_PIXEL_DIR"
            "ICLOUD_USERNAME"
            "ICLOUD_PASSWORD"
        )
        
        for var in "${required_vars[@]}"; do
            if grep -q "^${var}=" "config/settings.env"; then
                print_status "SUCCESS" "$var is configured"
            else
                print_status "WARNING" "$var is not configured"
            fi
        done
    else
        print_status "ERROR" "config/settings.env not found"
    fi
}

test_environment_variables() {
    print_status "INFO" "Testing environment variable usage..."
    
    # Check if scripts use environment variables
    local scripts_to_check=(
        "scripts/run_pipeline.py"
        "scripts/prepare_bridge_batch.py"
        "scripts/sync_to_pixel.py"
        "scripts/upload_icloud.py"
    )
    
    for script in "${scripts_to_check[@]}"; do
        if [ -f "$script" ]; then
            if grep -q "os.getenv" "$script"; then
                print_status "SUCCESS" "$script uses environment variables"
            else
                print_status "WARNING" "$script may not use environment variables"
            fi
        else
            print_status "ERROR" "$script not found"
        fi
    done
}

test_dynamic_paths() {
    print_status "INFO" "Testing dynamic path configuration..."
    
    # Check if scripts read from settings.env
    local scripts_to_check=(
        "scripts/check_and_fix.sh"
        "setup_nas_structure.sh"
    )
    
    for script in "${scripts_to_check[@]}"; do
        if [ -f "$script" ]; then
            if grep -q "settings.env" "$script"; then
                print_status "SUCCESS" "$script reads from settings.env"
            else
                print_status "WARNING" "$script may not read from settings.env"
            fi
        else
            print_status "ERROR" "$script not found"
        fi
    done
}

test_gitignore() {
    print_status "INFO" "Testing .gitignore configuration..."
    
    if [ -f ".gitignore" ]; then
        print_status "SUCCESS" ".gitignore exists"
        
        # Check for important entries
        local important_entries=(
            "config/settings.env"
            "originals/"
            "compressed/"
            "bridge/"
            "uploaded/"
            "sorted/"
            "logs/"
        )
        
        for entry in "${important_entries[@]}"; do
            if grep -q "$entry" ".gitignore"; then
                print_status "SUCCESS" "$entry is in .gitignore"
            else
                print_status "WARNING" "$entry is not in .gitignore"
            fi
        done
    else
        print_status "ERROR" ".gitignore not found"
    fi
}

test_requirements() {
    print_status "INFO" "Testing requirements files..."
    
    if [ -f "requirements.txt" ]; then
        print_status "SUCCESS" "requirements.txt exists"
    else
        print_status "ERROR" "requirements.txt not found"
    fi
    
    if [ -f "package.json" ]; then
        print_status "SUCCESS" "package.json exists"
        
        # Check for Puppeteer
        if grep -q "puppeteer" "package.json"; then
            print_status "SUCCESS" "Puppeteer is in package.json"
        else
            print_status "WARNING" "Puppeteer is not in package.json"
        fi
    else
        print_status "ERROR" "package.json not found"
    fi
}

show_summary() {
    echo
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Test Summary${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Run installation: sudo ./install.sh"
    echo "2. Setup configuration: ./manage_config.sh setup"
    echo "3. Run health check: sudo ./scripts/check_and_fix.sh"
    echo "4. Start services: systemctl start media-pipeline"
    echo
    echo -e "${BLUE}For troubleshooting:${NC}"
    echo "- Check logs: journalctl -u media-pipeline -f"
    echo "- Run health check: sudo ./scripts/check_and_fix.sh"
    echo "- Edit config: ./manage_config.sh edit"
    echo
}

main() {
    print_header
    
    test_script_executability
    echo
    
    test_configuration_files
    echo
    
    test_environment_variables
    echo
    
    test_dynamic_paths
    echo
    
    test_gitignore
    echo
    
    test_requirements
    echo
    
    show_summary
}

main "$@"
