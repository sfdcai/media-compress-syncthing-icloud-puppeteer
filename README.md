# Media Pipeline - iCloud to Google Photos Automation

A comprehensive media compression and syncing pipeline for iCloud and Google Photos, designed to run in Ubuntu LXC containers on Proxmox. This system automatically downloads media from iCloud, compresses it, and uploads it to both iCloud Photos and Google Photos (via Syncthing) with intelligent deduplication and organization.

## Features

- **Automated Download**: Downloads media from iCloud using icloudpd with database tracking
- **Smart Deduplication**: Removes duplicate files using MD5 hashing
- **Progressive Compression**: Compresses media with age-based recompression
- **Dual Upload**: Syncs to both iCloud Photos and Google Photos (via Syncthing)
- **Post-Upload Organization**: Sorts files into yyyy/mm/dd structure
- **Database Tracking**: Comprehensive logging and tracking via Supabase
- **Feature Toggles**: Enable/disable individual components
- **LXC Ready**: Optimized for Ubuntu LXC containers on Proxmox
- **Environment Management**: Stable Python environment with backup/restore
- **Sync Monitoring**: Real-time Syncthing sync status monitoring
- **Batch Processing**: Configurable batch sizes for optimal performance
- **Error Recovery**: Comprehensive error handling and recovery mechanisms

## Architecture

```
1. Download originals from iCloud → originals/
2. Deduplicate files → Remove duplicates, track in database
3. Compress media → compressed/ (with progressive compression)
4. Prepare files → bridge/icloud/ & bridge/pixel/ (direct files, no numbered batches)
5. Upload:
   - iCloud: Puppeteer automation → processes all files in bridge/icloud/
   - Pixel: Syncthing sync → syncs all files from bridge/pixel/
6. Sort uploaded files → sorted/yyyy/mm/dd/
7. Verify & cleanup → Remove processed files
```
## 🎯 **Production Status: READY**

**✅ All core components are working and production-ready!**

### **Latest Updates (December 2024)**
- ✅ Enhanced iCloud download with database tracking
- ✅ Complete Pixel sync workflow with Syncthing monitoring
- ✅ Robust environment management system
- ✅ Comprehensive error handling and recovery
- ✅ Real-time sync status monitoring
- ✅ Configurable batch processing
- ✅ **NEW**: Fixed Puppeteer API compatibility (waitForTimeout → setTimeout)
- ✅ **NEW**: External selector configuration for iCloud Photos
- ✅ **NEW**: Manual selector testing script for easy updates
- ✅ **NEW**: Chrome dependencies included in installation
- ✅ **NEW**: Improved error handling and troubleshooting
- ✅ Database backfill utilities

### **Quick Start Command**
```bash
bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"
```

## 🚀 Quick Start

### **Complete Installation Process**

#### **Step 1: Initial Setup**
```bash
# Quick setup (recommended)
bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"

# Or manual setup
git clone https://github.com/sfdcai/media-compress-syncthing-icloud-puppeteer.git
cd media-compress-syncthing-icloud-puppeteer

# Make scripts executable
chmod +x scripts/setup_lxc.sh install.sh manage_config.sh cleanup_and_setup.sh

# Run the comprehensive installation
sudo ./install.sh
```

#### **Step 2: Configuration Management**
```bash
# Setup configuration management (moves config outside project)
./manage_config.sh setup

# Edit your configuration
./manage_config.sh edit
```

#### **Step 3: Health Check & Setup**
```bash
# Run comprehensive health check and auto-fix
sudo ./scripts/check_and_fix.sh

# This will:
# - Check all system packages
# - Verify Node.js and Python environments
# - Create NAS directory structure
# - Fix permissions and services
# - Configure Syncthing
# - Test pipeline components
```

#### **Step 4: Start Services**
```bash
# Start the media pipeline service
systemctl start media-pipeline

# Start Syncthing (if not already running)
systemctl start syncthing@root

# Check service status
systemctl status media-pipeline
systemctl status syncthing@root
```

