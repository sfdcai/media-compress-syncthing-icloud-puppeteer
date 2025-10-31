# Media Pipeline

A production-grade media ingestion, compression, and synchronization system designed for hybrid iCloud and Google Photos workflows. The project targets Ubuntu 22.04+ LXC containers on Proxmox but can be adapted to other Linux environments.

---

## Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Architecture](#architecture)
4. [Repository Layout](#repository-layout)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Database & Storage](#database--storage)
8. [Pipeline Operations](#pipeline-operations)
9. [Automation & Services](#automation--services)
10. [Testing & Quality Assurance](#testing--quality-assurance)
11. [Maintenance Toolkit](#maintenance-toolkit)
12. [Troubleshooting](#troubleshooting)
13. [Roadmap & Future Enhancements](#roadmap--future-enhancements)
14. [Contributing & Support](#contributing--support)

---

## Overview
The pipeline continuously downloads media from iCloud, deduplicates and compresses assets, stages batches for multiple destinations, and synchronizes uploads to iCloud and Google Photos. Metadata, progress, and operational history are tracked in Supabase and a mirrored local cache so that offline processing stays in sync with the cloud database.

**Key capabilities**
- End-to-end automation: iCloud ingest ➔ deduplication ➔ compression ➔ bridge preparation ➔ upload ➔ verification ➔ archival sorting.
- Dual-destination synchronization: iCloud uploads driven by Puppeteer automation, Pixel/Google Photos synchronization handled through Syncthing and optional Magisk modules.
- Configurable feature toggles and directory layout, suitable for NAS-backed storage mounted inside LXC containers.
- Comprehensive monitoring hooks via CLI utilities, scheduled scripts, and a Flask-based web dashboard.
- Schema parity between the local SQLite cache and the Supabase Postgres instance, enforced by automated tests.

---

## System Requirements
| Component | Recommended | Notes |
|-----------|-------------|-------|
| Operating System | Ubuntu 22.04 LTS (LXC container or bare metal) | Other Debian-based systems work with minor tweaks. |
| CPU & RAM | 2 vCPU / 4 GB RAM minimum | Increase for heavy compression or large concurrent uploads. |
| Disk | ≥ 20 GB free | Ensure additional space for originals and compressed artifacts. |
| Python | 3.10+ (uses virtual environment) | Managed by `install.sh`. |
| Node.js | 18.x or newer | Installed from NodeSource if missing. |
| Additional tools | `ffmpeg`, `exiftool`, `rsync`, `parallel`, `syncthing` | Installed by the installer script when possible. |

Networking prerequisites include outbound HTTPS access to Apple, Google, Supabase, and Telegram APIs. The Pixel automation path also requires LAN access to the NAS share exposed to the device.

---

## Architecture

### Data Flow
```
1. download_from_icloud.py   ➔ originals/
2. deduplicate.py            ➔ mark duplicates in DB and filesystem
3. compress_media.py         ➔ compressed/
4. prepare_bridge_batch.py   ➔ bridge/icloud/ and bridge/pixel/
5. upload_icloud.js ➔ uploads prepared batches to iCloud via Puppeteer
6. sync_to_pixel.py          ➔ hands off batches to Syncthing / Pixel devices
7. verify_and_cleanup.py     ➔ verification, manifest updates, cleanup
8. sort_uploaded.py          ➔ sorted/YYYY/MM/DD organization
```

### Core Components
| Area | Description | Key Files |
|------|-------------|-----------|
| CLI & automation scripts | Operational entry points for each pipeline stage and diagnostics. | `scripts/*.py`, `scripts/upload_icloud.js`, `scripts/utils.py` |
| Python package | Shared business logic for orchestration, processors, and utilities. | `src/core`, `src/processors`, `src/utils`, `src/run_pipeline.py` |
| Web dashboard | Flask-based control panel and static assets for monitoring. | `web/server.py`, `web/index.html`, `web/install_web_dashboard.sh` |
| Database schema | Canonical Supabase definitions and local SQLite synchronization helpers. | `supabase/schema.sql`, `supabase_schema/__init__.py`, `scripts/local_db_manager.py` |
| Tests | Pytest suites for schema parity, utilities, and integration smoke tests. | `tests/`, `scripts/test_*.py` |

---

## Repository Layout
| Path | Purpose |
|------|---------|
| `scripts/` | Operational scripts for ingest, compression, upload automation, diagnostics, and health checks. |
| `src/` | Importable Python package powering the pipeline orchestration, processors, and shared utilities. |
| `web/` | Web dashboard assets and deployment helper scripts. |
| `supabase/` | Canonical SQL schema for the Supabase Postgres deployment. |
| `supabase_schema/` | Python module exposing canonical CREATE statements shared by tests and setup tooling. |
| `config/` | Checked-in configuration templates (`settings.env`, Google OAuth template). Actual secrets live outside the repo. |
| `tests/` | Pytest suites validating schema consistency and utility behavior. |
| `magisk_module*` | Pixel backup Magisk modules and helper scripts. |
| `install.sh`, `cleanup_and_setup.sh`, `manage_config.sh` | Deployment, recovery, and configuration automation. |

---

## Installation

### 1. Clone or bootstrap the repository
```bash
# Full bootstrap on a fresh container
bash -c "$(wget -qO- https://raw.githubusercontent.com/sfdcai/media-compress-syncthing-icloud-puppeteer/main/setup-git-clone.sh)"

# Or clone manually
git clone https://github.com/sfdcai/media-compress-syncthing-icloud-puppeteer.git
cd media-compress-syncthing-icloud-puppeteer
```

### 2. Run the guided installer
```bash
sudo ./install.sh
```
The installer performs system validation, installs missing packages (Python, Node.js, ffmpeg, exiftool, etc.), creates `/opt/media-pipeline`, provisions a Python virtual environment, installs Python and Node dependencies, configures the `media-pipeline` system user, and registers the `media-pipeline` systemd service.

### 3. Configure secrets and feature toggles
```bash
./manage_config.sh setup   # moves config into /opt/media-pipeline/.config and symlinks it
./manage_config.sh edit    # open the consolidated configuration file for editing
```
Populate credentials for iCloud, Supabase, Telegram, Syncthing paths, and compression preferences. Default values act as documentation for each setting.

### 4. Optional: Provision ancillary services
- **Syncthing:** ensure the service is enabled for the `media-pipeline` user or root (`systemctl enable syncthing@root`).
- **Web dashboard:** run `./setup_web_dashboard.sh` to deploy the Flask service and nginx reverse proxy if desired.
- **Pixel Magisk module:** use `setup_magisk_module.sh` or `setup_pixel_backup_gang.sh` to package device-side helpers once core services are verified.

---

## Configuration

All runtime configuration lives in `/opt/media-pipeline/.config/settings.env` and is symlinked back into `config/settings.env` for convenience. Key sections include:

### Feature Toggles
| Variable | Description |
|----------|-------------|
| `ENABLE_ICLOUD_DOWNLOAD`, `ENABLE_FOLDER_DOWNLOAD` | Control which sources feed the download stage. |
| `ENABLE_ICLOUD_UPLOAD`, `ENABLE_PIXEL_UPLOAD` | Gate each upload target individually. |
| `ENABLE_COMPRESSION`, `ENABLE_DEDUPLICATION`, `ENABLE_FILE_PREPARATION`, `ENABLE_SORTING`, `ENABLE_VERIFICATION` | Control downstream pipeline stages during debugging. |
| `ENABLE_GOOGLE_PHOTOS_SYNC_CHECK` | Enables sync verification logic and related diagnostics. |

### Credentials & Integrations
| Variable | Purpose |
|----------|---------|
| `ICLOUD_USERNAME` / `ICLOUD_PASSWORD` | App-specific password for iCloud downloads. |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase Postgres API connection. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Optional notification channels (configure via `manage_config.sh edit`). |
| `GOOGLE_PHOTOS_CLIENT_ID`, `GOOGLE_PHOTOS_CLIENT_SECRET` | OAuth credentials for Google Photos sync checker and dashboard flows. |

### Storage Layout
Mount your NAS at `NAS_MOUNT` and update the directory variables (`ORIGINALS_DIR`, `COMPRESSED_DIR`, `BRIDGE_ICLOUD_DIR`, `BRIDGE_PIXEL_DIR`, `SORTED_DIR`, etc.) to match your environment. The defaults assume `/mnt/wd_all_pictures/sync/...` within an LXC container.

### Upload Automation Controls
- Puppeteer uploader accepts `--upload-selector <css>` or `ICLOUD_UPLOAD_SELECTOR` to override the Photos web UI upload button. The script automatically falls back to known selectors and waits for UI stabilization to minimize fragility.
- Persist browser cookies between runs by supplying `--session-file <path>` (or `ICLOUD_SESSION_FILE`). The file will be created automatically after a successful login and refreshed whenever cookies change.
- Tune robustness with `UPLOAD_RETRY_ATTEMPTS`, `UPLOAD_RETRY_DELAY`, and `ICLOUD_UPLOAD_TIMEOUT` (seconds) or `ICLOUD_UPLOAD_TIMEOUT_MS` (milliseconds). CLI overrides (`--max-retries`, `--retry-delay`, `--timeout`) take precedence per run.
- Adjust Chromium launch behaviour with `PUPPETEER_HEADLESS`, `PUPPETEER_SLOWMO`, and `PUPPETEER_EXTRA_ARGS` (comma-separated). The CLI exposes `--headless/--headful`, `--slowmo`, and repeatable `--launch-arg` to change these on demand.

---

## Database & Storage

### Supabase & Local Cache
- Canonical table definitions reside in `supabase_schema/__init__.py` and are synchronized with `supabase/schema.sql`.
- The local cache managed by `scripts/local_db_manager.py` mirrors the Supabase schema (batches, media_files, duplicate_files, pipeline_logs) so offline processing can later reconcile with Supabase.
- `setup_supabase_tables.py` consumes the shared schema definitions to provision or update tables.
- `tests/test_schema_consistency.py` ensures the Supabase SQL and local SQLite structures stay aligned; run it whenever schema changes are proposed.

### File System Contracts
The pipeline expects the following directory structure inside `NAS_MOUNT`:
- `originals/` – raw downloads from iCloud.
- `compressed/` – recompressed assets generated by `compress_media.py`.
- `bridge/icloud/`, `bridge/pixel/` – staging areas consumed by uploaders.
- `uploaded/icloud/`, `uploaded/pixel/` – holding areas for successfully uploaded assets.
- `sorted/YYYY/MM/DD/` – long-term archival layout produced by `sort_uploaded.py`.
- `cleanup/` – temporary workspace for verification and pruning.

Use `setup_nas_structure.sh` to scaffold the directories (it drops a README inside the mount with reminders for permissions and quotas).

---

## Pipeline Operations

### Running Individual Stages
Each stage can be executed directly from the installed virtual environment:
```bash
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/deduplicate.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py
sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py
node /opt/media-pipeline/scripts/upload_icloud.js --dir /mnt/.../bridge/icloud --session-file /opt/media-pipeline/.config/icloud_session.json
```
Other helpers include `run_pipeline.py` (full sequential run), `run_pipeline_manual.py` (prompts before each stage), and `run_pixel_sync.py` for Pixel-only workflows.

### Upload Automation
- **iCloud:** `scripts/upload_icloud.js` authenticates with Puppeteer, restores saved session cookies when available, discovers the correct upload control (frame-aware), detects file inputs, and watches progress events. Provide `--session-file <path>`, `--upload-selector <css>`, and `--dir <path>` as needed. Additional hardening flags include `--max-retries`, `--retry-delay`, `--timeout`, `--headful/--headless`, `--slowmo`, and repeatable `--launch-arg` overrides for Chromium.
- **Google Photos / Pixel:** `sync_to_pixel.py` coordinates with Syncthing, while `google_photos_sync_checker.py` validates token health, API scopes, and pipeline integration.

### Verification & Cleanup
`scripts/verify_and_cleanup.py` ensures uploads completed, reconciles manifests, and removes processed files. `scripts/sort_uploaded.py` performs final archival moves into the date-based hierarchy.

---

## Automation & Services

### Systemd Units
- `media-pipeline.service` orchestrates scheduled pipeline runs; installed and enabled by `install.sh`.
- `syncthing@root.service` (or user-level Syncthing) must be enabled for Pixel synchronization.
- Optional: `media-pipeline-web.service` provides the Flask dashboard when installed through `setup_web_dashboard.sh`.

Use `systemctl status media-pipeline` and `journalctl -u media-pipeline` to monitor execution. The installer prints the most common service management commands upon completion.

### Scheduling
The default systemd timer triggers the pipeline; adjust `/opt/media-pipeline/scripts/run_pipeline.py` or accompanying timer units to fit your cadence. For manual runs, invoke `start_pipeline.sh` or the individual scripts shown above.

---

## Testing & Quality Assurance

### Python Unit & Integration Tests
```bash
pytest                 # core utility and schema tests
RUN_PROD_TESTS=1 pytest scripts/test_google_photos_sync.py  # enables live Google Photos smoke checks
```
`tests/test_schema_consistency.py` enforces schema parity, while `tests/test_utils_retry.py` and `tests/test_deduplicate_targets.py` cover retry helpers and deduplication targets. Integration scripts (`scripts/test_complete_pipeline.py`, `scripts/test_google_photos_*`) double as manual diagnostics and pytest-aware checks thanks to shared `_test_result` helpers.

### Node.js Diagnostics
```bash
node scripts/upload_icloud.js --help
node scripts/upload_icloud.js --dir /tmp/test --session-file /tmp/icloud_session.json --upload-selector "button[aria-label='Upload']" --max-retries 5 --retry-delay 10 --timeout 600 --headful
```
The CLI prints actionable status messages and hints if the upload selector must be overridden.

### Continuous Verification
`manual_test_commands.sh` prints a curated checklist of commands for smoke testing each stage. Execute it after upgrades or infrastructure changes to confirm the environment is healthy.

---

## Maintenance Toolkit

| Script | Purpose |
|--------|---------|
| `cleanup_and_setup.sh` | Resets the environment, reinstalls dependencies, and reapplies permissions for disaster recovery. |
| `scripts/check_and_fix.sh` | Comprehensive health check covering packages, services, directory structure, Syncthing status, and permissions. |
| `update_packages.sh` | Safely upgrades system packages and restarts the pipeline service if required. |
| `manage_config.sh` | Manages configuration outside the repo, supports template creation, editing, and Git updates. |
| `deploy.sh` | Syncs the repository into `/opt/media-pipeline`, handles ownership, and restarts services. |
| `deploy_pixel_backup_manual.sh` | Packages Pixel backup artifacts along with documentation extracted from this README. |
| `setup_magisk_module.sh` / `setup_pixel_backup_gang.sh` | Generate Magisk-ready modules and companion guides for device-side automation. |
| `setup_nas_structure.sh` | Creates the NAS directory tree and seeds an on-share README with usage guidance. |

Legacy uploader experiments now live in `scripts/legacy_uploaders/`; consult them only if you need to reference historical automation approaches.

---

## Troubleshooting

1. **Authentication failures**
   - Regenerate app-specific passwords for iCloud and re-run `download_from_icloud.py` interactively to complete 2FA prompts.
   - For Google Photos, re-run `scripts/setup_google_photos_api.py` followed by `scripts/complete_google_photos_auth.py` to refresh OAuth tokens.
2. **Upload button not detected**
   - Pass `--upload-selector` to `upload_icloud.js` with the current CSS selector. The CLI applies it ahead of the bundled `icloud_selectors.json` hints.
   - Update `scripts/icloud_selectors.json` with the new selector (add to `uploadButtonSelectors`) so future runs inherit the fix. Keep older selectors for backward compatibility with slowly rolling UI changes.
   - In Chrome DevTools, right-click the upload button ➔ **Inspect**, then copy the CSS selector via the context menu (`Copy ➔ Copy selector`). Prefer stable attributes such as `aria-label` or `data-testid`.
3. **Repeated logins every run**
   - Provide `--session-file /path/to/icloud_session.json` (or set `ICLOUD_SESSION_FILE`) so Puppeteer stores trusted cookies after a successful login.
   - If the session file becomes invalid, delete it and rerun once interactively to refresh cookies. The uploader will recreate the file automatically.
   - Check uploader logs for `Photos interface ready after …` entries to confirm the telemetry is tracking how long the interface takes to settle; persistent timeouts indicate selectors need attention.
4. **Supabase schema mismatch**
   - Run `pytest tests/test_schema_consistency.py` to view diffs and update `supabase/schema.sql` and `scripts/local_db_manager.py` together.
5. **Syncthing not syncing**
   - Check `monitor_syncthing_sync.py` for detailed status and ensure `syncthing@root` is active.
6. **Storage pressure**
   - Use `scripts/compress_media.py --help` (run manually) to adjust compression thresholds, and monitor NAS quotas with `setup_nas_structure.sh` output.
7. **Service crashes**
   - Inspect `journalctl -u media-pipeline`, rerun `scripts/check_and_fix.sh`, and confirm Python virtualenv dependencies are installed under `/opt/media-pipeline/venv`.

---

## Roadmap & Future Enhancements
Condensed from the historical planning documents:
- **Media intelligence:** face and object detection, content-aware compression, HDR-aware processing.
- **Automation insights:** predictive scheduling based on bandwidth and storage trends, enhanced auto-recovery strategies.
- **Security posture:** end-to-end encryption options, privacy controls (location scrubbing, selective sharing), RBAC for multi-user deployments.
- **Integration expansion:** support for Google Drive, Dropbox, OneDrive, and AWS S3/Glacier; webhook and REST APIs for third-party automation.
- **Analytics:** usage dashboards with storage trends, content insights, and scheduled reporting.
- **Mobile ecosystem:** Magisk modules, native apps, and browser extensions for ad-hoc uploads and monitoring.

---

## Contributing & Support
1. **Issues & Pull Requests:** open an issue describing the change or bug before submitting a PR. Align schema changes with `supabase_schema/__init__.py` and update tests.
2. **Coding Standards:**
   - Python: follow PEP 8, use type hints where practical, keep business logic in `src/` and thin CLI wrappers in `scripts/`.
   - Node.js: modern ES modules (`type: module`) with async/await and no `try/catch` around imports.
3. **Testing:** run `pytest` and relevant integration scripts (`RUN_PROD_TESTS=1 pytest ...`) before committing.
4. **Deployment:** prefer using `deploy.sh` or `install.sh` for consistent permissions and service management.

For operational support, review the Troubleshooting section, consult inline script help (`--help` flags), or contact the maintainers through the repository issue tracker.
