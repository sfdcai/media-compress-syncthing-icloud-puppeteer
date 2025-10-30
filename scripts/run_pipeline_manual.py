#!/usr/bin/env python3
"""
Manual Pipeline Execution Script
Allows running the pipeline manually with different options
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from run_pipeline import MediaPipeline, get_phase_summary
from utils.telegram_notifier import send_pipeline_notification
from utils.utils import log_step

def run_single_execution():
    """Run pipeline once and exit"""
    log_step("manual_pipeline", "Starting manual pipeline execution", "info")
    
    pipeline = MediaPipeline()
    success = pipeline.run()
    
    # Get execution statistics
    stats = pipeline.get_execution_stats()
    
    if stats:
        log_step("manual_pipeline", f"Manual execution completed. Success: {success}, Duration: {stats['duration_seconds']:.1f}s", "info")
        
        # Send Telegram notification
        if success:
            message = f"""
🎯 <b>Manual Pipeline Execution Completed</b>

⏱️ <b>Duration:</b> {stats['duration_seconds']:.1f} seconds
📊 <b>Success Rate:</b> {stats['success_rate']:.1f}% ({stats['successful_phases']}/{stats['total_phases']} phases)
🕐 <b>Completed:</b> {stats['end_time']}

<b>Phase Details:</b>
{get_phase_summary(pipeline.results)}
            """
            send_pipeline_notification(message, "success")
        else:
            message = f"""
❌ <b>Manual Pipeline Execution Failed</b>

⏱️ <b>Duration:</b> {stats['duration_seconds']:.1f} seconds
📊 <b>Success Rate:</b> {stats['success_rate']:.1f}% ({stats['successful_phases']}/{stats['total_phases']} phases)
🕐 <b>Failed:</b> {stats['end_time']}

<b>Phase Details:</b>
{get_phase_summary(pipeline.results)}
            """
            send_pipeline_notification(message, "error")
    
    return success

def run_with_custom_interval(interval_minutes):
    """Run pipeline with custom interval"""
    log_step("manual_pipeline", f"Starting pipeline with {interval_minutes} minute interval", "info")
    
    # Temporarily set environment variable
    os.environ['PIPELINE_EXECUTION_INTERVAL_MINUTES'] = str(interval_minutes)
    os.environ['PIPELINE_EXECUTION_MODE'] = 'continuous'
    
    # Import and run the main function
    from run_pipeline import main
    main()

def show_status():
    """Show current pipeline status"""
    log_step("manual_pipeline", "Checking pipeline status", "info")
    
    # Check service status
    import subprocess
    try:
        result = subprocess.run(['systemctl', 'is-active', 'media-pipeline.service'], 
                               capture_output=True, text=True)
        service_status = result.stdout.strip()
        
        print(f"📊 Pipeline Service Status: {service_status}")
        
        if service_status == 'active':
            # Get recent logs
            result = subprocess.run(['journalctl', '-u', 'media-pipeline.service', '--no-pager', '-n', '10'], 
                                   capture_output=True, text=True)
            print(f"\n📋 Recent Logs:")
            print(result.stdout)
        else:
            print("⚠️  Pipeline service is not running")
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='Manual Pipeline Execution Tool')
    parser.add_argument('action', choices=['run', 'status', 'interval'], 
                       help='Action to perform')
    parser.add_argument('--interval', type=int, default=60,
                       help='Interval in minutes for continuous mode (default: 60)')
    
    args = parser.parse_args()
    
    print("🚀 Media Pipeline Manual Execution Tool")
    print("=" * 50)
    
    try:
        if args.action == 'run':
            print("🎯 Running single pipeline execution...")
            success = run_single_execution()
            sys.exit(0 if success else 1)
            
        elif args.action == 'status':
            show_status()
            
        elif args.action == 'interval':
            print(f"🔄 Starting pipeline with {args.interval} minute interval...")
            run_with_custom_interval(args.interval)
            
    except KeyboardInterrupt:
        print("\n⏹️  Execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()