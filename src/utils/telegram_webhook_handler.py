#!/usr/bin/env python3
"""
Telegram Webhook Handler for Media Pipeline Bot
Handles incoming messages and commands from Telegram
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime
from pathlib import Path
import subprocess
import psutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils import log_step
from enhanced_telegram_bot import EnhancedTelegramBot
from intelligent_2fa_handler import Intelligent2FAHandler

class TelegramWebhookHandler:
    def __init__(self):
        """Initialize webhook handler"""
        self.bot = EnhancedTelegramBot()
        self.handler = Intelligent2FAHandler()
        self.last_update_id = 0
        
        log_step("telegram_webhook_handler", "Telegram webhook handler initialized", "info")
    
    def process_update(self, update_data: dict):
        """Process incoming Telegram update"""
        try:
            update_id = update_data.get('update_id', 0)
            if update_id <= self.last_update_id:
                return  # Skip duplicate updates
            
            self.last_update_id = update_id
            
            # Handle different types of updates
            if 'message' in update_data:
                self._handle_message(update_data['message'])
            elif 'callback_query' in update_data:
                self._handle_callback_query(update_data['callback_query'])
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error processing update: {e}", "error")
    
    def _handle_message(self, message: dict):
        """Handle incoming message"""
        try:
            text = message.get('text', '')
            chat_id = message.get('chat', {}).get('id')
            
            if not text or chat_id != int(self.bot.chat_id):
                return  # Ignore messages from other chats
            
            # Handle commands
            if text.startswith('/'):
                self._handle_command(text, message)
            else:
                # Handle 2FA code submission
                self._handle_2fa_code(text, message)
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error handling message: {e}", "error")
    
    def _handle_command(self, command: str, message: dict):
        """Handle bot commands"""
        try:
            if command == '/start':
                self.bot.send_help_message()
            
            elif command == '/status':
                self._send_pipeline_status()
            
            elif command == '/summary':
                try:
                    success = self.bot.send_daily_summary()
                    if not success:
                        self.bot.send_message("❌ Failed to send daily summary")
                except Exception as e:
                    self.bot.send_message(f"❌ Error sending summary: {str(e)}")
            
            elif command == '/2fa_status':
                self._send_2fa_status()
            
            elif command == '/clear_2fa':
                cleared = self.handler.clear_expired_requests()
                self.bot.send_message(f"🧹 Cleared {cleared} expired 2FA requests")
            
            elif command == '/logs':
                self._send_recent_logs()
            
            elif command == '/system':
                self._send_system_info()
            
            elif command == '/help':
                self.bot.send_help_message()
            
            else:
                self.bot.send_message(f"❓ Unknown command: {command}\n\nUse /help to see available commands.")
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error handling command: {e}", "error")
            self.bot.send_message(f"❌ Error processing command: {str(e)}")
    
    def _handle_2fa_code(self, text: str, message: dict):
        """Handle 2FA code submission"""
        try:
            # Check if it looks like a 2FA code (6 digits)
            if text.isdigit() and len(text) == 6:
                # Find the most recent pending request
                active_requests = self.handler.get_active_requests()
                pending_requests = [req for req in active_requests.values() if req['status'] == 'pending']
                
                if pending_requests:
                    # Get the most recent request
                    latest_request = max(pending_requests, key=lambda x: x['created_at'])
                    request_id = latest_request['id']
                    
                    if self.handler.submit_2fa_code(request_id, text):
                        self.bot.send_message(f"✅ 2FA code received and submitted!\n\n🔐 Code: {text}\n📝 Step: {latest_request['pipeline_step']}")
                        log_step("telegram_webhook_handler", f"2FA code submitted: {text}", "info")
                    else:
                        self.bot.send_message("❌ Failed to submit 2FA code. Please try again.")
                else:
                    # Create a new request if none exists (for manual submissions)
                    request_id = self.handler.create_2fa_request("Manual 2FA Submission", 5)
                    if self.handler.submit_2fa_code(request_id, text):
                        self.bot.send_message(f"✅ 2FA code received!\n\n🔐 Code: {text}\n📝 Created manual request")
                        log_step("telegram_webhook_handler", f"Manual 2FA code submitted: {text}", "info")
                    else:
                        self.bot.send_message("❌ Failed to process 2FA code. Please try again.")
            else:
                self.bot.send_message("❓ Please send a 6-digit 2FA code, or use /help to see available commands.")
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error handling 2FA code: {e}", "error")
            self.bot.send_message(f"❌ Error processing 2FA code: {str(e)}")
    
    def _send_pipeline_status(self):
        """Send current pipeline status"""
        try:
            # Check if pipeline service is running
            result = subprocess.run(['systemctl', 'is-active', 'media-pipeline'], 
                                 capture_output=True, text=True)
            service_status = result.stdout.strip()
            
            # Get system stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            status_emoji = "✅" if service_status == "active" else "❌"
            
            message = f"""
