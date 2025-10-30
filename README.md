# Media Pipeline

A production-ready automation pipeline that downloads new media from iCloud, deduplicates and compresses it, then distributes the processed assets to iCloud Photos and Google Photos (via Syncthing/Pixel) with full auditing and recovery tooling.

## Highlights
- **End-to-end automation** – Orchestrated phases cover download, dedupe, compression, staging, upload, sorting, and verification.
- **Storage efficiency** – Age-aware compression, hash-based dedupe, and cleanup jobs keep NAS usage predictable.
- **Resilient bookkeeping** – Supabase is the source of truth while an embedded SQLite mirror maintains progress when offline.
- **Browser automation** – A hardened Puppeteer workflow uploads compressed videos to iCloud Photos with interactive diagnostics when required.
- **Syncthing integration** – Continuous monitoring detects stalled folders, reports remaining items, and verifies pixel sync completion.
- **Operational tooling** – Health checks, install scripts, environment backups, and manual command bundles make maintenance repeatable.
- **Multi-source intake** – Beyond icloudpd downloads, configurable NAS intake folders and Syncthing drops are swept into the same dedupe/compression pipeline.

## Architecture Overview
```
1. download_from_icloud.py         → originals/
2. deduplicate.py                  → logs hashes + local cache
3. compress_media.py               → compressed/
4. prepare_bridge_batch.py         → bridge/icloud & bridge/pixel
5. upload_icloud.py (Puppeteer)    → uploaded/icloud
6. sync_to_pixel.py (Syncthing)    → uploaded/pixel
7. sort_uploaded.py                → sorted/yyyy/mm/dd
8. verify_and_cleanup.py           → cleanup/, reports, notifications
```
Each script can run standalone for troubleshooting or be orchestrated by `run_pipeline.py`.

## System Requirements
- Ubuntu 22.04 LXC on Proxmox (tested) with root access
- 4 vCPU / 6 GB RAM recommended (Chromium uploads need extra headroom)
- Mounted NAS providing the directories referenced in `config/settings.env`
- Node.js ≥ 18, Python ≥ 3.11, ffmpeg, exiftool, rsync, syncthing, chromium dependencies

## Quick Start
```bash
bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"
cd media-compress-syncthing-icloud-puppeteer
sudo ./install.sh                     # provisions packages, Python venv, node modules
./manage_config.sh setup              # symlink config outside repo
./manage_config.sh edit               # populate settings.env (see below)
sudo ./scripts/check_and_fix.sh       # optional: health check + remediation
```

## Configuration (`config/settings.env`)
| Variable | Purpose |
| --- | --- |
| `ENABLE_ICLOUD_UPLOAD`, `ENABLE_PIXEL_UPLOAD`, `ENABLE_COMPRESSION`, `ENABLE_DEDUPLICATION`, `ENABLE_SORTING` | Feature toggles for pipeline phases |
| `ICLOUD_USERNAME`, `ICLOUD_PASSWORD` | App-specific credentials for icloudpd & Puppeteer auth |
| `SUPABASE_URL`, `SUPABASE_KEY` | Remote metadata store (hashes, batches, logs) |
| `NAS_MOUNT`, `ORIGINALS_DIR`, `COMPRESSED_DIR`, `BRIDGE_ICLOUD_DIR`, `BRIDGE_PIXEL_DIR`, `PIXEL_SYNC_FOLDER` | Directory layout for NAS/Syncthing |
| `DEDUPLICATION_DIRECTORIES` | Optional comma/newline separated list of extra folders to deduplicate alongside the defaults |
| `LOG_LEVEL`, `VERBOSE_LOGGING` | Increase log verbosity for debugging |
| `ICLOUD_INTERACTIVE`, `ICLOUD_INSPECT_UPLOAD` | Launches a visible browser and prints selectors before upload |
| `JPEG_QUALITY`, `VIDEO_CRF`, `COMPRESSION_INTERVAL_YEARS` | Compression policies |
| `MAX_BATCH_SIZE_GB`, `MAX_BATCH_FILES` | Bridge sizing for uploads |

> Run `./manage_config.sh status` at any time to confirm the active configuration path.