### **Manual Step-by-Step Testing (Recommended for First-Time Setup)**

For complete control and testing of each component:

#### **Phase 1: System Setup**
```bash
# 1. Setup LXC container and dependencies
sudo ./scripts/setup_lxc.sh

# 2. Setup NAS directory structure
sudo ./setup_nas_structure.sh

# 3. Run comprehensive health check
sudo ./scripts/check_and_fix.sh

# 4. Setup configuration management
./manage_config.sh setup

# 5. Edit your configuration
./manage_config.sh edit
```

#### **Phase 2: Manual Pipeline Testing**
```bash
# 6. Test iCloud download
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py

# 7. Test media compression
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py

# 8. Test deduplication
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/deduplicate.py

# 9. Test bridge preparation (iCloud)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py

# 10. Test iCloud upload
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/upload_icloud.py

# 11. Test Pixel sync preparation
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py

# 12. Test Pixel sync
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sync_to_pixel.py

# 13. Test file sorting
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sort_uploaded.py

# 14. Test cleanup
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/verify_and_cleanup.py
```

#### **Phase 3: Full Pipeline Test**
```bash
# 15. Test complete pipeline (all steps in sequence)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```

#### **Phase 4: Service Setup (Only After Manual Testing Passes)**
```bash
# 16. Start Syncthing service
systemctl start syncthing@root
systemctl enable syncthing@root

# 17. Start media pipeline service (automated)
systemctl start media-pipeline
systemctl enable media-pipeline

# 18. Check service status
systemctl status media-pipeline
systemctl status syncthing@root
```

### **Manual Testing Benefits:**
- ✅ **Complete Control** - Test each component individually
- ✅ **Issue Isolation** - Identify problems at specific steps
- ✅ **Learning** - Understand how each component works
- ✅ **Debugging** - Easy to troubleshoot specific issues
- ✅ **Confidence** - Verify everything works before automation

### **Manual Testing Guide - What Each Command Does:**

#### **Phase 1: System Setup Commands**

**Command 1: `sudo ./scripts/setup_lxc.sh`**
- **What it does**: Installs all system packages, Node.js, Python dependencies, creates user/group
- **Success check**: No error messages, all packages installed
- **Logs**: Check terminal output for "LXC container setup completed successfully!"

**Command 2: `sudo ./setup_nas_structure.sh`**
- **What it does**: Creates directory structure on your NAS mount
- **Success check**: Directories created in `/mnt/wd_all_pictures/sync/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/`

**Command 3: `sudo ./scripts/check_and_fix.sh`**
- **What it does**: Comprehensive health check of all components
- **Success check**: All checks pass (green ✓ marks)
- **Fix issues**: Script will offer to fix any problems found

**Command 4: `./manage_config.sh setup`**
- **What it does**: Moves config outside project, creates symlink
- **Success check**: "Configuration setup completed"
- **Verify**: `./manage_config.sh status`

**Command 5: `./manage_config.sh edit`**
- **What it does**: Opens your configuration file for editing
- **Success check**: File opens in editor, save and exit
- **Verify**: Check your iCloud credentials and paths are correct

**Command 5.5: `sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase.py`**
- **What it does**: Tests Supabase connection, table structure, and database operations
- **Success check**: All tests pass (Connection, Tables, Operations, Permissions, Pooling)
- **Verify**: Check that all required tables exist and CRUD operations work

#### **Phase 2: Manual Pipeline Testing Commands**

**Command 6: iCloud Download Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py
```
- **What it does**: Downloads photos/videos from iCloud to `originals/`
- **Success check**: Files appear in `/mnt/wd_all_pictures/sync/originals/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/originals/`

**Command 7: Media Compression Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py
```
- **What it does**: Compresses media files, saves to `compressed/`
- **Success check**: Compressed files in `/mnt/wd_all_pictures/sync/compressed/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/compressed/`

