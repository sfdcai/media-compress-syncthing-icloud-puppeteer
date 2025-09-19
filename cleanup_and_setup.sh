#!/bin/bash
# Cleanup and Setup Script
# Helps clean up local files and set up proper configuration

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
    echo -e "${BLUE}  Media Pipeline Cleanup & Setup${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

backup_user_data() {
    print_status "INFO" "Backing up user data..."
    
    # Create backup directory
    BACKUP_DIR="../media-pipeline-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup user data directories
    for dir in originals compressed bridge uploaded sorted logs temp cleanup optimalstorage; do
        if [ -d "$dir" ]; then
            print_status "INFO" "Backing up $dir..."
            cp -r "$dir" "$BACKUP_DIR/"
        fi
    done
    
    # Backup configuration files
    if [ -f "config/settings.env" ]; then
        cp "config/settings.env" "$BACKUP_DIR/"
        print_status "INFO" "Backed up config/settings.env"
    fi
    
    # Backup any old .env files if they exist
    if [ -f ".env" ]; then
        cp ".env" "$BACKUP_DIR/"
        print_status "INFO" "Backed up .env"
    fi
    
    print_status "SUCCESS" "User data backed up to: $BACKUP_DIR"
}

clean_git_repository() {
    print_status "INFO" "Cleaning Git repository..."
    
    # Remove untracked files and directories
    git clean -fd
    
    # Reset any local changes
    git reset --hard HEAD
    
    print_status "SUCCESS" "Git repository cleaned"
}

setup_configuration() {
    print_status "INFO" "Setting up configuration..."
    
    # Make manage_config.sh executable
    chmod +x manage_config.sh
    
    # Find the most recent backup to get the config file
    BACKUP_DIR=$(ls -td ../media-pipeline-backup-* 2>/dev/null | head -1)
    
    if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/settings.env" ]; then
        print_status "INFO" "Using backed-up configuration file..."
        # Copy the backed-up config to the project directory temporarily
        cp "$BACKUP_DIR/settings.env" config/settings.env
    fi
    
    # Run setup
    ./manage_config.sh setup
    
    print_status "SUCCESS" "Configuration setup completed"
}

restore_user_data() {
    print_status "INFO" "Restoring user data..."
    
    # Find the most recent backup
    BACKUP_DIR=$(ls -td ../media-pipeline-backup-* 2>/dev/null | head -1)
    
    if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
        print_status "INFO" "Found backup: $BACKUP_DIR"
        
        # Restore directories
        for dir in originals compressed bridge uploaded sorted logs temp cleanup optimalstorage; do
            if [ -d "$BACKUP_DIR/$dir" ]; then
                print_status "INFO" "Restoring $dir..."
                cp -r "$BACKUP_DIR/$dir" ./
            fi
        done
        
        print_status "SUCCESS" "User data restored"
    else
        print_status "WARNING" "No backup found, skipping restore"
    fi
}

update_from_git() {
    print_status "INFO" "Updating from Git repository..."
    
    # Pull latest changes
    git pull origin main
    
    print_status "SUCCESS" "Git update completed"
}

show_summary() {
    echo
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Edit your configuration:"
    echo "   ./manage_config.sh edit"
    echo
    echo "2. Check configuration status:"
    echo "   ./manage_config.sh status"
    echo
    echo "3. Run health check:"
    echo "   sudo ./scripts/check_and_fix.sh"
    echo
    echo -e "${BLUE}Configuration File Location:${NC}"
    echo "   ~/.config/media-pipeline/settings.env"
    echo
    echo -e "${BLUE}For Future Updates:${NC}"
    echo "   ./manage_config.sh update"
    echo
}

main() {
    print_header
    
    print_status "WARNING" "This script will:"
    echo "  - Backup your user data"
    echo "  - Clean the Git repository"
    echo "  - Set up proper configuration"
    echo "  - Update from Git"
    echo "  - Restore your user data"
    echo
    
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "INFO" "Operation cancelled"
        exit 0
    fi
    
    # Execute steps
    backup_user_data
    clean_git_repository
    update_from_git
    setup_configuration
    restore_user_data
    show_summary
}

main "$@"
