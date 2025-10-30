#!/usr/bin/env python3
"""
Google Photos Monitor for Magisk Module
Monitors Google Photos app activity and provides notifications
Leverages Pixel's built-in Google Photos app instead of custom API
"""

import os
import sys
import json
import time
import hashlib
import requests
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    log_dir = "/data/adb/modules/google_photos_monitor/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(f"{log_dir}/monitor.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class GooglePhotosMonitor:
    """Monitor Google Photos app activity and file changes"""
    
    def __init__(self, config_file: str = "/data/adb/modules/google_photos_monitor/credentials.json"):
        self.config = self.load_config(config_file)
        self.known_files = set()
        self.uploaded_files = set()
        self.failed_files = set()
        self.running = False
        
        # Directories to monitor
        self.monitor_dirs = self.config['monitoring']['directories']
        self.supported_formats = self.config['monitoring']['supported_formats']
        
        # Load existing state
        self.load_state()
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "monitoring": {
                "enabled": True,
                "interval_seconds": 30,
                "directories": [
                    "/sdcard/DCIM/Camera",
                    "/sdcard/Pictures/Screenshots",
                    "/sdcard/Download"
                ],
                "supported_formats": [".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"]
            },
            "telegram": {
                "enabled": True,
                "bot_token": "",
                "chat_id": ""
            },
            "auto_cleanup": {
                "enabled": False,
                "delete_after_hours": 24,
                "keep_original": True
            }
        }
    
    def load_state(self):
        """Load monitor state from file"""
        state_file = "/data/adb/modules/google_photos_monitor/state.json"
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.known_files = set(state.get('known_files', []))
                    self.uploaded_files = set(state.get('uploaded_files', []))
                    self.failed_files = set(state.get('failed_files', []))
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
    
    def save_state(self):
        """Save monitor state to file"""
        state_file = "/data/adb/modules/google_photos_monitor/state.json"
        try:
            state = {
                'known_files': list(self.known_files),
                'uploaded_files': list(self.uploaded_files),
                'failed_files': list(self.failed_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Get MD5 hash of file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def scan_for_new_files(self) -> List[str]:
        """Scan directories for new files"""
        new_files = []
        
        for directory in self.monitor_dirs:
            if not os.path.exists(directory):
                continue
                
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if not any(filename.lower().endswith(fmt) for fmt in self.supported_formats):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    file_hash = self.get_file_hash(file_path)
                    
                    if file_hash and file_hash not in self.known_files:
                        new_files.append(file_path)
                        self.known_files.add(file_hash)
        
        return new_files
    
    def check_google_photos_activity(self) -> Dict:
        """Check Google Photos app activity using dumpsys"""
        try:
            # Get Google Photos app info
            result = subprocess.run([
                'dumpsys', 'package', 'com.google.android.apps.photos'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return {'status': 'not_installed', 'message': 'Google Photos not installed'}
            
            # Check if app is running
            result = subprocess.run([
                'dumpsys', 'activity', 'activities', '|', 'grep', 'com.google.android.apps.photos'
            ], shell=True, capture_output=True, text=True, timeout=10)
            
            is_running = 'com.google.android.apps.photos' in result.stdout
            
            # Get app version
            result = subprocess.run([
                'dumpsys', 'package', 'com.google.android.apps.photos', '|', 'grep', 'versionName'
            ], shell=True, capture_output=True, text=True, timeout=10)
            
            version = "Unknown"
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'versionName' in line:
                        version = line.split('=')[1].strip()
                        break
            
            return {
                'status': 'installed',
                'running': is_running,
                'version': version,
                'message': f'Google Photos v{version} - {"Running" if is_running else "Not running"}'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Error checking Google Photos: {e}'}
    
    def check_upload_progress(self) -> Dict:
        """Check if files are being uploaded by monitoring file changes"""
        try:
            # Check for files that might be uploading (recently modified)
            now = datetime.now()
            recent_files = []
            
            for directory in self.monitor_dirs:
                if not os.path.exists(directory):
                    continue
                    
                for root, dirs, filenames in os.walk(directory):
                    for filename in filenames:
                        if not any(filename.lower().endswith(fmt) for fmt in self.supported_formats):
                            continue
                        
                        file_path = os.path.join(root, filename)
                        try:
                            stat = os.stat(file_path)
                            modified_time = datetime.fromtimestamp(stat.st_mtime)
                            
                            # Check if file was modified in the last 5 minutes
                            if (now - modified_time).total_seconds() < 300:
                                recent_files.append({
                                    'path': file_path,
                                    'filename': filename,
                                    'modified': modified_time.isoformat(),
                                    'size': stat.st_size
                                })
                        except OSError:
                            continue
            
            return {
                'recent_files': len(recent_files),
                'files': recent_files[:5]  # First 5 files
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def send_telegram_notification(self, message: str, debug: bool = False):
        """Send notification to Telegram"""
        if not self.config['telegram']['enabled']:
            return
        
        try:
            bot_token = self.config['telegram']['bot_token']
            chat_id = self.config['telegram']['chat_id']
            
            if not bot_token or not chat_id:
                return
            
            # Add debug prefix if needed
            if debug:
                message = f"[DEBUG] {message}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': f"📱 Google Photos Monitor\n{message}",
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logger.debug(f"Telegram notification failed: {e}")
    
    def process_new_files(self, new_files: List[str]):
        """Process newly detected files"""
        if not new_files:
            return
        
        logger.info(f"Found {len(new_files)} new files")
        
        for file_path in new_files:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Send notification about new file
            self.send_telegram_notification(
                f"📸 New file detected: {filename}\n"
                f"📁 Size: {file_size / 1024 / 1024:.1f} MB\n"
                f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            # Schedule cleanup if enabled
            if self.config['auto_cleanup']['enabled']:
                self.schedule_file_cleanup(file_path)
    
    def schedule_file_cleanup(self, file_path: str):
        """Schedule file for cleanup after upload"""
        if not self.config['auto_cleanup']['enabled']:
            return
        
        delay_hours = self.config['auto_cleanup']['delete_after_hours']
        cleanup_time = datetime.now() + timedelta(hours=delay_hours)
        
        # Store cleanup schedule
        cleanup_file = "/data/adb/modules/google_photos_monitor/cleanup.json"
        cleanup_schedule = []
        
        if os.path.exists(cleanup_file):
            try:
                with open(cleanup_file, 'r') as f:
                    cleanup_schedule = json.load(f)
            except Exception:
                pass
        
        cleanup_schedule.append({
            'file_path': file_path,
            'cleanup_at': cleanup_time.isoformat(),
            'keep_original': self.config['auto_cleanup']['keep_original']
        })
        
        with open(cleanup_file, 'w') as f:
            json.dump(cleanup_schedule, f, indent=2)
    
    def process_scheduled_cleanup(self):
        """Process scheduled file cleanup"""
        cleanup_file = "/data/adb/modules/google_photos_monitor/cleanup.json"
        if not os.path.exists(cleanup_file):
            return
        
        try:
            with open(cleanup_file, 'r') as f:
                cleanup_schedule = json.load(f)
            
            now = datetime.now()
            remaining_cleanup = []
            
            for item in cleanup_schedule:
                cleanup_at = datetime.fromisoformat(item['cleanup_at'])
                if now >= cleanup_at:
                    # Check if file still exists
                    file_path = item['file_path']
                    if os.path.exists(file_path):
                        if item['keep_original']:
                            # Move to a backup location instead of deleting
                            backup_dir = "/sdcard/GooglePhotosBackup"
                            os.makedirs(backup_dir, exist_ok=True)
                            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                            
                            try:
                                os.rename(file_path, backup_path)
                                logger.info(f"Moved file to backup: {os.path.basename(file_path)}")
                                self.send_telegram_notification(f"📦 Moved to backup: {os.path.basename(file_path)}")
                            except Exception as e:
                                logger.error(f"Failed to move file: {e}")
                        else:
                            # Delete the file
                            try:
                                os.remove(file_path)
                                logger.info(f"Deleted file: {os.path.basename(file_path)}")
                                self.send_telegram_notification(f"🗑️ Deleted: {os.path.basename(file_path)}")
                            except Exception as e:
                                logger.error(f"Failed to delete file: {e}")
                    else:
                        logger.info(f"File already removed: {os.path.basename(file_path)}")
                else:
                    remaining_cleanup.append(item)
            
            # Save remaining cleanup schedule
            with open(cleanup_file, 'w') as f:
                json.dump(remaining_cleanup, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to process cleanup: {e}")
    
    def generate_status_report(self) -> Dict:
        """Generate status report"""
        google_photos_status = self.check_google_photos_activity()
        upload_progress = self.check_upload_progress()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'google_photos': google_photos_status,
            'upload_progress': upload_progress,
            'monitoring': {
                'directories': len(self.monitor_dirs),
                'known_files': len(self.known_files),
                'uploaded_files': len(self.uploaded_files),
                'failed_files': len(self.failed_files)
            }
        }
    
    def run(self):
        """Main monitor loop"""
        logger.info("Google Photos Monitor started")
        self.running = True
        
        # Send startup notification
        self.send_telegram_notification("🚀 Google Photos Monitor started")
        
        while self.running:
            try:
                # Process scheduled cleanup
                self.process_scheduled_cleanup()
                
                # Scan for new files
                new_files = self.scan_for_new_files()
                
                if new_files:
                    self.process_new_files(new_files)
                    self.save_state()
                
                # Generate and log status report
                status_report = self.generate_status_report()
                logger.debug(f"Status: {status_report}")
                
                # Wait for next scan
                time.sleep(self.config['monitoring']['interval_seconds'])
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait before retrying
        
        logger.info("Google Photos Monitor stopped")
        self.send_telegram_notification("🛑 Google Photos Monitor stopped")
    
    def stop(self):
        """Stop the monitor"""
        self.running = False

def main():
    """Main function"""
    try:
        monitor = GooglePhotosMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()