**Command 8: Deduplication Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/deduplicate.py
```
- **What it does**: Removes duplicate files, logs to database
- **Success check**: Duplicates removed, database updated
- **Verify**: Check logs for "duplicates removed" messages

**Command 9: Bridge Preparation Test (iCloud)**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py
```
- **What it does**: Prepares compressed video files for iCloud upload in `bridge/icloud/`
- **Success check**: Only video files (e.g. `.mp4`, `.mov`) copied to `/mnt/wd_all_pictures/sync/bridge/icloud/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/bridge/icloud/`

**Command 10: iCloud Upload Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/upload_icloud.py
```
- **What it does**: Uploads compressed video files to iCloud Photos using Puppeteer
- **Success check**: Files uploaded, moved to `uploaded/icloud/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/uploaded/icloud/`

> 💡 **Selector diagnostics**: Set `ICLOUD_INTERACTIVE=true ICLOUD_INSPECT_UPLOAD=true` when running the command above to launch a visible browser, print all detected upload controls, and pause so you can inspect the UI manually before attempting an upload.

**Command 11: Bridge Preparation Test (Pixel)**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py
```
- **What it does**: Prepares files for Pixel sync in `bridge/pixel/`
- **Success check**: Files copied to `/mnt/wd_all_pictures/sync/bridge/pixel/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/bridge/pixel/`

**Command 12: Pixel Sync Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sync_to_pixel.py
```
- **What it does**: Syncs files to Pixel via Syncthing
- **Success check**: Files synced, moved to `uploaded/pixel/`
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/uploaded/pixel/`

**Command 13: File Sorting Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sort_uploaded.py
```
- **What it does**: Organizes uploaded files by date in `sorted/`
- **Success check**: Files organized in date folders
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/sorted/`

**Command 14: Cleanup Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/verify_and_cleanup.py
```
- **What it does**: Verifies uploads and cleans up processed files
- **Success check**: Files moved to `cleanup/`, originals removed
- **Verify**: `ls -la /mnt/wd_all_pictures/sync/cleanup/`

#### **Phase 3: Full Pipeline Test**

**Command 15: Complete Pipeline Test**
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```
- **What it does**: Runs all steps in sequence (download → compress → dedupe → upload → sort → cleanup)
- **Success check**: All phases complete successfully
- **Verify**: Check logs and final directory structure

#### **Phase 4: Service Setup (Only After Manual Testing)**

**Commands 16-18: Service Setup**
- **What they do**: Start automated services for continuous operation
- **Success check**: Services running without errors
- **Verify**: `systemctl status media-pipeline` and `systemctl status syncthing@root`

### **Quick Reference: Manual Testing Commands**

For easy copy-paste access to all manual testing commands:

```bash
# Display all manual testing commands
chmod +x manual_test_commands.sh
./manual_test_commands.sh
```

This script will display all 18 manual testing commands with explanations, making it easy to copy and paste each command for individual testing.

### **Testing Workflow:**

1. **Run each command individually** - Don't skip steps
2. **Verify success** - Check the "Success check" criteria for each command
3. **Fix issues** - If a command fails, troubleshoot before proceeding
4. **Only start services** - After ALL manual tests pass successfully
5. **Monitor services** - Watch logs after starting automated services

### **Supabase Database Testing:**

The `test_supabase.py` script performs comprehensive testing of your Supabase setup:

#### **What it tests:**
1. **Connection Test** - Verifies Supabase URL and API key
2. **Table Structure Test** - Checks if all required tables exist with correct columns
3. **Database Operations Test** - Tests INSERT, SELECT, UPDATE, DELETE operations
4. **Permissions Test** - Verifies Row Level Security (RLS) and access rights
5. **Connection Pooling Test** - Tests multiple rapid connections

#### **Required Tables:**
- `media_files` - Stores file metadata, hashes, and processing status
- `batches` - Tracks batch processing operations (icloud/pixel uploads)
- `duplicate_files` - Tracks duplicate file relationships
- `pipeline_logs` - Records pipeline step execution and status

