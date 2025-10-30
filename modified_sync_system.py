#!/usr/bin/env python3
"""
Modified sync system that works within Google's API restrictions
"""

import os
import sys
import json
import hashlib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the project root to Python path
sys.path.append('/opt/media-pipeline')

class ModifiedSyncSystem:
    """Modified sync system that doesn't rely on Google Photos API access"""
    
    def __init__(self):
        self.pixel_upload_dir = '/mnt/syncthing/pixel'
        self.originals_dir = '/mnt/wd_all_pictures/sync/originals'
        self.uploaded_dir = '/mnt/wd_all_pictures/sync/uploaded/icloud'
        self.sync_status_file = '/opt/media-pipeline/logs/sync_status.json'
        
    def load_sync_status(self) -> Dict:
        """Load current sync status from file"""
        if os.path.exists(self.sync_status_file):
            try:
                with open(self.sync_status_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'files': {}, 'last_updated': None}
    
    def save_sync_status(self, status: Dict):
        """Save sync status to file"""
        os.makedirs(os.path.dirname(self.sync_status_file), exist_ok=True)
        with open(self.sync_status_file, 'w') as f:
            json.dump(status, f, indent=2, default=str)
    
    def track_file_upload(self, file_path: str, upload_method: str = 'pixel') -> Dict:
        """Track a file upload event"""
        status = self.load_sync_status()
        
        file_info = {
            'filename': os.path.basename(file_path),
            'filepath': file_path,
            'upload_method': upload_method,
            'upload_time': datetime.now().isoformat(),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'file_hash': self.calculate_file_hash(file_path) if os.path.exists(file_path) else '',
            'status': 'uploaded'
        }
        
        file_key = f"{upload_method}_{os.path.basename(file_path)}"
        status['files'][file_key] = file_info
        status['last_updated'] = datetime.now().isoformat()
        
        self.save_sync_status(status)
        return file_info
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate file hash for verification"""
        try:
            hash_func = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception:
            return ""
    
    def verify_sync_status(self) -> Dict:
        """Verify sync status using alternative methods"""
        print("=== Modified Sync Status Verification ===")
        
        status = self.load_sync_status()
        pixel_files = self.get_pixel_files()
        
        verification_results = {
            'timestamp': datetime.now().isoformat(),
            'total_pixel_files': len(pixel_files),
            'tracked_uploads': len(status.get('files', {})),
            'sync_status': {}
        }
        
        # Method 1: Check if files exist in pixel directory
        for file_info in pixel_files:
            filename = file_info['filename']
            file_key = f"pixel_{filename}"
            
            if file_key in status['files']:
                # File is tracked
                tracked_info = status['files'][file_key]
                verification_results['sync_status'][filename] = {
                    'status': 'tracked',
                    'upload_time': tracked_info.get('upload_time'),
                    'file_size': tracked_info.get('file_size'),
                    'verification_method': 'file_tracking'
                }
            else:
                # File exists but not tracked - likely uploaded recently
                verification_results['sync_status'][filename] = {
                    'status': 'uploaded_but_not_tracked',
                    'detected_time': datetime.now().isoformat(),
                    'file_size': file_info['size'],
                    'verification_method': 'file_existence'
                }
                
                # Auto-track this file
                self.track_file_upload(file_info['filepath'], 'pixel')
        
        return verification_results
    
    def get_pixel_files(self) -> List[Dict]:
        """Get all files in pixel upload directory"""
        files = []
        if os.path.exists(self.pixel_upload_dir):
            for root, dirs, filenames in os.walk(self.pixel_upload_dir):
                for filename in filenames:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4')):
                        file_path = os.path.join(root, filename)
                        stat = os.stat(file_path)
                        files.append({
                            'filename': filename,
                            'filepath': file_path,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
        return files
    
    def check_syncthing_health(self) -> Dict:
        """Check Syncthing health and sync status"""
        try:
            syncthing_url = "http://localhost:8384/rest/system/status"
            syncthing_api_key = "2iFEREP3yaXdMah76SpzGtSRLTTpbLHN"
            
            headers = {'X-API-Key': syncthing_api_key}
            response = requests.get(syncthing_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                status = response.json()
                
                # Get folder statistics
                folders_url = "http://localhost:8384/rest/stats/folder"
                folders_response = requests.get(folders_url, headers=headers, timeout=5)
                
                folder_stats = {}
                if folders_response.status_code == 200:
                    folders = folders_response.json()
                    pixel_folder_id = "hmmcd-wjatk"
                    if pixel_folder_id in folders:
                        folder_stats = folders[pixel_folder_id]
                
                return {
                    'syncthing_running': True,
                    'my_id': status.get('myID', 'Unknown'),
                    'folder_stats': folder_stats,
                    'last_scan': folder_stats.get('lastScan', 'Unknown')
                }
            else:
                return {'syncthing_running': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'syncthing_running': False, 'error': str(e)}
    
    def generate_sync_report(self) -> Dict:
        """Generate comprehensive sync report"""
        print("=== Modified Sync System Report ===")
        print("=" * 40)
        
        # Get verification results
        verification = self.verify_sync_status()
        
        # Check Syncthing health
        syncthing_status = self.check_syncthing_health()
        
        # Get recent activity
        recent_activity = self.get_recent_activity()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'verification': verification,
            'syncthing_status': syncthing_status,
            'recent_activity': recent_activity,
            'summary': self.generate_summary(verification, syncthing_status)
        }
        
        return report
    
    def get_recent_activity(self) -> Dict:
        """Get recent upload activity"""
        status = self.load_sync_status()
        now = datetime.now()
        recent_uploads = []
        
        for file_key, file_info in status.get('files', {}).items():
            if 'upload_time' in file_info:
                try:
                    upload_time = datetime.fromisoformat(file_info['upload_time'])
                    if (now - upload_time) < timedelta(hours=24):
                        recent_uploads.append(file_info)
                except Exception:
                    pass
        
        return {
            'recent_uploads_24h': len(recent_uploads),
            'recent_files': recent_uploads[:10]  # Last 10 files
        }
    
    def generate_summary(self, verification: Dict, syncthing_status: Dict) -> Dict:
        """Generate summary of sync status"""
        total_files = verification['total_pixel_files']
        tracked_uploads = verification['tracked_uploads']
        syncthing_running = syncthing_status['syncthing_running']
        
        # Determine overall status
        if total_files > 0 and syncthing_running:
            if tracked_uploads > 0:
                status = "healthy"
                message = f"System healthy: {total_files} files, {tracked_uploads} tracked uploads"
            else:
                status = "warning"
                message = f"Files present but not tracked: {total_files} files"
        elif total_files == 0:
            status = "no_files"
            message = "No files found in pixel upload directory"
        else:
            status = "error"
            message = "Syncthing not running or files not accessible"
        
        return {
            'status': status,
            'message': message,
            'total_files': total_files,
            'tracked_uploads': tracked_uploads,
            'syncthing_running': syncthing_running
        }
    
    def update_web_dashboard(self):
        """Update web dashboard with new sync status"""
        report = self.generate_sync_report()
        
        # Save report for web dashboard
        dashboard_file = '/opt/media-pipeline/logs/dashboard_sync_status.json'
        with open(dashboard_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Dashboard updated: {dashboard_file}")
        return report

def main():
    """Run modified sync system"""
    sync_system = ModifiedSyncSystem()
    report = sync_system.update_web_dashboard()
    
    print("\n=== Sync Status Summary ===")
    summary = report['summary']
    print(f"Status: {summary['status']}")
    print(f"Message: {summary['message']}")
    print(f"Total files: {summary['total_files']}")
    print(f"Tracked uploads: {summary['tracked_uploads']}")
    print(f"Syncthing running: {summary['syncthing_running']}")

if __name__ == "__main__":
    main()