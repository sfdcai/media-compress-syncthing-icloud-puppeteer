#!/usr/bin/env python3
"""
Enhanced media compression script with OptimalStorage progressive compression logic
Supports both images and videos with database tracking
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from PIL import Image
try:  # Allow running both as part of package and as standalone script
    from .utils import (
        log_step,
        get_file_size_gb,
        ensure_directory_exists,
        get_feature_toggle,
        retry,
        calculate_file_hash,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from utils import (  # type: ignore
        log_step,
        get_file_size_gb,
        ensure_directory_exists,
        get_feature_toggle,
        retry,
        calculate_file_hash,
    )

# Configuration
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 85))
VIDEO_CRF = os.getenv("VIDEO_CRF", "28")
VIDEO_PRESET = os.getenv("VIDEO_PRESET", "fast")
COMPRESSION_INTERVAL_YEARS = int(os.getenv("COMPRESSION_INTERVAL_YEARS", 2))
INITIAL_RESIZE_PERCENTAGE = int(os.getenv("INITIAL_RESIZE_PERCENTAGE", 80))
SUBSEQUENT_RESIZE_PERCENTAGE = int(os.getenv("SUBSEQUENT_RESIZE_PERCENTAGE", 90))
INITIAL_VIDEO_RESOLUTION = int(os.getenv("INITIAL_VIDEO_RESOLUTION", 1080))
SUBSEQUENT_VIDEO_RESOLUTION = int(os.getenv("SUBSEQUENT_VIDEO_RESOLUTION", 720))
MAX_FILES_TO_PROCESS = int(os.getenv("MAX_FILES_TO_PROCESS", 10))

def get_file_age_in_years(file_path):
    """Get file age in years based on modification time"""
    try:
        file_stat = os.stat(file_path)
        file_age_days = (time.time() - file_stat.st_mtime) / (365.25 * 24 * 3600)
        return int(file_age_days)
    except Exception as e:
        log_step("file_age", f"Failed to get age for {file_path}: {e}", "error")
        return 0

def is_image_file(file_path):
    """Check if file is an image"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.bmp', '.tiff', '.webp'}
    return Path(file_path).suffix.lower() in image_extensions

def is_video_file(file_path):
    """Check if file is a video"""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    return Path(file_path).suffix.lower() in video_extensions

@retry(max_attempts=3, delay=5)
def compress_image_progressive(src, dst, is_initial=True):
    """Compress image with progressive compression logic"""
    try:
        # Open image
        img = Image.open(src)
        original_size = get_file_size_gb(src)
        
        # Determine compression parameters
        if is_initial:
            # First compression: reduce resolution
            new_width = int(img.width * (INITIAL_RESIZE_PERCENTAGE / 100))
            new_height = int(img.height * (INITIAL_RESIZE_PERCENTAGE / 100))
            quality = JPEG_QUALITY
        else:
            # Subsequent compression: further reduce resolution
            new_width = int(img.width * (SUBSEQUENT_RESIZE_PERCENTAGE / 100))
            new_height = int(img.height * (SUBSEQUENT_RESIZE_PERCENTAGE / 100))
            quality = max(JPEG_QUALITY - 10, 60)  # Reduce quality further
        
        # Resize image
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save with compression
        img_resized.save(dst, "JPEG", quality=quality, optimize=True)
        
        # Calculate compression ratio
        compressed_size = get_file_size_gb(dst)
        compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
        
        log_step("compress_image", f"Compressed {src} -> {dst} ({compression_ratio:.1f}% reduction)", "success")
        return True, compression_ratio
        
    except Exception as e:
        log_step("compress_image", f"Failed to compress {src}: {e}", "error")
        return False, 0

