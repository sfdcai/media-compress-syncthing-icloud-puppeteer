#!/usr/bin/env python3
"""
Simple Supabase Test Script
Quick test for Supabase connectivity and basic operations
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/settings.env')

def test_supabase_simple():
    """Simple Supabase connectivity test"""
    print("🔍 Testing Supabase Connection...")
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url:
        print("❌ SUPABASE_URL not found in config/settings.env")
        return False
    
    if not supabase_key:
        print("❌ SUPABASE_KEY not found in config/settings.env")
        return False
    
    print(f"✅ Found Supabase URL: {supabase_url}")
    print(f"✅ Found Supabase Key: {supabase_key[:20]}...")
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        # Test basic connection
        result = supabase.table('media_files').select("count").limit(1).execute()
        print("✅ Supabase connection successful!")
        print("✅ Database is accessible!")
        
        return True
        
    except ImportError:
        print("❌ Supabase package not installed")
        print("Run: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_supabase_simple()
    if success:
        print("\n🎉 Supabase is ready for use!")
    else:
        print("\n⚠️  Supabase setup needs attention")
        print("Run the full test: python3 test_supabase.py")
    
    sys.exit(0 if success else 1)