### **Production Scripts Usage:**

#### **Individual Operations:**
```bash
# Download from iCloud (with database tracking)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py

# Prepare files for Pixel sync
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_pixel_sync.py

# Monitor Syncthing sync status
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/monitor_syncthing_sync.py

# Complete Pixel sync workflow
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pixel_sync.py

# Run complete pipeline
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```

#### **Environment Management:**
```bash
# Create stable environment
sudo ./scripts/create_stable_environment.sh

# Backup environment
sudo ./scripts/backup_environment.sh backup

# Quick environment fix
sudo ./scripts/quick_env_fix.sh
```

#### **Testing & Debugging:**
```bash
# Test Supabase connection
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/test_supabase.py

# Test iCloud credentials
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/test_icloud_credentials.py

# Backfill database with existing files
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/backfill_database.py
```

#### **Running the test:**
```bash
# Test Supabase setup (using virtual environment)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase.py

# Or quick test
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase_simple.py

# Expected output: All 5 tests should pass
# ✓ Connection: PASS
# ✓ Table Structure: PASS  
# ✓ Database Operations: PASS
# ✓ Permissions: PASS
# ✓ Connection Pooling: PASS
```

#### **If tests fail:**
- **Connection fails** → Check `SUPABASE_URL` and `SUPABASE_KEY` in `settings.env`
- **Tables missing** → Run the `supabase/schema.sql` script in your Supabase dashboard
- **Permission errors** → Check RLS policies in Supabase dashboard
- **API key issues** → Verify the key has correct permissions

### **Common Issues During Manual Testing:**

- **iCloud authentication fails** → Check app-specific password in `settings.env`
- **Supabase connection fails** → Run `python3 test_supabase.py` to diagnose
- **Permission errors** → Run `sudo ./scripts/check_and_fix.sh --fix-permissions`
- **Missing directories** → Run `sudo ./setup_nas_structure.sh`
- **Syncthing not accessible** → Check firewall and web interface access
- **Python/Node.js errors** → Run `sudo ./scripts/check_and_fix.sh`

### **Configuration**
**IMPORTANT**: All directory paths are configured via environment variables in `config/settings.env`. No hardcoded paths are used in the scripts.

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
NAS_MOUNT=/mnt/wd_all_pictures/sync
ORIGINALS_DIR=/mnt/wd_all_pictures/sync/originals
COMPRESSED_DIR=/mnt/wd_all_pictures/sync/compressed
BRIDGE_ICLOUD_DIR=/mnt/wd_all_pictures/sync/bridge/icloud
BRIDGE_PIXEL_DIR=/mnt/wd_all_pictures/sync/bridge/pixel
PIXEL_SYNC_FOLDER=/mnt/syncthing/pixel
```

## Configuration Options

### Environment Variables
All scripts use environment variables from `config/settings.env` for configuration. This ensures:
- **No hardcoded paths** in any script
- **Flexible configuration** for different setups
- **Easy customization** without code changes
- **Consistent paths** across all components

### Directory Configuration
All directory paths are configurable via environment variables:

- `NAS_MOUNT`: Base directory for all media files
- `ORIGINALS_DIR`: Where iCloud downloads are stored
- `COMPRESSED_DIR`: Where compressed media is stored
- `BRIDGE_ICLOUD_DIR`: Files ready for iCloud upload
- `BRIDGE_PIXEL_DIR`: Files ready for Pixel sync
- `UPLOADED_ICLOUD_DIR`: Tracking uploaded iCloud files
- `UPLOADED_PIXEL_DIR`: Tracking uploaded Pixel files
- `SORTED_DIR`: Final organized storage
- `CLEANUP_DIR`: Files ready for cleanup
- `PIXEL_SYNC_FOLDER`: Where Syncthing syncs files to

### Feature Toggles
- `ENABLE_ICLOUD_UPLOAD`: Enable/disable iCloud uploads
- `ENABLE_PIXEL_UPLOAD`: Enable/disable Pixel/Syncthing uploads
- `ENABLE_COMPRESSION`: Enable/disable media compression
- `ENABLE_DEDUPLICATION`: Enable/disable duplicate removal
- `ENABLE_SORTING`: Enable/disable post-upload sorting

### Upload Diagnostics
- `ICLOUD_INSPECT_UPLOAD`: When `true`, the iCloud uploader opens a diagnostic session, prints detected upload controls, and skips queueing files so you can adjust selectors safely.

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

#### 5. **iCloud Authentication Issues**
**Symptoms**: EOFError, authentication failures, password prompts
```bash
# Check icloudpd installation
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --version

