#!/usr/bin/env python3
"""
iCloudPD wrapper with Telegram 2FA integration
Handles 2FA authentication by providing codes from Telegram bot
"""

import os
import sys
import subprocess
import threading
import time
import queue
import re
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils import log_step
from intelligent_2fa_handler import Intelligent2FAHandler

class iCloudPDWith2FA:
    def __init__(self):
        """Initialize iCloudPD with 2FA handler"""
        self.handler = Intelligent2FAHandler()
        self.input_queue = queue.Queue()
        self.process = None
        self.code_provided = False
        
        log_step("icloudpd_2fa", "iCloudPD with Telegram 2FA initialized", "info")
    
    def run_icloudpd(self, args: list) -> int:
        """Run icloudpd with 2FA support"""
        try:
            # Build command
            cmd = ['/opt/media-pipeline/venv/bin/icloudpd'] + args
            
            log_step("icloudpd_2fa", f"Running icloudpd: {' '.join(cmd[:4])}...", "info")
            
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start threads for monitoring
            stdout_thread = threading.Thread(target=self._monitor_stdout)
            stderr_thread = threading.Thread(target=self._monitor_stderr)
            input_thread = threading.Thread(target=self._monitor_input)
            
            stdout_thread.start()
            stderr_thread.start()
            input_thread.start()
            
            # Wait for process to complete
            return_code = self.process.wait()
            
            # Wait for threads to finish
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            input_thread.join(timeout=5)
            
            log_step("icloudpd_2fa", f"iCloudPD completed with return code: {return_code}", "info")
            return return_code
            
        except Exception as e:
            log_step("icloudpd_2fa", f"Error running icloudpd: {e}", "error")
            return 1
    
    def _monitor_stdout(self):
        """Monitor stdout for 2FA prompts"""
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    print(line.strip())
                    
                    # Check for 2FA prompt
                    if self._is_2fa_prompt(line):
                        self._handle_2fa_prompt()
                        
        except Exception as e:
            log_step("icloudpd_2fa", f"Error monitoring stdout: {e}", "error")
    
    def _monitor_stderr(self):
        """Monitor stderr for errors and 2FA prompts"""
        try:
            for line in iter(self.process.stderr.readline, ''):
                if line:
                    print(line.strip(), file=sys.stderr)
                    
                    # Check for 2FA prompt in stderr
                    if self._is_2fa_prompt(line):
                        self._handle_2fa_prompt()
                        
        except Exception as e:
            log_step("icloudpd_2fa", f"Error monitoring stderr: {e}", "error")
    
    def _monitor_input(self):
        """Monitor for input requests and provide 2FA codes"""
        try:
            while self.process and self.process.poll() is None:
                if not self.input_queue.empty():
                    input_data = self.input_queue.get()
                    if input_data:
                        self.process.stdin.write(input_data + '\n')
                        self.process.stdin.flush()
                        log_step("icloudpd_2fa", f"Provided input: {input_data}", "info")
                
                time.sleep(0.1)
                
        except Exception as e:
            log_step("icloudpd_2fa", f"Error monitoring input: {e}", "error")
    
    def _is_2fa_prompt(self, line: str) -> bool:
        """Check if line contains 2FA prompt"""
        line_lower = line.lower()
        return (
            'two-factor authentication' in line_lower or
            '2fa' in line_lower or
            'authentication code' in line_lower or
            'enter two-factor' in line_lower or
            'please enter' in line_lower and 'code' in line_lower
        )
    
    def _handle_2fa_prompt(self):
        """Handle 2FA prompt by requesting code from Telegram"""
        if self.code_provided:
            return  # Already handled this prompt
            
        log_step("icloudpd_2fa", "2FA prompt detected, requesting code from Telegram", "info")
        
        # Request 2FA code
        code = self.handler.wait_for_2fa_code("iCloud Download", 5)
        
        if code:
            log_step("icloudpd_2fa", f"2FA code received: {code}", "info")
            self.input_queue.put(code)
            self.code_provided = True
        else:
            log_step("icloudpd_2fa", "No 2FA code received, icloudpd will fail", "error")
            # Send empty input to continue
            self.input_queue.put("")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 icloudpd_with_telegram_2fa.py <icloudpd_args>")
        print("Example: python3 icloudpd_with_telegram_2fa.py --directory /path --username user --password pass")
        return 1
    
    # Get icloudpd arguments
    icloudpd_args = sys.argv[1:]
    
    # Run icloudpd with 2FA support
    wrapper = iCloudPDWith2FA()
    return wrapper.run_icloudpd(icloudpd_args)

if __name__ == "__main__":
    sys.exit(main())