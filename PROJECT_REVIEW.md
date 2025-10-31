# Project Review and Recommendations

## Executive Summary
The media pipeline has evolved into a comprehensive automation suite that now includes schema parity checks, an orchestration layer with phase gating, and a hardened Puppeteer uploader. The system ships with a consolidated README and an installer capable of bootstrapping dependencies on Ubuntu hosts. Despite this maturity, several areas would benefit from additional hardening, documentation alignment, and automated coverage—particularly around configuration defaults and browser automation reliability.

## Observations

### Architecture & Orchestration
* The pipeline orchestrator evaluates phase toggles at runtime, including a callable gate for the download stage so it activates when either iCloud or folder-based ingestion is enabled.【F:src/run_pipeline.py†L47-L119】
* Local caching mirrors the Supabase schema (batches, media files, duplicate tracking, pipeline logs) and performs legacy column migrations on demand, keeping offline runs in sync.【F:scripts/local_db_manager.py†L1-L104】

### Tooling & Operations
* The installer provisions Python, Node.js, ffmpeg, Syncthing, and related tooling, then deploys to `/opt/media-pipeline` under a dedicated service account.【F:install.sh†L1-L168】
* Configuration management lives in `manage_config.sh`, which now seeds every pipeline toggle (download, compression, verification, and Google Photos checks) and symlinks the generated file back into the repo for editing.【F:manage_config.sh†L1-L140】【F:config/settings.env†L1-L120】
* The Puppeteer uploader restores saved sessions, surfaces configurable retries/timeouts, and exposes headless/headful, slow-motion, and launch-argument overrides so operators can adapt quickly when Apple tweaks the UI.【F:scripts/upload_icloud.js†L1-L420】

### Testing
* The pytest suite passes, with integration-heavy scripts intentionally skipped unless production credentials are available, leaving ten active unit-style tests exercising retry helpers, schema parity, and download toggle behavior.【c13286†L1-L19】

### Codebase Hygiene
* Legacy upload variants have been quarantined under `scripts/legacy_uploaders`, leaving the hardened Puppeteer script as the documented Node entry point.【F:scripts/legacy_uploaders/README.md†L1-L60】【F:package.json†L1-L24】
* Retry/backoff defaults live in environment variables but are interpreted ad-hoc by shell scripts, Python utilities, and the Puppeteer uploader, which increases the chance of future drift.【F:scripts/utils.py†L300-L360】【F:scripts/upload_icloud.js†L1-L420】

## Recommendations

1. **Codify retry/backoff parsing in a shared module.** Create a centralized configuration helper (Python + Node) that reads `UPLOAD_RETRY_ATTEMPTS`, `UPLOAD_RETRY_DELAY`, and timeout values once and shares the result across scripts to prevent future drift between automation layers.【F:scripts/utils.py†L300-L360】【F:scripts/upload_icloud.js†L1-L420】
2. **Automate Puppeteer smoke tests.** Add a headless CI exercise that loads a fixture HTML page (mirroring iCloud's upload controls) to assert selector discovery, retry handling, and CLI overrides so regressions surface before production rollouts.【F:scripts/upload_icloud.js†L200-L420】【F:tests/test_feature_toggles.py†L1-L80】
3. **Harden telemetry & structured logging.** Expand uploader logging to emit structured JSON (file name, retry count, selector used) and feed it into the existing Supabase/local logging pipeline so operations can query upload health historically.【F:scripts/upload_icloud.js†L230-L360】【F:scripts/utils.py†L80-L160】

Implementing these improvements should reduce configuration drift, improve browser automation reliability, and make the operational surface area easier to understand for future maintainers.
