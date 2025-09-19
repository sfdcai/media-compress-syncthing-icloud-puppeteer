#!/bin/bash
# Configuration Management Script
# Helps manage environment files and Git updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/media-pipeline"
ENV_FILE="$CONFIG_DIR/settings.env"
PROJECT_ENV="$PROJECT_DIR/config/settings.env"

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
    echo -e "${BLUE}  Media Pipeline Configuration Manager${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

setup_config_directory() {
    print_status "INFO" "Setting up configuration directory..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    # Copy environment file if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$PROJECT_ENV" ]; then
            cp "$PROJECT_ENV" "$ENV_FILE"
            print_status "SUCCESS" "Copied config/settings.env to $ENV_FILE"
        else
            print_status "WARNING" "No config/settings.env found in project, creating template..."
            create_template_env
        fi
    else
        print_status "INFO" "Configuration file already exists at $ENV_FILE"
    fi
    
    # Create symlink in project
    if [ -f "$ENV_FILE" ] && [ ! -L "$PROJECT_ENV" ]; then
        rm -f "$PROJECT_ENV"
        ln -s "$ENV_FILE" "$PROJECT_ENV"
        print_status "SUCCESS" "Created symlink: $PROJECT_ENV -> $ENV_FILE"
    fi
}

create_template_env() {
    cat > "$ENV_FILE" << 'EOF'
# Feature Toggles
ENABLE_ICLOUD_UPLOAD=true
ENABLE_PIXEL_UPLOAD=true
ENABLE_COMPRESSION=true
ENABLE_DEDUPLICATION=true
ENABLE_SORTING=true

# iCloud
ICLOUD_USERNAME=your@email.com
ICLOUD_PASSWORD=your-app-password

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# NAS Mount Path (for LXC) - Your base folder
NAS_MOUNT=/mnt/wd_all_pictures/sync

# Directory Structure (relative to NAS_MOUNT)
ORIGINALS_DIR=/mnt/wd_all_pictures/sync/originals
COMPRESSED_DIR=/mnt/wd_all_pictures/sync/compressed

# Bridge Directories (simplified - no numbered batches)
BRIDGE_ICLOUD_DIR=/mnt/wd_all_pictures/sync/bridge/icloud
BRIDGE_PIXEL_DIR=/mnt/wd_all_pictures/sync/bridge/pixel

# Uploaded Directories (for tracking)
UPLOADED_ICLOUD_DIR=/mnt/wd_all_pictures/sync/uploaded/icloud
UPLOADED_PIXEL_DIR=/mnt/wd_all_pictures/sync/uploaded/pixel

# Final Organization Directories
SORTED_DIR=/mnt/wd_all_pictures/sync/sorted
CLEANUP_DIR=/mnt/wd_all_pictures/sync/cleanup

# Pixel Syncthing Folder (for LXC) - Where Syncthing syncs to
PIXEL_SYNC_FOLDER=/mnt/syncthing/pixel

# File Processing Settings (simplified - no numbered batches)
# These settings control how files are organized before upload
MAX_PROCESSING_SIZE_GB=5
MAX_PROCESSING_FILES=500

# Compression Settings
JPEG_QUALITY=85
VIDEO_CRF=28
VIDEO_PRESET=fast

# Deduplication Settings
DEDUPLICATION_HASH_ALGORITHM=md5
DEDUPLICATION_BATCH_SIZE=1000

# Sorting Settings
SORTING_USE_EXIF=true
SORTING_FALLBACK_TO_CREATION_DATE=true

# Logging
LOG_LEVEL=INFO

# LXC/Proxmox Specific
LXC_USER=media-pipeline
LXC_GROUP=media-pipeline
MOUNT_PERMISSIONS=755

# Upload Settings
ICLOUD_BATCH_SIZE=50
PIXEL_SYNC_TIMEOUT=300
UPLOAD_RETRY_ATTEMPTS=3
UPLOAD_RETRY_DELAY=30

# Simplified Processing Settings
CLEAR_BRIDGE_BEFORE_PROCESSING=true
ENABLE_FILENAME_CONFLICT_RESOLUTION=true
EOF
    print_status "SUCCESS" "Created template configuration file with dynamic directory structure"
}

update_git() {
    print_status "INFO" "Updating from Git repository..."
    
    # Check if we're in a git repository
    if [ ! -d ".git" ]; then
        print_status "ERROR" "Not in a Git repository"
        return 1
    fi
    
    # Stash any local changes
    print_status "INFO" "Stashing local changes..."
    git stash push -m "Local changes before update $(date)"
    
    # Pull latest changes
    print_status "INFO" "Pulling latest changes..."
    git pull origin main
    
    # Restore stashed changes (if any)
    if git stash list | grep -q "Local changes before update"; then
        print_status "INFO" "Restoring local changes..."
        git stash pop
    fi
    
    print_status "SUCCESS" "Git update completed"
}

show_status() {
    print_status "INFO" "Configuration Status:"
    echo "  Project Directory: $PROJECT_DIR"
    echo "  Config Directory: $CONFIG_DIR"
    echo "  Environment File: $ENV_FILE"
    echo "  Project Symlink: $PROJECT_ENV"
    echo
    
    if [ -f "$ENV_FILE" ]; then
        print_status "SUCCESS" "Configuration file exists"
    else
        print_status "WARNING" "Configuration file not found"
    fi
    
    if [ -L "$PROJECT_ENV" ]; then
        print_status "SUCCESS" "Symlink is properly configured"
    else
        print_status "WARNING" "Symlink not configured"
    fi
}

show_help() {
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  setup     - Set up configuration directory and symlink"
    echo "  update    - Update from Git repository"
    echo "  status    - Show configuration status"
    echo "  edit      - Edit configuration file"
    echo "  help      - Show this help message"
    echo
    echo "Examples:"
    echo "  $0 setup    # Initial setup"
    echo "  $0 update   # Update from Git"
    echo "  $0 edit     # Edit configuration"
}

main() {
    print_header
    
    case "${1:-help}" in
        "setup")
            setup_config_directory
            show_status
            ;;
        "update")
            update_git
            ;;
        "status")
            show_status
            ;;
        "edit")
            if [ -f "$ENV_FILE" ]; then
                ${EDITOR:-nano} "$ENV_FILE"
            else
                print_status "ERROR" "Configuration file not found. Run 'setup' first."
            fi
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

main "$@"
