# Media Pipeline

## Setup
1. Run `./install.sh` to install dependencies.
2. Update `config/settings.env` with credentials and paths.

## Usage
Run scripts manually in order:
```
python scripts/download_from_icloud.py
python scripts/compress_media.py
python scripts/prepare_bridge_batch.py
python scripts/upload_to_icloud_via_ifuse.py
python scripts/sync_to_pixel.py
python scripts/verify_and_cleanup.py
```

## Notes
- iCloud 2FA: enter manually when prompted.
- Logs in `logs/`.
- Configurable batch size, file count, compression in `settings.env`.
