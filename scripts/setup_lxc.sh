#!/bin/bash
# LXC Container Setup Script for Media Pipeline
# Sets up Ubuntu LXC container with all required dependencies

set -e

echo "Setting up LXC container for media pipeline..."

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo "Installing required packages..."
apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    exiftool \
    rsync \
    parallel \
    pv \
    systemd \
    curl \
    wget \
    unzip \
    git

# Install Node.js 18+ using NodeSource repository
echo "Installing Node.js 18+..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Create dedicated user and group
echo "Creating media-pipeline user and group..."
groupadd -r media-pipeline || true
useradd -r -g media-pipeline -d /opt/media-pipeline -s /bin/bash media-pipeline || true

# Create directory structure
echo "Creating directory structure..."
mkdir -p /opt/media-pipeline/{originals,compressed,bridge,uploaded,logs,temp,cleanup}
mkdir -p /opt/media-pipeline/bridge/{icloud,pixel}
mkdir -p /opt/media-pipeline/uploaded/{icloud,pixel}
mkdir -p /opt/media-pipeline/sorted/{icloud,pixel}

# Setup mount points for NAS and Syncthing (will be configured via settings.env)
echo "Setting up mount points..."
# Note: Actual mount points will be created based on settings.env configuration
# This is just for initial setup - real paths are configured in settings.env

# Set proper ownership and permissions
echo "Setting permissions..."
chown -R media-pipeline:media-pipeline /opt/media-pipeline
chmod -R 755 /opt/media-pipeline

# Setup Python virtual environment
echo "Setting up Python virtual environment..."
sudo -u media-pipeline python3 -m venv /opt/media-pipeline/venv
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install --upgrade pip
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install \
    icloudpd \
    pillow \
    ffmpeg-python \
    python-dotenv \
    supabase \
    psutil

# Verify icloudpd installation
echo "Verifying icloudpd installation..."
if sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --version >/dev/null 2>&1; then
    echo "✓ icloudpd installed successfully"
else
    echo "⚠ icloudpd installation verification failed"
    echo "  This may be normal - icloudpd will be verified during pipeline execution"
fi

# Setup Node.js dependencies
echo "Setting up Node.js dependencies..."
cd /opt/media-pipeline
sudo -u media-pipeline npm init -y
sudo -u media-pipeline npm install puppeteer

# Create systemd service file
echo "Creating systemd service..."
cat > /etc/systemd/system/media-pipeline.service << EOF
[Unit]
Description=Media Pipeline Service
After=network.target

[Service]
Type=simple
User=media-pipeline
Group=media-pipeline
WorkingDirectory=/opt/media-pipeline
ExecStart=/opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
Restart=always
RestartSec=10
Environment=PATH=/opt/media-pipeline/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "Enabling systemd service..."
systemctl daemon-reload
systemctl enable media-pipeline

# Create log rotation configuration
echo "Setting up log rotation..."
cat > /etc/logrotate.d/media-pipeline << EOF
/opt/media-pipeline/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 media-pipeline media-pipeline
}
EOF

# Create cron job for regular execution
echo "Setting up cron job..."
cat > /etc/cron.d/media-pipeline << EOF
# Run media pipeline daily at 2 AM
0 2 * * * media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py >> /opt/media-pipeline/logs/cron.log 2>&1
EOF

# Set up log directory permissions
chown -R media-pipeline:media-pipeline /opt/media-pipeline/logs

# Copy pipeline files to the target directory
echo "Copying pipeline files..."
if [ -d "$(pwd)" ]; then
    cp -r "$(pwd)"/* /opt/media-pipeline/
    chown -R media-pipeline:media-pipeline /opt/media-pipeline
    echo "✓ Pipeline files copied successfully"
else
    echo "Warning: Could not determine source directory. Please copy files manually."
fi

echo "LXC container setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Update /opt/media-pipeline/config/settings.env with your configuration"
echo "2. Run the health check script: sudo ./scripts/check_and_fix.sh"
echo "3. Test the setup with: sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py"
echo "4. Start the service with: systemctl start media-pipeline"
echo ""
echo "Service management:"
echo "- Start: systemctl start media-pipeline"
echo "- Stop: systemctl stop media-pipeline"
echo "- Status: systemctl status media-pipeline"
echo "- Logs: journalctl -u media-pipeline -f"
