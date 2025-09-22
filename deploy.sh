#!/bin/bash

# Media Pipeline Deployment Script
# Fetches latest updates from git and deploys to /opt/media-pipeline/
# Keeps running application separate from git repository

set -e  # Exit on any error

# Configuration
GIT_REPO_DIR="$(pwd)"
DEPLOY_DIR="/opt/media-pipeline"
BACKUP_DIR="/opt/media-pipeline-backup"
LOG_FILE="/opt/media-pipeline/logs/deploy.log"
SERVICE_USER="media-pipeline"
SERVICE_GROUP="media-pipeline"

# Ensure logs directory exists from the start
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to run commands with or without sudo based on current user
run_cmd() {
    if [[ $EUID -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Helper function to run commands as service user
run_as_service_user() {
    if [[ $EUID -eq 0 ]]; then
        sudo -u "$SERVICE_USER" "$@"
    else
        sudo -u "$SERVICE_USER" "$@"
    fi
}

# Ensure logs directory exists
ensure_logs_dir() {
    run_cmd mkdir -p "$(dirname "$LOG_FILE")"
}

# Logging function
log() {
    ensure_logs_dir
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    ensure_logs_dir
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    ensure_logs_dir
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    ensure_logs_dir
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root. This is not recommended for production deployments."
        warning "Consider running as a regular user with sudo privileges instead."
        warning "Continuing with root privileges..."
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install git first."
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not in a git repository. Please run this script from the project root."
    fi
    
    # Check if deployment directory exists
    if [[ ! -d "$DEPLOY_DIR" ]]; then
        error "Deployment directory $DEPLOY_DIR does not exist. Please run the installation script first."
    fi
    
    # Check if user has sudo privileges (only if not running as root)
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        error "This script requires sudo privileges. Please ensure you can run sudo commands."
    fi
    
    success "Prerequisites check passed"
}

# Create backup of current deployment
create_backup() {
    log "Creating backup of current deployment..."
    
    # Create backup directory with timestamp
    BACKUP_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    CURRENT_BACKUP_DIR="${BACKUP_DIR}_${BACKUP_TIMESTAMP}"
    
    run_cmd mkdir -p "$CURRENT_BACKUP_DIR"
    
    # Backup current deployment (excluding logs and temp files)
    run_cmd rsync -av --exclude='logs/' --exclude='temp/' --exclude='venv/' \
        "$DEPLOY_DIR/" "$CURRENT_BACKUP_DIR/" || {
        error "Failed to create backup"
    }
    
    # Keep only last 5 backups
    run_cmd find "$BACKUP_DIR"* -maxdepth 0 -type d 2>/dev/null | sort -r | tail -n +6 | run_cmd xargs rm -rf
    
    success "Backup created at $CURRENT_BACKUP_DIR"
    echo "$CURRENT_BACKUP_DIR" > /tmp/last_backup_path
}

# Fetch latest updates from git
fetch_updates() {
    log "Fetching latest updates from git..."
    
    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    log "Current branch: $CURRENT_BRANCH"
    
    # Fetch latest changes
    git fetch origin || error "Failed to fetch from origin"
    
    # Check if there are updates
    LOCAL_COMMIT=$(git rev-parse HEAD)
    REMOTE_COMMIT=$(git rev-parse origin/$CURRENT_BRANCH)
    
    if [[ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ]]; then
        warning "No updates available. Local repository is up to date."
        return 1
    fi
    
    # Show what will be updated
    log "Updates available:"
    git log --oneline "$LOCAL_COMMIT..origin/$CURRENT_BRANCH"
    
    # Pull latest changes
    git pull origin "$CURRENT_BRANCH" || error "Failed to pull latest changes"
    
    success "Git updates fetched successfully"
    return 0
}

# Deploy files to production directory
deploy_files() {
    log "Deploying files to $DEPLOY_DIR..."
    
    # Create necessary directories
    run_cmd mkdir -p "$DEPLOY_DIR"/{scripts,config,supabase,logs,temp}
    
    # Copy application files (excluding git directory and development files)
    run_cmd rsync -av --delete \
        --exclude='.git/' \
        --exclude='*.md' \
        --exclude='deploy.sh' \
        --exclude='test_*.py' \
        --exclude='debug_*.py' \
        --exclude='manual_test_commands.sh' \
        --exclude='cleanup_and_setup.sh' \
        --exclude='fix_*.sh' \
        --exclude='install.sh' \
        --exclude='manage_config.sh' \
        --exclude='setup_*.sh' \
        --exclude='sort.sh' \
        --exclude='update_packages.sh' \
        --exclude='test_setup.sh' \
        --exclude='optimalstorage/' \
        --exclude='PRODUCTION_READINESS_REPORT.md' \
        --exclude='EADME.md' \
        --exclude='Deduplication_sorting_README.md' \
        --exclude='node_modules/' \
        --exclude='venv/' \
        --exclude='logs/' \
        --exclude='temp/' \
        "$GIT_REPO_DIR/" "$DEPLOY_DIR/" || {
        error "Failed to deploy files"
    }
    
    # Set proper ownership
    run_cmd chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DEPLOY_DIR"
    
    # Set proper permissions
    run_cmd chmod -R 755 "$DEPLOY_DIR"
    run_cmd chmod +x "$DEPLOY_DIR"/scripts/*.py
    run_cmd chmod +x "$DEPLOY_DIR"/scripts/*.sh
    
    success "Files deployed successfully"
}

# Update Python virtual environment
update_venv() {
    log "Updating Python virtual environment..."
    
    # Check if virtual environment exists
    if [[ ! -d "$DEPLOY_DIR/venv" ]]; then
        log "Creating new virtual environment..."
        run_as_service_user python3 -m venv "$DEPLOY_DIR/venv"
    fi
    
    # Update pip
    run_as_service_user "$DEPLOY_DIR/venv/bin/pip" install --upgrade pip
    
    # Install/update requirements
    if [[ -f "$DEPLOY_DIR/requirements.txt" ]]; then
        run_as_service_user "$DEPLOY_DIR/venv/bin/pip" install -r "$DEPLOY_DIR/requirements.txt"
    fi
    
    success "Python virtual environment updated"
}

# Update Node.js dependencies
update_node_deps() {
    log "Updating Node.js dependencies..."
    
    if [[ -f "$DEPLOY_DIR/package.json" ]]; then
        cd "$DEPLOY_DIR"
        run_as_service_user npm install --production
        cd "$GIT_REPO_DIR"
    fi
    
    success "Node.js dependencies updated"
}

# Validate deployment
validate_deployment() {
    log "Validating deployment..."
    
    # Check if main scripts exist and are executable
    local scripts=(
        "scripts/run_pipeline.py"
        "scripts/download_from_icloud.py"
        "scripts/prepare_pixel_sync.py"
        "scripts/monitor_syncthing_sync.py"
        "scripts/run_pixel_sync.py"
    )
    
    for script in "${scripts[@]}"; do
        if [[ ! -f "$DEPLOY_DIR/$script" ]]; then
            error "Required script $script not found in deployment"
        fi
        
        if [[ ! -x "$DEPLOY_DIR/$script" ]]; then
            warning "Script $script is not executable, fixing..."
            run_cmd chmod +x "$DEPLOY_DIR/$script"
        fi
    done
    
    # Check if config file exists
    if [[ ! -f "$DEPLOY_DIR/config/settings.env" ]]; then
        warning "Configuration file not found. Please ensure config/settings.env is properly configured."
    fi
    
    # Test Python environment
    if ! run_as_service_user "$DEPLOY_DIR/venv/bin/python" -c "import supabase, icloudpd" 2>/dev/null; then
        warning "Some Python dependencies may be missing. Check the virtual environment."
    fi
    
    success "Deployment validation completed"
}

# Restart services (if any are running)
restart_services() {
    log "Checking for running services..."
    
    # Check if there are any systemd services for the media pipeline
    if systemctl is-active --quiet media-pipeline 2>/dev/null; then
        log "Restarting media-pipeline service..."
        run_cmd systemctl restart media-pipeline
        success "Service restarted"
    else
        log "No active media-pipeline service found"
    fi
}

# Rollback function
rollback() {
    error "Deployment failed. Rolling back..."
    
    if [[ -f /tmp/last_backup_path ]]; then
        BACKUP_PATH=$(cat /tmp/last_backup_path)
        if [[ -d "$BACKUP_PATH" ]]; then
            log "Restoring from backup: $BACKUP_PATH"
            run_cmd rsync -av --delete "$BACKUP_PATH/" "$DEPLOY_DIR/"
            run_cmd chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DEPLOY_DIR"
            success "Rollback completed"
        fi
    fi
}

# Main deployment function
main() {
    log "Starting Media Pipeline deployment..."
    
    # Set up error handling
    trap rollback ERR
    
    # Run deployment steps
    check_root
    check_prerequisites
    
    # Only proceed if there are updates or force deployment
    if [[ "$FORCE_DEPLOY" == "true" ]] || fetch_updates; then
        if [[ "$NO_BACKUP" != "true" ]]; then
            create_backup
        fi
        deploy_files
        update_venv
        update_node_deps
        validate_deployment
        restart_services
        
        success "Deployment completed successfully!"
        log "Deployment log saved to: $LOG_FILE"
        
        # Show deployment summary
        echo ""
        echo "=========================================="
        echo "Deployment Summary:"
        echo "=========================================="
        echo "Deployed to: $DEPLOY_DIR"
        echo "Backup location: $(cat /tmp/last_backup_path 2>/dev/null || echo 'No backup created')"
        echo "Log file: $LOG_FILE"
        echo "=========================================="
    else
        log "No updates to deploy"
    fi
    
    # Clean up
    rm -f /tmp/last_backup_path
}

# Show usage if help requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Media Pipeline Deployment Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --force        Force deployment even if no git updates"
    echo "  --no-backup    Skip backup creation"
    echo ""
    echo "This script will:"
    echo "  1. Check prerequisites"
    echo "  2. Fetch latest git updates"
    echo "  3. Create backup of current deployment"
    echo "  4. Deploy files to /opt/media-pipeline/"
    echo "  5. Update Python and Node.js dependencies"
    echo "  6. Validate deployment"
    echo "  7. Restart services if needed"
    echo ""
    exit 0
fi

# Handle command line arguments
FORCE_DEPLOY=false
NO_BACKUP=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE_DEPLOY=true
            ;;
        --no-backup)
            NO_BACKUP=true
            ;;
    esac
done

# Run main function
main
