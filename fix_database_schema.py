#!/usr/bin/env python3
"""
Fix database schema by adding missing synced_to_supabase columns
"""

import sys
import os
sys.path.append('/opt/media-pipeline/src')

from core.local_db_manager import get_db_manager

def fix_database_schema():
    """Add missing synced_to_supabase columns to all tables"""
    print("🔧 Fixing database schema...")
    
    try:
        db = get_db_manager()
        
        # Tables that need the synced_to_supabase column
        tables = ['media_files', 'batches', 'pipeline_logs']
        
        for table in tables:
            try:
                print(f"Adding synced_to_supabase column to {table}...")
                db._execute_query(f'ALTER TABLE {table} ADD COLUMN synced_to_supabase BOOLEAN DEFAULT FALSE')
                print(f"✅ Added synced_to_supabase column to {table}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"✅ Column already exists in {table}")
                else:
                    print(f"❌ Error adding column to {table}: {e}")
        
        print("\n🎉 Database schema fix complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False

if __name__ == "__main__":
    fix_database_schema()