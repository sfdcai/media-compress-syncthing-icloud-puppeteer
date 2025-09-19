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

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure media-pipeline user has proper permissions
2. **Mount Point Issues**: Verify NAS and Syncthing mounts are accessible
3. **Node.js Dependencies**: Run `npm install` in the project directory
4. **Python Dependencies**: Ensure virtual environment is activated

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in `config/settings.env`.

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

## License

MIT License - see LICENSE file for details.
