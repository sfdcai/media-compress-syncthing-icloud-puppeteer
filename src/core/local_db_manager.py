#!/usr/bin/env python3
"""
Local PostgreSQL Database Manager
Primary data store for all Media Pipeline operations
All writes go to local PostgreSQL, sync to Supabase happens separately
"""

import os
import sys
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import threading
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.utils import log_step
except ImportError:
    # Fallback logging function if utils is not available
    def log_step(step, message, level="info"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} [{level.upper()}] {step}: {message}")

class LocalDBManager:
    def __init__(self):
        """Initialize local PostgreSQL database manager"""
        self.db_config = self._get_db_config()
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self.max_pool_size = 10
        
        # Test connection
        self._test_connection()
        
        log_step("local_db_manager", "Local PostgreSQL database manager initialized", "info")
    
    def _get_db_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'host': os.getenv('LOCAL_DB_HOST', 'localhost'),
            'port': int(os.getenv('LOCAL_DB_PORT', 5432)),
            'database': os.getenv('LOCAL_DB_NAME', 'media_pipeline'),
            'user': os.getenv('LOCAL_DB_USER', 'media_pipeline'),
            'password': os.getenv('LOCAL_DB_PASSWORD', 'media_pipeline_2024')
        }
    
    def _test_connection(self):
        """Test database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            log_step("local_db_manager", f"Connected to PostgreSQL at {self.db_config['host']}:{self.db_config['port']}", "info")
        except Exception as e:
            log_step("local_db_manager", f"Failed to connect to PostgreSQL: {e}", "error")
            raise
    
    def _get_connection(self):
        """Get database connection from pool or create new one"""
        with self.pool_lock:
            if self.connection_pool:
                return self.connection_pool.pop()
        
        return psycopg2.connect(**self.db_config)
    
    def _return_connection(self, conn):
        """Return connection to pool"""
        with self.pool_lock:
            if len(self.connection_pool) < self.max_pool_size:
                self.connection_pool.append(conn)
            else:
                conn.close()
    
    def _execute_query(self, query: str, params: tuple = None, fetch: bool = False, commit: bool = True) -> Optional[List[Dict]]:
        """Execute database query with error handling"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute(query, params)
            
            if commit:
                conn.commit()
            
            if fetch:
                result = cursor.fetchall()
                return [dict(row) for row in result]
            
            return None
            
        except Exception as e:
            if conn:
                conn.rollback()
            log_step("local_db_manager", f"Database error: {e}", "error")
            raise
        finally:
            if conn:
                cursor.close()
                self._return_connection(conn)
    
    # =====================================================
    # PIPELINE LOGS OPERATIONS
    # =====================================================
    
    def log_pipeline_step(self, pipeline_step: str, status: str, message: str, metadata: Dict = None) -> int:
        """Log a pipeline step to local database"""
        query = """
            INSERT INTO pipeline_logs (pipeline_step, status, message, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            pipeline_step,
            status,
            message,
            json.dumps(metadata) if metadata else None,
            datetime.now()
        )
        
        result = self._execute_query(query, params, fetch=True)
        log_id = result[0]['id'] if result else None
        
        log_step("local_db_manager", f"Logged pipeline step: {pipeline_step} - {status}", "debug")
        return log_id
    
    def get_pipeline_logs(self, limit: int = 100, status: str = None, pipeline_step: str = None) -> List[Dict]:
        """Get pipeline logs from local database"""
        query = "SELECT * FROM pipeline_logs WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        if pipeline_step:
            query += " AND pipeline_step = %s"
            params.append(pipeline_step)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        return self._execute_query(query, tuple(params), fetch=True) or []
    
    def get_unsynced_pipeline_logs(self, limit: int = 1000) -> List[Dict]:
        """Get pipeline logs that haven't been synced to Supabase"""
        query = """
            SELECT * FROM pipeline_logs 
            WHERE synced_to_supabase = FALSE 
            ORDER BY created_at ASC 
            LIMIT %s
        """
        return self._execute_query(query, (limit,), fetch=True) or []
    
    def mark_pipeline_log_synced(self, log_id: int, success: bool = True, error_message: str = None):
        """Mark a pipeline log as synced"""
        if success:
            query = """
                UPDATE pipeline_logs 
                SET synced_to_supabase = TRUE, sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = NULL
                WHERE id = %s
            """
            params = (datetime.now(), log_id)
        else:
            query = """
                UPDATE pipeline_logs 
                SET sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = %s
                WHERE id = %s
            """
            params = (datetime.now(), error_message, log_id)
        
        self._execute_query(query, params)
    
    # =====================================================
    # TELEGRAM 2FA REQUESTS OPERATIONS
    # =====================================================
    
    def create_2fa_request(self, request_id: str, pipeline_step: str, expires_minutes: int = 5) -> bool:
        """Create a 2FA request in local database"""
        query = """
            INSERT INTO telegram_2fa_requests (id, pipeline_step, status, expires_at)
            VALUES (%s, %s, 'pending', %s)
            ON CONFLICT (id) DO UPDATE SET
                pipeline_step = EXCLUDED.pipeline_step,
                status = 'pending',
                expires_at = EXCLUDED.expires_at,
                synced_to_supabase = FALSE
        """
        
        expires_at = datetime.now() + timedelta(minutes=expires_minutes)
        params = (request_id, pipeline_step, expires_at)
        
        self._execute_query(query, params)
        log_step("local_db_manager", f"Created 2FA request: {request_id}", "debug")
        return True
    
    def get_2fa_request(self, request_id: str) -> Optional[Dict]:
        """Get a 2FA request by ID"""
        query = "SELECT * FROM telegram_2fa_requests WHERE id = %s"
        result = self._execute_query(query, (request_id,), fetch=True)
        return result[0] if result else None
    
    def update_2fa_request(self, request_id: str, status: str, code: str = None) -> bool:
        """Update a 2FA request status"""
        query = """
            UPDATE telegram_2fa_requests 
            SET status = %s, code = %s, completed_at = %s, synced_to_supabase = FALSE
            WHERE id = %s
        """
        
        completed_at = datetime.now() if status in ['completed', 'expired'] else None
        params = (status, code, completed_at, request_id)
        
        self._execute_query(query, params)
        log_step("local_db_manager", f"Updated 2FA request {request_id}: {status}", "debug")
        return True
    
    def get_pending_2fa_requests(self) -> List[Dict]:
        """Get all pending 2FA requests"""
        query = """
            SELECT * FROM telegram_2fa_requests 
            WHERE status = 'pending' AND expires_at > %s
            ORDER BY created_at ASC
        """
        return self._execute_query(query, (datetime.now(),), fetch=True) or []
    
    def get_unsynced_2fa_requests(self, limit: int = 100) -> List[Dict]:
        """Get 2FA requests that haven't been synced to Supabase"""
        query = """
            SELECT * FROM telegram_2fa_requests 
            WHERE synced_to_supabase = FALSE 
            ORDER BY created_at ASC 
            LIMIT %s
        """
        return self._execute_query(query, (limit,), fetch=True) or []
    
    def mark_2fa_request_synced(self, request_id: str, success: bool = True, error_message: str = None):
        """Mark a 2FA request as synced"""
        if success:
            query = """
                UPDATE telegram_2fa_requests 
                SET synced_to_supabase = TRUE, sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = NULL
                WHERE id = %s
            """
            params = (datetime.now(), request_id)
        else:
            query = """
                UPDATE telegram_2fa_requests 
                SET sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = %s
                WHERE id = %s
            """
            params = (datetime.now(), error_message, request_id)
        
        self._execute_query(query, params)
    
    # =====================================================
    # TELEGRAM NOTIFICATIONS OPERATIONS
    # =====================================================
    
    def log_telegram_notification(self, notification_type: str, message: str, success: bool = True, 
                                 error_message: str = None, metadata: Dict = None) -> int:
        """Log a Telegram notification to local database"""
        query = """
            INSERT INTO telegram_notifications (notification_type, message, success, error_message, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            notification_type,
            message,
            success,
            error_message,
            json.dumps(metadata) if metadata else None
        )
        
        result = self._execute_query(query, params, fetch=True)
        notification_id = result[0]['id'] if result else None
        
        log_step("local_db_manager", f"Logged Telegram notification: {notification_type}", "debug")
        return notification_id
    
    def get_telegram_notifications(self, limit: int = 100, notification_type: str = None) -> List[Dict]:
        """Get Telegram notifications from local database"""
        query = "SELECT * FROM telegram_notifications WHERE 1=1"
        params = []
        
        if notification_type:
            query += " AND notification_type = %s"
            params.append(notification_type)
        
        query += " ORDER BY sent_at DESC LIMIT %s"
        params.append(limit)
        
        return self._execute_query(query, tuple(params), fetch=True) or []
    
    def get_unsynced_notifications(self, limit: int = 100) -> List[Dict]:
        """Get notifications that haven't been synced to Supabase"""
        query = """
            SELECT * FROM telegram_notifications 
            WHERE synced_to_supabase = FALSE 
            ORDER BY sent_at ASC 
            LIMIT %s
        """
        return self._execute_query(query, (limit,), fetch=True) or []
    
    def mark_notification_synced(self, notification_id: int, success: bool = True, error_message: str = None):
        """Mark a notification as synced"""
        if success:
            query = """
                UPDATE telegram_notifications 
                SET synced_to_supabase = TRUE, sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = NULL
                WHERE id = %s
            """
            params = (datetime.now(), notification_id)
        else:
            query = """
                UPDATE telegram_notifications 
                SET sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = %s
                WHERE id = %s
            """
            params = (datetime.now(), error_message, notification_id)
        
        self._execute_query(query, params)
    
    # =====================================================
    # CACHE METRICS OPERATIONS
    # =====================================================
    
    def log_cache_metrics(self, cache_type: str, hit_count: int, miss_count: int, 
                         total_requests: int, api_calls_saved: int, cache_size: int, 
                         hit_rate: float, metadata: Dict = None) -> int:
        """Log cache metrics to local database"""
        query = """
            INSERT INTO cache_metrics (cache_type, hit_count, miss_count, total_requests, 
                                     api_calls_saved, cache_size, hit_rate, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            cache_type,
            hit_count,
            miss_count,
            total_requests,
            api_calls_saved,
            cache_size,
            hit_rate,
            json.dumps(metadata) if metadata else None
        )
        
        result = self._execute_query(query, params, fetch=True)
        metrics_id = result[0]['id'] if result else None
        
        log_step("local_db_manager", f"Logged cache metrics: {cache_type} - {hit_rate}% hit rate", "debug")
        return metrics_id
    
    def get_cache_metrics(self, limit: int = 100, cache_type: str = None) -> List[Dict]:
        """Get cache metrics from local database"""
        query = "SELECT * FROM cache_metrics WHERE 1=1"
        params = []
        
        if cache_type:
            query += " AND cache_type = %s"
            params.append(cache_type)
        
        query += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(limit)
        
        return self._execute_query(query, tuple(params), fetch=True) or []
    
    def get_unsynced_cache_metrics(self, limit: int = 100) -> List[Dict]:
        """Get cache metrics that haven't been synced to Supabase"""
        query = """
            SELECT * FROM cache_metrics 
            WHERE synced_to_supabase = FALSE 
            ORDER BY recorded_at ASC 
            LIMIT %s
        """
        return self._execute_query(query, (limit,), fetch=True) or []
    
    def mark_cache_metrics_synced(self, metrics_id: int, success: bool = True, error_message: str = None):
        """Mark cache metrics as synced"""
        if success:
            query = """
                UPDATE cache_metrics 
                SET synced_to_supabase = TRUE, sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = NULL
                WHERE id = %s
            """
            params = (datetime.now(), metrics_id)
        else:
            query = """
                UPDATE cache_metrics 
                SET sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = %s
                WHERE id = %s
            """
            params = (datetime.now(), error_message, metrics_id)
        
        self._execute_query(query, params)
    
    # =====================================================
    # PIPELINE METRICS OPERATIONS
    # =====================================================
    
    def log_pipeline_metric(self, metric_name: str, metric_value: float, 
                           metric_unit: str = None, metadata: Dict = None) -> int:
        """Log a pipeline metric to local database"""
        query = """
            INSERT INTO pipeline_metrics (metric_name, metric_value, metric_unit, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            metric_name,
            metric_value,
            metric_unit,
            json.dumps(metadata) if metadata else None
        )
        
        result = self._execute_query(query, params, fetch=True)
        metric_id = result[0]['id'] if result else None
        
        log_step("local_db_manager", f"Logged pipeline metric: {metric_name} = {metric_value}", "debug")
        return metric_id
    
    def get_pipeline_metrics(self, limit: int = 100, metric_name: str = None) -> List[Dict]:
        """Get pipeline metrics from local database"""
        query = "SELECT * FROM pipeline_metrics WHERE 1=1"
        params = []
        
        if metric_name:
            query += " AND metric_name = %s"
            params.append(metric_name)
        
        query += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(limit)
        
        return self._execute_query(query, tuple(params), fetch=True) or []
    
    def get_unsynced_pipeline_metrics(self, limit: int = 100) -> List[Dict]:
        """Get pipeline metrics that haven't been synced to Supabase"""
        query = """
            SELECT * FROM pipeline_metrics 
            WHERE synced_to_supabase = FALSE 
            ORDER BY recorded_at ASC 
            LIMIT %s
        """
        return self._execute_query(query, (limit,), fetch=True) or []
    
    def mark_pipeline_metric_synced(self, metric_id: int, success: bool = True, error_message: str = None):
        """Mark a pipeline metric as synced"""
        if success:
            query = """
                UPDATE pipeline_metrics 
                SET synced_to_supabase = TRUE, sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = NULL
                WHERE id = %s
            """
            params = (datetime.now(), metric_id)
        else:
            query = """
                UPDATE pipeline_metrics 
                SET sync_attempts = sync_attempts + 1, 
                    last_sync_attempt = %s, sync_error = %s
                WHERE id = %s
            """
            params = (datetime.now(), error_message, metric_id)
        
        self._execute_query(query, params)
    
    # =====================================================
    # SYSTEM CONFIGURATION OPERATIONS
    # =====================================================
    
    def get_config(self, config_key: str) -> Optional[str]:
        """Get system configuration value"""
        query = "SELECT config_value FROM system_config WHERE config_key = %s"
        result = self._execute_query(query, (config_key,), fetch=True)
        return result[0]['config_value'] if result else None
    
    def set_config(self, config_key: str, config_value: str, config_type: str = 'string', 
                  description: str = None, is_sensitive: bool = False) -> bool:
        """Set system configuration value"""
        query = """
            INSERT INTO system_config (config_key, config_value, config_type, description, is_sensitive)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (config_key) DO UPDATE SET
                config_value = EXCLUDED.config_value,
                config_type = EXCLUDED.config_type,
                description = EXCLUDED.description,
                is_sensitive = EXCLUDED.is_sensitive,
                updated_at = NOW()
        """
        
        params = (config_key, config_value, config_type, description, is_sensitive)
        self._execute_query(query, params)
        return True
    
    def get_all_config(self) -> Dict[str, str]:
        """Get all system configuration"""
        query = "SELECT config_key, config_value FROM system_config"
        result = self._execute_query(query, fetch=True)
        return {row['config_key']: row['config_value'] for row in result} if result else {}
    
    # =====================================================
    # SYNC STATUS OPERATIONS
    # =====================================================
    
    def get_sync_status(self, table_name: str) -> Optional[Dict]:
        """Get sync status for a table"""
        query = "SELECT * FROM sync_status WHERE table_name = %s"
        result = self._execute_query(query, (table_name,), fetch=True)
        return result[0] if result else None
    
    def update_sync_status(self, table_name: str, records_synced: int = 0, 
                          error_message: str = None) -> bool:
        """Update sync status for a table"""
        if error_message:
            query = """
                UPDATE sync_status 
                SET last_sync_timestamp = %s, error_count = error_count + 1, 
                    last_error = %s, updated_at = NOW()
                WHERE table_name = %s
            """
            params = (datetime.now(), error_message, table_name)
        else:
            query = """
                UPDATE sync_status 
                SET last_sync_timestamp = %s, total_records_synced = total_records_synced + %s,
                    error_count = 0, last_error = NULL, updated_at = NOW()
                WHERE table_name = %s
            """
            params = (datetime.now(), records_synced, table_name)
        
        self._execute_query(query, params)
        return True
    
    def get_all_sync_status(self) -> List[Dict]:
        """Get sync status for all tables"""
        query = "SELECT * FROM sync_status ORDER BY table_name"
        return self._execute_query(query, fetch=True) or []
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for all tables"""
        stats = {}
        
        # Get all table row counts - comprehensive list of all tables
        tables = [
            'batches', 'cache_metrics', 'duplicate_files', 'media_files', 
            'pipeline_logs', 'pipeline_metrics', 'sync_config', 'sync_stats', 
            'sync_status', 'system_config', 'telegram_2fa_requests', 
            'telegram_notifications', 'twofa_requests'
        ]
        
        for table in tables:
            try:
                query = f"SELECT COUNT(*) as count FROM {table}"
                result = self._execute_query(query, fetch=True)
                stats[f'{table}_count'] = result[0]['count'] if result else 0
            except Exception as e:
                log_step("local_db_manager", f"Error counting {table}: {e}", "warning")
                stats[f'{table}_count'] = 0
        
        # Get unsynced counts for tables that have synced_to_supabase column
        syncable_tables = ['pipeline_logs', 'telegram_2fa_requests', 'telegram_notifications', 
                          'cache_metrics', 'pipeline_metrics', 'batches', 'media_files']
        
        for table in syncable_tables:
            try:
                query = f"SELECT COUNT(*) as count FROM {table} WHERE synced_to_supabase = FALSE"
                result = self._execute_query(query, fetch=True)
                stats[f'{table}_unsynced'] = result[0]['count'] if result else 0
            except Exception as e:
                log_step("local_db_manager", f"Error counting unsynced {table}: {e}", "warning")
                stats[f'{table}_unsynced'] = 0
        
        return stats
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records to prevent database bloat"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        tables_cleanup = [
            ('pipeline_logs', 'created_at'),
            ('telegram_notifications', 'sent_at'),
            ('cache_metrics', 'recorded_at'),
            ('pipeline_metrics', 'recorded_at')
        ]
        
        for table, date_column in tables_cleanup:
            query = f"DELETE FROM {table} WHERE {date_column} < %s AND synced_to_supabase = TRUE"
            result = self._execute_query(query, (cutoff_date,))
            log_step("local_db_manager", f"Cleaned up old records from {table}", "info")

# Global database manager instance
_db_manager = None

def get_db_manager() -> LocalDBManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = LocalDBManager()
    return _db_manager

def main():
    """Main function for testing"""
    if len(sys.argv) < 2:
        print("Usage: python3 local_db_manager.py <command>")
        print("Commands: test, stats, cleanup")
        return
    
    command = sys.argv[1]
    db_manager = get_db_manager()
    
    if command == "test":
        # Test database functionality
        print("🧪 Testing Local PostgreSQL Database...")
        
        # Test pipeline log
        log_id = db_manager.log_pipeline_step("test", "info", "Testing local database")
        print(f"✅ Pipeline log created: ID {log_id}")
        
        # Test 2FA request
        request_id = "test_request_123"
        db_manager.create_2fa_request(request_id, "test", 5)
        print(f"✅ 2FA request created: {request_id}")
        
        # Test notification
        notif_id = db_manager.log_telegram_notification("test", "Test notification")
        print(f"✅ Notification logged: ID {notif_id}")
        
        # Test cache metrics
        metrics_id = db_manager.log_cache_metrics("test", 10, 5, 15, 10, 100, 66.67)
        print(f"✅ Cache metrics logged: ID {metrics_id}")
        
        # Test pipeline metric
        metric_id = db_manager.log_pipeline_metric("test_metric", 100.0, "count")
        print(f"✅ Pipeline metric logged: ID {metric_id}")
        
        print("🎉 All tests passed!")
    
    elif command == "stats":
        stats = db_manager.get_database_stats()
        print("📊 Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif command == "cleanup":
        db_manager.cleanup_old_records(30)
        print("✅ Old records cleaned up")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()