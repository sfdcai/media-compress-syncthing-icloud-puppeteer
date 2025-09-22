# Media Pipeline Setup Instructions

## Quick Setup (Recommended)

### 1. Initial Setup
```bash
# Clone the repository
git clone <your-repo-url> /opt/git/media-compress-syncthing-icloud-puppeteer
cd /opt/git/media-compress-syncthing-icloud-puppeteer

# Run the unified setup script
sudo ./scripts/setup_unified_environment.sh
```

### 2. Deploy to Production
```bash
# Deploy with force (preserves environments)
sudo ./deploy.sh --force
```

### 3. Configure Settings
```bash
# Edit your configuration
sudo nano /opt/media-pipeline/config/settings.env
```

### 4. Test the Setup
```bash
# Test Python environment
sudo -u media-pipeline /opt/media-pipeline/venv/bin/icloudpd --help

# Test Node.js environment
cd /opt/media-pipeline
sudo -u media-pipeline node scripts/upload_icloud.js --help
```

## Environment Locations

All environments are now consistently located under `/opt/media-pipeline/`:

- **Python Virtual Environment**: `/opt/media-pipeline/venv/`
- **Node.js Dependencies**: `/opt/media-pipeline/node_modules/`
- **Configuration**: `/opt/media-pipeline/config/`
- **Scripts**: `/opt/media-pipeline/scripts/`
- **Logs**: `/opt/media-pipeline/logs/`

## Troubleshooting

### If Python Environment Issues Occur
```bash
# Quick fix - Run the automated fix script
sudo ./scripts/setup_unified_environment.sh

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

### If Node.js Environment Issues Occur
```bash
# Reinstall Node.js dependencies
cd /opt/media-pipeline
sudo -u media-pipeline npm install --production

# Test Node.js environment
sudo -u media-pipeline node --version
sudo -u media-pipeline npm --version
```

### If Upload Script Issues Occur
```bash
# Clear cookies and force fresh login
cd /opt/media-pipeline
sudo -u media-pipeline node scripts/clear_cookies_and_login.js

# Run with interactive login
sudo -u media-pipeline node scripts/upload_icloud.js --dir /tmp/test_upload --interactive
```

## Deployment Process

The deployment script now preserves all environments and configurations:

- ✅ **Preserves**: `venv/`, `node_modules/`, `config/settings.env`, `cookies.json`
- ✅ **Updates**: Scripts, configuration files, dependencies
- ✅ **Tests**: Both Python and Node.js environments after deployment

## Service User

All operations run as the `media-pipeline` user for security:

```bash
# Switch to service user for testing
sudo -u media-pipeline bash

# Run commands as service user
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python script.py
sudo -u media-pipeline node /opt/media-pipeline/scripts/script.js
```

## Environment Information

After setup, check the environment info:
```bash
cat /opt/media-pipeline/environment_info.txt
```

This file contains:
- Setup date and time
- Python and Node.js versions
- Installed packages
- Environment paths
- Service user information

## Common Commands

```bash
# Deploy updates
sudo ./deploy.sh --force

# Deploy without backup
sudo ./deploy.sh --force --no-backup

# Test Python environment
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python -c "import supabase, icloudpd; print('OK')"

# Test Node.js environment
sudo -u media-pipeline node -e "require('puppeteer'); console.log('OK')"

# Run upload script
sudo -u media-pipeline node /opt/media-pipeline/scripts/upload_icloud.js --dir /tmp/test_upload --interactive

# Debug upload issues
sudo -u media-pipeline node /opt/media-pipeline/scripts/debug_icloud_headless.js
```

## File Permissions

All files are owned by `media-pipeline:media-pipeline` with appropriate permissions:
- Scripts: `755` (executable)
- Config: `644` (readable)
- Logs: `755` (writable)
- Environments: `755` (accessible)
