#!/usr/bin/env python3
"""
Run Google Photos sync check and fix database schema issues
"""

import sys
import os
sys.path.append('/opt/media-pipeline/src')
sys.path.append('/opt/media-pipeline/scripts')

def fix_database_schema():
    """Fix database schema by adding missing columns"""
    print("🔧 Fixing database schema...")
    
    try:
        from core.local_db_manager import get_db_manager
        db = get_db_manager()
        
        # Add missing columns
        tables = ['media_files', 'batches', 'pipeline_logs']
        
        for table in tables:
            try:
                db._execute_query(f'ALTER TABLE {table} ADD COLUMN synced_to_supabase BOOLEAN DEFAULT FALSE')
                print(f"✅ Added synced_to_supabase column to {table}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"✅ Column already exists in {table}")
                else:
                    print(f"❌ Error with {table}: {e}")
        
        # Test the queries
        print("\n🧪 Testing database queries...")
        try:
            result = db._execute_query('SELECT COUNT(*) as count FROM media_files WHERE synced_to_supabase = FALSE', fetch=True)
            print(f"✅ Found {result[0]['count']} unsynced media files")
        except Exception as e:
            print(f"❌ Error querying media_files: {e}")
        
        try:
            result = db._execute_query('SELECT COUNT(*) as count FROM batches WHERE synced_to_supabase = FALSE', fetch=True)
            print(f"✅ Found {result[0]['count']} unsynced batches")
        except Exception as e:
            print(f"❌ Error querying batches: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False

def run_google_photos_sync():
    """Run Google Photos sync check"""
    print("\n🔍 Running Google Photos sync check...")
    
    try:
        from google_photos_sync_checker import GooglePhotosSyncChecker
        checker = GooglePhotosSyncChecker()
        
        # Load credentials and tokens
        if not checker.load_credentials():
            print('❌ Failed to load credentials')
            return False
            
        if not checker.load_tokens():
            print('❌ Failed to load tokens')
            return False
            
        if not checker.ensure_valid_token():
            print('❌ Token validation failed')
            return False
            
        print('✅ Google Photos API ready')
        
        # Check for files in Pixel upload directory
        pixel_dir = '/opt/media-pipeline/data/pixel_upload'
        if not os.path.exists(pixel_dir):
            print(f"📁 Creating Pixel upload directory: {pixel_dir}")
            os.makedirs(pixel_dir, exist_ok=True)
        
        files = [f for f in os.listdir(pixel_dir) if os.path.isfile(os.path.join(pixel_dir, f))]
        print(f"📁 Found {len(files)} files in Pixel upload directory")
        
        if files:
            print("Files:")
            for f in files[:5]:  # Show first 5 files
                print(f"  - {f}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more files")
            
            # Check sync status for each file
            print("\n🔍 Checking sync status for files...")
            synced_count = 0
            for file in files[:3]:  # Check first 3 files
                file_path = os.path.join(pixel_dir, file)
                try:
                    is_synced = checker.check_file_sync_status(file_path)
                    if is_synced:
                        synced_count += 1
                        print(f"✅ {file} - Synced to Google Photos")
                    else:
                        print(f"❌ {file} - Not synced to Google Photos")
                except Exception as e:
                    print(f"⚠️ {file} - Error checking sync: {e}")
            
            print(f"\n📊 Sync Summary: {synced_count}/{min(3, len(files))} files checked are synced")
        else:
            print("📁 No files found in Pixel upload directory")
            print("💡 To test Google Photos sync, add some media files to the Pixel upload directory")
        
        return True
        
    except Exception as e:
        print(f"❌ Error running Google Photos sync: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Google Photos Sync Check and Database Fix")
    print("=" * 50)
    
    # Fix database schema first
    if not fix_database_schema():
        print("❌ Database schema fix failed")
        return False
    
    # Run Google Photos sync check
    if not run_google_photos_sync():
        print("❌ Google Photos sync check failed")
        return False
    
    print("\n🎉 All operations completed successfully!")
    return True

if __name__ == "__main__":
    main()