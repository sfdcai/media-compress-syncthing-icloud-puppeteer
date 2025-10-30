# Compression and Deduplication Guide

## 🎯 **Compression System Overview**

### **Compression Timing in Pipeline**
The compression happens **BEFORE** Pixel sync, not after. Here's the exact pipeline order:

```
1. Download Phase (iCloud + Local Folder)
2. Deduplication Phase (Remove duplicates)
3. Compression Phase (Compress images/videos) ← COMPRESSION HAPPENS HERE
4. File Preparation Phase (Organize for upload)
5. iCloud Upload Phase (Upload to iCloud)
6. Pixel Upload Phase (Sync to Google Photos) ← PIXEL SYNC HAPPENS HERE
7. Sorting Phase (Organize files)
8. Verification Phase (Quality check)
```

**Why compression happens before Pixel sync:**
- Reduces file sizes before upload (saves bandwidth and storage)
- Faster upload times to Google Photos
- More efficient storage usage
- Better performance during sync operations

### **Compression Options**

#### **Master Compression Toggle**
```env
ENABLE_COMPRESSION=true
```
- **Purpose**: Master switch for all compression features
- **Effect**: When `false`, no compression happens regardless of other settings

#### **Image Compression Toggle**
```env
ENABLE_IMAGE_COMPRESSION=true
```
- **Purpose**: Enable/disable image compression specifically
- **Supported Formats**: JPEG, PNG, HEIC, HEIF, BMP, TIFF, WebP
- **Effect**: When `false`, images are skipped during compression phase

#### **Video Compression Toggle**
```env
ENABLE_VIDEO_COMPRESSION=true
```
- **Purpose**: Enable/disable video compression specifically
- **Supported Formats**: MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V
- **Effect**: When `false`, videos are skipped during compression phase

### **Compression Settings**

#### **Image Compression**
```env
JPEG_QUALITY=90                    # Quality (1-100, higher = better quality)
INITIAL_RESIZE_PERCENTAGE=80       # First compression: 80% of original size
SUBSEQUENT_RESIZE_PERCENTAGE=90    # Re-compression: 90% of current size
COMPRESSION_INTERVAL_YEARS=2       # Re-compress files older than 2 years
```

#### **Video Compression**
```env
VIDEO_CRF=28                       # Constant Rate Factor (lower = better quality)
VIDEO_PRESET=fast                  # Encoding speed (ultrafast, fast, medium, slow)
INITIAL_VIDEO_RESOLUTION=1080      # First compression: 4K → 1080p
SUBSEQUENT_VIDEO_RESOLUTION=720    # Re-compression: 1080p → 720p
```

### **Progressive Compression Logic**

The system uses **progressive compression** with two tiers:

#### **Tier 1 (Initial Compression)**
- **Images**: Resize to 80% of original dimensions, JPEG quality 90
- **Videos**: Scale to 1080p resolution, CRF 28
- **Trigger**: When files are first processed

#### **Tier 2 (Subsequent Compression)**
- **Images**: Resize to 90% of current dimensions, JPEG quality 80
- **Videos**: Scale to 720p resolution, CRF 33
- **Trigger**: When files are older than 2 years

### **Compression Examples**

#### **Image Compression**
```
Original: IMG_001.jpg (5MB, 4000x3000)
Tier 1:   IMG_001.jpg (2MB, 3200x2400) - 60% reduction
Tier 2:   IMG_001.jpg (1.2MB, 2880x2160) - 76% total reduction
```

#### **Video Compression**
```
Original: VIDEO_001.mp4 (500MB, 4K)
Tier 1:   VIDEO_001.mp4 (150MB, 1080p) - 70% reduction
Tier 2:   VIDEO_001.mp4 (75MB, 720p) - 85% total reduction
```

---

## 🔍 **Deduplication System Overview**

### **How Deduplication Works**

#### **1. Hash Calculation**
- **Algorithm**: MD5 (configurable to SHA256)
- **Process**: Calculate hash of file content (not filename)
- **Database**: Store hash in `duplicate_files` table

#### **2. Duplicate Detection**
- **Method**: Compare file hashes against database
- **Logic**: If hash exists, file is considered duplicate
- **Tracking**: Original file ID and duplicate file ID stored

#### **3. File Management**
- **Original**: Keep first occurrence of file
- **Duplicates**: Move to `duplicates` directory
- **Naming**: Handle conflicts with counter (file_1.jpg, file_2.jpg)

### **Deduplication Configuration**

```env
ENABLE_DEDUPLICATION=true          # Enable/disable deduplication
DEDUPLICATION_HASH_ALGORITHM=md5   # Hash algorithm (md5 or sha256)
DEDUPLICATION_BATCH_SIZE=1000      # Process files in batches of 1000
```

### **Deduplication Process**

#### **Step 1: File Discovery**
```python
# Scan directory for media files
media_files = get_media_files(source_directory)
# Supported extensions: .jpg, .jpeg, .png, .heic, .heif, .mp4, .mov, .avi, .mkv
```

