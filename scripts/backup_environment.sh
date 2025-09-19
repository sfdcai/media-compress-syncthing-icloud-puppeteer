#!/bin/bash
"""
Backup and restore scripts for Python virtual environment
"""

set -e

ENV_BACKUP_DIR="/opt/media-pipeline/backups"
ENV_SOURCE="/opt/media-pipeline/venv"
ENV_BACKUP_NAME="media-pipeline-env-$(date +%Y%m%d-%H%M%S).tar.gz"

backup_environment() {
    echo "Creating environment backup..."
    
    # Create backup directory
    sudo mkdir -p "$ENV_BACKUP_DIR"
    
    # Create backup
    sudo tar -czf "$ENV_BACKUP_DIR/$ENV_BACKUP_NAME" -C "$(dirname $ENV_SOURCE)" "$(basename $ENV_SOURCE)"
    
    echo "✓ Environment backed up to: $ENV_BACKUP_DIR/$ENV_BACKUP_NAME"
    
    # Keep only last 5 backups
    cd "$ENV_BACKUP_DIR"
    ls -t media-pipeline-env-*.tar.gz | tail -n +6 | xargs -r rm
    
    echo "✓ Old backups cleaned up (keeping last 5)"
}

restore_environment() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        echo "Available backups:"
        ls -la "$ENV_BACKUP_DIR"/media-pipeline-env-*.tar.gz 2>/dev/null || echo "No backups found"
        echo "Usage: $0 restore <backup-file>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        echo "Backup file not found: $backup_file"
        exit 1
    fi
    
    echo "Restoring environment from: $backup_file"
    
    # Remove current environment
    sudo rm -rf "$ENV_SOURCE"
    
    # Restore from backup
    sudo tar -xzf "$backup_file" -C "$(dirname $ENV_SOURCE)"
    
    # Fix permissions
    sudo chown -R media-pipeline:media-pipeline "$ENV_SOURCE"
    
    echo "✓ Environment restored successfully"
}

list_backups() {
    echo "Available environment backups:"
    ls -la "$ENV_BACKUP_DIR"/media-pipeline-env-*.tar.gz 2>/dev/null || echo "No backups found"
}

case "$1" in
    backup)
        backup_environment
        ;;
    restore)
        restore_environment "$2"
        ;;
    list)
        list_backups
        ;;
    *)
        echo "Usage: $0 {backup|restore|list}"
        echo "  backup  - Create a new environment backup"
        echo "  restore - Restore from backup (specify backup file)"
        echo "  list    - List available backups"
        exit 1
        ;;
esac
