#!/bin/bash
"""
Quick environment fix - restore from backup or recreate if needed
"""

set -e

PROJECT_DIR="/opt/media-pipeline"
BACKUP_DIR="/opt/media-pipeline/backups"
STABLE_ENV_DIR="/opt/python-envs/media-pipeline"

echo "=== Quick Environment Fix ==="

# Check if stable environment exists
if [ -d "$STABLE_ENV_DIR" ]; then
    echo "✓ Stable environment found at: $STABLE_ENV_DIR"
    
    # Test if it's working
    if sudo -u media-pipeline "$STABLE_ENV_DIR/bin/python" -c "import supabase" 2>/dev/null; then
        echo "✓ Environment is working correctly"
        
        # Ensure symlink exists
        if [ ! -L "$PROJECT_DIR/venv" ]; then
            echo "Creating symlink..."
            sudo ln -s "$STABLE_ENV_DIR" "$PROJECT_DIR/venv"
            echo "✓ Symlink created"
        fi
        
        echo "Environment is ready to use!"
        exit 0
    else
        echo "⚠ Environment exists but has issues"
    fi
fi

# Try to restore from latest backup
echo "Attempting to restore from latest backup..."
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/media-pipeline-env-*.tar.gz 2>/dev/null | head -n1)

if [ -n "$LATEST_BACKUP" ]; then
    echo "Found backup: $LATEST_BACKUP"
    
    # Remove broken environment
    sudo rm -rf "$STABLE_ENV_DIR"
    
    # Restore from backup
    sudo mkdir -p "$(dirname $STABLE_ENV_DIR)"
    sudo tar -xzf "$LATEST_BACKUP" -C "$(dirname $STABLE_ENV_DIR)"
    sudo chown -R media-pipeline:media-pipeline "$STABLE_ENV_DIR"
    
    # Create symlink
    sudo rm -f "$PROJECT_DIR/venv"
    sudo ln -s "$STABLE_ENV_DIR" "$PROJECT_DIR/venv"
    
    echo "✓ Environment restored from backup"
    
    # Test
    if sudo -u media-pipeline "$STABLE_ENV_DIR/bin/python" -c "import supabase" 2>/dev/null; then
        echo "✓ Restored environment is working"
        exit 0
    else
        echo "⚠ Restored environment still has issues"
    fi
else
    echo "No backups found"
fi

# Last resort: recreate environment
echo "Recreating environment from scratch..."
sudo rm -rf "$STABLE_ENV_DIR"
sudo python3 -m venv "$STABLE_ENV_DIR"
sudo chown -R media-pipeline:media-pipeline "$STABLE_ENV_DIR"

# Install packages
sudo -u media-pipeline "$STABLE_ENV_DIR/bin/pip" install --upgrade pip
sudo -u media-pipeline "$STABLE_ENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# Create symlink
sudo rm -f "$PROJECT_DIR/venv"
sudo ln -s "$STABLE_ENV_DIR" "$PROJECT_DIR/venv"

# Create backup
sudo mkdir -p "$BACKUP_DIR"
sudo tar -czf "$BACKUP_DIR/media-pipeline-env-recreated-$(date +%Y%m%d-%H%M%S).tar.gz" -C "$(dirname $STABLE_ENV_DIR)" "$(basename $STABLE_ENV_DIR)"

echo "✓ Environment recreated and backed up"

# Test
if sudo -u media-pipeline "$STABLE_ENV_DIR/bin/python" -c "import supabase" 2>/dev/null; then
    echo "✓ New environment is working"
else
    echo "✗ Environment creation failed"
    exit 1
fi

echo "Environment fix completed successfully!"
