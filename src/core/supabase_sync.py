#!/usr/bin/env python3
"""
Supabase Sync Process
Syncs data from local PostgreSQL to Supabase
Runs as a background service with configurable frequency
"""

import os
import sys
import json
import requests
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import signal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from local_db_manager import get_db_manager

try:
    from utils.utils import log_step
except ImportError:
    # Fallback logging function if utils is not available
    def log_step(step, message, level="info"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} [{level.upper()}] {step}: {message}")

class SupabaseSync:
    def __init__(self):
        """Initialize Supabase sync process"""
        self.db_manager = get_db_manager()
        self.supabase_url = self.db_manager.get_config('supabase_url')
        self.supabase_key = self.db_manager.get_config('supabase_key')
        self.sync_enabled = self.db_manager.get_config('sync_enabled') == 'true'
        self.max_sync_attempts = int(self.db_manager.get_config('max_sync_attempts'))
        self.batch_size = int(self.db_manager.get_config('batch_size'))
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and key must be configured")
        
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates'
        }
        
        self.running = False
        self.sync_thread = None
        
        log_step("supabase_sync", "Supabase sync process initialized", "info")
    
    def start_sync(self):
        """Start the sync process"""
        if not self.sync_enabled:
            log_step("supabase_sync", "Sync is disabled in configuration", "warning")
            return
        
        if self.running:
            log_step("supabase_sync", "Sync process is already running", "warning")
            return
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        
        log_step("supabase_sync", "Sync process started", "info")
    
    def stop_sync(self):
        """Stop the sync process"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=10)
        
        log_step("supabase_sync", "Sync process stopped", "info")
    
    def _sync_loop(self):
        """Main sync loop"""
        while self.running:
            try:
                self._sync_all_tables()
                
                # Get sync frequency from database
                sync_frequency = int(self.db_manager.get_config('sync_frequency_seconds'))
                time.sleep(sync_frequency)
                
            except Exception as e:
                log_step("supabase_sync", f"Sync loop error: {e}", "error")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _sync_all_tables(self):
        """Sync all tables to Supabase"""
        tables_to_sync = [
            'pipeline_logs',
            'telegram_2fa_requests',
            'telegram_notifications',
            'cache_metrics',
            'pipeline_metrics'
        ]
        
        for table_name in tables_to_sync:
            try:
                self._sync_table(table_name)
            except Exception as e:
                log_step("supabase_sync", f"Error syncing {table_name}: {e}", "error")
                self.db_manager.update_sync_status(table_name, error_message=str(e))
    
    def _sync_table(self, table_name: str):
        """Sync a specific table to Supabase"""
        sync_status = self.db_manager.get_sync_status(table_name)
        if not sync_status or not sync_status['is_enabled']:
            return
        
        # Get unsynced records
        unsynced_records = self._get_unsynced_records(table_name)
        
        if not unsynced_records:
            return
        
        log_step("supabase_sync", f"Syncing {len(unsynced_records)} records from {table_name}", "debug")
        
        # Process in batches
        batch_size = min(self.batch_size, len(unsynced_records))
        success_count = 0
        error_count = 0
        
        for i in range(0, len(unsynced_records), batch_size):
            batch = unsynced_records[i:i + batch_size]
            
            try:
                if self._sync_batch(table_name, batch):
                    success_count += len(batch)
                    self._mark_batch_synced(table_name, batch)
                else:
                    error_count += len(batch)
                    
            except Exception as e:
                log_step("supabase_sync", f"Batch sync error for {table_name}: {e}", "error")
                error_count += len(batch)
        
        # Update sync status
        if error_count == 0:
            self.db_manager.update_sync_status(table_name, records_synced=success_count)
            log_step("supabase_sync", f"Successfully synced {success_count} records from {table_name}", "info")
        else:
            self.db_manager.update_sync_status(table_name, error_message=f"Failed to sync {error_count} records")
            log_step("supabase_sync", f"Synced {success_count} records, {error_count} failed from {table_name}", "warning")
    
    def _get_unsynced_records(self, table_name: str) -> List[Dict]:
        """Get unsynced records for a table"""
        if table_name == 'pipeline_logs':
            return self.db_manager.get_unsynced_pipeline_logs(self.batch_size)
        elif table_name == 'telegram_2fa_requests':
            return self.db_manager.get_unsynced_2fa_requests(self.batch_size)
        elif table_name == 'telegram_notifications':
            return self.db_manager.get_unsynced_notifications(self.batch_size)
        elif table_name == 'cache_metrics':
            return self.db_manager.get_unsynced_cache_metrics(self.batch_size)
        elif table_name == 'pipeline_metrics':
            return self.db_manager.get_unsynced_pipeline_metrics(self.batch_size)
        else:
            return []
    
    def _check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in Supabase"""
        try:
            url = f"{self.supabase_url}/rest/v1/{table_name}"
            response = requests.get(url, headers=self.headers, params={"limit": 1}, timeout=10)
            return response.status_code in [200, 206]  # 206 is partial content
        except:
            return False
    
    def _sync_batch(self, table_name: str, records: List[Dict]) -> bool:
        """Sync a batch of records to Supabase"""
        if not records:
            return True
        
        # Check if table exists in Supabase
        if not self._check_table_exists(table_name):
            log_step("supabase_sync", f"Table {table_name} does not exist in Supabase, skipping sync", "warning")
            return True  # Don't fail, just skip
        
        # Define which columns to sync for each table (only columns that exist in Supabase)
        # Note: Supabase column names may differ from local database column names
        table_columns = {
            'pipeline_logs': ['id', 'step', 'status', 'message'],  # Supabase uses 'step' not 'pipeline_step'
            'telegram_2fa_requests': ['id', 'pipeline_step', 'status', 'created_at', 'expires_at', 'code', 'completed_at'],
            'telegram_notifications': ['id', 'notification_type', 'message', 'sent_at', 'success', 'error_message', 'metadata'],
            'cache_metrics': ['id', 'cache_type', 'hit_count', 'miss_count', 'total_requests', 'api_calls_saved', 'cache_size', 'hit_rate', 'recorded_at', 'metadata'],
            'pipeline_metrics': ['id', 'metric_name', 'metric_value', 'metric_unit', 'recorded_at', 'metadata']
        }
        
        # Define column mapping from local database to Supabase
        column_mapping = {
            'pipeline_logs': {
                'pipeline_step': 'step',  # Map local 'pipeline_step' to Supabase 'step'
                'status': 'status',
                'message': 'message',
                'id': 'id'
            }
        }
        
        # Prepare data for Supabase (only sync columns that exist in Supabase)
        supabase_data = []
        allowed_columns = table_columns.get(table_name, [])
        mapping = column_mapping.get(table_name, {})
        
        for record in records:
            supabase_record = {}
            for k, v in record.items():
                # Map local column name to Supabase column name
                supabase_column = mapping.get(k, k)
                
                if supabase_column in allowed_columns:
                    # Convert datetime objects to ISO format strings
                    if isinstance(v, datetime):
                        supabase_record[supabase_column] = v.isoformat()
                    else:
                        supabase_record[supabase_column] = v
            supabase_data.append(supabase_record)
        
        # Perform UPSERT to Supabase
        url = f"{self.supabase_url}/rest/v1/{table_name}"
        
        try:
            response = requests.post(url, json=supabase_data, headers=self.headers, timeout=30)
            
            if response.status_code in [200, 201]:
                return True
            else:
                # Provide more specific error information
                error_msg = response.text
                if "PGRST204" in error_msg and "column" in error_msg:
                    log_step("supabase_sync", f"Schema mismatch for {table_name}: {error_msg}. Skipping sync until Supabase schema is updated.", "warning")
                    return True  # Don't fail, just skip
                else:
                    log_step("supabase_sync", f"Supabase API error for {table_name}: {response.status_code} - {error_msg}", "error")
                    return False
                
        except requests.exceptions.RequestException as e:
            log_step("supabase_sync", f"Network error syncing {table_name}: {e}", "error")
            return False
    
    def _mark_batch_synced(self, table_name: str, records: List[Dict]):
        """Mark a batch of records as synced"""
        for record in records:
            record_id = record.get('id')
            if record_id:
                if table_name == 'pipeline_logs':
                    self.db_manager.mark_pipeline_log_synced(record_id)
                elif table_name == 'telegram_2fa_requests':
                    self.db_manager.mark_2fa_request_synced(record_id)
                elif table_name == 'telegram_notifications':
                    self.db_manager.mark_notification_synced(record_id)
                elif table_name == 'cache_metrics':
                    self.db_manager.mark_cache_metrics_synced(record_id)
                elif table_name == 'pipeline_metrics':
                    self.db_manager.mark_pipeline_metric_synced(record_id)
    
    def force_sync_table(self, table_name: str) -> Dict[str, Any]:
        """Force sync a specific table (for manual operations)"""
        try:
            unsynced_records = self._get_unsynced_records(table_name)
            
            if not unsynced_records:
                return {
                    'success': True,
                    'message': f'No unsynced records found for {table_name}',
                    'records_synced': 0
                }
            
            # Sync all records
            success_count = 0
            error_count = 0
            
            for i in range(0, len(unsynced_records), self.batch_size):
                batch = unsynced_records[i:i + self.batch_size]
                
                if self._sync_batch(table_name, batch):
                    success_count += len(batch)
                    self._mark_batch_synced(table_name, batch)
                else:
                    error_count += len(batch)
            
            self.db_manager.update_sync_status(table_name, records_synced=success_count)
            
            return {
                'success': True,
                'message': f'Synced {success_count} records from {table_name}',
                'records_synced': success_count,
                'errors': error_count
            }
            
        except Exception as e:
            self.db_manager.update_sync_status(table_name, error_message=str(e))
            return {
                'success': False,
                'message': f'Error syncing {table_name}: {e}',
                'records_synced': 0
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for all tables"""
        sync_status = self.db_manager.get_all_sync_status()
        db_stats = self.db_manager.get_database_stats()
        
        return {
            'sync_enabled': self.sync_enabled,
            'running': self.running,
            'tables': sync_status,
            'database_stats': db_stats,
            'configuration': {
                'sync_frequency_seconds': int(self.db_manager.get_config('sync_frequency_seconds')),
                'max_sync_attempts': self.max_sync_attempts,
                'batch_size': self.batch_size
            }
        }
    
    def update_sync_config(self, config_updates: Dict[str, str]) -> bool:
        """Update sync configuration"""
        try:
            for key, value in config_updates.items():
                self.db_manager.set_config(key, value)
            
            # Reload configuration
            self.sync_enabled = self.db_manager.get_config('sync_enabled') == 'true'
            self.max_sync_attempts = int(self.db_manager.get_config('max_sync_attempts'))
            self.batch_size = int(self.db_manager.get_config('batch_size'))
            
            log_step("supabase_sync", f"Updated sync configuration: {config_updates}", "info")
            return True
            
        except Exception as e:
            log_step("supabase_sync", f"Error updating sync configuration: {e}", "error")
            return False

# Global sync instance
_sync_instance = None

def get_sync_instance() -> SupabaseSync:
    """Get global sync instance"""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = SupabaseSync()
    return _sync_instance

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    sync_instance = get_sync_instance()
    sync_instance.stop_sync()
    sys.exit(0)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 supabase_sync.py <command>")
        print("Commands: start, stop, status, sync-table <table_name>, config")
        return
    
    command = sys.argv[1]
    sync_instance = get_sync_instance()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if command == "start":
        sync_instance.start_sync()
        try:
            # Keep the process running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sync_instance.stop_sync()
    
    elif command == "stop":
        sync_instance.stop_sync()
    
    elif command == "status":
        status = sync_instance.get_sync_status()
        print("📊 Supabase Sync Status:")
        print(f"  Sync Enabled: {status['sync_enabled']}")
        print(f"  Running: {status['running']}")
        print(f"  Sync Frequency: {status['configuration']['sync_frequency_seconds']}s")
        print(f"  Batch Size: {status['configuration']['batch_size']}")
        print("\n📋 Table Status:")
        for table in status['tables']:
            print(f"  {table['table_name']}: {table['sync_frequency_seconds']}s interval, enabled: {table['is_enabled']}")
        print("\n📊 Database Stats:")
        for key, value in status['database_stats'].items():
            print(f"  {key}: {value}")
    
    elif command == "sync-table":
        if len(sys.argv) < 3:
            print("Usage: python3 supabase_sync.py sync-table <table_name>")
            return
        
        table_name = sys.argv[2]
        result = sync_instance.force_sync_table(table_name)
        print(f"🔄 Sync Result for {table_name}:")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
        print(f"  Records Synced: {result['records_synced']}")
        if 'errors' in result:
            print(f"  Errors: {result['errors']}")
    
    elif command == "config":
        print("⚙️ Current Sync Configuration:")
        config = sync_instance.get_sync_status()['configuration']
        for key, value in config.items():
            print(f"  {key}: {value}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()