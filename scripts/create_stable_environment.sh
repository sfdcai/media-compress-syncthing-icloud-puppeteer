#!/bin/bash
"""
Create a stable Python environment in a better location
"""

set -e

# Configuration
STABLE_ENV_DIR="/opt/python-envs/media-pipeline"
PROJECT_DIR="/opt/media-pipeline"
BACKUP_DIR="/opt/media-pipeline/backups"

echo "=== Creating Stable Python Environment ==="

# Create stable environment directory
echo "Creating stable environment directory..."
sudo mkdir -p "$(dirname $STABLE_ENV_DIR)"
sudo python3 -m venv "$STABLE_ENV_DIR"
sudo chown -R media-pipeline:media-pipeline "$STABLE_ENV_DIR"

echo "✓ Stable environment created at: $STABLE_ENV_DIR"

# Install required packages
echo "Installing required packages..."
sudo -u media-pipeline "$STABLE_ENV_DIR/bin/pip" install --upgrade pip
sudo -u media-pipeline "$STABLE_ENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

echo "✓ Required packages installed"

# Create symlink for easy access
echo "Creating symlink..."
sudo rm -f "$PROJECT_DIR/venv"
sudo ln -s "$STABLE_ENV_DIR" "$PROJECT_DIR/venv"

echo "✓ Symlink created: $PROJECT_DIR/venv -> $STABLE_ENV_DIR"

# Test the environment
echo "Testing environment..."
sudo -u media-pipeline "$STABLE_ENV_DIR/bin/python" -c "import supabase; print('✓ Supabase import successful')"
sudo -u media-pipeline "$STABLE_ENV_DIR/bin/icloudpd" --help > /dev/null && echo "✓ icloudpd working"

# Create backup
echo "Creating initial backup..."
sudo mkdir -p "$BACKUP_DIR"
sudo tar -czf "$BACKUP_DIR/media-pipeline-env-initial-$(date +%Y%m%d).tar.gz" -C "$(dirname $STABLE_ENV_DIR)" "$(basename $STABLE_ENV_DIR)"

echo "✓ Initial backup created"

echo ""
echo "=== Environment Setup Complete ==="
echo "Environment location: $STABLE_ENV_DIR"
echo "Symlink: $PROJECT_DIR/venv"
echo "Backup location: $BACKUP_DIR"
echo ""
echo "You can now use:"
echo "  $PROJECT_DIR/venv/bin/python"
echo "  $PROJECT_DIR/venv/bin/icloudpd"
echo "  $PROJECT_DIR/venv/bin/pip"
echo ""
echo "To backup: sudo $PROJECT_DIR/scripts/backup_environment.sh backup"
echo "To restore: sudo $PROJECT_DIR/scripts/backup_environment.sh restore <backup-file>"
