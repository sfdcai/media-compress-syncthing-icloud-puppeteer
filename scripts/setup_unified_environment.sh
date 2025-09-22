#!/bin/bash

# Unified Environment Setup Script
# This script sets up both Python and Node.js environments in a consistent location
# All environments will be under /opt/media-pipeline/

set -e  # Exit on any error

# Configuration
DEPLOY_DIR="/opt/media-pipeline"
SERVICE_USER="media-pipeline"
SERVICE_GROUP="media-pipeline"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
fi

log "Starting unified environment setup..."

# Create deployment directory structure
log "Creating directory structure..."
mkdir -p "$DEPLOY_DIR"/{scripts,config,supabase,logs,temp,venv,node_modules}
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"

# Install system dependencies
log "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nodejs \
    npm \
    git \
    curl \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils

success "System dependencies installed"

# Setup Python virtual environment
log "Setting up Python virtual environment..."
if [[ -d "$DEPLOY_DIR/venv" ]]; then
    warning "Python virtual environment already exists, removing old one..."
    rm -rf "$DEPLOY_DIR/venv"
fi

# Create virtual environment as service user
sudo -u "$SERVICE_USER" python3 -m venv "$DEPLOY_DIR/venv"

# Upgrade pip in virtual environment
log "Upgrading pip in virtual environment..."
sudo -u "$SERVICE_USER" "$DEPLOY_DIR/venv/bin/pip" install --upgrade pip

# Install Python requirements
if [[ -f "$DEPLOY_DIR/requirements.txt" ]]; then
    log "Installing Python requirements..."
    sudo -u "$SERVICE_USER" "$DEPLOY_DIR/venv/bin/pip" install -r "$DEPLOY_DIR/requirements.txt"
    success "Python requirements installed"
else
    warning "requirements.txt not found, skipping Python package installation"
fi

# Test Python environment
log "Testing Python environment..."
if sudo -u "$SERVICE_USER" "$DEPLOY_DIR/venv/bin/python" -c "import sys; print('Python version:', sys.version)" 2>/dev/null; then
    success "Python environment working"
else
    error "Python environment test failed"
fi

# Setup Node.js environment
log "Setting up Node.js environment..."
cd "$DEPLOY_DIR"

# Install Node.js dependencies
if [[ -f "$DEPLOY_DIR/package.json" ]]; then
    log "Installing Node.js dependencies..."
    sudo -u "$SERVICE_USER" npm install --production
    success "Node.js dependencies installed"
else
    warning "package.json not found, skipping Node.js package installation"
fi

# Test Node.js environment
log "Testing Node.js environment..."
if sudo -u "$SERVICE_USER" node --version 2>/dev/null; then
    success "Node.js environment working"
else
    error "Node.js environment test failed"
fi

# Set proper permissions
log "Setting proper permissions..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"
chmod +x "$DEPLOY_DIR"/scripts/*.py 2>/dev/null || true
chmod +x "$DEPLOY_DIR"/scripts/*.sh 2>/dev/null || true
chmod +x "$DEPLOY_DIR"/scripts/*.js 2>/dev/null || true

# Create environment info file
log "Creating environment info..."
cat > "$DEPLOY_DIR/environment_info.txt" << EOF
Media Pipeline Environment Setup
===============================
Setup Date: $(date)
Python Virtual Environment: $DEPLOY_DIR/venv
Node.js Environment: $DEPLOY_DIR/node_modules
Service User: $SERVICE_USER
Service Group: $SERVICE_GROUP

Python Version:
$(sudo -u "$SERVICE_USER" "$DEPLOY_DIR/venv/bin/python" --version)

Node.js Version:
$(sudo -u "$SERVICE_USER" node --version)

NPM Version:
$(sudo -u "$SERVICE_USER" npm --version)

Installed Python Packages:
$(sudo -u "$SERVICE_USER" "$DEPLOY_DIR/venv/bin/pip" list)

Installed Node.js Packages:
$(sudo -u "$SERVICE_USER" npm list --depth=0)
EOF

chown "$SERVICE_USER:$SERVICE_GROUP" "$DEPLOY_DIR/environment_info.txt"

success "Environment info saved to $DEPLOY_DIR/environment_info.txt"

# Final validation
log "Running final validation..."

# Test key Python packages
if sudo -u "$SERVICE_USER" "$DEPLOY_DIR/venv/bin/python" -c "import supabase, icloudpd" 2>/dev/null; then
    success "Key Python packages (supabase, icloudpd) are working"
else
    warning "Some Python packages may be missing. Check the environment info file."
fi

# Test Node.js packages
if sudo -u "$SERVICE_USER" node -e "require('puppeteer')" 2>/dev/null; then
    success "Puppeteer is working"
else
    warning "Puppeteer may not be properly installed. Check the environment info file."
fi

echo ""
echo "=========================================="
echo "Unified Environment Setup Complete!"
echo "=========================================="
echo "Python Environment: $DEPLOY_DIR/venv"
echo "Node.js Environment: $DEPLOY_DIR/node_modules"
echo "Service User: $SERVICE_USER"
echo "Environment Info: $DEPLOY_DIR/environment_info.txt"
echo ""
echo "Next steps:"
echo "1. Configure your settings in $DEPLOY_DIR/config/settings.env"
echo "2. Test the upload script: node $DEPLOY_DIR/scripts/upload_icloud.js --help"
echo "3. Run with interactive login: node $DEPLOY_DIR/scripts/upload_icloud.js --dir /tmp/test_upload --interactive"
echo "=========================================="