📊 <b>Pipeline Status</b>

{status_emoji} <b>Service:</b> {service_status.title()}
💻 <b>CPU:</b> {cpu_percent}%
🧠 <b>Memory:</b> {memory.percent}%
🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<b>Active 2FA Requests:</b> {len(self.handler.get_active_requests())}
            """
            
            self.bot.send_message(message)
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error sending pipeline status: {e}", "error")
    
    def _send_2fa_status(self):
        """Send 2FA requests status"""
        try:
            active_requests = self.handler.get_active_requests()
            
            if not active_requests:
                self.bot.send_message("✅ No active 2FA requests")
                return
            
            message = "🔐 <b>Active 2FA Requests</b>\n\n"
            
            for req_id, req_data in active_requests.items():
                status_emoji = "⏳" if req_data['status'] == 'pending' else "✅"
                created_time = datetime.fromisoformat(req_data['created_at']).strftime('%H:%M:%S')
                
                message += f"{status_emoji} <b>{req_data['pipeline_step']}</b>\n"
                message += f"   ID: <code>{req_id}</code>\n"
                message += f"   Created: {created_time}\n"
                message += f"   Status: {req_data['status']}\n\n"
            
            self.bot.send_message(message)
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error sending 2FA status: {e}", "error")
    
    def _send_recent_logs(self):
        """Send recent pipeline logs"""
        try:
            log_file = Path('/opt/media-pipeline/logs/pipeline.log')
            if not log_file.exists():
                self.bot.send_message("📝 No log file found")
                return
            
            # Get last 10 lines
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            recent_lines = lines[-10:] if len(lines) >= 10 else lines
            log_content = ''.join(recent_lines)
            
            # Truncate if too long
            if len(log_content) > 3000:
                log_content = "..." + log_content[-3000:]
            
            message = f"""
📝 <b>Recent Pipeline Logs</b>

<code>{log_content}</code>
            """
            
            self.bot.send_message(message)
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error sending logs: {e}", "error")
    
    def _send_system_info(self):
        """Send system information"""
        try:
            # Get system stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            
            message = f"""
💻 <b>System Information</b>

🖥️ <b>CPU Usage:</b> {cpu_percent}%
🧠 <b>Memory:</b> {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
💾 <b>Disk:</b> {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)
⏰ <b>Uptime:</b> {uptime_hours:.1f} hours
🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            self.bot.send_message(message)
            
        except Exception as e:
            log_step("telegram_webhook_handler", f"Error sending system info: {e}", "error")
    
    def start_polling(self):
        """Start polling for updates"""
        log_step("telegram_webhook_handler", "Starting Telegram polling", "info")
        
        while True:
            try:
                # Get updates
                url = f"{self.bot.base_url}/getUpdates"
                params = {'offset': self.last_update_id + 1, 'timeout': 30}
                
                response = requests.get(url, params=params, timeout=35)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('ok') and data.get('result'):
                        for update in data['result']:
                            self.process_update(update)
                else:
                    log_step("telegram_webhook_handler", f"Error getting updates: {response.status_code}", "warning")
                
                time.sleep(1)  # Small delay between requests
                
            except Exception as e:
                log_step("telegram_webhook_handler", f"Error in polling loop: {e}", "error")
                time.sleep(5)  # Wait before retrying

def main():
    """Main function"""
    handler = TelegramWebhookHandler()
    
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        handler.start_polling()
    else:
        print("Usage: python3 telegram_webhook_handler.py poll")
        print("This will start polling for Telegram updates")

if __name__ == "__main__":
    main()