# Check iCloud credentials in config
grep -E "ICLOUD_USERNAME|ICLOUD_PASSWORD" /opt/media-pipeline/config/settings.env

# Test icloudpd manually (will prompt for password)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --username your@email.com --password your-app-password --directory /tmp/test --dry-run

# Fix: Ensure credentials are properly set
nano /opt/media-pipeline/config/settings.env
# Set ICLOUD_USERNAME=your@email.com
# Set ICLOUD_PASSWORD=your-app-specific-password
```

#### 6. **Pipeline Dependency Issues**
**Symptoms**: Import errors, missing modules, command not found
```bash
# Check all pipeline dependencies
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python -c "import icloudpd, PIL, ffmpeg, dotenv, supabase, psutil; print('All modules available')"

# Reinstall all dependencies
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install --upgrade pip
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install -r /opt/media-pipeline/requirements.txt

# Check Node.js dependencies
cd /opt/media-pipeline
sudo -u media-pipeline npm list puppeteer
```

#### 7. **Mount Point Issues**
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

### ☁️ iCloud Setup & Troubleshooting

#### iCloud App-Specific Password Setup
1. **Enable Two-Factor Authentication** on your Apple ID
2. **Generate App-Specific Password**:
   - Go to [appleid.apple.com](https://appleid.apple.com)
   - Sign in with your Apple ID
   - Go to "Security" section
   - Click "Generate Password" under "App-Specific Passwords"
   - Label it "Media Pipeline" or similar
   - Copy the generated password

#### Configure iCloud Credentials
```bash
# Edit configuration file
nano /opt/media-pipeline/config/settings.env

# Set your credentials
ICLOUD_USERNAME=your@email.com
ICLOUD_PASSWORD=your-app-specific-password
```

#### Test iCloud Connection
```bash
# Test icloudpd manually
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd \
    --username your@email.com \
    --password your-app-specific-password \
    --directory /tmp/test \
    --dry-run

# If successful, you should see authentication success message
```

#### Common iCloud Issues

**Issue**: `EOFError` or password prompts in service
**Solution**: Service can't prompt for password interactively
```bash
# Ensure credentials are in config file, not prompted
grep -E "ICLOUD_USERNAME|ICLOUD_PASSWORD" /opt/media-pipeline/config/settings.env

# Test with explicit credentials
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd \
    --username $(grep ICLOUD_USERNAME /opt/media-pipeline/config/settings.env | cut -d'=' -f2) \
    --password $(grep ICLOUD_PASSWORD /opt/media-pipeline/config/settings.env | cut -d'=' -f2) \
    --directory /tmp/test \
    --dry-run
```

**Issue**: Authentication failed
**Solution**: Check credentials and 2FA setup
```bash
# Verify credentials format
cat /opt/media-pipeline/config/settings.env | grep ICLOUD

# Test with verbose output
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd \
    --username your@email.com \
    --password your-app-specific-password \
    --directory /tmp/test \
    --dry-run \
    --verbose
```

**Issue**: Rate limiting or quota exceeded
**Solution**: Wait and retry, check iCloud storage
```bash
# Check iCloud storage usage
# Visit icloud.com and check storage

# Add delays between requests
# Edit config to add:
ICLOUD_DOWNLOAD_DELAY=5
ICLOUD_BATCH_SIZE=100
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

