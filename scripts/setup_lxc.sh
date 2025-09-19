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
    nodejs \
    npm \
    ffmpeg \
    exiftool \
    rsync \
    md5sum \
    parallel \
    pv \
    systemd \
    curl \
    wget \
    unzip \
    git

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

# Setup mount points for NAS and Syncthing
echo "Setting up mount points..."
mkdir -p /mnt/nas/photos
mkdir -p /mnt/syncthing/pixel

# Set proper ownership and permissions
echo "Setting permissions..."
chown -R media-pipeline:media-pipeline /opt/media-pipeline
chown -R media-pipeline:media-pipeline /mnt/nas
chown -R media-pipeline:media-pipeline /mnt/syncthing
chmod -R 755 /opt/media-pipeline
chmod -R 755 /mnt/nas
chmod -R 755 /mnt/syncthing

# Setup Python virtual environment
echo "Setting up Python virtual environment..."
sudo -u media-pipeline python3 -m venv /opt/media-pipeline/venv
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install \
    icloudpd \
    pillow \
    ffmpeg-python \
    python-dotenv \
    supabase \
    psutil

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

echo "LXC container setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy your media pipeline files to /opt/media-pipeline/"
echo "2. Update /opt/media-pipeline/config/settings.env with your configuration"
echo "3. Test the setup with: sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py"
echo "4. Start the service with: systemctl start media-pipeline"
echo ""
echo "Service management:"
echo "- Start: systemctl start media-pipeline"
echo "- Stop: systemctl stop media-pipeline"
echo "- Status: systemctl status media-pipeline"
echo "- Logs: journalctl -u media-pipeline -f"
