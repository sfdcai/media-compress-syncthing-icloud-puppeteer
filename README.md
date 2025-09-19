# Media Pipeline

A comprehensive media compression and syncing pipeline for iCloud and Google Photos, designed to run in Ubuntu LXC containers on Proxmox.

## Features

- **Automated Download**: Downloads media from iCloud using icloudpd
- **Smart Deduplication**: Removes duplicate files using MD5 hashing
- **Progressive Compression**: Compresses media with age-based recompression
- **Dual Upload**: Syncs to both iCloud Photos and Google Photos (via Syncthing)
- **Post-Upload Organization**: Sorts files into yyyy/mm/dd structure
- **Database Tracking**: Comprehensive logging and tracking via Supabase
- **Feature Toggles**: Enable/disable individual components
- **LXC Ready**: Optimized for Ubuntu LXC containers on Proxmox

## Architecture

```
1. Download originals from iCloud → originals/
2. Deduplicate files → Remove duplicates, track in database
3. Compress media → compressed/ (with progressive compression)
4. Prepare batches → bridge/icloud/ & bridge/pixel/
5. Upload:
   - iCloud: Puppeteer automation → uploaded/icloud/
   - Pixel: Syncthing sync → uploaded/pixel/
6. Sort uploaded files → sorted/yyyy/mm/dd/
7. Verify & cleanup → Remove processed batches
```
start with 
bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"

## Quick Start

### 1. LXC Container Setup
```bash
# Run the LXC setup script
chmod +x scripts/setup_lxc.sh
sudo ./scripts/setup_lxc.sh
```

### 2. Configuration
Edit `config/settings.env` with your credentials and settings:

```env
# Feature Toggles
ENABLE_ICLOUD_UPLOAD=true
ENABLE_PIXEL_UPLOAD=true
ENABLE_COMPRESSION=true
ENABLE_DEDUPLICATION=true
ENABLE_SORTING=true

# iCloud Credentials
ICLOUD_USERNAME=your@email.com
ICLOUD_PASSWORD=your-app-password

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# Storage Paths
NAS_MOUNT=/mnt/nas/photos
PIXEL_SYNC_FOLDER=/mnt/syncthing/pixel
```

### 3. Run Pipeline
```bash
# Manual execution
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py

# Or start the systemd service
sudo systemctl start media-pipeline
```

## Configuration Options

### Feature Toggles
- `ENABLE_ICLOUD_UPLOAD`: Enable/disable iCloud uploads
- `ENABLE_PIXEL_UPLOAD`: Enable/disable Pixel/Syncthing uploads
- `ENABLE_COMPRESSION`: Enable/disable media compression
- `ENABLE_DEDUPLICATION`: Enable/disable duplicate removal
- `ENABLE_SORTING`: Enable/disable post-upload sorting

### Compression Settings
- `JPEG_QUALITY`: Image compression quality (default: 85)
- `VIDEO_CRF`: Video compression quality (default: 28)
- `COMPRESSION_INTERVAL_YEARS`: Recompression interval (default: 2)

### Batch Settings
- `MAX_BATCH_SIZE_GB`: Maximum batch size in GB (default: 5)
- `MAX_BATCH_FILES`: Maximum files per batch (default: 500)

## Directory Structure

```
/media-pipeline/
├── originals/           # Raw downloads from iCloud
├── compressed/          # Compressed media files
├── bridge/
│   ├── icloud/         # Batches for iCloud upload
│   └── pixel/          # Batches for Pixel/Syncthing
├── uploaded/           # Successfully uploaded files
│   ├── icloud/
│   └── pixel/
├── sorted/             # Organized by date
│   ├── icloud/
│   └── pixel/
├── logs/               # Pipeline logs
├── temp/               # Temporary files
└── cleanup/            # Processed batches
```

## Service Management

```bash
# Start service
sudo systemctl start media-pipeline

# Stop service
sudo systemctl stop media-pipeline

# Check status
sudo systemctl status media-pipeline

# View logs
sudo journalctl -u media-pipeline -f

# Enable auto-start
sudo systemctl enable media-pipeline
```

## Monitoring

- **Logs**: Check `logs/pipeline.log` for detailed execution logs
- **Database**: Monitor progress via Supabase dashboard
- **Reports**: Generated in `logs/` directory after each run

## Troubleshooting & Debugging

### 🔧 Health Check & Auto-Fix Tool

Use the comprehensive health check script to diagnose and fix issues automatically:

```bash
# Run the health check and fix tool
sudo ./scripts/check_and_fix.sh
```

This tool will:
- ✅ Check all system packages and dependencies
- ✅ Verify Node.js and Python environments
- ✅ Check file permissions and ownership
- ✅ Monitor service status and restart counts
- ✅ Detect and fix Syncthing configuration issues
- ✅ Provide system recommendations
- ✅ Show access URLs and service management commands