## 🚀 Enhanced Installation Options

### Option 1: One-Command Installation (Recommended)
```bash
# Download and run the enhanced installation script
bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"
```

### Option 2: Manual Installation
```bash
# Clone the repository
git clone https://github.com/sfdcai/media-compress-syncthing-icloud-puppeteer.git
cd media-compress-syncthing-icloud-puppeteer

# Run the enhanced installation script
sudo ./install.sh
```

### Option 3: LXC Container Setup
```bash
# For Proxmox LXC containers
sudo ./scripts/setup_lxc.sh
```

## 🔧 External Services Setup

### ☁️ Supabase Database Setup

1. **Create Supabase Project**:
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and API key

2. **Configure Database Schema**:
   ```bash
   # The schema is automatically created from supabase/schema.sql
   # Or manually run the SQL commands in your Supabase SQL editor
   ```

3. **Update Configuration**:
   ```bash
   nano /opt/media-pipeline/config/settings.env
   
   # Add your Supabase credentials:
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   ```

### 🍎 iCloud Setup

1. **Enable Two-Factor Authentication**:
   - Go to [appleid.apple.com](https://appleid.apple.com)
   - Sign in with your Apple ID
   - Enable Two-Factor Authentication

2. **Generate App-Specific Password**:
   - In Apple ID settings, go to "Security" section
   - Click "Generate Password" under "App-Specific Passwords"
   - Label it "Media Pipeline"
   - Copy the generated password

3. **Configure Credentials**:
   ```bash
   nano /opt/media-pipeline/config/settings.env
   
   # Set your iCloud credentials:
   ICLOUD_USERNAME=your@email.com
   ICLOUD_PASSWORD=your-app-specific-password
   ```

### 🔄 Syncthing Setup

1. **Access Web Interface**:
   - Open http://YOUR_IP:8384 in your browser
   - Set up a password for security

2. **Add Devices**:
   - Share your device ID with other devices
   - Accept device invitations
   - Configure folder sharing

3. **Configure Folders**:
   - Create a folder for media sync
   - Set the path to `/mnt/syncthing/pixel`
   - Configure sync settings

### 🔥 Firewall Configuration

The installation script automatically configures UFW firewall, but you can manually configure:

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow Syncthing ports
sudo ufw allow 8384/tcp comment "Syncthing Web UI"
sudo ufw allow 22000/tcp comment "Syncthing Sync"
sudo ufw allow 21027/udp comment "Syncthing Discovery"

# Check status
sudo ufw status
```

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

## 🚀 Latest Updates & Improvements

### Simplified Batch System (v2.1)
We've completely simplified the batch processing system for better efficiency and easier management:

#### **What Changed:**
- **❌ Removed**: Numbered batch folders (`batch_1/`, `batch_2/`, etc.)
- **✅ Added**: Direct file processing in bridge directories
- **🎯 Result**: Cleaner, more efficient workflow

#### **New Simplified Workflow:**
```
1. Download → originals/
2. Compression → compressed/
3. File Preparation → bridge/icloud/ & bridge/pixel/ (direct files)
4. Upload Processing:
   - iCloud: All files in bridge/icloud/ processed directly
   - Pixel: All files in bridge/pixel/ synced directly via Syncthing
5. Sorting → sorted/yyyy/mm/dd/
```

#### **Benefits:**
- **Simpler**: No more numbered batch folders to manage
- **Cleaner**: Direct file processing without unnecessary subfolders
- **More Efficient**: Syncthing syncs entire folder directly
- **Easier to Debug**: Clear file paths without batch numbers
- **Better for Syncthing**: One folder to sync instead of multiple numbered folders

#### **Updated Scripts:**
- `prepare_bridge_batch.py` → Now `prepare_files_for_type()` (no numbered batches)
- `sync_to_pixel.py` → Now `sync_files_to_pixel()` (direct folder sync)
- `upload_icloud.py` → Now `upload_files_to_icloud()` (direct file processing)
- `run_pipeline.py` → Updated phase names and function calls

#### **NAS Structure Check:**
- Added `check_nas_structure()` to `check_and_fix.sh`
- Automatically creates missing NAS directories
- Fixes ownership and permissions
- Integrated into comprehensive health check

### Enhanced Installation & Setup:
- **Comprehensive `install.sh`**: Complete system setup with error handling
- **Enhanced `check_and_fix.sh`**: Now includes NAS structure validation
- **Updated `setup_nas_structure.sh`**: Reflects simplified folder structure
- **Better Error Handling**: More robust installation and troubleshooting

## 🔧 Configuration Management

### Managing Your Configuration
The project includes tools to help you manage your configuration and keep it separate from the Git repository:

#### **Configuration Management Scripts:**
- **`manage_config.sh`** - Configuration management
- **`cleanup_and_setup.sh`** - One-time setup and cleanup

#### **Initial Setup:**
```bash
# Make scripts executable
chmod +x manage_config.sh cleanup_and_setup.sh

# Run the cleanup and setup script
./cleanup_and_setup.sh
```

#### **Managing Configuration:**
```bash
# Edit configuration
./manage_config.sh edit

# Check status
./manage_config.sh status

# Update from Git (preserves your config)
./manage_config.sh update
```

### **Configuration File Location:**
Your configuration is stored outside the project directory:
- **Ubuntu/LXC**: `~/.config/media-pipeline/settings.env`

**Note**: The project uses `config/settings.env` with dynamic directory paths. The configuration management scripts will move this file outside the project and create a symlink.

### **Benefits:**
- ✅ **No Git Conflicts**: Your config is never committed to Git
- ✅ **Easy Updates**: Pull latest changes without losing your settings
- ✅ **Backup Safe**: Configuration is preserved during updates
- ✅ **Ubuntu/LXC Optimized**: Designed specifically for Ubuntu LXC containers

## 🔧 Troubleshooting & Debugging

### **Quick Diagnostics**
```bash
# Run comprehensive health check
sudo ./scripts/check_and_fix.sh

# Check service status
systemctl status media-pipeline
systemctl status syncthing@root

# View recent logs
journalctl -u media-pipeline -f --lines=50
journalctl -u syncthing@root -f --lines=50

# Check configuration
./manage_config.sh status
```

### **Common Issues & Solutions**

#### **1. Permission Errors**
```bash
# Fix permissions for pipeline directory
sudo ./scripts/check_and_fix.sh --fix-permissions

# Or manually fix
sudo chown -R media-pipeline:media-pipeline /opt/media-pipeline
sudo chmod -R 755 /opt/media-pipeline
```

#### **2. Service Not Starting**
```bash
# Check service logs
journalctl -u media-pipeline -f

# Common causes:
# - Missing Python packages
# - Permission issues
# - Configuration errors
# - Missing directories

# Fix with health check
sudo ./scripts/check_and_fix.sh
```

#### **3. Syncthing Issues**
```bash
# Check Syncthing status
systemctl status syncthing@root

# Access web interface
# http://YOUR_IP:8384

# Fix Syncthing configuration
sudo ./scripts/check_and_fix.sh
```

#### **4. Configuration Problems**
```bash
# Verify configuration file
./manage_config.sh status

# Edit configuration
./manage_config.sh edit

# Check environment variables
grep -v "^#" config/settings.env
```

#### **5. Node.js/Puppeteer Issues**
```bash
# Check Node.js version
node --version

# Reinstall Puppeteer
cd /opt/media-pipeline
npm install puppeteer@latest
npm audit fix --force
```

#### **6. Python Environment Issues**
```bash
# Quick fix - Run the automated fix script
chmod +x fix_python_venv.sh
sudo ./fix_python_venv.sh

# Manual fix steps:
# Check virtual environment
ls -la /opt/media-pipeline/venv/

# Check if python3-venv is installed
dpkg -l | grep python3-venv

# Install python3-venv if missing
sudo apt install -y python3-venv

# Recreate virtual environment
sudo -u media-pipeline python3 -m venv /opt/media-pipeline/venv

# Upgrade pip in virtual environment
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install --upgrade pip

# Install requirements
sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install -r /opt/media-pipeline/requirements.txt

# Test icloudpd in virtual environment
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --help
```

#### **7. iCloud Authentication Issues**
```bash
# Check iCloud credentials
grep "ICLOUD_" /opt/media-pipeline/config/settings.env

# Test icloudpd manually (using virtual environment)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --help

# Test icloudpd with credentials
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --username your@email.com --password your-app-password --list-albums

# Common issues:
# - Wrong app-specific password
# - 2FA not properly configured
# - Account locked
# - icloudpd not installed in virtual environment
```

#### **8. Supabase Database Issues**
```bash
# Test Supabase connection and database
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase.py

# Quick test
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase_simple.py

# Check Supabase configuration
grep "SUPABASE_" config/settings.env

# Common issues:
# - Wrong SUPABASE_URL or SUPABASE_KEY
# - Missing database tables
# - RLS (Row Level Security) policies blocking access
# - API key permissions insufficient
# - Missing python-dotenv package
```

#### **9. Directory Structure Issues**
```bash
# Check NAS mount
mount | grep wd_all_pictures

# Verify directory structure
ls -la /mnt/wd_all_pictures/sync/

# Recreate directories
sudo ./setup_nas_structure.sh
```

### **Advanced Debugging**

#### **Manual Pipeline Testing**
```bash
# Test individual components
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py
```

#### **Log Analysis**
```bash
# Pipeline logs
tail -f /opt/media-pipeline/logs/pipeline.log

# System logs
journalctl -u media-pipeline --since "1 hour ago"

# Syncthing logs
journalctl -u syncthing@root --since "1 hour ago"
```

#### **Network Diagnostics**
```bash
# Check network connectivity
ping google.com
ping icloud.com

# Check firewall
ufw status
netstat -tlnp | grep :8384
```

### **Emergency Recovery**
```bash
# Complete system reset
sudo ./cleanup_and_setup.sh

# Reinstall from scratch
sudo ./install.sh

# Fix specific issues
sudo ./scripts/check_and_fix.sh --fix-permissions
```

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

## 🚨 **Known Limitations & Considerations**

### **iCloud Photos Upload Limitations**
- **Web Automation Dependency**: iCloud Photos upload relies on web automation (Puppeteer)
- **Session Management**: Web sessions may expire and require re-authentication
- **Upload Button Detection**: May need selector updates if iCloud changes their interface
- **Rate Limiting**: Apple may impose rate limits on uploads
- **2FA Requirements**: Requires two-factor authentication setup

### **Google Photos Integration Limitations**
- **Syncthing Dependency**: Google Photos integration requires Syncthing setup
- **P2P Sync**: Requires network connectivity between devices
- **Storage Management**: No automatic deletion from local storage after cloud upload
- **Album Organization**: Limited album organization capabilities

### **System Limitations**
- **Headless Operation**: Some features may not work in headless environments
- **Network Dependency**: Requires stable internet connectivity
- **Storage Requirements**: Significant local storage needed for processing
- **Processing Time**: Large media collections may take considerable time to process

### **Authentication Limitations**
- **iCloud App-Specific Passwords**: Requires Apple ID with 2FA and app-specific passwords
- **Session Expiration**: Both iCloud and Google Photos sessions may expire
- **Manual Intervention**: May require manual login for expired sessions

### **Data Management Limitations**
- **Duplicate Detection**: Based on file hashes, may not catch all duplicates
- **Metadata Preservation**: Some metadata may be lost during compression
- **File Format Support**: Limited to common image and video formats
- **Batch Processing**: Large batches may timeout or fail

## License

MIT License - see LICENSE file for details.