@retry(max_attempts=3, delay=5)
def compress_video_progressive(src, dst, is_initial=True):
    """Compress video with progressive compression logic"""
    try:
        original_size = get_file_size_gb(src)
        
        # Determine compression parameters
        if is_initial:
            # First compression: 4K to 1080p
            scale = f"1920:{INITIAL_VIDEO_RESOLUTION}"
            crf = VIDEO_CRF
        else:
            # Subsequent compression: 1080p to 720p
            scale = f"1280:{SUBSEQUENT_VIDEO_RESOLUTION}"
            crf = str(int(VIDEO_CRF) + 5)  # Increase CRF for more compression
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-vf", f"scale={scale}",
            "-c:v", "libx264",
            "-preset", VIDEO_PRESET,
            "-crf", crf,
            "-c:a", "aac",
            "-b:a", "128k",
            dst
        ]
        
        # Run compression
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Calculate compression ratio
        compressed_size = get_file_size_gb(dst)
        compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
        
        log_step("compress_video", f"Compressed {src} -> {dst} ({compression_ratio:.1f}% reduction)", "success")
        return True, compression_ratio
        
    except subprocess.CalledProcessError as e:
        log_step("compress_video", f"FFmpeg failed for {src}: {e.stderr}", "error")
        return False, 0
    except Exception as e:
        log_step("compress_video", f"Failed to compress {src}: {e}", "error")
        return False, 0

def should_recompress(file_path):
    """Determine if file should be recompressed based on age"""
    file_age_years = get_file_age_in_years(file_path)
    return file_age_years >= COMPRESSION_INTERVAL_YEARS

def process_media_file(file_path, output_dir, is_initial=True):
    """Process a single media file for compression"""
    try:
        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)
        
        # Check if file should be recompressed
        if not is_initial and not should_recompress(file_path):
            log_step("compression", f"File {filename} does not need recompression yet", "info")
            return False
        
        # Determine compression type
        if is_image_file(file_path):
            success, compression_ratio = compress_image_progressive(file_path, output_path, is_initial)
        elif is_video_file(file_path):
            success, compression_ratio = compress_video_progressive(file_path, output_path, is_initial)
        else:
            log_step("compression", f"Unsupported file type: {filename}", "warning")
            return False
        
        if success:
            # Calculate file hash for tracking
            file_hash = calculate_file_hash(output_path)
            
            # Log compression details
            log_step("compression", f"Successfully compressed {filename} with {compression_ratio:.1f}% reduction", "success")
            return True
        else:
            return False
            
    except Exception as e:
        log_step("compression", f"Error processing {file_path}: {e}", "error")
        return False

def compress_directory(source_dir, output_dir, max_files=None):
    """Compress all media files in a directory"""
    if not os.path.exists(source_dir):
        log_step("compression", f"Source directory {source_dir} does not exist", "error")
        return False
    
    # Create output directory
    ensure_directory_exists(output_dir)
    
    log_step("compression", f"Starting compression of {source_dir}", "info")
    
    # Get all media files
    media_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if is_image_file(file_path) or is_video_file(file_path):
                media_files.append(file_path)
    
    if not media_files:
        log_step("compression", "No media files found to compress", "info")
        return True
    
    # Limit files to process
    if max_files:
        media_files = media_files[:max_files]
    
    total_files = len(media_files)
    log_step("compression", f"Found {total_files} files to compress", "info")
    
    # Process files
    processed = 0
    successful = 0
    errors = 0
    
    for i, file_path in enumerate(media_files, 1):
        log_step("compression", f"Processing file {i}/{total_files}: {os.path.basename(file_path)}", "info")
        
        if process_media_file(file_path, output_dir, is_initial=True):
            successful += 1
        else:
            errors += 1
        
        processed += 1
        
        # Log progress every 10 files
        if i % 10 == 0:
            progress = (i / total_files) * 100
            log_step("compression", f"Progress: {progress:.1f}% ({i}/{total_files})", "info")
    
    # Summary
    log_step("compression", f"Compression completed: {successful} successful, {errors} errors out of {processed} files", "success")
    return True

def main():
    """Main compression function"""
    if not get_feature_toggle("ENABLE_COMPRESSION"):
        log_step("compression", "Compression is disabled, skipping", "info")
        return
    
    # Get configuration
    source_dir = os.getenv("ORIGINALS_DIR", "originals")
    output_dir = os.getenv("COMPRESSED_DIR", "compressed")
    max_files = int(os.getenv("MAX_FILES_TO_PROCESS", "10"))
    
    # Validate source directory
    if not os.path.exists(source_dir):
        log_step("compression", f"Source directory {source_dir} does not exist", "error")
        return
    
    # Run compression
    success = compress_directory(
        source_dir=source_dir,
        output_dir=output_dir,
        max_files=max_files
    )
    
    if success:
        log_step("compression", "Compression completed successfully", "success")
    else:
        log_step("compression", "Compression failed", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
