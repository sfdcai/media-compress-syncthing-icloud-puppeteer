#!/usr/bin/env python3
"""
Alternative sync verification methods that don't rely on Google Photos API
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

class AlternativeSyncVerifier:
    """Alternative methods to verify file sync status without Google Photos API"""
    
    def __init__(self):
        self.pixel_upload_dir = '/mnt/syncthing/pixel'
        self.originals_dir = '/mnt/wd_all_pictures/sync/originals'
        self.uploaded_dir = '/mnt/wd_all_pictures/sync/uploaded/icloud'
        
    def get_file_metadata(self, file_path: str) -> Dict:
        """Get comprehensive file metadata"""
        try:
            stat = os.stat(file_path)
            file_hash = self.calculate_file_hash(file_path)
            
            return {
                'filename': os.path.basename(file_path),
                'filepath': file_path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'hash': file_hash,
                'extension': os.path.splitext(file_path)[1].lower()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """Calculate file hash for comparison"""
        try:
            hash_func = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception:
            return ""
    
    def method1_file_tracking(self) -> Dict:
        """Method 1: Track files through pipeline stages"""
        print("=== Method 1: File Pipeline Tracking ===")
        
        stages = {
            'originals': self.originals_dir,
            'pixel_upload': self.pixel_upload_dir,
            'icloud_uploaded': self.uploaded_dir
        }
        
        results = {}
        for stage_name, stage_dir in stages.items():
            if os.path.exists(stage_dir):
                files = []
                for root, dirs, filenames in os.walk(stage_dir):
                    for filename in filenames:
                        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4')):
                            file_path = os.path.join(root, filename)
                            metadata = self.get_file_metadata(file_path)
                            files.append(metadata)
                
                results[stage_name] = {
                    'count': len(files),
                    'files': files[:5]  # First 5 files as sample
                }
                print(f"{stage_name}: {len(files)} files")
            else:
                results[stage_name] = {'count': 0, 'files': []}
                print(f"{stage_name}: Directory not found")
        
        return results
    
    def method2_upload_timestamps(self) -> Dict:
        """Method 2: Compare upload timestamps and file modifications"""
        print("\n=== Method 2: Upload Timestamp Analysis ===")
        
        pixel_files = []
        if os.path.exists(self.pixel_upload_dir):
            for root, dirs, filenames in os.walk(self.pixel_upload_dir):
                for filename in filenames:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4')):
                        file_path = os.path.join(root, filename)
                        metadata = self.get_file_metadata(file_path)
                        pixel_files.append(metadata)
        
        # Analyze upload patterns
        now = datetime.now()
        recent_uploads = []
        for file_info in pixel_files:
            if 'modified' in file_info:
                time_diff = now - file_info['modified']
                if time_diff < timedelta(hours=24):  # Uploaded in last 24 hours
                    recent_uploads.append(file_info)
        
        print(f"Total pixel files: {len(pixel_files)}")
        print(f"Recent uploads (24h): {len(recent_uploads)}")
        
        return {
            'total_files': len(pixel_files),
            'recent_uploads': len(recent_uploads),
            'recent_files': recent_uploads[:5]
        }
    
    def method3_syncthing_status(self) -> Dict:
        """Method 3: Check Syncthing sync status"""
        print("\n=== Method 3: Syncthing Status Check ===")
        
        try:
            # Check if Syncthing is running
            syncthing_url = "http://localhost:8384/rest/system/status"
            syncthing_api_key = "2iFEREP3yaXdMah76SpzGtSRLTTpbLHN"
            
            headers = {'X-API-Key': syncthing_api_key}
            response = requests.get(syncthing_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                status = response.json()
                print(f"Syncthing status: {status.get('myID', 'Unknown')}")
                
                # Get folder status
                folders_url = "http://localhost:8384/rest/stats/folder"
                folders_response = requests.get(folders_url, headers=headers, timeout=5)
                
                if folders_response.status_code == 200:
                    folders = folders_response.json()
                    print(f"Syncthing folders: {len(folders)}")
                    
                    # Look for pixel folder
                    pixel_folder_id = "hmmcd-wjatk"  # From your config
                    if pixel_folder_id in folders:
                        folder_stats = folders[pixel_folder_id]
                        print(f"Pixel folder stats: {folder_stats}")
                        
                        return {
                            'syncthing_running': True,
                            'pixel_folder_stats': folder_stats,
                            'last_scan': folder_stats.get('lastScan', 'Unknown')
                        }
                
                return {'syncthing_running': True, 'folders': len(folders)}
            else:
                print(f"Syncthing not responding: {response.status_code}")
                return {'syncthing_running': False, 'error': 'Not responding'}
                
        except Exception as e:
            print(f"Syncthing check failed: {e}")
            return {'syncthing_running': False, 'error': str(e)}
    
    def method4_file_size_analysis(self) -> Dict:
        """Method 4: Analyze file sizes and patterns"""
        print("\n=== Method 4: File Size Analysis ===")
        
        pixel_files = []
        if os.path.exists(self.pixel_upload_dir):
            for root, dirs, filenames in os.walk(self.pixel_upload_dir):
                for filename in filenames:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4')):
                        file_path = os.path.join(root, filename)
                        metadata = self.get_file_metadata(file_path)
                        if 'size' in metadata:
                            pixel_files.append(metadata)
        
        if not pixel_files:
            return {'error': 'No files found'}
        
        # Analyze file sizes
        sizes = [f['size'] for f in pixel_files if 'size' in f]
        total_size = sum(sizes)
        avg_size = total_size / len(sizes) if sizes else 0
        
        # Group by file type
        by_extension = {}
        for file_info in pixel_files:
            ext = file_info.get('extension', 'unknown')
            if ext not in by_extension:
                by_extension[ext] = []
            by_extension[ext].append(file_info)
        
        print(f"Total files: {len(pixel_files)}")
        print(f"Total size: {total_size / (1024*1024):.2f} MB")
        print(f"Average size: {avg_size / (1024*1024):.2f} MB")
        print("By extension:")
        for ext, files in by_extension.items():
            print(f"  {ext}: {len(files)} files")
        
        return {
            'total_files': len(pixel_files),
            'total_size_mb': total_size / (1024*1024),
            'average_size_mb': avg_size / (1024*1024),
            'by_extension': {ext: len(files) for ext, files in by_extension.items()}
        }
    
    def method5_upload_log_analysis(self) -> Dict:
        """Method 5: Analyze upload logs for sync patterns"""
        print("\n=== Method 5: Upload Log Analysis ===")
        
        log_files = [
            '/opt/media-pipeline/logs/pipeline.log',
            '/opt/media-pipeline/logs/web_server.log'
        ]
        
        upload_events = []
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if 'upload' in line.lower() and ('success' in line.lower() or 'completed' in line.lower()):
                                upload_events.append({
                                    'timestamp': line.split(']')[0] if ']' in line else 'Unknown',
                                    'message': line.strip()
                                })
                except Exception as e:
                    print(f"Error reading {log_file}: {e}")
        
        print(f"Found {len(upload_events)} upload events in logs")
        for event in upload_events[-5:]:  # Last 5 events
            print(f"  {event['timestamp']}: {event['message'][:100]}...")
        
        return {
            'upload_events': len(upload_events),
            'recent_events': upload_events[-10:]  # Last 10 events
        }
    
    def generate_sync_report(self) -> Dict:
        """Generate comprehensive sync verification report"""
        print("=== Alternative Sync Verification Report ===")
        print("=" * 50)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'methods': {}
        }
        
        # Run all methods
        report['methods']['file_tracking'] = self.method1_file_tracking()
        report['methods']['upload_timestamps'] = self.method2_upload_timestamps()
        report['methods']['syncthing_status'] = self.method3_syncthing_status()
        report['methods']['file_size_analysis'] = self.method4_file_size_analysis()
        report['methods']['upload_log_analysis'] = self.method5_upload_log_analysis()
        
        # Overall assessment
        pixel_files = report['methods']['file_tracking']['pixel_upload']['count']
        recent_uploads = report['methods']['upload_timestamps']['recent_uploads']
        syncthing_running = report['methods']['syncthing_status']['syncthing_running']
        
        print(f"\n=== Overall Assessment ===")
        print(f"Pixel files found: {pixel_files}")
        print(f"Recent uploads (24h): {recent_uploads}")
        print(f"Syncthing running: {syncthing_running}")
        
        if pixel_files > 0 and recent_uploads > 0:
            print("✅ Files are being uploaded and synced")
        elif pixel_files > 0:
            print("⚠️  Files found but no recent uploads")
        else:
            print("❌ No files found in pixel upload directory")
        
        return report

def main():
    """Run alternative sync verification"""
    verifier = AlternativeSyncVerifier()
    report = verifier.generate_sync_report()
    
    # Save report
    report_file = f'/opt/media-pipeline/logs/alternative_sync_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nReport saved to: {report_file}")

if __name__ == "__main__":
    main()