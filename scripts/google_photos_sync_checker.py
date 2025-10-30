#!/usr/bin/env python3
"""
Google Photos Sync Checker
Checks if files uploaded to Pixel are synced to Google Photos cloud
"""

import os
import sys
import json
import hashlib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')

from utils.utils import log_step, get_config_value

class GooglePhotosSyncChecker:
    """Google Photos sync status checker"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.client_id = get_config_value('GOOGLE_PHOTOS_CLIENT_ID', '')
        self.client_secret = get_config_value('GOOGLE_PHOTOS_CLIENT_SECRET', '')
        self.credentials_file = '/opt/media-pipeline/config/google_photos_credentials.json'
        self.token_file = '/opt/media-pipeline/config/google_photos_tokens.json'
        
    def load_credentials(self) -> bool:
        """Load Google Photos API credentials"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)
                    self.client_id = creds.get('client_id', self.client_id)
                    self.client_secret = creds.get('client_secret', self.client_secret)
                    return True
            else:
                log_step("google_photos_sync", "Google Photos credentials file not found", "warning")
                return False
        except Exception as e:
            log_step("google_photos_sync", f"Error loading credentials: {e}", "error")
            return False
    
    def load_tokens(self) -> bool:
        """Load stored access and refresh tokens"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    tokens = json.load(f)
                    self.access_token = tokens.get('access_token')
                    self.refresh_token = tokens.get('refresh_token')
                    return True
            return False
        except Exception as e:
            log_step("google_photos_sync", f"Error loading tokens: {e}", "error")
            return False
    
    def save_tokens(self, access_token: str, refresh_token: str = None) -> bool:
        """Save access and refresh tokens"""
        try:
            tokens = {
                'access_token': access_token,
                'refresh_token': refresh_token or self.refresh_token,
                'updated_at': datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            return True
        except Exception as e:
            log_step("google_photos_sync", f"Error saving tokens: {e}", "error")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        try:
            if not self.refresh_token:
                log_step("google_photos_sync", "No refresh token available", "error")
                return False
            
            url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Save the new access token
            self.save_tokens(self.access_token)
            log_step("google_photos_sync", "Access token refreshed successfully", "success")
            return True
            
        except Exception as e:
            log_step("google_photos_sync", f"Error refreshing access token: {e}", "error")
            return False
    
    def get_authorization_url(self) -> str:
        """Get Google Photos API authorization URL"""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        # Use localhost for OAuth (Google doesn't allow private IPs)
        redirect_uri = 'http://localhost:8080'
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'https://www.googleapis.com/auth/photoslibrary.readonly',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    
    def exchange_code_for_tokens(self, authorization_code: str) -> bool:
        """Exchange authorization code for access and refresh tokens"""
        try:
            url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': 'http://localhost:8080'
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            
            # Save tokens
            self.save_tokens(self.access_token, self.refresh_token)
            log_step("google_photos_sync", "Tokens obtained and saved successfully", "success")
            return True
            
        except Exception as e:
            log_step("google_photos_sync", f"Error exchanging code for tokens: {e}", "error")
            return False
    
    def ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token"""
        if not self.access_token:
            if not self.load_tokens():
                log_step("google_photos_sync", "No tokens available. Need to authenticate first.", "warning")
                return False
        
        # Try to use the token, refresh if needed
        if not self.test_token():
            if not self.refresh_access_token():
                log_step("google_photos_sync", "Failed to refresh access token", "error")
                return False
        
        return True
    
    def test_token(self) -> bool:
        """Test if the current access token is valid"""
        try:
            if not self.access_token:
                return False
                
            # Use a simple endpoint to test the token
            url = "https://photoslibrary.googleapis.com/v1/mediaItems"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            # 200 or 400 (no media items) are both valid responses
            return response.status_code in [200, 400]
            
        except Exception as e:
            log_step("google_photos_sync", f"Token test failed: {e}", "error")
            return False
    
    def search_media_items(self, filename: str = None, date_range: Tuple[datetime, datetime] = None) -> List[Dict]:
        """Search for media items in Google Photos"""
        try:
            if not self.ensure_valid_token():
                return []
            
            url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Build search request
            search_request = {}
            
            if date_range:
                start_date = date_range[0].strftime('%Y-%m-%dT%H:%M:%SZ')
                end_date = date_range[1].strftime('%Y-%m-%dT%H:%M:%SZ')
                search_request['filters'] = {
                    'dateFilter': {
                        'ranges': [{
                            'startDate': {'year': date_range[0].year, 'month': date_range[0].month, 'day': date_range[0].day},
                            'endDate': {'year': date_range[1].year, 'month': date_range[1].month, 'day': date_range[1].day}
                        }]
                    }
                }
            
            response = requests.post(url, headers=headers, json=search_request)
            response.raise_for_status()
            
            data = response.json()
            media_items = data.get('mediaItems', [])
            
            # Filter by filename if provided
            if filename:
                filtered_items = []
                for item in media_items:
                    if filename.lower() in item.get('filename', '').lower():
                        filtered_items.append(item)
                return filtered_items
            
            return media_items
            
        except Exception as e:
            log_step("google_photos_sync", f"Error searching media items: {e}", "error")
            return []
    
    def check_file_sync_status(self, file_path: str, upload_date: datetime = None) -> Dict:
        """Check if a specific file is synced to Google Photos"""
        try:
            filename = os.path.basename(file_path)
            
            # If no upload date provided, use file modification time
            if not upload_date:
                upload_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # Search for files uploaded around the same time (±1 day)
            start_date = upload_date - timedelta(days=1)
            end_date = upload_date + timedelta(days=1)
            
            log_step("google_photos_sync", f"Checking sync status for {filename}", "info")
            
            # Search for the file
            media_items = self.search_media_items(filename, (start_date, end_date))
            
            if not media_items:
                return {
                    'filename': filename,
                    'synced': False,
                    'reason': 'Not found in Google Photos',
                    'search_date_range': f"{start_date.date()} to {end_date.date()}"
                }
            
            # Check for exact filename match
            exact_matches = [item for item in media_items if item.get('filename', '').lower() == filename.lower()]
            
            if exact_matches:
                item = exact_matches[0]
                return {
                    'filename': filename,
                    'synced': True,
                    'google_photos_id': item.get('id'),
                    'google_photos_url': item.get('baseUrl'),
                    'creation_time': item.get('mediaMetadata', {}).get('creationTime'),
                    'file_size': item.get('mediaMetadata', {}).get('size'),
                    'mime_type': item.get('mimeType')
                }
            
            # Check for similar filenames (in case of renaming)
            similar_matches = [item for item in media_items if filename.split('.')[0].lower() in item.get('filename', '').lower()]
            
            if similar_matches:
                item = similar_matches[0]
                return {
                    'filename': filename,
                    'synced': True,
                    'google_photos_filename': item.get('filename'),
                    'google_photos_id': item.get('id'),
                    'google_photos_url': item.get('baseUrl'),
                    'creation_time': item.get('mediaMetadata', {}).get('creationTime'),
                    'reason': 'Found with similar filename'
                }
            
            return {
                'filename': filename,
                'synced': False,
                'reason': 'No matching files found',
                'search_date_range': f"{start_date.date()} to {end_date.date()}"
            }
            
        except Exception as e:
            log_step("google_photos_sync", f"Error checking sync status for {file_path}: {e}", "error")
            return {
                'filename': os.path.basename(file_path),
                'synced': False,
                'reason': f'Error: {str(e)}'
            }
    
    def check_pixel_uploaded_files(self, pixel_upload_dir: str) -> List[Dict]:
        """Check sync status for all files uploaded to Pixel"""
        try:
            if not os.path.exists(pixel_upload_dir):
                log_step("google_photos_sync", f"Pixel upload directory not found: {pixel_upload_dir}", "warning")
                return []
            
            # Get all media files from Pixel upload directory
            media_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.mp4', '.mov', '.avi', '.mkv'}
            files_to_check = []
            
            for root, dirs, filenames in os.walk(pixel_upload_dir):
                for filename in filenames:
                    if Path(filename).suffix.lower() in media_extensions:
                        file_path = os.path.join(root, filename)
                        files_to_check.append(file_path)
            
            if not files_to_check:
                log_step("google_photos_sync", "No media files found in Pixel upload directory", "info")
                return []
            
            log_step("google_photos_sync", f"Found {len(files_to_check)} files to check", "info")
            
            # Check each file
            results = []
            for file_path in files_to_check:
                result = self.check_file_sync_status(file_path)
                results.append(result)
                
                # Log result
                status = "✅ SYNCED" if result['synced'] else "❌ NOT SYNCED"
                log_step("google_photos_sync", f"{status}: {result['filename']} - {result.get('reason', 'Unknown')}", 
                        "success" if result['synced'] else "warning")
            
            return results
            
        except Exception as e:
            log_step("google_photos_sync", f"Error checking Pixel uploaded files: {e}", "error")
            return []
    
    def generate_sync_report(self, results: List[Dict]) -> str:
        """Generate a sync status report"""
        if not results:
            return "No files checked."
        
        synced_count = sum(1 for r in results if r['synced'])
        total_count = len(results)
        sync_rate = (synced_count / total_count * 100) if total_count > 0 else 0
        
        report = f"""
Google Photos Sync Status Report
===============================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary:
- Total files checked: {total_count}
- Successfully synced: {synced_count}
- Not synced: {total_count - synced_count}
- Sync rate: {sync_rate:.1f}%

Detailed Results:
"""
        
        for result in results:
            status = "✅ SYNCED" if result['synced'] else "❌ NOT SYNCED"
            report += f"\n{status} {result['filename']}"
            if result['synced']:
                if 'google_photos_filename' in result:
                    report += f" (as {result['google_photos_filename']})"
                if 'creation_time' in result:
                    report += f" - Created: {result['creation_time']}"
            else:
                report += f" - {result.get('reason', 'Unknown reason')}"
        
        return report

