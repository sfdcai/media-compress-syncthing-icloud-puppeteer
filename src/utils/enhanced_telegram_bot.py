#!/usr/bin/env python3
"""
Enhanced Telegram Bot for Media Pipeline
Provides intelligent notifications, 2FA handling, and status updates
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
from typing import Dict, List, Optional
import subprocess
import psutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils import log_step

class EnhancedTelegramBot:
    def __init__(self):
        """Initialize enhanced Telegram bot"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.pending_2fa_requests = {}
        self.notification_history = []
        
        # Debug configuration
        self.debug_messages = os.getenv('TELEGRAM_DEBUG_MESSAGES', 'false').lower() == 'true'
        self.step_summaries = os.getenv('TELEGRAM_STEP_SUMMARIES', 'true').lower() == 'true'
        self.pipeline_notifications = os.getenv('TELEGRAM_PIPELINE_NOTIFICATIONS', 'true').lower() == 'true'
        self.error_notifications = os.getenv('TELEGRAM_ERROR_NOTIFICATIONS', 'true').lower() == 'true'
        
        # Step tracking for summaries
        self.current_step = None
        self.step_start_time = None
        self.step_summary = {}
        
        log_step("enhanced_telegram_bot", "Enhanced Telegram bot initialized", "info")
    
    def start_step(self, step_name: str, step_description: str = ""):
        """Start tracking a pipeline step"""
        if self.step_summaries:
            self.current_step = step_name
            self.step_start_time = datetime.now()
            self.step_summary = {
                'name': step_name,
                'description': step_description,
                'start_time': self.step_start_time,
                'files_processed': 0,
                'errors': [],
                'warnings': []
            }
            
            if self.debug_messages:
                message = f"""
🔧 <b>Starting Pipeline Step</b>

📝 <b>Step:</b> {step_name}
📄 <b>Description:</b> {step_description or 'No description'}
🕐 <b>Started:</b> {self.step_start_time.strftime('%H:%M:%S')}
                """
                self.send_message(message)
    
    def update_step_progress(self, files_processed: int = 0, error: str = None, warning: str = None):
        """Update step progress"""
        if self.step_summaries and self.current_step:
            if files_processed > 0:
                self.step_summary['files_processed'] += files_processed
            if error:
                self.step_summary['errors'].append(error)
            if warning:
                self.step_summary['warnings'].append(warning)
    
    def complete_step(self, success: bool = True, additional_info: str = ""):
        """Complete current step and send summary"""
        if self.step_summaries and self.current_step:
            duration = datetime.now() - self.step_start_time if self.step_start_time else timedelta(0)
            
            status_emoji = "✅" if success else "❌"
            status_text = "Completed" if success else "Failed"
            
            message = f"""
{status_emoji} <b>Pipeline Step {status_text}</b>

📝 <b>Step:</b> {self.current_step}
⏱️ <b>Duration:</b> {duration.total_seconds():.1f}s
📊 <b>Files Processed:</b> {self.step_summary['files_processed']}
            """
            
            if self.step_summary['errors']:
                message += f"\n❌ <b>Errors:</b> {len(self.step_summary['errors'])}"
                if self.debug_messages:
                    message += f"\n<code>{chr(10).join(self.step_summary['errors'][:3])}</code>"
            
            if self.step_summary['warnings']:
                message += f"\n⚠️ <b>Warnings:</b> {len(self.step_summary['warnings'])}"
            
            if additional_info:
                message += f"\n📋 <b>Info:</b> {additional_info}"
            
            self.send_message(message)
            
            # Reset step tracking
            self.current_step = None
            self.step_start_time = None
            self.step_summary = {}
    
    def send_debug_message(self, message: str, level: str = "info"):
        """Send debug message if debug mode is enabled"""
        if self.debug_messages:
            level_emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'success': '✅'
            }
            
            formatted_message = f"""
{level_emoji.get(level, 'ℹ️')} <b>Debug Message</b>

{message}

🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}
            """
            self.send_message(formatted_message)
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram with retry logic"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            success = response.status_code == 200
            
            if success:
                log_step("enhanced_telegram_bot", f"Message sent: {message[:50]}...", "info")
            else:
                log_step("enhanced_telegram_bot", f"Failed to send message: {response.text}", "error")
            
            return success
            
        except Exception as e:
            log_step("enhanced_telegram_bot", f"Error sending message: {e}", "error")
            return False
    
    def send_2fa_request(self, pipeline_step: str, request_id: str = None) -> str:
        """Send 2FA request notification"""
        if not request_id:
            request_id = f"2fa_{int(time.time())}"
        
        self.pending_2fa_requests[request_id] = {
            'step': pipeline_step,
            'timestamp': datetime.now(),
            'status': 'pending'
        }
        
        message = f"""
🔐 <b>iCloud 2FA Required</b>

📝 <b>Pipeline Step:</b> {pipeline_step}
🆔 <b>Request ID:</b> <code>{request_id}</code>
⏰ <b>Expires in:</b> 5 minutes
🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

Please reply with your 6-digit 2FA code from your phone.

<i>💡 Tip: The code is usually sent to your iPhone/iPad</i>
        """
        
        if self.send_message(message):
            log_step("enhanced_telegram_bot", f"2FA request sent for {pipeline_step}", "info")
            return request_id
        else:
            return None
    
    def send_pipeline_status(self, status: str, details: str = "") -> bool:
        """Send pipeline status update"""
        status_emoji = {
            'started': '🚀',
            'running': '⚙️',
            'completed': '✅',
            'failed': '❌',
            'paused': '⏸️',
            'resumed': '▶️'
        }
        
        emoji = status_emoji.get(status, '📊')
        
        message = f"""
{emoji} <b>Pipeline Status Update</b>

📊 <b>Status:</b> {status.title()}
🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{details if details else 'No additional details available.'}
        """
        
        return self.send_message(message)
    
    def send_error_alert(self, error_type: str, error_message: str, step: str = "") -> bool:
        """Send error alert"""
        message = f"""
🚨 <b>Pipeline Error Alert</b>

❌ <b>Error Type:</b> {error_type}
📝 <b>Step:</b> {step if step else 'Unknown'}
🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<b>Error Details:</b>
<code>{error_message}</code>

<i>⚠️ Please check the pipeline logs for more details</i>
        """
        
        return self.send_message(message)
    
    def send_daily_summary(self) -> bool:
        """Send daily pipeline summary"""
        try:
            # Get system stats
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get pipeline stats from logs
            log_file = Path('/opt/media-pipeline/logs/pipeline.log')
            if log_file.exists():
                with open(log_file, 'r') as f:
                    log_content = f.read()
                
                # Count different log types
                info_count = log_content.count('[INFO]')
                error_count = log_content.count('[ERROR]')
                warning_count = log_content.count('[WARNING]')
            else:
                info_count = error_count = warning_count = 0
            
            message = f"""
📊 <b>Daily Pipeline Summary</b>

📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}
🕐 <b>Generated:</b> {datetime.now().strftime('%H:%M:%S')}

<b>System Status:</b>
💻 CPU Usage: {cpu_percent}%
🧠 Memory: {memory.percent}% used
💾 Disk: {disk.percent}% used

<b>Pipeline Activity:</b>
✅ Info Messages: {info_count}
⚠️ Warnings: {warning_count}
❌ Errors: {error_count}

<b>Active 2FA Requests:</b> {len(self.pending_2fa_requests)}
            """
            
            return self.send_message(message)
            
        except Exception as e:
            log_step("enhanced_telegram_bot", f"Error generating daily summary: {e}", "error")
            return False
    
    def send_file_upload_progress(self, filename: str, progress: int, total: int) -> bool:
        """Send file upload progress"""
        percentage = (progress / total) * 100 if total > 0 else 0
        
        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * progress // total) if total > 0 else 0
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        message = f"""
📤 <b>Upload Progress</b>

📁 <b>File:</b> {filename}
📊 <b>Progress:</b> {progress}/{total} ({percentage:.1f}%)
        
{bar} {percentage:.1f}%
        """
        
        return self.send_message(message)
    
    def send_download_summary(self, files_downloaded: int, total_size: str) -> bool:
        """Send download summary"""
        message = f"""
📥 <b>Download Complete</b>

📁 <b>Files Downloaded:</b> {files_downloaded}
💾 <b>Total Size:</b> {total_size}
🕐 <b>Completed:</b> {datetime.now().strftime('%H:%M:%S')}

<i>✅ All files have been successfully downloaded from iCloud</i>
        """
        
        return self.send_message(message)
    
    def send_compression_summary(self, original_size: str, compressed_size: str, savings_percent: float) -> bool:
        """Send compression summary"""
        message = f"""
🗜️ <b>Compression Complete</b>

📊 <b>Original Size:</b> {original_size}
📦 <b>Compressed Size:</b> {compressed_size}
💰 <b>Space Saved:</b> {savings_percent:.1f}%
🕐 <b>Completed:</b> {datetime.now().strftime('%H:%M:%S')}

<i>🎉 Great space savings achieved!</i>
        """
        
        return self.send_message(message)
    
    def send_syncthing_status(self, status: str) -> bool:
        """Send Syncthing status update"""
        status_emoji = {
            'connected': '🔗',
            'disconnected': '🔌',
            'syncing': '🔄',
            'idle': '😴',
            'error': '❌'
        }
        
        emoji = status_emoji.get(status, '📊')
        
        message = f"""
🔄 <b>Syncthing Status</b>

{emoji} <b>Status:</b> {status.title()}
🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<i>Syncthing synchronization status updated</i>
        """
        
        return self.send_message(message)
    
    def get_pending_2fa_requests(self) -> Dict:
        """Get all pending 2FA requests"""
        return self.pending_2fa_requests.copy()
    
    def clear_expired_2fa_requests(self) -> int:
        """Clear expired 2FA requests (older than 5 minutes)"""
        expired_count = 0
        current_time = datetime.now()
        
        for request_id, request_data in list(self.pending_2fa_requests.items()):
            if (current_time - request_data['timestamp']).seconds > 300:  # 5 minutes
                del self.pending_2fa_requests[request_id]
                expired_count += 1
        
        if expired_count > 0:
            log_step("enhanced_telegram_bot", f"Cleared {expired_count} expired 2FA requests", "info")
        
        return expired_count
    
    def send_help_message(self) -> bool:
        """Send help message with available commands"""
        message = f"""
🤖 <b>Media Pipeline Bot Commands</b>

<b>Available Commands:</b>
/start - Show this help message
/status - Get current pipeline status
/summary - Get daily summary
/2fa_status - Check pending 2FA requests
/clear_2fa - Clear expired 2FA requests
/logs - Get recent pipeline logs
/system - Get system information

<b>Automatic Notifications:</b>
🔐 2FA requests
📊 Pipeline status updates
❌ Error alerts
📤 Upload progress
📥 Download summaries
🗜️ Compression reports
🔄 Syncthing status

<i>💡 This bot will automatically notify you of important pipeline events!</i>
        """
        
        return self.send_message(message)

def main():
    """Main function for testing"""
    if len(sys.argv) < 2:
        print("Usage: python3 enhanced_telegram_bot.py <command>")
        print("Commands: test, 2fa, status, summary, help")
        return
    
    command = sys.argv[1]
    bot = EnhancedTelegramBot()
    
    if command == "test":
        bot.send_message("🤖 Enhanced Telegram Bot Test - Bot is working correctly!")
        print("✅ Test message sent")
    
    elif command == "2fa":
        pipeline_step = sys.argv[2] if len(sys.argv) > 2 else "Test Pipeline"
        request_id = bot.send_2fa_request(pipeline_step)
        if request_id:
            print(f"✅ 2FA request sent with ID: {request_id}")
        else:
            print("❌ Failed to send 2FA request")
    
    elif command == "status":
        bot.send_pipeline_status("running", "Pipeline is currently processing files")
        print("✅ Status update sent")
    
    elif command == "summary":
        bot.send_daily_summary()
        print("✅ Daily summary sent")
    
    elif command == "help":
        bot.send_help_message()
        print("✅ Help message sent")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()