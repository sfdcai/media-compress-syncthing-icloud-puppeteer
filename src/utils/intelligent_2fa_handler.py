#!/usr/bin/env python3
"""
Intelligent 2FA Handler for Media Pipeline
Integrates with enhanced Telegram bot and handles 2FA for all pipeline steps
"""

import os
import sys
import json
import time
import requests
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils import log_step
from enhanced_telegram_bot import EnhancedTelegramBot
from core.local_db_manager import get_db_manager

class Intelligent2FAHandler:
    def __init__(self):
        """Initialize intelligent 2FA handler"""
        self.bot = EnhancedTelegramBot()
        self.db_manager = get_db_manager()
        self.active_requests = {}
        
        log_step("intelligent_2fa_handler", "Intelligent 2FA handler initialized", "info")
    
    def create_2fa_request(self, pipeline_step: str, timeout_minutes: int = 5) -> str:
        """Create a new 2FA request"""
        request_id = f"2fa_{int(time.time())}_{pipeline_step.replace(' ', '_').lower()}"
        
        # Create request in local database
        try:
            self.db_manager.create_2fa_request(request_id, pipeline_step, timeout_minutes)
            log_step("intelligent_2fa_handler", f"Created 2FA request: {request_id}", "info")
        except Exception as e:
            log_step("intelligent_2fa_handler", f"Error creating request: {e}", "error")
            return None
        
        return request_id
    
    def _store_request_in_supabase(self, request_data: Dict):
        """Store 2FA request in Supabase (optional)"""
        try:
            # For now, skip Supabase storage and use local storage only
            # This avoids the table creation issue
            log_step("intelligent_2fa_handler", f"Storing request locally: {request_data['id']}", "debug")
        except Exception as e:
            log_step("intelligent_2fa_handler", f"Error storing request: {e}", "warning")
    
    def _update_request_in_supabase(self, request_id: str, updates: Dict):
        """Update 2FA request in Supabase (optional)"""
        try:
            # For now, skip Supabase updates and use local storage only
            log_step("intelligent_2fa_handler", f"Updating request locally: {request_id}", "debug")
        except Exception as e:
            log_step("intelligent_2fa_handler", f"Error updating request: {e}", "warning")
    
    def wait_for_2fa_code(self, pipeline_step: str = "iCloud Operation", timeout_minutes: int = 5) -> Optional[str]:
        """Wait for 2FA code with intelligent handling"""
        request_id = self.create_2fa_request(pipeline_step, timeout_minutes)
        
        if not request_id:
            log_step("intelligent_2fa_handler", "Failed to create 2FA request", "error")
            return None
        
        # Send Telegram notification
        if not self.bot.send_2fa_request(pipeline_step, request_id):
            log_step("intelligent_2fa_handler", "Failed to send Telegram notification", "error")
            return None
        
        log_step("intelligent_2fa_handler", f"Waiting for 2FA code for {pipeline_step}", "info")
        
        # Wait for code with intelligent polling
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            # Check local database for request status
            try:
                request_data = self.db_manager.get_2fa_request(request_id)
                if request_data:
                    if request_data['status'] == 'completed' and request_data['code']:
                        log_step("intelligent_2fa_handler", f"2FA code received: {request_data['code']}", "info")
                        return request_data['code']
                    
                    # Check if expired
                    expires_at = datetime.fromisoformat(request_data['expires_at'])
                    if datetime.now() > expires_at:
                        log_step("intelligent_2fa_handler", "2FA request expired", "warning")
                        break
                else:
                    log_step("intelligent_2fa_handler", f"Request {request_id} not found in database", "error")
                    break
                    
            except Exception as e:
                log_step("intelligent_2fa_handler", f"Error checking request status: {e}", "error")
            
            time.sleep(2)  # Check every 2 seconds
        
        # Timeout
        log_step("intelligent_2fa_handler", "2FA timeout - no code received", "error")
        self._cleanup_request(request_id)
        return None
    
    def _check_supabase_status(self, request_id: str):
        """Check Supabase for request status updates (optional)"""
        try:
            # For now, skip Supabase checks and use local storage only
            log_step("intelligent_2fa_handler", f"Checking request locally: {request_id}", "debug")
        except Exception as e:
            log_step("intelligent_2fa_handler", f"Error checking status: {e}", "warning")
    
    def submit_2fa_code(self, request_id: str, code: str) -> bool:
        """Submit 2FA code for a request"""
        try:
            # Update request in local database
            success = self.db_manager.update_2fa_request(request_id, 'completed', code)
            
            if success:
                log_step("intelligent_2fa_handler", f"2FA code submitted: {code}", "info")
                return True
            else:
                log_step("intelligent_2fa_handler", f"Failed to update request {request_id}", "error")
                return False
            
        except Exception as e:
            log_step("intelligent_2fa_handler", f"Error submitting code: {e}", "error")
            return False
    
    def _cleanup_request(self, request_id: str):
        """Clean up expired request"""
        if request_id in self.active_requests:
            del self.active_requests[request_id]
        
        # Mark as expired locally
        log_step("intelligent_2fa_handler", f"Cleaned up request: {request_id}", "debug")
    
    def get_active_requests(self) -> Dict:
        """Get all active 2FA requests"""
        try:
            # Get pending requests from local database
            pending_requests = self.db_manager.get_pending_2fa_requests()
            return {req['id']: req for req in pending_requests}
        except Exception as e:
            log_step("intelligent_2fa_handler", f"Error getting active requests: {e}", "error")
            return {}
    
    def clear_expired_requests(self) -> int:
        """Clear expired requests"""
        expired_count = 0
        current_time = datetime.now()
        
        for request_id, request_data in list(self.active_requests.items()):
            expires_at = datetime.fromisoformat(request_data['expires_at'])
            if current_time > expires_at:
                self._cleanup_request(request_id)
                expired_count += 1
        
        return expired_count

def main():
    """Main function for testing"""
    if len(sys.argv) < 2:
        print("Usage: python3 intelligent_2fa_handler.py <command> [args]")
        print("Commands:")
        print("  wait <pipeline_step> [timeout_minutes] - Wait for 2FA code")
        print("  submit <request_id> <code> - Submit 2FA code")
        print("  status - Show active requests")
        print("  clear - Clear expired requests")
        return
    
    command = sys.argv[1]
    handler = Intelligent2FAHandler()
    
    if command == "wait":
        pipeline_step = sys.argv[2] if len(sys.argv) > 2 else "Test Pipeline"
        timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        
        print(f"🔐 Waiting for 2FA code for: {pipeline_step}")
        code = handler.wait_for_2fa_code(pipeline_step, timeout)
        
        if code:
            print(f"✅ 2FA code received: {code}")
        else:
            print("❌ No 2FA code received (timeout)")
    
    elif command == "submit":
        if len(sys.argv) < 4:
            print("Usage: submit <request_id> <code>")
            return
        
        request_id = sys.argv[2]
        code = sys.argv[3]
        
        if handler.submit_2fa_code(request_id, code):
            print(f"✅ 2FA code submitted for {request_id}")
        else:
            print(f"❌ Failed to submit 2FA code for {request_id}")
    
    elif command == "status":
        requests = handler.get_active_requests()
        print(f"📊 Active 2FA requests: {len(requests)}")
        for req_id, req_data in requests.items():
            print(f"  - {req_id}: {req_data['pipeline_step']} ({req_data['status']})")
    
    elif command == "clear":
        cleared = handler.clear_expired_requests()
        print(f"🧹 Cleared {cleared} expired requests")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()