def setup_google_photos_api():
    """Setup Google Photos API credentials"""
    checker = GooglePhotosSyncChecker()
    
    if not checker.load_credentials():
        print("Google Photos API setup required.")
        print("Please create a Google Cloud Project and enable the Photos Library API.")
        print("Then create credentials and save them to:", checker.credentials_file)
        print("\nExample credentials file format:")
        print(json.dumps({
            "client_id": "your_client_id.apps.googleusercontent.com",
            "client_secret": "your_client_secret"
        }, indent=2))
        return False
    
    print("Google Photos API credentials loaded.")
    print("To authenticate, visit this URL and get the authorization code:")
    print(checker.get_authorization_url())
    
    auth_code = input("Enter the authorization code: ").strip()
    
    if checker.exchange_code_for_tokens(auth_code):
        print("✅ Google Photos API authentication successful!")
        return True
    else:
        print("❌ Google Photos API authentication failed!")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup_google_photos_api()
        return
    
    # Check if we have valid credentials
    checker = GooglePhotosSyncChecker()
    if not checker.load_credentials() or not checker.load_tokens():
        print("Google Photos API not configured. Run with 'setup' argument first.")
        print("Usage: python3 google_photos_sync_checker.py setup")
        return
    
    # Get Pixel upload directory from config
    pixel_upload_dir = get_config_value('UPLOADED_PIXEL_DIR', '/mnt/wd_all_pictures/sync/uploaded/pixel')
    
    log_step("google_photos_sync", "Starting Google Photos sync check", "info")
    
    # Check all files
    results = checker.check_pixel_uploaded_files(pixel_upload_dir)
    
    # Generate and save report
    report = checker.generate_sync_report(results)
    
    # Save report to file
    report_file = f"/opt/media-pipeline/logs/google_photos_sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(report)
    print(f"\nReport saved to: {report_file}")
    
    # Log summary
    synced_count = sum(1 for r in results if r['synced'])
    total_count = len(results)
    sync_rate = (synced_count / total_count * 100) if total_count > 0 else 0
    
    log_step("google_photos_sync", f"Sync check completed: {synced_count}/{total_count} files synced ({sync_rate:.1f}%)", 
             "success" if sync_rate > 80 else "warning")

if __name__ == "__main__":
    main()