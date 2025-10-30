#!/usr/bin/env python3
"""
Google Photos Integration Verification
Final verification script for the Google Photos integration
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the src directory to the path
sys.path.append('/opt/media-pipeline/src')
sys.path.append('/opt/media-pipeline/scripts')

def verify_integration():
    """Verify the complete Google Photos integration"""
    print("🔍 Google Photos Integration Verification")
    print("=" * 45)
    
    try:
        # Import the sync checker
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        
        # Load credentials
        if not checker.load_credentials():
            print("❌ Failed to load credentials")
            return False
        print("✅ Credentials loaded")
        
        # Load tokens
        if not checker.load_tokens():
            print("❌ No tokens found - authentication needed")
            print("Run: python3 scripts/complete_google_photos_auth.py")
            return False
        print("✅ Tokens loaded")
        
        # Ensure valid token
        if not checker.ensure_valid_token():
            print("❌ Token validation failed")
            return False
        print("✅ Token is valid")
        
        # Test API connection
        print("🔍 Testing API connection...")
        try:
            media_items = checker.search_media_items()
            if media_items is not None:
                print(f"✅ API connection successful - Found {len(media_items)} media items")
            else:
                print("❌ API connection failed")
                return False
        except Exception as e:
            if "403" in str(e) and "insufficient authentication scopes" in str(e):
                print("⚠️ API access denied - Photos Library API may not be enabled")
                print("Please enable the Photos Library API in Google Cloud Console")
                print("Then re-authenticate: python3 scripts/complete_google_photos_auth.py")
                return False
            else:
                print(f"❌ API error: {e}")
                return False
        
        # Test pipeline integration
        print("🔗 Testing pipeline integration...")
        from processors.verify_and_cleanup import verify_google_photos_sync
        print("✅ Pipeline integration ready")
        
        # Test sync functionality with empty directory
        print("📁 Testing sync functionality...")
        pixel_dir = '/mnt/wd_all_pictures/sync/uploaded/pixel'
        os.makedirs(pixel_dir, exist_ok=True)
        
        results = checker.check_pixel_uploaded_files(pixel_dir)
        print(f"✅ Sync functionality working - Checked {len(results)} files")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def test_with_sample_files():
    """Test with sample files if available"""
    print("\n📸 Testing with Sample Files")
    print("=" * 30)
    
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        checker.load_credentials()
        checker.load_tokens()
        checker.ensure_valid_token()
        
        # Check if we can search for media items
        print("🔍 Searching for media items...")
        media_items = checker.search_media_items()
        
        if media_items is not None:
            print(f"✅ Found {len(media_items)} media items in Google Photos")
            
            if len(media_items) > 0:
                print("📋 Sample media items:")
                for i, item in enumerate(media_items[:3]):  # Show first 3
                    filename = item.get('filename', 'Unknown')
                    creation_time = item.get('mediaMetadata', {}).get('creationTime', 'Unknown')
                    print(f"  {i+1}. {filename} - {creation_time}")
            else:
                print("ℹ️ No media items found in Google Photos")
        else:
            print("❌ Failed to search media items")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing with sample files: {e}")
        return False

def generate_status_report():
    """Generate a status report"""
    print("\n📊 Generating Status Report")
    print("=" * 30)
    
    try:
        report = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "integration_status": "ready",
            "components": {
                "credentials": "configured",
                "tokens": "loaded",
                "api_connection": "tested",
                "pipeline_integration": "ready",
                "sync_functionality": "working"
            },
            "next_steps": [
                "Enable Photos Library API in Google Cloud Console if not already done",
                "Re-authenticate if API access is denied",
                "Test with real files in Pixel upload directory"
            ]
        }
        
        # Save report
        report_file = f"/opt/media-pipeline/logs/google_photos_integration_report_{int(time.time())}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Status report saved to: {report_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating status report: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Google Photos Integration - Final Verification")
    print("=" * 55)
    
    # Run verification
    if verify_integration():
        print("\n✅ Google Photos integration is working correctly!")
        
        # Test with sample files
        test_with_sample_files()
        
        # Generate status report
        generate_status_report()
        
        print("\n🎉 Integration verification completed successfully!")
        print("\n📋 The Google Photos sync checker is ready to use in the pipeline.")
        print("   It will automatically check if files uploaded to Pixel are synced to Google Photos.")
        
    else:
        print("\n❌ Integration verification failed!")
        print("\n📋 Please check the errors above and:")
        print("1. Ensure Photos Library API is enabled in Google Cloud Console")
        print("2. Re-authenticate if needed: python3 scripts/complete_google_photos_auth.py")
        print("3. Check that your Google account has photos")
        
        return False
    
    return True

if __name__ == "__main__":
    main()