#!/usr/bin/env python3
"""
Complete Pixel sync workflow - prepare files and monitor sync status
"""

import os
import sys
import time
from dotenv import load_dotenv
from utils.utils import log_step

# Load environment variables
load_dotenv("config/settings.env")

def run_pixel_sync_workflow():
    """Run the complete Pixel sync workflow"""
    print("=== Pixel Sync Workflow ===")
    
    # Step 1: Prepare files for sync
    print("\nStep 1: Preparing files for Pixel sync...")
    try:
        from prepare_pixel_sync import prepare_pixel_sync
        prep_success = prepare_pixel_sync()
        
        if not prep_success:
            print("✗ File preparation failed")
            return False
        
        print("✓ Files prepared successfully")
        
    except Exception as e:
        print(f"✗ File preparation error: {e}")
        log_step("pixel_sync_workflow", f"File preparation failed: {e}", "error")
        return False
    
    # Step 2: Wait a moment for files to be copied
    print("\nStep 2: Waiting for file system sync...")
    time.sleep(5)
    
    # Step 3: Monitor sync status
    print("\nStep 3: Monitoring Syncthing sync...")
    try:
        from monitor_syncthing_sync import monitor_pixel_sync, check_synced_files
        
        # Monitor sync status
        sync_success = monitor_pixel_sync()
        
        if not sync_success:
            print("⚠ Sync monitoring failed or incomplete")
            # Continue to check files anyway
        
        # Check synced files
        synced_count, unsynced_count = check_synced_files()
        
        print(f"\n=== Sync Results ===")
        print(f"Files synced: {synced_count}")
        print(f"Files pending: {unsynced_count}")
        
        if synced_count > 0 and unsynced_count == 0:
            print("✓ All files successfully synced")
            log_step("pixel_sync_workflow", f"Successfully synced {synced_count} files", "success")
            return True
        elif synced_count > 0:
            print(f"⚠ Partial sync: {synced_count} synced, {unsynced_count} pending")
            log_step("pixel_sync_workflow", f"Partial sync: {synced_count}/{synced_count + unsynced_count} files", "warning")
            return False
        else:
            print("✗ No files were synced")
            log_step("pixel_sync_workflow", "No files were synced", "error")
            return False
        
    except Exception as e:
        print(f"✗ Sync monitoring error: {e}")
        log_step("pixel_sync_workflow", f"Sync monitoring failed: {e}", "error")
        return False

def main():
    """Main function"""
    print("Starting Pixel sync workflow...")
    
    try:
        success = run_pixel_sync_workflow()
        
        if success:
            print("\n✓ Pixel sync workflow completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Pixel sync workflow failed or incomplete")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        log_step("pixel_sync_workflow", f"Workflow failed: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
