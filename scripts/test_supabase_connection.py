#!/usr/bin/env python3
"""
Test Supabase connection and configuration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/settings.env")

def test_supabase_config():
    """Test Supabase configuration"""
    print("=== Supabase Configuration Test ===")
    
    # Get configuration
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_KEY: {'SET' if supabase_key else 'NOT SET'}")
    
    if supabase_key:
        print(f"SUPABASE_KEY (first 20 chars): {supabase_key[:20]}...")
    
    # Check if configuration looks valid
    if not supabase_url or supabase_url == "https://your-project.supabase.co":
        print("✗ SUPABASE_URL is not configured (still has placeholder value)")
        return False
    
    if not supabase_key or supabase_key.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6..."):
        print("✗ SUPABASE_KEY is not configured (still has placeholder value)")
        return False
    
    print("✓ Configuration looks valid")
    return True

def test_supabase_connection():
    """Test actual Supabase connection"""
    print("\n=== Supabase Connection Test ===")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        print("Creating Supabase client...")
        supabase = create_client(supabase_url, supabase_key)
        print("✓ Supabase client created successfully")
        
        # Test a simple query
        print("Testing database connection...")
        result = supabase.table("media_files").select("id").limit(1).execute()
        print(f"✓ Database connection successful (found {len(result.data)} records)")
        
        return True
        
    except Exception as e:
        print(f"✗ Supabase connection failed: {e}")
        return False

def test_utils_import():
    """Test importing utils module"""
    print("\n=== Utils Import Test ===")
    
    try:
        # Change to the scripts directory to import utils
        import sys
        sys.path.insert(0, '/opt/media-pipeline/scripts')
        
        from utils import log_step
        print("✓ Utils module imported successfully")
        
        # Test logging
        log_step("test", "Test log message", "info")
        print("✓ Logging function works")
        
        return True
        
    except Exception as e:
        print(f"✗ Utils import failed: {e}")
        return False

def main():
    """Main test function"""
    print("Testing Supabase setup...")
    
    # Test 1: Configuration
    config_ok = test_supabase_config()
    
    if not config_ok:
        print("\n=== Configuration Issues ===")
        print("Please update your config/settings.env file with:")
        print("1. Your actual Supabase project URL")
        print("2. Your actual Supabase API key")
        print("\nYou can find these in your Supabase dashboard:")
        print("- Go to Settings > API")
        print("- Copy the Project URL and anon/public key")
        return False
    
    # Test 2: Connection
    connection_ok = test_supabase_connection()
    
    if not connection_ok:
        print("\n=== Connection Issues ===")
        print("Please check:")
        print("1. Your Supabase project is running")
        print("2. Your API key has the correct permissions")
        print("3. Your network can reach Supabase")
        return False
    
    # Test 3: Utils import
    utils_ok = test_utils_import()
    
    if not utils_ok:
        print("\n=== Utils Import Issues ===")
        print("There might be an issue with the utils module")
        return False
    
    print("\n✓ All tests passed! Supabase is working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
