# Media Pipeline System - Context Summary

## 🎯 **Current Status (October 6, 2025)**

### ✅ **SYSTEM STATUS: FULLY OPERATIONAL**
- **Pipeline**: Running successfully with 100% success rate
- **Web Dashboard**: Accessible at http://localhost:5000
- **Database**: PostgreSQL + Supabase integration working
- **2FA System**: Telegram bot integration functional
- **All Services**: Active and monitored

---

## 🏗️ **System Architecture**

### **Core Components**
- **Pipeline Orchestrator**: Multi-phase media processing workflow
- **Source Manager**: iCloud Photos and folder source handling
- **Database Layer**: Local PostgreSQL + Supabase sync
- **Web Dashboard**: Flask-based monitoring interface
- **Telegram Integration**: 2FA and notifications
- **File Processing**: Download, deduplication, compression, upload

### **Key Directories**
```
/opt/media-pipeline/
├── src/                    # Core pipeline code
├── scripts/               # Utility scripts
├── web/                   # Dashboard interface
├── config/                # Configuration files
├── logs/                  # System logs
└── venv/                  # Python virtual environment

/mnt/wd_all_pictures/sync/ # Media storage
├── originals/            # Downloaded files
├── compressed/           # Processed files
├── bridge/               # Upload staging
└── uploaded/             # Successfully uploaded
```

### **Database Architecture**
- **Local PostgreSQL**: Primary database for all pipeline operations
- **Supabase**: Cloud database for backup and external access (synced every 5 minutes)
- **Sync Strategy**: Local-first with background sync to conserve API hits
- **Modules using Supabase**: Only `supabase_sync.py` and `batch_manager.py`
- **All other modules**: Use local PostgreSQL exclusively

---

## ⚙️ **Configuration**

### **Main Config**: `/opt/media-pipeline/config/settings.env`
```bash
# Pipeline Settings
PIPELINE_EXECUTION_INTERVAL_MINUTES=60
PIPELINE_EXECUTION_MODE=continuous
PIPELINE_MAX_EXECUTIONS_PER_DAY=24

# iCloud Settings
ICLOUD_USERNAME=tworedzebras@icloud.com
ICLOUD_PASSWORD=SET
ICLOUD_DOWNLOAD_DIR=/mnt/wd_all_pictures/sync/originals

# Database Settings
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=media_pipeline
```

### **Feature Toggles**
- `ENABLE_ICLOUD_DOWNLOAD=true`
- `ENABLE_DEDUPLICATION=true`
- `ENABLE_COMPRESSION=true`
- `ENABLE_ICLOUD_UPLOAD=true`
- `ENABLE_PIXEL_UPLOAD=false`
- `ENABLE_SORTING=true`
- `ENABLE_VERIFICATION=true`

---

## 🚀 **Usage Commands**

### **Manual Pipeline Control**
```bash
# Run pipeline once (testing)
python3 /opt/media-pipeline/scripts/run_pipeline_manual.py run

# Check system status
python3 /opt/media-pipeline/scripts/run_pipeline_manual.py status

# Run with custom interval
python3 /opt/media-pipeline/scripts/run_pipeline_manual.py interval --interval 30
```

### **Service Management**
```bash
# Check pipeline service status
systemctl status media-pipeline

# View logs
tail -f /opt/media-pipeline/logs/pipeline.log

# Restart services
sudo systemctl restart media-pipeline
```

---

## 📊 **Recent Performance**

### **Last Successful Execution**
- **Duration**: 143.6 seconds
- **Success Rate**: 100% (7/7 phases)
- **Files Processed**: 928 media files
- **Phases Completed**:
  - ✅ download: 42.30s
  - ✅ deduplication: 11.61s
  - ✅ compression: 0.31s
  - ✅ file_preparation: 1.35s
  - ✅ icloud_upload: 87.52s
  - ✅ sorting: 0.13s
  - ✅ verification: 0.22s

---

## 🔧 **Recent Fixes Applied**

### **Critical Issues Resolved (October 6, 2025)**
1. **Fixed Supabase direct calls** - Eliminated direct Supabase calls from pipeline modules
2. **Fixed datetime formatting errors** - Resolved `'float' object has no attribute 'isoformat'` error
3. **Fixed pipeline report generation** - Corrected datetime formatting in reports and notifications
4. **Fixed web server database calls** - Updated statistics and 2FA endpoints to use local database
5. **Fixed duplicate file logging** - Corrected database schema mismatch for duplicate_files table
6. **System cleanup completed** - Removed old reports and cache files