## Manual Validation Workflow
The repository ships with `manual_test_commands.sh`, but the commands below capture the recommended flow when verifying a new environment. Substitute paths if your NAS mount differs.

```bash
# 1. Download new items from iCloud
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py

# 2. Compress assets
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py

# 3. Remove duplicates (writes Supabase + local cache)
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/deduplicate.py

# 4. Stage compressed videos for upload/sync
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py

# 5. Upload to iCloud Photos (videos only)
ICLOUD_INTERACTIVE=true sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/upload_icloud.py

# 6. Initiate Pixel/Syncthing sync
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sync_to_pixel.py

# 7. Sort and archive
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sort_uploaded.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/verify_and_cleanup.py
```

To execute everything in sequence:
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py
```

## Service Management
```bash
systemctl start media-pipeline
systemctl enable media-pipeline
systemctl status media-pipeline

systemctl start syncthing@root
systemctl enable syncthing@root
journalctl -u media-pipeline -f
```
Pipeline executions generate timestamped reports under `/opt/media-pipeline/logs/` for auditing.

## Syncthing Monitoring
`scripts/monitor_syncthing_sync.py` calls the Syncthing REST API to track folder progress, show pending files/bytes, and alert when a folder reports "idle" while work remains. Configure `SYNCTHING_API_KEY` and target folders in `settings.env`.

## iCloud Upload Notes
- `scripts/upload_icloud.py` wraps `scripts/upload_icloud.js` (Puppeteer).
- Set `ICLOUD_INTERACTIVE=true` to open a visible Chromium window for MFA or selector inspection.
- When `ICLOUD_INSPECT_UPLOAD=true`, the script enumerates candidate upload buttons/inputs, pauses for manual review, and exits without queueing files.
- Upload batches are limited to compressed video extensions (`.mp4`, `.mov`, `.m4v`, `.hevc`).

## Database & Caching
- Supabase tables (`media_files`, `batches`, `duplicate_files`, `pipeline_logs`) store canonical metadata; see `supabase/schema.sql`.
- `scripts/local_db_manager.py` provides a mirrored SQLite store located under `/opt/media-pipeline/cache/` so dedupe and uploads can proceed offline.
- Use `scripts/backfill_database.py` to ingest existing NAS contents and `scripts/test_supabase_connection.py` to validate connectivity and permissions.

## Maintenance Utilities
- `scripts/check_and_fix.sh` – health check plus optional remediation of packages, permissions, services.
- `scripts/setup_lxc.sh` – baseline OS configuration (packages, users, services) for a fresh container.
- `scripts/create_stable_environment.sh`, `backup_environment.sh`, `quick_env_fix.sh` – manage the Python virtual environment snapshot.
- `cleanup_and_setup.sh` – reset repo working tree and reinstall dependencies after large updates.

## Development & Testing
```bash
python -m compileall scripts                   # sanity check Python sources
python -m unittest                             # run unit tests (includes retry decorator coverage)
node --check scripts/upload_icloud.js          # syntax check Puppeteer uploader
npm test                                       # (if web UI tests are added under package.json)
```
When modifying automation scripts, prefer relative imports that work under both `python script.py` and `python -m scripts.script` execution paths.

## Troubleshooting
| Symptom | Suggested Action |
| --- | --- |
| Supabase errors mentioning `synced_to_supabase` | Run latest code; `local_db_manager` migration adds the column automatically. |
| iCloud upload stalls before selecting files | Launch with `ICLOUD_INSPECT_UPLOAD=true` to print detected selectors, adjust overrides in `config/settings.env`. |
| Syncthing waits indefinitely | Run `scripts/monitor_syncthing_sync.py` to inspect folder state and pending items. |
| Missing directories under NAS mount | Execute `./setup_nas_structure.sh` to recreate structure with correct permissions. |
| Chromium launch fails in headless mode | Ensure `install.sh` installed the Chromium dependencies; rerun on updated hosts. |

## Additional Documentation
- `Deduplication_sorting_README.md` – detailed explanation of file organization logic.
- `PRODUCTION_READINESS_REPORT.md` – operational checklists and incident response notes.
- `manual_test_commands.sh` – scripted reference for manual validation commands.
- `move_files_to_originals.py` – helper that sweeps NAS intake folders into `originals/` before dedupe.

