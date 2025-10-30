#!/usr/bin/env python3
"""
Source Manager for Media Pipeline
Coordinates between different media sources (iCloud, folder, etc.)
"""

import os
import sys
from utils.utils import (
    log_step, validate_config, get_feature_toggle,
    get_config_value, ensure_directory_exists
)

class SourceManager:
    """Manages different media sources for the pipeline"""
    
    def __init__(self):
        self.sources = []
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize available sources based on configuration"""
        # Check iCloud source
        if get_feature_toggle("ENABLE_ICLOUD_DOWNLOAD"):
            self.sources.append({
                'type': 'icloud',
                'name': 'iCloud Photos',
                'enabled': True,
                'script': 'download_from_icloud',
                'description': 'Download photos and videos from iCloud'
            })
        
        # Check folder source
        if get_feature_toggle("ENABLE_FOLDER_DOWNLOAD"):
            self.sources.append({
                'type': 'folder',
                'name': 'Local Folder',
                'enabled': True,
                'script': 'folder_download',
                'description': 'Process media files from local folder'
            })
    
    def get_enabled_sources(self):
        """Get list of enabled sources"""
        return [source for source in self.sources if source['enabled']]
    
    def get_source_by_type(self, source_type):
        """Get source configuration by type"""
        for source in self.sources:
            if source['type'] == source_type:
                return source
        return None
    
    def setup_source_directories(self):
        """Setup directories for all enabled sources"""
        log_step("source_manager", "Setting up source directories", "info")
        
        # Base directories
        base_dir = get_config_value("NAS_MOUNT", "/mnt/wd_all_pictures/sync")
        
        directories = [
            os.path.join(base_dir, "originals"),
            os.path.join(base_dir, "compressed"),
            os.path.join(base_dir, "logs"),
            os.path.join(base_dir, "temp"),
            os.path.join(base_dir, "cleanup")
        ]
        
        # Source-specific directories
        for source in self.get_enabled_sources():
            source_type = source['type']
            
            # Bridge directories
            directories.extend([
                os.path.join(base_dir, f"bridge/{source_type}"),
                os.path.join(base_dir, f"uploaded/{source_type}"),
                os.path.join(base_dir, f"sorted/{source_type}")
            ])
        
        # Create all directories
        for directory in directories:
            ensure_directory_exists(directory)
        
        log_step("source_manager", f"Created {len(directories)} directories", "success")
    
    def validate_source_configurations(self):
        """Validate configurations for all enabled sources"""
        log_step("source_manager", "Validating source configurations", "info")
        
        validation_results = {}
        
        for source in self.get_enabled_sources():
            source_type = source['type']
            validation_results[source_type] = self._validate_source_config(source_type)
        
        # Log results
        for source_type, is_valid in validation_results.items():
            status = "valid" if is_valid else "invalid"
            log_step("source_manager", f"Source {source_type}: {status}", "info" if is_valid else "error")
        
        return all(validation_results.values())
    
    def _validate_source_config(self, source_type):
        """Validate configuration for a specific source type"""
        if source_type == 'icloud':
            return self._validate_icloud_config()
        elif source_type == 'folder':
            return self._validate_folder_config()
        else:
            log_step("source_manager", f"Unknown source type: {source_type}", "error")
            return False
    
    def _validate_icloud_config(self):
        """Validate iCloud configuration"""
        required_configs = [
            'ICLOUD_USERNAME',
            'ICLOUD_PASSWORD'
        ]
        
        for config in required_configs:
            if not get_config_value(config):
                log_step("source_manager", f"Missing iCloud config: {config}", "error")
                return False
        
        return True
    
    def _validate_folder_config(self):
        """Validate folder source configuration"""
        source_path = get_config_value("FOLDER_SOURCE_PATH")
        
        if not source_path:
            log_step("source_manager", "Missing folder source path configuration", "error")
            return False
        
        if not os.path.exists(source_path):
            log_step("source_manager", f"Folder source path does not exist: {source_path}", "error")
            return False
        
        return True
    
    def get_source_statistics(self):
        """Get statistics for all enabled sources"""
        stats = {}
        
        for source in self.get_enabled_sources():
            source_type = source['type']
            stats[source_type] = self._get_source_stats(source_type)
        
        return stats
    
    def _get_source_stats(self, source_type):
        """Get statistics for a specific source"""
        try:
            from local_db_manager import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get file count
            cursor.execute("""
                SELECT COUNT(*) FROM media_files 
                WHERE source_type = %s
            """, (source_type,))
            file_count = cursor.fetchone()[0]
            
            # Get total size
            cursor.execute("""
                SELECT COALESCE(SUM(file_size), 0) FROM media_files 
                WHERE source_type = %s
            """, (source_type,))
            total_size = cursor.fetchone()[0]
            
            # Get processed count
            cursor.execute("""
                SELECT COUNT(*) FROM media_files 
                WHERE source_type = %s AND processed = true
            """, (source_type,))
            processed_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                'file_count': file_count,
                'total_size': total_size,
                'processed_count': processed_count,
                'pending_count': file_count - processed_count
            }
            
        except Exception as e:
            log_step("source_manager", f"Error getting stats for {source_type}: {e}", "error")
            return {
                'file_count': 0,
                'total_size': 0,
                'processed_count': 0,
                'pending_count': 0
            }
    
    def run_source_download(self, source_type):
        """Run download for a specific source"""
        source = self.get_source_by_type(source_type)
        
        if not source:
            log_step("source_manager", f"Source not found: {source_type}", "error")
            return False
        
        if not source['enabled']:
            log_step("source_manager", f"Source is disabled: {source_type}", "info")
            return True
        
        log_step("source_manager", f"Running download for {source['name']}", "info")
        
        try:
            # Import and run the appropriate script
            script_name = source['script']
            
            if source_type == 'icloud':
                from processors.download_from_icloud import main
                result = main()
            elif source_type == 'folder':
                from processors.folder_download import main
                result = main()
            else:
                log_step("source_manager", f"Unknown source type: {source_type}", "error")
                return False
            
            log_step("source_manager", f"Download completed for {source['name']}", "success" if result else "error")
            return result
                
        except Exception as e:
            log_step("source_manager", f"Error running download for {source_type}: {e}", "error")
            return False
    
    def run_all_source_downloads(self):
        """Run downloads for all enabled sources"""
        log_step("source_manager", "Running downloads for all enabled sources", "info")
        
        results = {}
        
        for source in self.get_enabled_sources():
            source_type = source['type']
            results[source_type] = self.run_source_download(source_type)
        
        # Log overall results
        successful_sources = [source_type for source_type, success in results.items() if success]
        failed_sources = [source_type for source_type, success in results.items() if not success]
        
        if successful_sources:
            log_step("source_manager", f"Successful sources: {', '.join(successful_sources)}", "success")
        
        if failed_sources:
            log_step("source_manager", f"Failed sources: {', '.join(failed_sources)}", "error")
        
        return all(results.values())

def main():
    """Main function for source manager"""
    log_step("source_manager", "Starting source manager", "info")
    
    # Validate configuration
    if not validate_config():
        log_step("source_manager", "Configuration validation failed", "error")
        sys.exit(1)
    
    try:
        # Initialize source manager
        source_manager = SourceManager()
        
        # Setup directories
        source_manager.setup_source_directories()
        
        # Validate configurations
        if not source_manager.validate_source_configurations():
            log_step("source_manager", "Source configuration validation failed", "error")
            sys.exit(1)
        
        # Run all downloads
        success = source_manager.run_all_source_downloads()
        
        if success:
            log_step("source_manager", "All source downloads completed successfully", "success")
            sys.exit(0)
        else:
            log_step("source_manager", "Some source downloads failed", "error")
            sys.exit(1)
            
    except Exception as e:
        log_step("source_manager", f"Unexpected error: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()