### 🚨 Common Issues & Solutions

#### 1. **Service Failing with Permission Errors**
**Symptoms**: Service restarts continuously, permission denied errors
```bash
# Check service status and restart count
systemctl status media-pipeline

# Stop the failing service
systemctl stop media-pipeline
systemctl disable media-pipeline

# Fix permissions
sudo chown -R media-pipeline:media-pipeline /opt/media-pipeline
sudo chmod -R 755 /opt/media-pipeline

# Check logs directory specifically
sudo chown -R media-pipeline:media-pipeline /opt/media-pipeline/logs
sudo chmod 644 /opt/media-pipeline/logs/pipeline.log
```

#### 2. **Syncthing Web Interface Not Accessible**
**Symptoms**: Can't access http://IP:8384
```bash
# Check Syncthing service
systemctl status syncthing@root

# Check if GUI is bound to localhost only
grep -o 'address="[^"]*"' /root/.local/state/syncthing/config.xml

# Fix GUI binding (if bound to 127.0.0.1)
sed -i 's/address="127.0.0.1:8384"/address="0.0.0.0:8384"/g' /root/.local/state/syncthing/config.xml
systemctl restart syncthing@root
```

#### 3. **Node.js/Puppeteer Issues**
**Symptoms**: EBADENGINE warnings, syntax errors
```bash
# Check Node.js version
node --version  # Should be 18+

# If version is too old, upgrade
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt install -y nodejs

# Reinstall Puppeteer
cd /opt/media-pipeline
sudo -u media-pipeline npm install puppeteer
```

#### 4. **Python Package Issues**
**Symptoms**: Import errors, missing modules
```bash
# Check virtual environment
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip list

# Reinstall packages
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install -r /opt/media-pipeline/requirements.txt
```

#### 5. **Mount Point Issues**
**Symptoms**: NAS/Syncthing folders not accessible
```bash
# Check mount status
mountpoint /mnt/nas
mountpoint /mnt/syncthing

# Check permissions
ls -la /mnt/nas
ls -la /mnt/syncthing

# Fix permissions if needed
sudo chown -R media-pipeline:media-pipeline /mnt/nas
sudo chown -R media-pipeline:media-pipeline /mnt/syncthing
```

### 📊 Service Monitoring

#### Check Service Health
```bash
# Service status
systemctl status media-pipeline

# Check restart count (high numbers indicate problems)
systemctl show media-pipeline --property=RestartCount

# Real-time logs
journalctl -u media-pipeline -f

# Recent logs
journalctl -u media-pipeline --since "1 hour ago" -n 50
```

#### Check Pipeline Execution
```bash
# View latest pipeline report
ls -la /opt/media-pipeline/logs/pipeline_report_*.txt | tail -1
cat /opt/media-pipeline/logs/pipeline_report_*.txt | tail -1

# Check pipeline log
tail -f /opt/media-pipeline/logs/pipeline.log

# Check file activity
ls -la /opt/media-pipeline/originals/
ls -la /opt/media-pipeline/compressed/
ls -la /opt/media-pipeline/bridge/
```

### 🔍 Debug Mode

#### Enable Detailed Logging
```bash
# Edit configuration
nano /opt/media-pipeline/config/settings.env

# Add debug settings
LOG_LEVEL=DEBUG
VERBOSE_LOGGING=true
```

#### Manual Pipeline Testing
```bash
# Test individual components
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/upload_icloud.py

# Test full pipeline
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```

### 🛠️ Service Management

#### Manual vs Service Mode

**Service Mode (Automated)**:
```bash
# Enable service
systemctl enable media-pipeline
systemctl start media-pipeline

# Check status
systemctl status media-pipeline
```

**Manual Mode (Step-by-step)**:
```bash
# Disable service
systemctl stop media-pipeline
systemctl disable media-pipeline

# Run manually
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```

#### Scheduled Execution
```bash
# Check cron job
cat /etc/cron.d/media-pipeline

# View cron logs
tail -f /opt/media-pipeline/logs/cron.log

# Manual cron execution
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```

### 🔐 Security & Permissions

#### Fix Permission Issues
```bash
# Fix all permissions
sudo chown -R media-pipeline:media-pipeline /opt/media-pipeline
sudo chmod -R 755 /opt/media-pipeline
sudo chmod 644 /opt/media-pipeline/logs/*.log

# Fix mount permissions
sudo chown -R media-pipeline:media-pipeline /mnt/nas
sudo chown -R media-pipeline:media-pipeline /mnt/syncthing
```

#### SSH Access
```bash
# Check SSH service
systemctl status ssh

# Start SSH if needed
systemctl start ssh
systemctl enable ssh

# Access from external
ssh root@YOUR_IP_ADDRESS
```

### 📈 Performance Monitoring

#### System Resources
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU load
htop

