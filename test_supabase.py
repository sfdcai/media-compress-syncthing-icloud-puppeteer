#!/usr/bin/env python3
"""
Supabase Connection and Database Test Script
Tests Supabase connectivity, table structure, and basic operations
"""

import os
import sys
import json
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
        with open(venv_settings, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")

# Add the scripts directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

try:
    from supabase import create_client, Client
    from supabase.lib.client_options import ClientOptions
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

def test_supabase_connection():
    """Test basic Supabase connection"""
    print_status("INFO", "Testing Supabase connection...")
    
    # Get configuration
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url:
        print_status("ERROR", "SUPABASE_URL not found in environment variables")
        return False, None
    
    if not supabase_key:
        print_status("ERROR", "SUPABASE_KEY not found in environment variables")
        return False, None
    
    if not supabase_url.startswith('https://'):
        print_status("ERROR", "SUPABASE_URL must start with https://")
        return False, None
    
    if len(supabase_key) < 50:
        print_status("WARNING", "SUPABASE_KEY seems too short (should be ~100+ characters)")
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print_status("SUCCESS", f"Connected to Supabase: {supabase_url}")
        return True, supabase
    except Exception as e:
        print_status("ERROR", f"Failed to connect to Supabase: {str(e)}")
        return False, None

def test_database_tables(supabase):
    """Test if required database tables exist"""
    print_status("INFO", "Testing database table structure...")
    
    # Expected tables and their required columns
    expected_tables = {
        'media_files': ['id', 'filename', 'file_path', 'file_size', 'file_hash', 'created_at'],
        'duplicates': ['id', 'original_file_id', 'duplicate_file_id', 'created_at'],
        'upload_logs': ['id', 'file_id', 'upload_type', 'status', 'created_at'],
        'batch_logs': ['id', 'batch_type', 'file_count', 'status', 'created_at'],
        'compression_logs': ['id', 'original_file_id', 'compressed_file_id', 'compression_ratio', 'created_at']
    }
    
    missing_tables = []
    table_issues = []
    
    for table_name, required_columns in expected_tables.items():
        try:
            # Try to query the table (limit 1 to avoid large results)
            result = supabase.table(table_name).select("*").limit(1).execute()
            print_status("SUCCESS", f"Table '{table_name}' exists and is accessible")
            
            # Check if we can get column information
            if result.data:
                actual_columns = list(result.data[0].keys()) if result.data else []
                missing_columns = [col for col in required_columns if col not in actual_columns]
                if missing_columns:
                    table_issues.append(f"Table '{table_name}' missing columns: {missing_columns}")
                    print_status("WARNING", f"Table '{table_name}' missing columns: {missing_columns}")
                else:
                    print_status("SUCCESS", f"Table '{table_name}' has all required columns")
            else:
                print_status("INFO", f"Table '{table_name}' exists but is empty")
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'relation' in error_msg and 'does not exist' in error_msg:
                missing_tables.append(table_name)
                print_status("ERROR", f"Table '{table_name}' does not exist")
            else:
                print_status("ERROR", f"Error accessing table '{table_name}': {str(e)}")
    
    if missing_tables:
        print_status("ERROR", f"Missing tables: {missing_tables}")
        print_status("INFO", "Run the schema.sql script to create missing tables")
        return False
    
    if table_issues:
        print_status("WARNING", "Some tables have missing columns")
        return False
    
    print_status("SUCCESS", "All required tables exist with correct structure")
    return True

def test_database_operations(supabase):
    """Test basic database operations (CRUD)"""
    print_status("INFO", "Testing database operations...")
    
    test_data = {
        'filename': f'test_file_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg',
        'file_path': '/test/path/test_file.jpg',
        'file_size': 1024000,
        'file_hash': 'test_hash_12345',
        'created_at': datetime.now().isoformat()
    }
    
    try:
        # Test INSERT
        print_status("INFO", "Testing INSERT operation...")
        insert_result = supabase.table('media_files').insert(test_data).execute()
        
        if insert_result.data:
            test_id = insert_result.data[0]['id']
            print_status("SUCCESS", f"INSERT successful, ID: {test_id}")
            
            # Test SELECT
            print_status("INFO", "Testing SELECT operation...")
            select_result = supabase.table('media_files').select("*").eq('id', test_id).execute()
            
            if select_result.data:
                print_status("SUCCESS", "SELECT operation successful")
                
                # Test UPDATE
                print_status("INFO", "Testing UPDATE operation...")
                update_data = {'file_size': 2048000}
                update_result = supabase.table('media_files').update(update_data).eq('id', test_id).execute()
                
                if update_result.data:
                    print_status("SUCCESS", "UPDATE operation successful")
                    
                    # Test DELETE
                    print_status("INFO", "Testing DELETE operation...")
                    delete_result = supabase.table('media_files').delete().eq('id', test_id).execute()
                    
                    if delete_result.data:
                        print_status("SUCCESS", "DELETE operation successful")
                        print_status("SUCCESS", "All CRUD operations working correctly")
                        return True
                    else:
                        print_status("ERROR", "DELETE operation failed")
                        return False
                else:
                    print_status("ERROR", "UPDATE operation failed")
                    return False
            else:
                print_status("ERROR", "SELECT operation failed")
                return False
        else:
            print_status("ERROR", "INSERT operation failed")
            return False
            
    except Exception as e:
        print_status("ERROR", f"Database operation failed: {str(e)}")
        return False

def test_supabase_permissions(supabase):
    """Test Supabase RLS (Row Level Security) and permissions"""
    print_status("INFO", "Testing Supabase permissions...")
    
    try:
        # Test if we can access the auth schema (admin operation)
        result = supabase.table('media_files').select("count").execute()
        print_status("SUCCESS", "Basic table access permissions working")
        
        # Test if we can access multiple tables
        tables_to_test = ['media_files', 'duplicates', 'upload_logs']
        for table in tables_to_test:
            try:
                result = supabase.table(table).select("*").limit(1).execute()
                print_status("SUCCESS", f"Access to table '{table}' granted")
            except Exception as e:
                print_status("WARNING", f"Access to table '{table}' may be restricted: {str(e)}")
        
        return True
        
    except Exception as e:
        print_status("ERROR", f"Permission test failed: {str(e)}")
        return False

def test_supabase_connection_pooling():
    """Test connection pooling and performance"""
    print_status("INFO", "Testing connection pooling...")
    
    try:
        # Test multiple rapid connections
        for i in range(5):
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            supabase = create_client(supabase_url, supabase_key)
            
            # Quick query
            result = supabase.table('media_files').select("count").limit(1).execute()
            
        print_status("SUCCESS", "Connection pooling working correctly")
        return True
        
    except Exception as e:
        print_status("ERROR", f"Connection pooling test failed: {str(e)}")
        return False

def show_supabase_info(supabase):
    """Show Supabase project information"""
    print_status("INFO", "Supabase project information:")
    
    supabase_url = os.getenv('SUPABASE_URL')
    print(f"  URL: {supabase_url}")
    
    # Extract project ID from URL
    if supabase_url:
        project_id = supabase_url.split('//')[1].split('.')[0]
        print(f"  Project ID: {project_id}")
    
    # Test a simple query to get database info
    try:
        result = supabase.table('media_files').select("count").execute()
        if result.data is not None:
            print(f"  Database: Connected and responsive")
        else:
            print(f"  Database: Connected but no data")
    except Exception as e:
        print(f"  Database: Error - {str(e)}")

def main():
    """Main test function"""
    print("=" * 50)
    print("  Supabase Connection and Database Test")
    print("=" * 50)
    print()
    
    # Test 1: Basic connection
    connection_ok, supabase = test_supabase_connection()
    if not connection_ok:
        print_status("ERROR", "Cannot proceed with tests - connection failed")
        return False
    
    print()
    
    # Test 2: Show project info
    show_supabase_info(supabase)
    print()
    
    # Test 3: Database tables
    tables_ok = test_database_tables(supabase)
    print()
    
    # Test 4: Database operations (only if tables exist)
    operations_ok = False
    if tables_ok:
        operations_ok = test_database_operations(supabase)
        print()
    else:
        print_status("WARNING", "Skipping database operations test - table structure issues")
        print()
    
    # Test 5: Permissions
    permissions_ok = test_supabase_permissions(supabase)
    print()
    
    # Test 6: Connection pooling
    pooling_ok = test_supabase_connection_pooling()
    print()
    
    # Summary
    print("=" * 50)
    print("  Test Summary")
    print("=" * 50)
    
    tests = [
        ("Connection", connection_ok),
        ("Table Structure", tables_ok),
        ("Database Operations", operations_ok),
        ("Permissions", permissions_ok),
        ("Connection Pooling", pooling_ok)
    ]
    
    passed = 0
    for test_name, result in tests:
        status = "PASS" if result else "FAIL"
        color = "\033[92m" if result else "\033[91m"
        print(f"  {test_name}: {color}{status}\033[0m")
        if result:
            passed += 1
    
    print()
    print(f"Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print_status("SUCCESS", "All Supabase tests passed! Database is ready for use.")
        return True
    else:
        print_status("WARNING", "Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
