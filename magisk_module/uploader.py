#!/usr/bin/env python3
"""
Google Photos Uploader for Magisk Module
Automatically uploads photos to Google Photos without storing on NAND
"""

import os
import sys
import json
import time
import hashlib
import requests
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    log_dir = "/data/adb/modules/google_photos_uploader/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(f"{log_dir}/uploader.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class GooglePhotosUploader:
    """Google Photos uploader with NAND-free operation"""
    
    def __init__(self, config_file: str = "/data/adb/modules/google_photos_uploader/config.json"):
        self.config = self.load_config(config_file)
        self.access_token = None
        self.refresh_token = None
        self.upload_queue = []
        self.uploaded_files = set()
        self.failed_files = set()
        self.running = False
        
        # Directories
        self.camera_dir = "/sdcard/DCIM/Camera"
        self.screenshots_dir = "/sdcard/Pictures/Screenshots"
        self.downloads_dir = "/sdcard/Download"
        self.temp_dir = "/data/local/tmp/google_photos_uploader"
        
        # Create temp directory
        os.makedirs(self.temp_dir, exist_ok=True)
        
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
            "google_photos": {
                "client_id": "",
                "client_secret": "",
                "refresh_token": ""
            },
            "upload": {
                "enabled": True,
                "interval_seconds": 60,
                "max_file_size_mb": 100,
                "supported_formats": [".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"],
                "auto_delete_after_upload": False,
                "delete_delay_hours": 24
            },
            "telegram": {
                "enabled": True,
                "bot_token": "",
                "chat_id": "",
                "debug_mode": False
            },
            "directories": {
                "camera": "/sdcard/DCIM/Camera",
                "screenshots": "/sdcard/Pictures/Screenshots",
                "downloads": "/sdcard/Download"
            }
        }
    
    def load_state(self):
        """Load uploader state from file"""
        state_file = "/data/adb/modules/google_photos_uploader/state.json"
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.uploaded_files = set(state.get('uploaded_files', []))
                    self.failed_files = set(state.get('failed_files', []))
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
    
    def save_state(self):
        """Save uploader state to file"""
        state_file = "/data/adb/modules/google_photos_uploader/state.json"
        try:
            state = {
                'uploaded_files': list(self.uploaded_files),
                'failed_files': list(self.failed_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def authenticate(self) -> bool:
        """Authenticate with Google Photos API"""
        try:
            if not self.config['google_photos']['refresh_token']:
                logger.error("No refresh token configured")
                return False
            
            # Refresh access token
            url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': self.config['google_photos']['client_id'],
                'client_secret': self.config['google_photos']['client_secret'],
                'refresh_token': self.config['google_photos']['refresh_token'],
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            logger.info("Successfully authenticated with Google Photos API")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def scan_for_files(self) -> List[str]:
        """Scan directories for new files to upload"""
        files_to_upload = []
        supported_formats = self.config['upload']['supported_formats']
        max_size = self.config['upload']['max_file_size_mb'] * 1024 * 1024
        
        directories = [
            self.config['directories']['camera'],
            self.config['directories']['screenshots'],
            self.config['directories']['downloads']
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                continue
                
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    # Check if file is supported
                    if not any(filename.lower().endswith(fmt) for fmt in supported_formats):
                        continue
                    
                    # Check file size
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > max_size:
                            logger.debug(f"File too large: {filename} ({file_size / 1024 / 1024:.1f} MB)")
                            continue
                    except OSError:
                        continue
                    
                    # Check if already processed
                    file_hash = self.get_file_hash(file_path)
                    if file_hash in self.uploaded_files:
                        continue
                    
                    if file_hash in self.failed_files:
                        continue
                    
                    files_to_upload.append(file_path)
        
        logger.info(f"Found {len(files_to_upload)} new files to upload")
        return files_to_upload
    
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
    
    def upload_file(self, file_path: str) -> bool:
        """Upload a single file to Google Photos"""
        try:
            if not self.access_token:
                if not self.authenticate():
                    return False
            
            # Get file info
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.info(f"Uploading: {filename} ({file_size / 1024 / 1024:.1f} MB)")
            
            # Step 1: Upload raw bytes
            upload_url = self.upload_raw_bytes(file_path)
            if not upload_url:
                return False
            
            # Step 2: Create media item
            success = self.create_media_item(upload_url, filename)
            
            if success:
                file_hash = self.get_file_hash(file_path)
                self.uploaded_files.add(file_hash)
                self.save_state()
                
                # Send Telegram notification
                self.send_telegram_notification(f"✅ Uploaded: {filename}")
                
                # Auto-delete if enabled
                if self.config['upload']['auto_delete_after_upload']:
                    self.schedule_file_deletion(file_path)
                
                logger.info(f"Successfully uploaded: {filename}")
                return True
            else:
                file_hash = self.get_file_hash(file_path)
                self.failed_files.add(file_hash)
                self.save_state()
                return False
                
        except Exception as e:
            logger.error(f"Upload failed for {file_path}: {e}")
            return False
    
    def upload_raw_bytes(self, file_path: str) -> Optional[str]:
        """Upload raw bytes to Google Photos"""
        try:
            # Upload to Google Photos
            url = "https://photoslibrary.googleapis.com/v1/uploads"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/octet-stream',
                'X-Goog-Upload-Protocol': 'raw',
                'X-Goog-Upload-File-Name': os.path.basename(file_path)
            }
            
            with open(file_path, 'rb') as f:
                response = requests.post(url, headers=headers, data=f, timeout=300)
            
            response.raise_for_status()
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Raw bytes upload failed: {e}")
            return None
    
    def create_media_item(self, upload_token: str, filename: str) -> bool:
        """Create media item in Google Photos"""
        try:
            url = "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'newMediaItems': [{
                    'description': f'Uploaded by Media Pipeline System - {filename}',
                    'simpleMediaItem': {
                        'uploadToken': upload_token
                    }
                }]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'newMediaItemResults' in result and result['newMediaItemResults']:
                return result['newMediaItemResults'][0].get('status', {}).get('code') == 'OK'
            
            return False
            
        except Exception as e:
            logger.error(f"Media item creation failed: {e}")
            return False
    
    def schedule_file_deletion(self, file_path: str):
        """Schedule file for deletion after upload"""
        if not self.config['upload']['auto_delete_after_upload']:
            return
        
        delay_hours = self.config['upload']['delete_delay_hours']
        delete_time = datetime.now() + timedelta(hours=delay_hours)
        
        # Store deletion schedule
        deletion_file = f"/data/adb/modules/google_photos_uploader/deletions.json"
        deletions = []
        
        if os.path.exists(deletion_file):
            try:
                with open(deletion_file, 'r') as f:
                    deletions = json.load(f)
            except Exception:
                pass
        
        deletions.append({
            'file_path': file_path,
            'delete_at': delete_time.isoformat()
        })
        
        with open(deletion_file, 'w') as f:
            json.dump(deletions, f, indent=2)
    
    def process_scheduled_deletions(self):
        """Process scheduled file deletions"""
        deletion_file = f"/data/adb/modules/google_photos_uploader/deletions.json"
        if not os.path.exists(deletion_file):
            return
        
        try:
            with open(deletion_file, 'r') as f:
                deletions = json.load(f)
            
            now = datetime.now()
            remaining_deletions = []
            
            for deletion in deletions:
                delete_at = datetime.fromisoformat(deletion['delete_at'])
                if now >= delete_at:
                    # Delete the file
                    file_path = deletion['file_path']
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted file: {os.path.basename(file_path)}")
                        self.send_telegram_notification(f"🗑️ Deleted: {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
                else:
                    remaining_deletions.append(deletion)
            
            # Save remaining deletions
            with open(deletion_file, 'w') as f:
                json.dump(remaining_deletions, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to process deletions: {e}")
    
    def send_telegram_notification(self, message: str):
        """Send notification to Telegram"""
        if not self.config['telegram']['enabled']:
            return
        
        try:
            bot_token = self.config['telegram']['bot_token']
            chat_id = self.config['telegram']['chat_id']
            
            if not bot_token or not chat_id:
                return
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': f"📱 Google Photos Uploader\n{message}",
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logger.debug(f"Telegram notification failed: {e}")
    
    def run(self):
        """Main uploader loop"""
        logger.info("Google Photos Uploader started")
        self.running = True
        
        # Send startup notification
        self.send_telegram_notification("🚀 Google Photos Uploader started")
        
        while self.running:
            try:
                # Process scheduled deletions
                self.process_scheduled_deletions()
                
                # Scan for new files
                files_to_upload = self.scan_for_files()
                
                if files_to_upload:
                    logger.info(f"Processing {len(files_to_upload)} files")
                    
                    for file_path in files_to_upload:
                        if not self.running:
                            break
                        
                        success = self.upload_file(file_path)
                        if not success:
                            logger.warning(f"Failed to upload: {os.path.basename(file_path)}")
                
                # Wait for next scan
                time.sleep(self.config['upload']['interval_seconds'])
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait before retrying
        
        logger.info("Google Photos Uploader stopped")
        self.send_telegram_notification("🛑 Google Photos Uploader stopped")
    
    def stop(self):
        """Stop the uploader"""
        self.running = False

def main():
    """Main function"""
    try:
        uploader = GooglePhotosUploader()
        uploader.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()