# Check network ports
netstat -tulpn | grep -E "8384|22000|22"
```

#### Pipeline Performance
```bash
# Check processing times in logs
grep "completed" /opt/media-pipeline/logs/pipeline.log

# Check file counts
find /opt/media-pipeline/originals -type f | wc -l
find /opt/media-pipeline/compressed -type f | wc -l
```

### 🆘 Emergency Recovery

#### Stop All Services
```bash
# Stop pipeline service
systemctl stop media-pipeline
systemctl disable media-pipeline

# Stop Syncthing
systemctl stop syncthing@root
```

#### Reset Configuration
```bash
# Backup current config
cp /opt/media-pipeline/config/settings.env /opt/media-pipeline/config/settings.env.backup

# Restore from template
cp /opt/media-pipeline/config/settings.env.example /opt/media-pipeline/config/settings.env
```

#### Clean Restart
```bash
# Run health check and fix
sudo ./scripts/check_and_fix.sh

# Restart services
systemctl restart syncthing@root
systemctl start media-pipeline
```

## Advanced Configuration

### Custom Compression
Modify compression settings in `config/settings.env`:
- `INITIAL_RESIZE_PERCENTAGE`: First compression level
- `SUBSEQUENT_RESIZE_PERCENTAGE`: Recompression level
- `INITIAL_VIDEO_RESOLUTION`: First video compression resolution
- `SUBSEQUENT_VIDEO_RESOLUTION`: Recompression video resolution

### Batch Optimization
Adjust batch settings based on your network and storage:
- `MAX_BATCH_SIZE_GB`: Larger batches for faster networks
- `MAX_BATCH_FILES`: More files per batch for efficiency

## Security

- Runs as dedicated `media-pipeline` user
- Proper file permissions and ownership
- Secure credential storage in environment variables
- LXC container isolation

## 🆕 Latest Updates & Improvements

### Version 2.0 - Enhanced Monitoring & Auto-Fix

#### New Features:
- ✅ **Comprehensive Health Check Tool** (`scripts/check_and_fix.sh`)
  - Automatic detection and fixing of common issues
  - Service restart count monitoring
  - Permission and ownership verification
  - Syncthing configuration auto-fix
  - System resource monitoring
  - Interactive fix prompts

- ✅ **Enhanced Service Management**
  - Automatic service failure detection
  - Log file permission fixes
  - Service restart prevention for failing services
  - Better error reporting and diagnostics

- ✅ **Improved Syncthing Integration**
  - Automatic GUI binding configuration
  - Support for multiple config file locations
  - Web interface accessibility fixes
  - Service status monitoring

- ✅ **Better Package Management**
  - Fixed Node.js 18+ installation
  - Corrected package detection logic
  - Resolved npm dependency conflicts
  - Improved exiftool detection

#### Bug Fixes:
- 🔧 Fixed service permission errors causing continuous restarts
- 🔧 Resolved Syncthing web interface accessibility issues
- 🔧 Fixed Python package detection false positives
- 🔧 Corrected systemd service configuration
- 🔧 Improved error handling and logging

#### Documentation:
- 📚 Comprehensive troubleshooting guide
- 📚 Service monitoring and debugging instructions
- 📚 Manual vs automated execution guides
- 📚 Performance monitoring tools
- 📚 Emergency recovery procedures

### Installation Improvements:
- 🚀 **One-Command Setup**: `bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"`
- 🚀 **Automatic File Copying**: No more manual file copying steps
- 🚀 **Health Check Integration**: Built-in system verification
- 🚀 **Service Auto-Configuration**: Automatic systemd service setup

### System Requirements:
- **Ubuntu 22.04+** (LTS recommended)
- **Node.js 18+** (automatically installed)
- **Python 3.10+** (included in Ubuntu 22.04)
- **4GB+ RAM** (recommended for media processing)
- **50GB+ Storage** (for media files and processing)

### Performance Optimizations:
- ⚡ **Parallel Processing**: Multi-threaded media compression
- ⚡ **Smart Batching**: Optimized file grouping for uploads
- ⚡ **Progressive Compression**: Age-based recompression strategy
- ⚡ **Resource Monitoring**: Automatic system health checks

### Security Enhancements:
- 🔒 **Dedicated User**: Runs as `media-pipeline` user
- 🔒 **Proper Permissions**: Automatic permission management
- 🔒 **Secure Configuration**: Environment-based credential storage
- 🔒 **LXC Isolation**: Container-based security

## 📞 Support & Community

### Getting Help:
1. **Run Health Check**: `sudo ./scripts/check_and_fix.sh`
2. **Check Documentation**: Review troubleshooting section above
3. **View Logs**: `journalctl -u media-pipeline -f`
4. **Manual Testing**: Run individual pipeline components

### Reporting Issues:
- Include output from health check script
- Provide system logs and error messages
- Specify your system configuration
- Include steps to reproduce the issue

## License

MIT License - see LICENSE file for details.
