#!/usr/bin/env python3
"""
Pixel Backup Gang - Backup Manager
Integrates with Pixel's built-in Google Photos backup system
Based on the pixel-backup-gang approach
"""

import os
import sys
import json
import time
import subprocess
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    log_dir = "/data/adb/modules/pixel_backup_gang/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(f"{log_dir}/backup_manager.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class PixelBackupGang:
    """Manages Pixel's built-in Google Photos backup system"""
    
    def __init__(self, config_file: str = "/data/adb/modules/pixel_backup_gang/credentials.json"):
        self.config = self.load_config(config_file)
        self.running = False
        
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
            "backup_settings": {
                "enabled": True,
                "interval_seconds": 60,
                "auto_backup_enabled": True,
                "backup_photos": True,
                "backup_videos": True,
                "backup_screenshots": True,
                "wifi_only": False
            },
            "telegram": {
                "enabled": True,
                "bot_token": "",
                "chat_id": "",
                "debug_mode": False
            }
        }
    
    def run_adb_command(self, command: str) -> str:
        """Run ADB command on the device"""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"ADB command failed: {e}")
            return ""
    
    def enable_google_photos_backup(self) -> bool:
        """Enable Google Photos backup on the device"""
        try:
            logger.info("Enabling Google Photos backup...")
            
            # Enable backup for photos
            self.run_adb_command("settings put global backup_photos_enabled 1")
            
            # Enable backup for videos
            self.run_adb_command("settings put global backup_videos_enabled 1")
            
            # Set backup transport to Google
            self.run_adb_command("settings put global backup_transport com.google.android.gms/.backup.BackupTransportService")
            
            # Enable auto backup
            self.run_adb_command("settings put global auto_backup_enabled 1")
            
            # Set backup frequency to daily
            self.run_adb_command("settings put global backup_frequency 86400000")
            
            logger.info("Google Photos backup enabled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable Google Photos backup: {e}")
            return False
    
    def check_backup_status(self) -> Dict:
        """Check current backup status"""
        try:
            status = {
                'backup_photos': self.run_adb_command("settings get global backup_photos_enabled"),
                'backup_videos': self.run_adb_command("settings get global backup_videos_enabled"),
                'auto_backup': self.run_adb_command("settings get global auto_backup_enabled"),
                'backup_transport': self.run_adb_command("settings get global backup_transport")
            }
            
            # Check if backup is properly configured
            is_configured = (
                status['backup_photos'] == '1' and
                status['backup_videos'] == '1' and
                status['auto_backup'] == '1' and
                'google' in status['backup_transport'].lower()
            )
            
            status['is_configured'] = is_configured
            return status
            
        except Exception as e:
            logger.error(f"Failed to check backup status: {e}")
            return {'is_configured': False, 'error': str(e)}
    
    def force_backup_sync(self) -> bool:
        """Force a backup sync"""
        try:
            logger.info("Forcing backup sync...")
            
            # Trigger backup
            result = self.run_adb_command("bmgr backupnow --all")
            
            if "Backup" in result:
                logger.info("Backup sync started successfully")
                return True
            else:
                logger.error("Failed to start backup sync")
                return False
                
        except Exception as e:
            logger.error(f"Failed to force backup sync: {e}")
            return False
    
    def get_backup_progress(self) -> Dict:
        """Get current backup progress"""
        try:
            # Get backup status
            backup_list = self.run_adb_command("bmgr list")
            
            # Parse backup information
            lines = backup_list.split('\n')
            pending_backups = 0
            completed_backups = 0
            
            for line in lines:
                if 'Pending' in line:
                    pending_backups += 1
                elif 'Completed' in line:
                    completed_backups += 1
            
            return {
                'pending_backups': pending_backups,
                'completed_backups': completed_backups,
                'total_backups': pending_backups + completed_backups,
                'is_running': pending_backups > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup progress: {e}")
            return {'error': str(e)}
    
    def scan_new_files(self) -> List[Dict]:
        """Scan for new files in monitored directories"""
        try:
            new_files = []
            directories = self.config['monitoring']['directories']
            supported_formats = self.config['monitoring']['supported_formats']
            
            for directory in directories:
                if not os.path.exists(directory):
                    continue
                
                # Find files modified in the last hour
                for root, dirs, filenames in os.walk(directory):
                    for filename in filenames:
                        if any(filename.lower().endswith(fmt) for fmt in supported_formats):
                            file_path = os.path.join(root, filename)
                            try:
                                stat = os.stat(file_path)
                                modified_time = datetime.fromtimestamp(stat.st_mtime)
                                
                                # Check if file was modified in the last hour
                                if (datetime.now() - modified_time).total_seconds() < 3600:
                                    new_files.append({
                                        'path': file_path,
                                        'filename': filename,
                                        'size': stat.st_size,
                                        'modified': modified_time.isoformat()
                                    })
                            except OSError:
                                continue
            
            return new_files
            
        except Exception as e:
            logger.error(f"Failed to scan new files: {e}")
            return []
    
    def send_telegram_notification(self, message: str, debug: bool = False):
        """Send notification to Telegram"""
        if not self.config['telegram']['enabled']:
            return
        
        try:
            bot_token = self.config['telegram']['bot_token']
            chat_id = self.config['telegram']['chat_id']
            
            if not bot_token or not chat_id:
                return
            
            if debug and not self.config['telegram']['debug_mode']:
                return
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': f"📱 Pixel Backup Gang\n{message}",
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logger.debug(f"Telegram notification failed: {e}")
    
    def check_network_connectivity(self) -> bool:
        """Check if device has network connectivity"""
        try:
            # Check if connected to WiFi (if wifi_only is enabled)
            if self.config['backup_settings']['wifi_only']:
                wifi_info = self.run_adb_command("dumpsys wifi | grep mWifiInfo")
                return 'SSID' in wifi_info
            else:
                # Check any network connectivity
                result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                      capture_output=True, timeout=10)
                return result.returncode == 0
        except Exception:
            return False
    
    def run(self):
        """Main backup management loop"""
        logger.info("Pixel Backup Gang started")
        self.running = True
        
        # Send startup notification
        self.send_telegram_notification("🚀 Pixel Backup Gang started")
        
        # Enable Google Photos backup
        if not self.enable_google_photos_backup():
            logger.error("Failed to enable Google Photos backup")
            return
        
        while self.running:
            try:
                # Check network connectivity
                if not self.check_network_connectivity():
                    logger.debug("No network connectivity, skipping backup")
                    time.sleep(self.config['backup_settings']['interval_seconds'])
                    continue
                
                # Check backup status
                status = self.check_backup_status()
                if not status['is_configured']:
                    logger.warning("Backup not properly configured, re-enabling...")
                    self.enable_google_photos_backup()
                
                # Scan for new files
                new_files = self.scan_new_files()
                
                if new_files:
                    logger.info(f"Found {len(new_files)} new files")
                    self.send_telegram_notification(f"📸 Found {len(new_files)} new files")
                    
                    # Force backup sync
                    if self.force_backup_sync():
                        # Monitor backup progress
                        time.sleep(30)
                        progress = self.get_backup_progress()
                        
                        if progress.get('is_running'):
                            logger.info("Backup is running...")
                            self.send_telegram_notification("⏳ Backup in progress...")
                        else:
                            logger.info("Backup completed")
                            self.send_telegram_notification("✅ Backup completed")
                    else:
                        logger.error("Failed to start backup")
                        self.send_telegram_notification("❌ Failed to start backup")
                else:
                    logger.debug("No new files to backup")
                
                # Wait for next check
                time.sleep(self.config['backup_settings']['interval_seconds'])
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)
        
        logger.info("Pixel Backup Gang stopped")
        self.send_telegram_notification("🛑 Pixel Backup Gang stopped")
    
    def stop(self):
        """Stop the backup manager"""
        self.running = False

def main():
    """Main function"""
    try:
        backup_gang = PixelBackupGang()
        backup_gang.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()