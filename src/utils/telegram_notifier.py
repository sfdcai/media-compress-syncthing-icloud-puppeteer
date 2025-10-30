#!/usr/bin/env python3
"""
Telegram Notifier for Media Pipeline
Provides global access to Telegram bot for step tracking and debug messaging
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.utils import log_step
from utils.enhanced_telegram_bot import EnhancedTelegramBot

# Global bot instance
_telegram_bot = None

def get_telegram_bot():
    """Get global Telegram bot instance"""
    global _telegram_bot
    if _telegram_bot is None:
        try:
            _telegram_bot = EnhancedTelegramBot()
            log_step("telegram_notifier", "Global Telegram bot instance created", "info")
        except Exception as e:
            log_step("telegram_notifier", f"Failed to create Telegram bot: {e}", "error")
            _telegram_bot = None
    return _telegram_bot

def start_pipeline_step(step_name: str, step_description: str = ""):
    """Start tracking a pipeline step"""
    bot = get_telegram_bot()
    if bot:
        bot.start_step(step_name, step_description)

def update_step_progress(files_processed: int = 0, error: str = None, warning: str = None):
    """Update current step progress"""
    bot = get_telegram_bot()
    if bot:
        bot.update_step_progress(files_processed, error, warning)

def complete_pipeline_step(success: bool = True, additional_info: str = ""):
    """Complete current pipeline step"""
    bot = get_telegram_bot()
    if bot:
        bot.complete_step(success, additional_info)

def send_debug_message(message: str, level: str = "info"):
    """Send debug message"""
    bot = get_telegram_bot()
    if bot:
        bot.send_debug_message(message, level)

def send_pipeline_notification(message: str, level: str = "info"):
    """Send pipeline notification"""
    bot = get_telegram_bot()
    if bot and bot.pipeline_notifications:
        level_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }
        
        formatted_message = f"""
{level_emoji.get(level, 'ℹ️')} <b>Pipeline Notification</b>

{message}
        """
        bot.send_message(formatted_message)

def send_error_notification(error_message: str, step: str = ""):
    """Send error notification"""
    bot = get_telegram_bot()
    if bot and bot.error_notifications:
        message = f"""
❌ <b>Pipeline Error</b>

📝 <b>Step:</b> {step or 'Unknown'}
🚨 <b>Error:</b> {error_message}
        """
        bot.send_message(message)

# Convenience functions for common pipeline steps
def notify_download_started(source: str = "iCloud"):
    """Notify that download has started"""
    start_pipeline_step(f"Download from {source}", f"Downloading media files from {source}")

def notify_download_completed(files_count: int, source: str = "iCloud"):
    """Notify that download has completed"""
    complete_pipeline_step(True, f"Downloaded {files_count} files from {source}")

def notify_deduplication_started():
    """Notify that deduplication has started"""
    start_pipeline_step("Deduplication", "Removing duplicate files based on hash comparison")

def notify_deduplication_completed(duplicates_found: int, files_processed: int):
    """Notify that deduplication has completed"""
    complete_pipeline_step(True, f"Found {duplicates_found} duplicates in {files_processed} files")

def notify_compression_started():
    """Notify that compression has started"""
    start_pipeline_step("Compression", "Compressing media files to reduce storage")

def notify_compression_completed(files_compressed: int, space_saved: str = ""):
    """Notify that compression has completed"""
    complete_pipeline_step(True, f"Compressed {files_compressed} files. {space_saved}")

def notify_upload_started(target: str = "iCloud"):
    """Notify that upload has started"""
    start_pipeline_step(f"Upload to {target}", f"Uploading files to {target}")

def notify_upload_completed(files_uploaded: int, target: str = "iCloud"):
    """Notify that upload has completed"""
    complete_pipeline_step(True, f"Uploaded {files_uploaded} files to {target}")

def notify_pipeline_completed(total_files: int, duration: str = ""):
    """Notify that entire pipeline has completed"""
    message = f"""
🎉 <b>Pipeline Completed Successfully!</b>

📊 <b>Total Files Processed:</b> {total_files}
⏱️ <b>Duration:</b> {duration}
✅ <b>Status:</b> All phases completed successfully
    """
    send_pipeline_notification(message, "success")