#### **Step 2: Hash Calculation**
```python
# Calculate file hash
file_hash = calculate_file_hash(file_path, "md5")
# Example: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

#### **Step 3: Duplicate Check**
```python
# Check if hash exists in database
if is_duplicate_file(file_hash):
    # This is a duplicate
    move_to_duplicates_directory(file_path)
else:
    # This is original
    log_duplicate_file(file_id, None, file_hash)
```

#### **Step 4: Database Tracking**
```sql
-- Store duplicate relationship
INSERT INTO duplicate_files (
    original_file_id,
    duplicate_file_id,
    file_hash,
    created_at
) VALUES (?, ?, ?, ?);
```

### **Deduplication Examples**

#### **Scenario 1: Identical Files**
```
File A: IMG_001.jpg (hash: abc123...)
File B: IMG_001_copy.jpg (hash: abc123...) ← DUPLICATE
Result: File A kept, File B moved to duplicates/
```

#### **Scenario 2: Different Names, Same Content**
```
File A: vacation_photo.jpg (hash: def456...)
File B: holiday_pic.jpg (hash: def456...) ← DUPLICATE
Result: File A kept, File B moved to duplicates/
```

#### **Scenario 3: Different Content**
```
File A: IMG_001.jpg (hash: abc123...)
File B: IMG_002.jpg (hash: xyz789...) ← NOT DUPLICATE
Result: Both files kept
```

### **Deduplication Statistics**

#### **Current Status**
- **Total Files Scanned**: 192 media files
- **Duplicates Found**: 0 (system ready but not yet run)
- **Space Saved**: 0 MB (no duplicates detected yet)

#### **Expected Results**
- **Typical Duplicate Rate**: 5-15% of files
- **Space Savings**: 10-30% of total storage
- **Processing Time**: ~1-2 seconds per file

---

## 📊 **System Status Overview**

### **Updated Database Status**

The system now shows **both database connections** with timestamps:

#### **Supabase Connection**
```json
{
  "supabase": {
    "connected": true,
    "error": null,
    "checked_at": "2025-10-03T09:29:35.553321",
    "tables": 1
  }
}
```

#### **Localhost SQL Connection**
```json
{
  "localhost_sql": {
    "connected": true,
    "error": null,
    "checked_at": "2025-10-03T09:29:35.553321",
    "tables": 192
  }
}
```

#### **Overall Database Status**
```json
{
  "connected": true,
  "timestamp": "2025-10-03T09:29:35.553321"
}
```

### **Service Status**

#### **Media Pipeline Service**
- **Status**: Stopped (needs PYTHONPATH fix)
- **Issue**: "No module named 'scripts'" error
- **Solution**: Service configuration needs update

#### **Syncthing Service**
- **Status**: Running
- **Purpose**: File synchronization to Google Photos
- **Access**: http://192.168.1.7:8384

#### **Storage Mount**
- **Status**: Mounted and accessible
- **Usage**: 52.38% (2.06TB used of 3.93TB total)
- **Free Space**: 1.87TB available

---

## 🔧 **Configuration Examples**

### **Disable Image Compression Only**
```env
ENABLE_COMPRESSION=true
ENABLE_IMAGE_COMPRESSION=false    # Images won't be compressed
ENABLE_VIDEO_COMPRESSION=true     # Videos will still be compressed
```

### **Disable Video Compression Only**
```env
ENABLE_COMPRESSION=true
ENABLE_IMAGE_COMPRESSION=true     # Images will be compressed
ENABLE_VIDEO_COMPRESSION=false   # Videos won't be compressed
```

### **Disable All Compression**
```env
ENABLE_COMPRESSION=false          # No compression at all
ENABLE_IMAGE_COMPRESSION=true     # These settings ignored
ENABLE_VIDEO_COMPRESSION=true    # These settings ignored
```

### **Enable Deduplication Only**
```env
ENABLE_COMPRESSION=false          # No compression
ENABLE_DEDUPLICATION=true        # Only deduplication
```

---

## 🚀 **Next Steps**

### **Immediate Actions**
1. **Fix Pipeline Service**: Resolve PYTHONPATH configuration
2. **Test Compression**: Run compression on existing files
3. **Test Deduplication**: Run deduplication to find duplicates
4. **Monitor Performance**: Use performance monitoring system

### **Testing Commands**
```bash
# Test compression
cd /opt/media-pipeline && PYTHONPATH=/opt/media-pipeline/scripts python3 scripts/compress_media.py

# Test deduplication
cd /opt/media-pipeline && PYTHONPATH=/opt/media-pipeline/scripts python3 scripts/deduplicate.py

# Check system status
curl -s http://192.168.1.7:5000/api/status | python3 -m json.tool
```

---

**Guide Generated**: October 3, 2025  
**System Status**: Compression and deduplication systems ready for testing  
**Next Review**: After pipeline service fix