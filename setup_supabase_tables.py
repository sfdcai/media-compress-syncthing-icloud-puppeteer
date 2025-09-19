#!/usr/bin/env python3
"""
Setup Supabase Database Tables
Creates all required tables for the media pipeline
"""

import os
import sys
from datetime import datetime

# Try to load dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv('config/settings.env')
except ImportError:
    print("⚠️  Warning: python-dotenv not installed, using system environment variables")
    # Try to load from the virtual environment's settings
    venv_settings = '/opt/media-pipeline/config/settings.env'
    if os.path.exists(venv_settings):
        try:
            with open(venv_settings, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip('"').strip("'")
        except PermissionError:
            print("⚠️  Warning: Cannot read settings.env due to permissions")
            # Try to read from the actual file location
            actual_file = '/root/.config/media-pipeline/settings.env'
            if os.path.exists(actual_file):
                try:
                    with open(actual_file, 'r') as f:
                        for line in f:
                            if '=' in line and not line.startswith('#'):
                                key, value = line.strip().split('=', 1)
                                os.environ[key] = value.strip('"').strip("'")
                except PermissionError:
                    print("❌ Error: Cannot read settings file due to permissions")
                    print("Run: sudo chmod 644 /root/.config/media-pipeline/settings.env")

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Error: supabase package not installed")
    print("Run: sudo -u media-pipeline /opt/media-pipeline/venv/bin/pip install supabase")
    sys.exit(1)

def print_status(status, message):
    """Print colored status messages"""
    colors = {
        "INFO": "\033[94mℹ\033[0m",
        "SUCCESS": "\033[92m✓\033[0m", 
        "WARNING": "\033[93m⚠\033[0m",
        "ERROR": "\033[91m✗\033[0m"
    }
    print(f"{colors.get(status, '')} {message}")

def create_tables(supabase):
    """Create all required tables"""
    print_status("INFO", "Creating database tables...")
    
    # SQL commands to create tables
    sql_commands = [
        # Enhanced media_files table
        """
        CREATE TABLE IF NOT EXISTS media_files (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size BIGINT,
            file_hash TEXT,
            compression_ratio DECIMAL(5,2),
            is_duplicate BOOLEAN DEFAULT FALSE,
            source_path TEXT,
            status TEXT CHECK (status IN ('downloaded','deduplicated','compressed','batched','uploaded','verified','error')),
            batch_id UUID,
            created_at TIMESTAMP DEFAULT NOW(),
            processed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """,
        
        # Enhanced batches table
        """
        CREATE TABLE IF NOT EXISTS batches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            batch_type TEXT CHECK (batch_type IN ('icloud','pixel')),
            status TEXT CHECK (status IN ('created','uploading','uploaded','verified','error')),
            total_size_gb DECIMAL(10,2),
            file_count INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );
        """,
        
        # Duplicate files tracking (renamed from duplicates)
        """
        CREATE TABLE IF NOT EXISTS duplicates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            original_file_id UUID REFERENCES media_files(id),
            duplicate_file_id UUID REFERENCES media_files(id),
            hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        
        # Upload logs
        """
        CREATE TABLE IF NOT EXISTS upload_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            file_id UUID REFERENCES media_files(id),
            upload_type TEXT CHECK (upload_type IN ('icloud','pixel')),
            status TEXT CHECK (status IN ('pending','uploading','uploaded','failed')),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );
        """,
        
        # Batch logs
        """
        CREATE TABLE IF NOT EXISTS batch_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            batch_type TEXT CHECK (batch_type IN ('icloud','pixel')),
            file_count INTEGER,
            total_size_gb DECIMAL(10,2),
            status TEXT CHECK (status IN ('created','processing','completed','failed')),
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );
        """,
        
        # Compression logs
        """
        CREATE TABLE IF NOT EXISTS compression_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            original_file_id UUID REFERENCES media_files(id),
            compressed_file_id UUID REFERENCES media_files(id),
            compression_ratio DECIMAL(5,2),
            original_size BIGINT,
            compressed_size BIGINT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
        
        # Pipeline logs
        """
        CREATE TABLE IF NOT EXISTS pipeline_logs (
            id BIGSERIAL PRIMARY KEY,
            step TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT CHECK (status IN ('info','success','error','warning')),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    ]
    
    # Create indexes
    index_commands = [
        "CREATE INDEX IF NOT EXISTS idx_media_files_hash ON media_files(file_hash);",
        "CREATE INDEX IF NOT EXISTS idx_media_files_status ON media_files(status);",
        "CREATE INDEX IF NOT EXISTS idx_media_files_batch_id ON media_files(batch_id);",
        "CREATE INDEX IF NOT EXISTS idx_duplicates_hash ON duplicates(hash);",
        "CREATE INDEX IF NOT EXISTS idx_upload_logs_file_id ON upload_logs(file_id);",
        "CREATE INDEX IF NOT EXISTS idx_upload_logs_status ON upload_logs(status);",
        "CREATE INDEX IF NOT EXISTS idx_batch_logs_status ON batch_logs(status);",
        "CREATE INDEX IF NOT EXISTS idx_compression_logs_original ON compression_logs(original_file_id);",
        "CREATE INDEX IF NOT EXISTS idx_pipeline_logs_step ON pipeline_logs(step);",
        "CREATE INDEX IF NOT EXISTS idx_pipeline_logs_status ON pipeline_logs(status);"
    ]
    
    try:
        # Execute table creation commands
        for i, sql in enumerate(sql_commands, 1):
            print_status("INFO", f"Creating table {i}/{len(sql_commands)}...")
            result = supabase.rpc('exec_sql', {'sql': sql.strip()})
            print_status("SUCCESS", f"Table {i} created successfully")
        
        # Execute index creation commands
        print_status("INFO", "Creating indexes...")
        for i, sql in enumerate(index_commands, 1):
            result = supabase.rpc('exec_sql', {'sql': sql})
            print_status("SUCCESS", f"Index {i} created successfully")
        
        print_status("SUCCESS", "All tables and indexes created successfully!")
        return True
        
    except Exception as e:
        print_status("ERROR", f"Failed to create tables: {str(e)}")
        return False

def test_tables(supabase):
    """Test that all tables exist and are accessible"""
    print_status("INFO", "Testing table access...")
    
    tables_to_test = [
        'media_files',
        'duplicates', 
        'upload_logs',
        'batch_logs',
        'compression_logs',
        'pipeline_logs'
    ]
    
    all_good = True
    
    for table in tables_to_test:
        try:
            result = supabase.table(table).select("*").limit(1).execute()
            print_status("SUCCESS", f"Table '{table}' is accessible")
        except Exception as e:
            print_status("ERROR", f"Table '{table}' is not accessible: {str(e)}")
            all_good = False
    
    return all_good

def main():
    """Main function"""
    print("=" * 50)
    print("  Supabase Database Setup")
    print("=" * 50)
    print()
    
    # Get configuration
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print_status("ERROR", "SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print_status("SUCCESS", f"Connected to Supabase: {supabase_url}")
        
        # Create tables
        if create_tables(supabase):
            print()
            # Test tables
            if test_tables(supabase):
                print()
                print_status("SUCCESS", "Database setup completed successfully!")
                print()
                print_status("INFO", "You can now run the Supabase test:")
                print("  sudo -u media-pipeline /opt/media-pipeline/venv/bin/python /opt/media-pipeline/test_supabase.py")
                return True
            else:
                print_status("ERROR", "Table testing failed")
                return False
        else:
            print_status("ERROR", "Table creation failed")
            return False
            
    except Exception as e:
        print_status("ERROR", f"Failed to connect to Supabase: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
