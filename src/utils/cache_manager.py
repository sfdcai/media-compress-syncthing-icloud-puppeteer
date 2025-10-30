#!/usr/bin/env python3
"""
Unified Cache Manager for Media Pipeline
Provides intelligent caching for Supabase operations to reduce API costs
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3
import hashlib
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, 'config', 'settings.env'))

# Use simple logging to avoid circular imports
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def log_step(step, message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} [{level.upper()}] {step}: {message}")

class UnifiedCacheManager:
    def __init__(self):
        """Initialize unified cache manager"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        # Cache configuration
        self.cache_dir = project_root / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        self.db_path = self.cache_dir / "unified_cache.db"
        self.stats_path = self.cache_dir / "cache_stats.json"
        
        # Cache settings
        self.default_ttl = 300  # 5 minutes
        self.max_cache_size = 1000  # Maximum cached items
        self.batch_size = 50  # Batch operations size
        
        # Statistics
        self.stats = self._load_stats()
        self.lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        log_step("unified_cache_manager", "Unified cache manager initialized", "info")
    
    def _init_database(self):
        """Initialize cache database"""
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute('PRAGMA journal_mode=WAL')  # Use WAL mode for better concurrency
                conn.execute('PRAGMA synchronous=NORMAL')  # Faster writes
                cursor = conn.cursor()
                
                # Create cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        params TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_endpoint ON cache_entries(endpoint)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)')
                
                conn.commit()
                
        except Exception as e:
            log_step("unified_cache_manager", f"Error initializing cache database: {e}", "error")
    
    def _load_stats(self) -> Dict:
        """Load cache statistics"""
        try:
            if self.stats_path.exists():
                with open(self.stats_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            log_step("unified_cache_manager", f"Error loading stats: {e}", "warning")
        
        return {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls_saved': 0,
            'cache_size': 0,
            'last_reset': datetime.now().isoformat()
        }
    
    def _save_stats(self):
        """Save cache statistics"""
        try:
            with open(self.stats_path, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            log_step("unified_cache_manager", f"Error saving stats: {e}", "warning")
    
    def _generate_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for request"""
        key_data = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired cache entries"""
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute('PRAGMA journal_mode=WAL')
                cursor = conn.cursor()
                
                # Delete expired entries
                cursor.execute('''
                    DELETE FROM cache_entries 
                    WHERE expires_at < CURRENT_TIMESTAMP
                ''')
                
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    log_step("unified_cache_manager", f"Cleaned up {deleted_count} expired cache entries", "info")
                
                conn.commit()
                
        except Exception as e:
            log_step("unified_cache_manager", f"Error cleaning up cache: {e}", "error")
    
    def _cleanup_lru(self):
        """Remove least recently used entries if cache is too large"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current cache size
                cursor.execute('SELECT COUNT(*) FROM cache_entries')
                current_size = cursor.fetchone()[0]
                
                if current_size > self.max_cache_size:
                    # Delete oldest entries
                    excess = current_size - self.max_cache_size
                    cursor.execute('''
                        DELETE FROM cache_entries 
                        WHERE key IN (
                            SELECT key FROM cache_entries 
                            ORDER BY last_accessed ASC 
                            LIMIT ?
                        )
                    ''', (excess,))
                    
                    deleted_count = cursor.rowcount
                    log_step("unified_cache_manager", f"Cleaned up {deleted_count} LRU cache entries", "info")
                
                conn.commit()
                
        except Exception as e:
            log_step("unified_cache_manager", f"Error cleaning up LRU cache: {e}", "error")
    
    def get(self, endpoint: str, params: Dict = None, ttl: int = None) -> Optional[Dict]:
        """Get data from cache or Supabase"""
        with self.lock:
            cache_key = self._generate_cache_key(endpoint, params)
            ttl = ttl or self.default_ttl
            
            # Update statistics
            self.stats['total_requests'] += 1
            
            try:
                with sqlite3.connect(self.db_path, timeout=30) as conn:
                    conn.execute('PRAGMA journal_mode=WAL')
                    cursor = conn.cursor()
                    
                    # Check cache
                    cursor.execute('''
                        SELECT value, expires_at FROM cache_entries 
                        WHERE key = ? AND expires_at > CURRENT_TIMESTAMP
                    ''', (cache_key,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        value, expires_at = result
                        
                        # Update access count and last accessed
                        cursor.execute('''
                            UPDATE cache_entries 
                            SET access_count = access_count + 1, 
                                last_accessed = CURRENT_TIMESTAMP
                            WHERE key = ?
                        ''', (cache_key,))
                        conn.commit()
                        
                        # Cache hit
                        self.stats['cache_hits'] += 1
                        self.stats['api_calls_saved'] += 1
                        
                        log_step("unified_cache_manager", f"Cache hit for {endpoint}", "debug")
                        return json.loads(value)
            
            except Exception as e:
                log_step("unified_cache_manager", f"Error reading from cache: {e}", "error")
            
            # Cache miss - fetch from Supabase
            self.stats['cache_misses'] += 1
            
            try:
                data = self._fetch_from_supabase(endpoint, params)
                
                if data is not None:
                    # Store in cache
                    self._store_in_cache(cache_key, endpoint, params, data, ttl)
                    log_step("unified_cache_manager", f"Cache miss for {endpoint}, fetched from Supabase", "debug")
                
                return data
                
            except Exception as e:
                log_step("unified_cache_manager", f"Error fetching from Supabase: {e}", "error")
                return None
    
    def _fetch_from_supabase(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Fetch data from Supabase API with graceful error handling"""
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
                log_step("unified_cache_manager", f"Supabase API error: {response.status_code}", "error")
                return None
                
        except requests.exceptions.ConnectionError as e:
            log_step("unified_cache_manager", f"Network connection error: {e}", "warning")
            return None
        except requests.exceptions.Timeout as e:
            log_step("unified_cache_manager", f"Request timeout: {e}", "warning")
            return None
        except Exception as e:
            log_step("unified_cache_manager", f"Error fetching from Supabase: {e}", "error")
            return None
    
    def _store_in_cache(self, key: str, endpoint: str, params: Dict, data: Dict, ttl: int):
        """Store data in cache"""
        try:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute('PRAGMA journal_mode=WAL')
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, endpoint, params, expires_at, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                ''', (
                    key,
                    json.dumps(data),
                    endpoint,
                    json.dumps(params or {}),
                    expires_at.isoformat()
                ))
                
                conn.commit()
            
            # Update cache size
            self.stats['cache_size'] = self._get_cache_size()
            
            # Periodic cleanup
            if self.stats['total_requests'] % 100 == 0:
                self._cleanup_expired()
                self._cleanup_lru()
                self._save_stats()
                
        except Exception as e:
            log_step("unified_cache_manager", f"Error storing in cache: {e}", "error")
    
    def _get_cache_size(self) -> int:
        """Get current cache size"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM cache_entries')
                return cursor.fetchone()[0]
        except:
            return 0
    
    def post(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """Post data to Supabase and optionally invalidate cache"""
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
                result = response.json()
                return result
            else:
                log_step("unified_cache_manager", f"Supabase POST error: {response.status_code}", "error")
                return None
                
        except requests.exceptions.ConnectionError as e:
            log_step("unified_cache_manager", f"Network connection error: {e}", "warning")
            return None
        except requests.exceptions.Timeout as e:
            log_step("unified_cache_manager", f"Request timeout: {e}", "warning")
            return None
        except Exception as e:
            log_step("unified_cache_manager", f"Error posting to Supabase: {e}", "error")
            return None
    
    def _invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA busy_timeout=5000')
                cursor = conn.cursor()
                
                # Delete entries matching pattern
                cursor.execute('DELETE FROM cache_entries WHERE endpoint LIKE ?', (f'%{pattern}%',))
                
                invalidated_count = cursor.rowcount
                
                if invalidated_count > 0:
                    log_step("unified_cache_manager", f"Invalidated {invalidated_count} cache entries for {pattern}", "info")
                
                conn.commit()
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                log_step("unified_cache_manager", f"Database locked, skipping invalidation for {pattern}", "warning")
            else:
                log_step("unified_cache_manager", f"Database error invalidating cache: {e}", "error")
        except Exception as e:
            log_step("unified_cache_manager", f"Error invalidating cache: {e}", "error")
    
    def batch_get(self, requests: List[Dict]) -> List[Dict]:
        """Batch get multiple requests"""
        results = []
        
        for req in requests:
            endpoint = req.get('endpoint')
            params = req.get('params')
            ttl = req.get('ttl')
            
            result = self.get(endpoint, params, ttl)
            results.append(result)
        
        return results
    
    def batch_post(self, requests: List[Dict]) -> List[Dict]:
        """Batch post multiple requests"""
        results = []
        
        for req in requests:
            endpoint = req.get('endpoint')
            data = req.get('data')
            
            result = self.post(endpoint, data)
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            # Update cache size
            self.stats['cache_size'] = self._get_cache_size()
            
            # Calculate hit rate
            total_requests = self.stats['total_requests']
            if total_requests > 0:
                hit_rate = (self.stats['cache_hits'] / total_requests) * 100
                self.stats['hit_rate'] = round(hit_rate, 2)
            else:
                self.stats['hit_rate'] = 0
            
            # Calculate API calls saved
            self.stats['api_calls_saved'] = self.stats['cache_hits']
            
            return self.stats.copy()
    
    def clear_cache(self):
        """Clear all cache entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM cache_entries')
                deleted_count = cursor.rowcount
                conn.commit()
            
            # Reset statistics
            self.stats = {
                'total_requests': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'api_calls_saved': 0,
                'cache_size': 0,
                'last_reset': datetime.now().isoformat()
            }
            self._save_stats()
            
            log_step("unified_cache_manager", f"Cleared {deleted_count} cache entries", "info")
            
        except Exception as e:
            log_step("unified_cache_manager", f"Error clearing cache: {e}", "error")
    
    def optimize_cache(self):
        """Optimize cache by removing unused entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Remove entries with low access count and old last access
                cursor.execute('''
                    DELETE FROM cache_entries 
                    WHERE access_count < 2 
                    AND last_accessed < datetime('now', '-1 hour')
                ''')
                
                optimized_count = cursor.rowcount
                conn.commit()
            
            log_step("unified_cache_manager", f"Optimized {optimized_count} cache entries", "info")
            
        except Exception as e:
            log_step("unified_cache_manager", f"Error optimizing cache: {e}", "error")

# Global cache manager instance
_cache_manager = None

def get_cache_manager() -> UnifiedCacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = UnifiedCacheManager()
    return _cache_manager

def main():
    """Main function for testing"""
    if len(sys.argv) < 2:
        print("Usage: python3 cache_manager.py <command>")
        print("Commands: stats, clear, optimize, test")
        return
    
    command = sys.argv[1]
    cache_manager = get_cache_manager()
    
    if command == "stats":
        stats = cache_manager.get_stats()
        print("📊 Cache Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif command == "clear":
        cache_manager.clear_cache()
        print("✅ Cache cleared")
    
    elif command == "optimize":
        cache_manager.optimize_cache()
        print("✅ Cache optimized")
    
    elif command == "test":
        # Test cache functionality
        print("🧪 Testing unified cache functionality...")
        
        # Test GET request (first call - should be cache miss)
        print("First GET request (should be cache miss):")
        result = cache_manager.get("pipeline_logs", {"limit": 5})
        print(f"GET test: {len(result) if result else 0} records")
        
        # Test GET request (second call - should be cache hit)
        print("Second GET request (should be cache hit):")
        result = cache_manager.get("pipeline_logs", {"limit": 5})
        print(f"GET test: {len(result) if result else 0} records")
        
        # Test POST request
        test_data = {
            "step": "test",
            "status": "success",
            "message": "Unified cache test"
        }
        result = cache_manager.post("pipeline_logs", test_data)
        print(f"POST test: {'Success' if result else 'Failed'}")
        
        # Show stats
        stats = cache_manager.get_stats()
        print(f"Hit rate: {stats['hit_rate']}%")
        print(f"Cache size: {stats['cache_size']} entries")
        print(f"API calls saved: {stats['api_calls_saved']}")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Cache misses: {stats['cache_misses']}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()