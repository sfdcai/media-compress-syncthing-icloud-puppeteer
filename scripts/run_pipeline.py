#!/usr/bin/env python3
"""
Main pipeline orchestration script for media pipeline
Coordinates the entire workflow from download to organized storage
"""

import os
import sys
import time
from pathlib import Path
try:  # Allow running as package or standalone script
    from .utils import (
        log_step,
        validate_config,
        get_feature_toggle,
        ensure_directory_exists,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (  # type: ignore
        log_step,
        validate_config,
        get_feature_toggle,
        ensure_directory_exists,
    )

def setup_directories():
    """Setup required directories"""
    # Get base directory from environment
    base_dir = os.getenv("NAS_MOUNT", "/opt/media-pipeline")
    
    directories = [
        os.path.join(base_dir, "originals"),
        os.path.join(base_dir, "compressed"), 
        os.path.join(base_dir, "bridge/icloud"),
        os.path.join(base_dir, "bridge/pixel"),
        os.path.join(base_dir, "uploaded/icloud"),
        os.path.join(base_dir, "uploaded/pixel"),
        os.path.join(base_dir, "sorted/icloud"),
        os.path.join(base_dir, "sorted/pixel"),
        os.path.join(base_dir, "logs"),
        os.path.join(base_dir, "temp"),
        os.path.join(base_dir, "cleanup")
    ]
    
    for directory in directories:
        ensure_directory_exists(directory)
    
    log_step("pipeline", "Directory structure setup completed", "success")

def run_download():
    """Run download from iCloud"""
    log_step("pipeline", "Starting download phase", "info")
    
    try:
        from download_from_icloud import main as download_main
        download_main()
        log_step("pipeline", "Download phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"Download phase failed: {e}", "error")
        return False

def run_deduplication():
    """Run deduplication"""
    if not get_feature_toggle("ENABLE_DEDUPLICATION"):
        log_step("pipeline", "Deduplication is disabled, skipping", "info")
        return True
    
    log_step("pipeline", "Starting deduplication phase", "info")
    
    try:
        from deduplicate import main as dedupe_main
        dedupe_main()
        log_step("pipeline", "Deduplication phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"Deduplication phase failed: {e}", "error")
        return False

def run_compression():
    """Run compression"""
    if not get_feature_toggle("ENABLE_COMPRESSION"):
        log_step("pipeline", "Compression is disabled, skipping", "info")
        return True
    
    log_step("pipeline", "Starting compression phase", "info")
    
    try:
        from compress_media import main as compress_main
        compress_main()
        log_step("pipeline", "Compression phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"Compression phase failed: {e}", "error")
        return False

def run_file_preparation():
    """Run file preparation for uploads"""
    log_step("pipeline", "Starting file preparation phase", "info")
    
    try:
        from prepare_bridge_batch import main as file_main
        file_main()
        log_step("pipeline", "File preparation phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"File preparation phase failed: {e}", "error")
        return False

def run_icloud_upload():
    """Run iCloud upload"""
    if not get_feature_toggle("ENABLE_ICLOUD_UPLOAD"):
        log_step("pipeline", "iCloud upload is disabled, skipping", "info")
        return True
    
    log_step("pipeline", "Starting iCloud upload phase", "info")
    
    try:
        from upload_icloud import main as icloud_main
        icloud_main()
        log_step("pipeline", "iCloud upload phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"iCloud upload phase failed: {e}", "error")
        return False

def run_pixel_upload():
    """Run Pixel upload"""
    if not get_feature_toggle("ENABLE_PIXEL_UPLOAD"):
        log_step("pipeline", "Pixel upload is disabled, skipping", "info")
        return True
    
    log_step("pipeline", "Starting Pixel upload phase", "info")
    
    try:
        from sync_to_pixel import main as pixel_main
        pixel_main()
        log_step("pipeline", "Pixel upload phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"Pixel upload phase failed: {e}", "error")
        return False

def run_sorting():
    """Run post-upload sorting"""
    if not get_feature_toggle("ENABLE_SORTING"):
        log_step("pipeline", "Sorting is disabled, skipping", "info")
        return True
    
    log_step("pipeline", "Starting sorting phase", "info")
    
    try:
        from sort_uploaded import main as sort_main
        sort_main()
        log_step("pipeline", "Sorting phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"Sorting phase failed: {e}", "error")
        return False

def run_verification():
    """Run verification and cleanup"""
    log_step("pipeline", "Starting verification and cleanup phase", "info")
    
    try:
        from verify_and_cleanup import main as verify_main
        verify_main()
        log_step("pipeline", "Verification and cleanup phase completed", "success")
        return True
    except Exception as e:
        log_step("pipeline", f"Verification and cleanup phase failed: {e}", "error")
        return False

def generate_pipeline_report(start_time, end_time, phase_results):
    """Generate pipeline execution report"""
    try:
        report_dir = "logs"
        ensure_directory_exists(report_dir)
        
        report_file = os.path.join(report_dir, f"pipeline_report_{int(time.time())}.txt")
        
        with open(report_file, 'w') as f:
            f.write("Media Pipeline Execution Report\n")
            f.write("=" * 40 + "\n")
            f.write(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}\n")
            f.write(f"End Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}\n")
            f.write(f"Duration: {end_time - start_time:.2f} seconds\n\n")
            
            f.write("Phase Results:\n")
            f.write("-" * 20 + "\n")
            
            for phase, success in phase_results.items():
                status = "SUCCESS" if success else "FAILED"
                f.write(f"{phase}: {status}\n")
            
            f.write("\n")
            
            # Overall result
            overall_success = all(phase_results.values())
            f.write(f"Overall Result: {'SUCCESS' if overall_success else 'FAILED'}\n")
        
        log_step("pipeline", f"Pipeline report generated: {report_file}", "success")
        return True
        
    except Exception as e:
        log_step("pipeline", f"Error generating pipeline report: {e}", "error")
        return False

def main():
    """Main pipeline function"""
    start_time = time.time()
    
    log_step("pipeline", "Starting media pipeline", "info")
    
    # Validate configuration
    if not validate_config():
        log_step("pipeline", "Configuration validation failed", "error")
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Define pipeline phases
    phases = [
        ("Download", run_download),
        ("Deduplication", run_deduplication),
        ("Compression", run_compression),
        ("File Preparation", run_file_preparation),
        ("iCloud Upload", run_icloud_upload),
        ("Pixel Upload", run_pixel_upload),
        ("Sorting", run_sorting),
        ("Verification", run_verification)
    ]
    
    # Track phase results
    phase_results = {}
    
    # Run each phase
    for phase_name, phase_function in phases:
        log_step("pipeline", f"Starting {phase_name} phase", "info")
        
        try:
            success = phase_function()
            phase_results[phase_name] = success
            
            if not success:
                log_step("pipeline", f"{phase_name} phase failed, stopping pipeline", "error")
                break
                
        except Exception as e:
            log_step("pipeline", f"Unexpected error in {phase_name} phase: {e}", "error")
            phase_results[phase_name] = False
            break
    
    # Generate report
    end_time = time.time()
    generate_pipeline_report(start_time, end_time, phase_results)
    
    # Check overall success
    overall_success = all(phase_results.values())
    
    if overall_success:
        log_step("pipeline", "Media pipeline completed successfully", "success")
        sys.exit(0)
    else:
        log_step("pipeline", "Media pipeline failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
