#!/usr/bin/env python3
"""
File-Based Batch Manager for Media Pipeline
Writes operations to local files and syncs to Supabase in background
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, 'config', 'settings.env'))

# Simple logging
def log_step(step, message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} [{level.upper()}] {step}: {message}")

class BatchManager:
    def __init__(self):
        """Initialize batch manager"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        # File paths
        self.batch_dir = project_root / "cache" / "batches"
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        
        self.get_batch_file = self.batch_dir / "get_operations.jsonl"
        self.post_batch_file = self.batch_dir / "post_operations.jsonl"
        self.sync_log_file = self.batch_dir / "sync_log.jsonl"
        
        # Configuration
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        self.sync_interval = int(os.getenv('SYNC_INTERVAL', '60'))  # seconds
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '5'))  # seconds
        
        # Statistics
        self.stats = {
            'total_operations': 0,
            'pending_get_operations': 0,
            'pending_post_operations': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_sync': None,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls_saved': 0
        }
        
        # Cache for GET operations (simple in-memory cache)
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes
        
        self.lock = threading.Lock()
        
        log_step("batch_manager", "Batch manager initialized", "info")
        log_step("batch_manager", f"Batch size: {self.batch_size}, Sync interval: {self.sync_interval}s", "info")
    
    def _write_to_batch_file(self, file_path: Path, operation: Dict):
        """Write operation to batch file"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(operation) + '\n')
        except Exception as e:
            log_step("batch_manager", f"Error writing to batch file: {e}", "error")
    
    def _read_batch_file(self, file_path: Path, max_operations: int = None) -> List[Dict]:
        """Read operations from batch file"""
        operations = []
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if max_operations:
                        lines = lines[:max_operations]
                    
                    for line in lines:
                        try:
                            operations.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            log_step("batch_manager", f"Error reading batch file: {e}", "error")
        
        return operations
    
    def _clear_batch_file(self, file_path: Path, operations_to_keep: List[Dict]):
        """Clear batch file and write remaining operations"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for operation in operations_to_keep:
                    f.write(json.dumps(operation) + '\n')
        except Exception as e:
            log_step("batch_manager", f"Error clearing batch file: {e}", "error")
    
    def _generate_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for GET request"""
        key_data = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        return str(hash(key_data))
    
    def _is_cache_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.cache_timestamps:
            return True
        
        timestamp = self.cache_timestamps[key]
        return datetime.now() > timestamp
    
    def get(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Optional[Dict]:
        """Get data from cache or queue for batch processing"""
        with self.lock:
            self.stats['total_operations'] += 1
            
            # Check cache first
            if use_cache:
                cache_key = self._generate_cache_key(endpoint, params)
                
                if cache_key in self.cache and not self._is_cache_expired(cache_key):
                    # Cache hit
                    self.stats['cache_hits'] += 1
                    self.stats['api_calls_saved'] += 1
                    log_step("batch_manager", f"Cache hit for {endpoint}", "debug")
                    return self.cache[cache_key]
            
            # Cache miss - queue for batch processing
            self.stats['cache_misses'] += 1
            
            operation = {
                'timestamp': datetime.now().isoformat(),
                'type': 'get',
                'endpoint': endpoint,
                'params': params or {},
                'use_cache': use_cache
            }
            
            self._write_to_batch_file(self.get_batch_file, operation)
            self.stats['pending_get_operations'] += 1
            
            log_step("batch_manager", f"Queued GET operation for {endpoint}", "debug")
            
            # Return None for now - data will be available after next sync
            return None
    
    def post(self, endpoint: str, data: Dict) -> bool:
        """Queue POST operation for batch processing"""
        with self.lock:
            self.stats['total_operations'] += 1
            
            operation = {
                'timestamp': datetime.now().isoformat(),
                'type': 'post',
                'endpoint': endpoint,
                'data': data
            }
            
            self._write_to_batch_file(self.post_batch_file, operation)
            self.stats['pending_post_operations'] += 1
            
            log_step("batch_manager", f"Queued POST operation for {endpoint}", "debug")
            return True
    
    def _sync_get_operations(self) -> int:
        """Sync GET operations to Supabase"""
        operations = self._read_batch_file(self.get_batch_file, self.batch_size)
        if not operations:
            return 0
        
        successful_syncs = 0
        
        for operation in operations:
            try:
                endpoint = operation['endpoint']
                params = operation['params']
                use_cache = operation.get('use_cache', True)
                
                # Fetch from Supabase
                data = self._fetch_from_supabase(endpoint, params)
                
                if data is not None:
                    # Store in cache if requested
                    if use_cache:
                        cache_key = self._generate_cache_key(endpoint, params)
                        self.cache[cache_key] = data
                        self.cache_timestamps[cache_key] = datetime.now() + timedelta(seconds=self.cache_ttl)
                    
                    successful_syncs += 1
                    log_step("batch_manager", f"Synced GET operation for {endpoint}", "debug")
                else:
                    log_step("batch_manager", f"Failed to sync GET operation for {endpoint}", "warning")
                
            except Exception as e:
                log_step("batch_manager", f"Error syncing GET operation: {e}", "error")
        
        # Remove processed operations
        remaining_operations = self._read_batch_file(self.get_batch_file)[len(operations):]
        self._clear_batch_file(self.get_batch_file, remaining_operations)
        
        self.stats['pending_get_operations'] = len(remaining_operations)
        return successful_syncs
    
    def _sync_post_operations(self) -> int:
        """Sync POST operations to Supabase"""
        operations = self._read_batch_file(self.post_batch_file, self.batch_size)
        if not operations:
            return 0
        
        successful_syncs = 0
        
        for operation in operations:
            try:
                endpoint = operation['endpoint']
                data = operation['data']
                
                # Post to Supabase
                result = self._post_to_supabase(endpoint, data)
                
                if result is not None:
                    successful_syncs += 1
                    log_step("batch_manager", f"Synced POST operation for {endpoint}", "debug")
                else:
                    log_step("batch_manager", f"Failed to sync POST operation for {endpoint}", "warning")
                
            except Exception as e:
                log_step("batch_manager", f"Error syncing POST operation: {e}", "error")
        
        # Remove processed operations
        remaining_operations = self._read_batch_file(self.post_batch_file)[len(operations):]
        self._clear_batch_file(self.post_batch_file, remaining_operations)
        
        self.stats['pending_post_operations'] = len(remaining_operations)
        return successful_syncs
    
    def _fetch_from_supabase(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Fetch data from Supabase API"""
        try:
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            headers = {
                'apikey': self.supabase_key,
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, params=params or {}, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                log_step("batch_manager", f"Supabase API error: {response.status_code}", "error")
                return None
                
        except requests.exceptions.ConnectionError as e:
            log_step("batch_manager", f"Network connection error: {e}", "warning")
            return None
        except requests.exceptions.Timeout as e:
            log_step("batch_manager", f"Request timeout: {e}", "warning")
            return None
        except Exception as e:
            log_step("batch_manager", f"Error fetching from Supabase: {e}", "error")
            return None
    
    def _post_to_supabase(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """Post data to Supabase API"""
        try:
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            headers = {
                'apikey': self.supabase_key,
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                log_step("batch_manager", f"Supabase POST error: {response.status_code}", "error")
                return None
                
        except requests.exceptions.ConnectionError as e:
            log_step("batch_manager", f"Network connection error: {e}", "warning")
            return None
        except requests.exceptions.Timeout as e:
            log_step("batch_manager", f"Request timeout: {e}", "warning")
            return None
        except Exception as e:
            log_step("batch_manager", f"Error posting to Supabase: {e}", "error")
            return None
    
    def sync_batches(self) -> Dict:
        """Sync all pending operations to Supabase"""
        with self.lock:
            sync_start = datetime.now()
            
            # Sync GET operations
            get_synced = self._sync_get_operations()
            
            # Sync POST operations
            post_synced = self._sync_post_operations()
            
            total_synced = get_synced + post_synced
            
            if total_synced > 0:
                self.stats['successful_syncs'] += 1
                self.stats['last_sync'] = sync_start.isoformat()
                log_step("batch_manager", f"Synced {total_synced} operations ({get_synced} GET, {post_synced} POST)", "info")
            else:
                self.stats['failed_syncs'] += 1
                log_step("batch_manager", "No operations to sync", "debug")
            
            return {
                'get_synced': get_synced,
                'post_synced': post_synced,
                'total_synced': total_synced,
                'sync_time': sync_start.isoformat()
            }
    
    def get_stats(self) -> Dict:
        """Get batch manager statistics"""
        with self.lock:
            # Update pending counts
            self.stats['pending_get_operations'] = len(self._read_batch_file(self.get_batch_file))
            self.stats['pending_post_operations'] = len(self._read_batch_file(self.post_batch_file))
            
            # Calculate hit rate
            total_requests = self.stats['total_operations']
            if total_requests > 0:
                hit_rate = (self.stats['cache_hits'] / total_requests) * 100
                self.stats['hit_rate'] = round(hit_rate, 2)
            else:
                self.stats['hit_rate'] = 0
            
            return self.stats.copy()
    
    def clear_batches(self):
        """Clear all pending operations"""
        with self.lock:
            # Clear batch files
            for file_path in [self.get_batch_file, self.post_batch_file]:
                if file_path.exists():
                    file_path.unlink()
            
            # Clear cache
            self.cache.clear()
            self.cache_timestamps.clear()
            
            # Reset statistics
            self.stats = {
                'total_operations': 0,
                'pending_get_operations': 0,
                'pending_post_operations': 0,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'last_sync': None,
                'cache_hits': 0,
                'cache_misses': 0,
                'api_calls_saved': 0
            }
            
            log_step("batch_manager", "All batches and cache cleared", "info")
    
    def update_config(self, config: Dict):
        """Update batch manager configuration"""
        with self.lock:
            if 'batch_size' in config:
                self.batch_size = int(config['batch_size'])
            if 'sync_interval' in config:
                self.sync_interval = int(config['sync_interval'])
            if 'cache_ttl' in config:
                self.cache_ttl = int(config['cache_ttl'])
            if 'max_retries' in config:
                self.max_retries = int(config['max_retries'])
            if 'retry_delay' in config:
                self.retry_delay = int(config['retry_delay'])
            
            log_step("batch_manager", f"Configuration updated: {config}", "info")

# Global batch manager instance
_batch_manager = None

def get_batch_manager() -> BatchManager:
    """Get global batch manager instance"""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchManager()
    return _batch_manager

def main():
    """Main function for testing"""
    if len(sys.argv) < 2:
        print("Usage: python3 batch_manager.py <command>")
        print("Commands: stats, sync, clear, test, config")
        return
    
    command = sys.argv[1]
    batch_manager = get_batch_manager()
    
    if command == "stats":
        stats = batch_manager.get_stats()
        print("📊 Batch Manager Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif command == "sync":
        result = batch_manager.sync_batches()
        print(f"✅ Synced {result['total_synced']} operations")
        print(f"  GET operations: {result['get_synced']}")
        print(f"  POST operations: {result['post_synced']}")
    
    elif command == "clear":
        batch_manager.clear_batches()
        print("✅ All batches and cache cleared")
    
    elif command == "test":
        # Test batch functionality
        print("🧪 Testing batch manager functionality...")
        
        # Test GET operation (will be queued)
        print("Testing GET operation (queued):")
        result = batch_manager.get("pipeline_logs", {"limit": 5})
        print(f"GET result: {result}")
        
        # Test POST operation (will be queued)
        print("Testing POST operation (queued):")
        test_data = {
            "step": "test",
            "status": "success",
            "message": "Batch manager test"
        }
        result = batch_manager.post("pipeline_logs", test_data)
        print(f"POST result: {result}")
        
        # Show stats
        stats = batch_manager.get_stats()
        print(f"Pending GET operations: {stats['pending_get_operations']}")
        print(f"Pending POST operations: {stats['pending_post_operations']}")
        print(f"Total operations: {stats['total_operations']}")
        
        # Sync operations
        print("Syncing operations...")
        sync_result = batch_manager.sync_batches()
        print(f"Synced: {sync_result['total_synced']} operations")
        
        # Show final stats
        stats = batch_manager.get_stats()
        print(f"Hit rate: {stats['hit_rate']}%")
        print(f"API calls saved: {stats['api_calls_saved']}")
        print(f"Successful syncs: {stats['successful_syncs']}")
    
    elif command == "config":
        config = {
            'batch_size': batch_manager.batch_size,
            'sync_interval': batch_manager.sync_interval,
            'cache_ttl': batch_manager.cache_ttl,
            'max_retries': batch_manager.max_retries,
            'retry_delay': batch_manager.retry_delay
        }
        print("⚙️ Current Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()