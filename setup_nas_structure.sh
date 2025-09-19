#!/bin/bash
# Setup NAS Directory Structure Script
# Creates organized folder structure in your NAS mount

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAS_BASE="/mnt/wd_all_pictures/sync"
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
    echo -e "${BLUE}  NAS Directory Structure Setup${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_status "ERROR" "This script must be run as root (use sudo)"
        exit 1
    fi
}

create_directory_structure() {
    print_status "INFO" "Creating directory structure in $NAS_BASE..."
    
    # Main directories - Simplified structure
    local directories=(
        "$NAS_BASE"
        "$NAS_BASE/originals"           # iCloud downloads
        "$NAS_BASE/compressed"          # Compressed media
        "$NAS_BASE/bridge"
        "$NAS_BASE/bridge/icloud"       # Batches for Puppeteer iCloud uploader
        "$NAS_BASE/bridge/pixel"        # Batches for Syncthing to sync with Pixel
        "$NAS_BASE/sorted"              # Final organized storage (by date)
        "$NAS_BASE/temp"                # Temporary processing
        "$NAS_BASE/cleanup"             # Files ready for cleanup
        "$NAS_BASE/logs"                # Pipeline logs
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "SUCCESS" "Created: $dir"
        else
            print_status "INFO" "Exists: $dir"
        fi
    done
}

set_permissions() {
    print_status "INFO" "Setting proper permissions..."
    
    # Set ownership to media-pipeline user
    chown -R "$USER_NAME:$USER_NAME" "$NAS_BASE"
    
    # Set directory permissions
    chmod -R 755 "$NAS_BASE"
    
    # Set specific permissions for logs
    chmod -R 644 "$NAS_BASE/logs" 2>/dev/null || true
    
    print_status "SUCCESS" "Permissions set correctly"
}

create_readme() {
    print_status "INFO" "Creating README with folder explanations..."
    
    cat > "$NAS_BASE/README.md" << 'EOF'
# Media Pipeline Directory Structure

This directory contains the organized structure for the media pipeline.

## Directory Structure:

### `/originals/`
- **Purpose**: Raw iCloud downloads
- **Content**: Original photos and videos from iCloud
- **Processed by**: iCloud download script

### `/compressed/`
- **Purpose**: Compressed media files
- **Content**: Optimized photos and videos
- **Processed by**: Compression script

### `/bridge/`
- **Purpose**: Direct file processing folders (simplified - no numbered batches)
- **Content**: Files ready for upload processing
- **Subfolders**:
  - `icloud/`: Files for Puppeteer iCloud uploader
  - `pixel/`: Files for Syncthing to sync with Pixel device

### `/sorted/`
- **Purpose**: Final organized storage
- **Content**: Files organized by date (yyyy/mm/dd structure)
- **Process**: Files moved here after successful upload and verification

### `/temp/`
- **Purpose**: Temporary processing files
- **Content**: Files being processed (can be cleaned up)

### `/cleanup/`
- **Purpose**: Files ready for cleanup
- **Content**: Files that can be safely deleted

### `/logs/`
- **Purpose**: Pipeline operation logs
- **Content**: Detailed logs of all operations

## Workflow:
1. iCloud downloads → `/originals/`
2. Compression → `/compressed/`
3. File preparation → `/bridge/icloud/` and `/bridge/pixel/` (direct files, no numbered batches)
4. Upload processing → Files processed directly from bridge folders
5. Final organization → `/sorted/` (organized by date)
EOF

    chown "$USER_NAME:$USER_NAME" "$NAS_BASE/README.md"
    print_status "SUCCESS" "README created"
}

show_summary() {
    echo
    echo -e "${GREEN}NAS Directory Structure Setup Complete!${NC}"
    echo
    echo -e "${BLUE}Directory Structure:${NC}"
    tree "$NAS_BASE" 2>/dev/null || find "$NAS_BASE" -type d | sort
    echo
    echo -e "${BLUE}Configuration:${NC}"
    echo "• Base directory: $NAS_BASE"
    echo "• iCloud downloads: $NAS_BASE/originals"
    echo "• Pixel sync: $NAS_BASE/pixel"
    echo "• Owner: $USER_NAME"
    echo "• Permissions: 755 (directories), 644 (files)"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Update your settings.env:"
    echo "   NAS_MOUNT=$NAS_BASE"
    echo "   PIXEL_SYNC_FOLDER=$NAS_BASE/pixel"
    echo
    echo "2. Test the pipeline:"
    echo "   sudo -u $USER_NAME /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py"
    echo
}

# Main execution
main() {
    print_header
    
    check_root
    
    create_directory_structure
    set_permissions
    create_readme
    
    show_summary
}

# Run main function
main "$@"
