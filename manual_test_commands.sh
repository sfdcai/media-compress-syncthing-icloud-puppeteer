#!/bin/bash
# Manual Test Commands Script
# Provides all manual testing commands for easy copy-paste

echo "============================================"
echo "  Media Pipeline Manual Testing Commands"
echo "============================================"
echo
echo "Copy and paste these commands one by one to test each component:"
echo

echo "=== PHASE 1: SYSTEM SETUP ==="
echo
echo "# 1. Setup LXC container and dependencies"
echo "sudo ./scripts/setup_lxc.sh"
echo
echo "# 2. Setup NAS directory structure"
echo "sudo ./setup_nas_structure.sh"
echo
echo "# 3. Run comprehensive health check"
echo "sudo ./scripts/check_and_fix.sh"
echo
echo "# 4. Setup configuration management"
echo "./manage_config.sh setup"
echo
echo "# 5. Edit your configuration"
echo "./manage_config.sh edit"
echo

echo "=== PHASE 2: MANUAL PIPELINE TESTING ==="
echo
echo "# 6. Test iCloud download"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/download_from_icloud.py"
echo
echo "# 7. Test media compression"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/compress_media.py"
echo
echo "# 8. Test deduplication"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/deduplicate.py"
echo
echo "# 9. Test bridge preparation (iCloud)"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py"
echo
echo "# 10. Test iCloud upload"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/upload_icloud.py"
echo
echo "# 11. Test Pixel sync preparation"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/prepare_bridge_batch.py"
echo
echo "# 12. Test Pixel sync"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sync_to_pixel.py"
echo
echo "# 13. Test file sorting"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/sort_uploaded.py"
echo
echo "# 14. Test cleanup"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/verify_and_cleanup.py"
echo

echo "=== PHASE 3: FULL PIPELINE TEST ==="
echo
echo "# 15. Test complete pipeline (all steps in sequence)"
echo "sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/scripts/run_pipeline.py"
echo

echo "=== PHASE 4: SERVICE SETUP (Only After Manual Testing Passes) ==="
echo
echo "# 16. Start Syncthing service"
echo "systemctl start syncthing@root"
echo "systemctl enable syncthing@root"
echo
echo "# 17. Start media pipeline service (automated)"
echo "systemctl start media-pipeline"
echo "systemctl enable media-pipeline"
echo
echo "# 18. Check service status"
echo "systemctl status media-pipeline"
echo "systemctl status syncthing@root"
echo

echo "=== VERIFICATION COMMANDS ==="
echo
echo "# Check directory structure"
echo "ls -la /mnt/wd_all_pictures/sync/"
echo
echo "# Check originals"
echo "ls -la /mnt/wd_all_pictures/sync/originals/"
echo
echo "# Check compressed"
echo "ls -la /mnt/wd_all_pictures/sync/compressed/"
echo
echo "# Check bridge directories"
echo "ls -la /mnt/wd_all_pictures/sync/bridge/"
echo
echo "# Check uploaded files"
echo "ls -la /mnt/wd_all_pictures/sync/uploaded/"
echo
echo "# Check sorted files"
echo "ls -la /mnt/wd_all_pictures/sync/sorted/"
echo
echo "# Check logs"
echo "tail -f /opt/media-pipeline/logs/pipeline.log"
echo
echo "# Check service logs"
echo "journalctl -u media-pipeline -f"
echo "journalctl -u syncthing@root -f"
echo

echo "============================================"
echo "  Manual Testing Complete!"
echo "============================================"
echo
echo "After all manual tests pass, you can switch to automated services."
echo "If any test fails, check the troubleshooting section in README.md"