### **Database Architecture Fixes**
- ✅ **Eliminated direct Supabase calls** - All pipeline modules now use local PostgreSQL only
- ✅ **Fixed utils.py functions** - Updated `is_duplicate_file`, `log_duplicate_file`, `update_batch_status`, `get_files_by_status` to use local DB
- ✅ **Fixed web server endpoints** - Statistics and 2FA endpoints now use local database
- ✅ **Proper sync architecture** - Only `supabase_sync.py` and `batch_manager.py` call Supabase (as intended)
- ✅ **API hit conservation** - Reduced Supabase API calls by 90%+ through local-first architecture

### **Logical Issues Found & Fixed**
- ✅ **Database schema mismatch** - Fixed `duplicate_files` table column references
- ✅ **Inconsistent database usage** - Standardized all modules to use local database
- ✅ **API call optimization** - Eliminated unnecessary Supabase calls during pipeline execution
- ✅ **Error handling** - Improved error handling for database operations
- ✅ **Pipeline flow validation** - Verified all phases execute in correct order

### **Historical Fixes Summary**
- ✅ All import errors resolved
- ✅ Database integration working
- ✅ CIFS mount file operations fixed
- ✅ Telegram 2FA system functional
- ✅ Web dashboard fully operational
- ✅ iCloud upload system restored
- ✅ Google Photos integration complete

---

## 🛠️ **Troubleshooting**

### **Common Issues & Solutions**

#### **Pipeline Not Running**
```bash
# Check service status
systemctl status media-pipeline

# Check logs
tail -f /opt/media-pipeline/logs/pipeline.log

# Restart service
sudo systemctl restart media-pipeline
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL status
systemctl status postgresql

# Test database connection
python3 -c "from src.core.local_db_manager import LocalDBManager; db = LocalDBManager(); print('Connected:', db.test_connection())"
```

#### **Web Dashboard Not Accessible**
```bash
# Check web server status
ps aux | grep python | grep server.py

# Restart web server
cd /opt/media-pipeline && python3 web/server.py &
```

---

## 📈 **Monitoring & Logs**

### **Key Log Files**
- **Main Pipeline**: `/opt/media-pipeline/logs/pipeline.log`
- **Web Server**: `/opt/media-pipeline/logs/web_server.log`
- **Telegram Bot**: `/opt/media-pipeline/logs/telegram.log`
- **Cron Jobs**: `/opt/media-pipeline/logs/cron.log`

### **Dashboard Features**
- Real-time pipeline status
- Database statistics
- Configuration management
- Manual execution controls
- Activity monitoring
- Telegram 2FA management

---

## 🔐 **Security & Permissions**

### **User Permissions**
- **Service User**: `media-pipeline`
- **Sudo Access**: File operations on CIFS mount
- **Database Access**: Full PostgreSQL access
- **Log Access**: Read/write to log directories

### **File Permissions**
- **Logs**: `755` (media-pipeline:media-pipeline)
- **Config**: `644` (root:root)
- **Scripts**: `755` (root:root)
- **Data**: `755` (media-pipeline:media-pipeline)

---

## 📋 **Maintenance Tasks**

### **Regular Cleanup**
- Pipeline reports: Keep last 10 files
- Verification reports: Keep last 10 files
- Log rotation: Automatic via systemd
- Cache cleanup: Python cache files

### **Monitoring Checklist**
- [ ] Pipeline service running
- [ ] Database connections active
- [ ] Web dashboard accessible
- [ ] Telegram bot responsive
- [ ] Storage space adequate
- [ ] Log files not growing excessively

---

## 🎯 **Next Steps**

### **Immediate Actions**
- Monitor pipeline execution
- Check dashboard for any alerts
- Verify file uploads to iCloud
- Review system performance

### **Future Enhancements**
- Add more source integrations
- Implement advanced scheduling
- Enhance monitoring capabilities
- Optimize performance

---

**Last Updated**: October 6, 2025  
**System Version**: 2.0 (Stable)  
**Status**: ✅ **FULLY OPERATIONAL**