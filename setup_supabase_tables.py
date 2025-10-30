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

from supabase_schema import INDEXES, TABLES

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
    
    sql_commands = list(TABLES.values())

    try:
        # Execute table creation commands
        for i, sql in enumerate(sql_commands, 1):
            print_status("INFO", f"Creating table {i}/{len(sql_commands)}...")
            result = supabase.rpc('exec_sql', {'sql': sql.strip()})
            print_status("SUCCESS", f"Table {i} created successfully")
        
        # Execute index creation commands
        print_status("INFO", "Creating indexes...")
        for i, sql in enumerate(INDEXES, 1):
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
    
    tables_to_test = list(TABLES.keys())
    
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
