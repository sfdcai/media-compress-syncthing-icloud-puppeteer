#!/usr/bin/env python3
"""
Monitor Syncthing sync status using REST API
"""

import os
import sys
import time
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
try:  # Allow monitor to run both inside and outside the package context
    from .utils import log_step, update_file_status, update_batch_status
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import log_step, update_file_status, update_batch_status  # type: ignore

# Load environment variables
load_dotenv("config/settings.env")

class SyncthingMonitor:
    def __init__(self, api_url="http://localhost:8384", api_key=None):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key or os.getenv("SYNCTHING_API_KEY")
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({'X-API-Key': self.api_key})
    
    def get_system_status(self):
        """Get Syncthing system status"""
        try:
            response = self.session.get(f"{self.api_url}/rest/system/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log_step("syncthing_monitor", f"Failed to get system status: {e}", "error")
            return None
    
    def get_folder_statistics(self, folder_id=None):
        """Get folder statistics"""
        try:
            if folder_id:
                response = self.session.get(
                    f"{self.api_url}/rest/stats/folder",
                    params={"folder": folder_id},
                    timeout=10,
                )
                response.raise_for_status()
                stats = response.json()
                # API returns a dictionary keyed by folder id even when filtered
                if isinstance(stats, dict):
                    return stats.get(folder_id, stats)
                return stats
            else:
                response = self.session.get(f"{self.api_url}/rest/stats/folder", timeout=10)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            log_step("syncthing_monitor", f"Failed to get folder statistics: {e}", "error")
            return None
    
    def get_folder_status(self, folder_id):
        """Get specific folder status"""
        try:
            response = self.session.get(f"{self.api_url}/rest/db/status", params={'folder': folder_id}, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log_step("syncthing_monitor", f"Failed to get folder status for {folder_id}: {e}", "error")
            return None
    
    def get_connections(self):
        """Get device connections status"""
        try:
            response = self.session.get(f"{self.api_url}/rest/system/connections", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log_step("syncthing_monitor", f"Failed to get connections: {e}", "error")
            return None
    
    def is_syncing(self, folder_id, *, status=None):
        """Check if folder is currently syncing"""
        try:
            if status is None:
                status = self.get_folder_status(folder_id)
            if not status:
                return False

            state = str(status.get('state', '')).lower()
            need_bytes = status.get('needBytes', 0) or 0
            need_files = status.get('needFiles', 0) or 0

            if state in {"syncing", "scanning", "cleaning"}:
                return True

            return need_bytes > 0 or need_files > 0
        except Exception as e:
            log_step("syncthing_monitor", f"Error checking sync status: {e}", "error")
            return False
    
    def wait_for_sync_completion(self, folder_id, timeout=600, check_interval=30):
        """Wait for sync to complete"""
        log_step("syncthing_monitor", f"Waiting for sync completion (timeout: {timeout}s)", "info")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_folder_status(folder_id)
            if not status:
                log_step("syncthing_monitor", "Unable to fetch folder status during wait", "warning")
                time.sleep(check_interval)
                continue

            if not self.is_syncing(folder_id, status=status):
                log_step("syncthing_monitor", "Sync completed", "success")
                return True

            need_bytes = status.get('needBytes', 0)
            need_files = status.get('needFiles', 0)
            state = status.get('state', 'unknown')

            time.sleep(check_interval)
            elapsed = int(time.time() - start_time)
            log_step(
                "syncthing_monitor",
                f"Still syncing... state={state}, remaining={need_files} files / {need_bytes} bytes ({elapsed}s elapsed)",
                "info",
            )
        
        log_step("syncthing_monitor", "Sync timeout reached", "warning")
        return False

def monitor_pixel_sync():
    """Monitor Pixel folder sync status"""
    print("=== Syncthing Sync Monitor ===")
    
    # Configuration
    syncthing_url = os.getenv("SYNCTHING_URL", "http://localhost:8384")
    syncthing_api_key = os.getenv("SYNCTHING_API_KEY")
    pixel_folder_id = os.getenv("PIXEL_FOLDER_ID", "pixel")
    bridge_dir = os.getenv("BRIDGE_PIXEL_DIR", "/mnt/wd_all_pictures/sync/bridge/pixel")
    sync_folder = os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel")
    
    print(f"Syncthing URL: {syncthing_url}")
    print(f"Pixel folder ID: {pixel_folder_id}")
    print(f"Bridge directory: {bridge_dir}")
    print(f"Sync folder: {sync_folder}")
    
    # Initialize monitor
    monitor = SyncthingMonitor(syncthing_url, syncthing_api_key)
    
    # Check system status
    print("\nStep 1: Checking Syncthing system status...")
    system_status = monitor.get_system_status()
    
    if not system_status:
        print("✗ Cannot connect to Syncthing API")
        return False
    
    print(f"✓ Syncthing is running (version: {system_status.get('version', 'unknown')})")
    
    # Check connections
    print("\nStep 2: Checking device connections...")
    connections = monitor.get_connections()
    
    if connections:
        connected_devices = [dev for dev, status in connections.get('connections', {}).items() 
                           if status.get('connected', False)]
        print(f"✓ Connected to {len(connected_devices)} devices: {', '.join(connected_devices)}")
    else:
        print("⚠ Could not get connection status")
    
    # Check folder statistics
    print("\nStep 3: Checking folder statistics...")
    folder_stats = monitor.get_folder_statistics(pixel_folder_id)
    
    if folder_stats:
        print(f"✓ Folder statistics retrieved")
        print(f"  - Last scan: {folder_stats.get('lastScan', 'unknown')}")
        print(f"  - Files: {folder_stats.get('files', 0)}")
        print(f"  - Directories: {folder_stats.get('dirs', 0)}")
    else:
        print("⚠ Could not get folder statistics")
    
    # Check current sync status
    print("\nStep 4: Checking current sync status...")
    folder_status = monitor.get_folder_status(pixel_folder_id)
    
    if folder_status:
        current_state = folder_status.get('state', 'unknown')
        need_bytes = folder_status.get('needBytes', 0)
        need_files = folder_status.get('needFiles', 0)
        is_syncing = monitor.is_syncing(pixel_folder_id, status=folder_status)

        print(f"✓ Sync status: {'Syncing' if is_syncing else 'Idle'} (state: {current_state})")

        if is_syncing:
            print(f"  - Bytes remaining: {need_bytes}")
            print(f"  - Files remaining: {need_files}")
            print(f"  - Total bytes in sync: {folder_status.get('inSyncBytes', 0)}")

            # Wait for sync completion
            print("\nStep 5: Waiting for sync completion...")
            sync_completed = monitor.wait_for_sync_completion(pixel_folder_id, timeout=300)

            if sync_completed:
                print("✓ Sync completed successfully")
                return True
            else:
                print("⚠ Sync did not complete within timeout")
                return False
        else:
            if need_bytes or need_files:
                print(f"⚠ Syncthing reports idle but {need_files} files / {need_bytes} bytes remain")
            else:
                print("✓ No active sync in progress")
            return True
    else:
        print("✗ Could not get folder status")
        return False

def check_synced_files():
    """Check which files have been synced"""
    print("\n=== Checking Synced Files ===")
    
    bridge_dir = os.getenv("BRIDGE_PIXEL_DIR", "/mnt/wd_all_pictures/sync/bridge/pixel")
    sync_folder = os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel")
    
    # Get files in bridge directory
    bridge_files = []
    if os.path.exists(bridge_dir):
        for filename in os.listdir(bridge_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov')):
                bridge_files.append(filename)
    
    # Get files in sync folder
    sync_files = []
    if os.path.exists(sync_folder):
        for filename in os.listdir(sync_folder):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov')):
                sync_files.append(filename)
    
    print(f"Files in bridge directory: {len(bridge_files)}")
    print(f"Files in sync folder: {len(sync_files)}")
    
    # Check which files have been synced
    synced_files = set(bridge_files) & set(sync_files)
    unsynced_files = set(bridge_files) - set(sync_files)
    
    print(f"Synced files: {len(synced_files)}")
    print(f"Unsynced files: {len(unsynced_files)}")
    
    if unsynced_files:
        print(f"Unsynced files: {list(unsynced_files)[:5]}{'...' if len(unsynced_files) > 5 else ''}")
    
    return len(synced_files), len(unsynced_files)

def main():
    """Main monitoring function"""
    try:
        # Monitor sync status
        sync_success = monitor_pixel_sync()
        
        # Check synced files
        synced_count, unsynced_count = check_synced_files()
        
        print(f"\n=== Sync Summary ===")
        print(f"Sync status: {'Success' if sync_success else 'Failed/Incomplete'}")
        print(f"Files synced: {synced_count}")
        print(f"Files pending: {unsynced_count}")
        
        if sync_success and unsynced_count == 0:
            print("✓ All files successfully synced")
            sys.exit(0)
        else:
            print("⚠ Sync incomplete or failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        log_step("syncthing_monitor", f"Monitoring failed: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
