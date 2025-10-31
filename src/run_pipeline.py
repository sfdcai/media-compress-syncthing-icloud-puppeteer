#!/usr/bin/env python3
"""
Media Pipeline Orchestrator
Coordinates the entire workflow from download to organized storage
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from utils.utils import (
    log_step, validate_config, get_feature_toggle,
    ensure_directory_exists
)
from utils.telegram_notifier import (
    start_pipeline_step, complete_pipeline_step, update_step_progress,
    send_debug_message, send_error_notification, notify_pipeline_completed
)


class PhaseStatus(Enum):
    """Pipeline phase status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class PhaseResult:
    """Result of a pipeline phase execution"""
    name: str
    status: PhaseStatus
    duration: float
    error: Optional[str] = None


class MediaPipeline:
    """Main media pipeline orchestrator class"""
    
    def __init__(self):
        self.phases: List[Tuple[str, Union[str, Callable[[], bool]], Callable[[], bool]]] = [
            ("download", self._is_download_phase_enabled, self.run_download),
            ("deduplication", "ENABLE_DEDUPLICATION", self.run_deduplication),
            ("compression", "ENABLE_COMPRESSION", self.run_compression),
            ("file_preparation", "ENABLE_FILE_PREPARATION", self.run_file_preparation),
            ("icloud_upload", "ENABLE_ICLOUD_UPLOAD", self.run_icloud_upload),
            ("pixel_upload", "ENABLE_PIXEL_UPLOAD", self.run_pixel_upload),
            ("sorting", "ENABLE_SORTING", self.run_sorting),
            ("verification", "ENABLE_VERIFICATION", self.run_verification)
        ]
        self.results: List[PhaseResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def setup_directories(self) -> bool:
        """Setup required directories using source manager"""
        log_step("pipeline", "Setting up directory structure", "info")
        
        try:
            from core.source_manager import SourceManager
            source_manager = SourceManager()
            source_manager.setup_source_directories()
            log_step("pipeline", "Directory structure setup completed", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Error setting up directories: {e}", "error")
            return self._setup_fallback_directories()
    
    def _setup_fallback_directories(self) -> bool:
        """Fallback directory setup"""
        try:
            # Use local directories instead of NAS mount for fallback
            base_dir = "/opt/media-pipeline"
            directories = [
                os.path.join(base_dir, "logs"),
                os.path.join(base_dir, "temp"),
                os.path.join(base_dir, "cache")
            ]
            
            for directory in directories:
                ensure_directory_exists(directory)
            
            log_step("pipeline", "Basic directory structure setup completed", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Fallback directory setup failed: {e}", "error")
            return False
    
    def _is_download_phase_enabled(self) -> bool:
        """Determine whether the download phase should run"""
        if get_feature_toggle("ENABLE_ICLOUD_DOWNLOAD"):
            return True

        if get_feature_toggle("ENABLE_FOLDER_DOWNLOAD"):
            return True

        return False

    def run_phase(
        self,
        phase_name: str,
        toggle_ref: Union[str, Callable[[], bool]],
        phase_func: Callable[[], bool]
    ) -> PhaseResult:
        """Run a single pipeline phase with comprehensive error handling"""
        start_time = datetime.now()

        try:
            toggle_enabled = toggle_ref() if callable(toggle_ref) else get_feature_toggle(toggle_ref)
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Failed to evaluate toggle for {phase_name}: {e}"
            log_step("pipeline", error_msg, "error")
            return PhaseResult(
                name=phase_name,
                status=PhaseStatus.FAILED,
                duration=duration,
                error=str(e)
            )

        # Check if phase is enabled
        if not toggle_enabled:
            log_step("pipeline", f"{phase_name} phase disabled", "info")
            return PhaseResult(
                name=phase_name,
                status=PhaseStatus.DISABLED,
                duration=0.0
            )
        
        log_step("pipeline", f"Starting {phase_name} phase", "info")
        
        try:
            success = phase_func()
            duration = (datetime.now() - start_time).total_seconds()
            
            if success:
                log_step("pipeline", f"{phase_name} phase completed in {duration:.2f}s", "success")
                return PhaseResult(
                    name=phase_name,
                    status=PhaseStatus.SUCCESS,
                    duration=duration
                )
            else:
                log_step("pipeline", f"{phase_name} phase failed after {duration:.2f}s", "error")
                return PhaseResult(
                    name=phase_name,
                    status=PhaseStatus.FAILED,
                    duration=duration,
                    error="Phase execution returned False"
                )
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            log_step("pipeline", f"{phase_name} phase failed with error: {error_msg} after {duration:.2f}s", "error")
            return PhaseResult(
                name=phase_name,
                status=PhaseStatus.FAILED,
                duration=duration,
                error=error_msg
            )
    
    def run(self) -> bool:
        """Main pipeline execution function"""
        self.start_time = datetime.now()
        log_step("pipeline", "Starting media pipeline", "info")
        
        # Send pipeline start notification
        send_debug_message("🚀 Media Pipeline Started", "info")
        
        try:
            # Validate configuration
            if not validate_config():
                log_step("pipeline", "Configuration validation failed", "error")
                send_error_notification("Configuration validation failed", "Pipeline Start")
                return False
            
            # Setup directories
            if not self.setup_directories():
                log_step("pipeline", "Directory setup failed", "error")
                send_error_notification("Directory setup failed", "Pipeline Start")
                return False
            
            # Run pipeline phases
            self.results = []
            for phase_name, toggle_name, phase_func in self.phases:
                result = self.run_phase(phase_name, toggle_name, phase_func)
                self.results.append(result)
            
            self.end_time = datetime.now()
            
            # Generate report
            self.generate_report()
            
            # Calculate success rate
            successful_phases = sum(1 for r in self.results if r.status == PhaseStatus.SUCCESS)
            total_enabled_phases = sum(1 for r in self.results if r.status != PhaseStatus.DISABLED)
            
            log_step("pipeline", 
                    f"Media pipeline completed: {successful_phases}/{total_enabled_phases} phases successful", 
                    "success")
            
            # Send pipeline completion notification
            duration = self.end_time - self.start_time
            notify_pipeline_completed(successful_phases, f"{duration.total_seconds():.1f}s")
            
            return successful_phases > 0
            
        except Exception as e:
            self.end_time = datetime.now()
            log_step("pipeline", f"Pipeline failed with error: {e}", "error")
            return False
    
    def generate_report(self) -> bool:
        """Generate pipeline execution report"""
        if not self.start_time or not self.end_time:
            return False
        
        try:
            report_file = f"/opt/media-pipeline/logs/pipeline_report_{int(self.start_time.timestamp())}.txt"
            
            with open(report_file, 'w') as f:
                f.write("Media Pipeline Execution Report\n")
                f.write("=" * 40 + "\n")
                f.write(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"End Time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                duration = self.end_time - self.start_time
                f.write(f"Duration: {duration.total_seconds():.2f} seconds\n\n")
                
                f.write("Phase Results:\n")
                f.write("-" * 20 + "\n")
                
                for result in self.results:
                    f.write(f"{result.name}: {result.status.value.upper()}")
                    if result.duration > 0:
                        f.write(f" ({result.duration:.2f}s)")
                    if result.error:
                        f.write(f" - {result.error}")
                    f.write("\n")
                
                f.write("\n")
                
                # Overall result
                successful_phases = sum(1 for r in self.results if r.status == PhaseStatus.SUCCESS)
                total_enabled_phases = sum(1 for r in self.results if r.status != PhaseStatus.DISABLED)
                success_rate = (successful_phases / total_enabled_phases * 100) if total_enabled_phases > 0 else 0
                
                f.write(f"Overall Result: {success_rate:.1f}% success rate\n")
                f.write(f"Successful Phases: {successful_phases}/{total_enabled_phases}\n")
            
            log_step("pipeline", f"Pipeline report generated: {report_file}", "success")
            return True
            
        except Exception as e:
            log_step("pipeline", f"Error generating pipeline report: {e}", "error")
            return False
    
    # Phase implementation methods
    def run_download(self) -> bool:
        """Run download from all enabled sources"""
        log_step("pipeline", "Starting download phase", "info")
        start_pipeline_step("Download Phase", "Downloading media files from configured sources")
        
        try:
            from core.source_manager import SourceManager
            source_manager = SourceManager()
            
            # Validate source configurations
            if not source_manager.validate_source_configurations():
                log_step("pipeline", "Source configuration validation failed", "error")
                send_error_notification("Source configuration validation failed", "Download Phase")
                complete_pipeline_step(False, "Configuration validation failed")
                return False
            
            # Run downloads for all enabled sources
            success = source_manager.run_all_source_downloads()
            
            if success:
                log_step("pipeline", "Download phase completed successfully", "success")
                complete_pipeline_step(True, "Download completed successfully")
            else:
                log_step("pipeline", "Download phase failed", "error")
                send_error_notification("Download phase failed", "Download Phase")
                complete_pipeline_step(False, "Download failed")
            
            return success
            
        except Exception as e:
            log_step("pipeline", f"Download phase error: {e}", "error")
            return False
    
    def run_deduplication(self) -> bool:
        """Run deduplication phase"""
        log_step("pipeline", "Starting deduplication phase", "info")
        
        try:
            from processors.deduplicate import main as dedupe_main
            dedupe_main()
            log_step("pipeline", "Deduplication phase completed successfully", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Deduplication phase error: {e}", "error")
            return False
    
    def run_compression(self) -> bool:
        """Run compression phase"""
        log_step("pipeline", "Starting compression phase", "info")
        
        try:
            from processors.compress_media import main as compress_main
            compress_main()
            log_step("pipeline", "Compression phase completed successfully", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Compression phase error: {e}", "error")
            return False
    
    def run_file_preparation(self) -> bool:
        """Run file preparation phase"""
        log_step("pipeline", "Starting file preparation phase", "info")
        
        try:
            from processors.prepare_bridge_batch import main as file_main
            file_main()
            log_step("pipeline", "File preparation phase completed successfully", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"File preparation phase error: {e}", "error")
            return False
    
    def run_icloud_upload(self) -> bool:
        """Run iCloud upload phase"""
        log_step("pipeline", "Starting iCloud upload phase", "info")
        
        try:
            from processors.upload_icloud import upload_to_icloud
            result = upload_to_icloud("/mnt/wd_all_pictures/sync/bridge/icloud", interactive=False)
            if result:
                log_step("pipeline", "iCloud upload phase completed successfully", "success")
                return True
            else:
                log_step("pipeline", "iCloud upload phase failed", "error")
                return False
        except Exception as e:
            log_step("pipeline", f"iCloud upload phase error: {e}", "error")
            return False
    
    def run_pixel_upload(self) -> bool:
        """Run Pixel upload phase"""
        log_step("pipeline", "Starting Pixel upload phase", "info")
        
        try:
            from processors.sync_to_pixel import main as pixel_main
            pixel_main()
            log_step("pipeline", "Pixel upload phase completed successfully", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Pixel upload phase error: {e}", "error")
            return False
    
    def run_sorting(self) -> bool:
        """Run sorting phase"""
        log_step("pipeline", "Starting sorting phase", "info")
        
        try:
            from processors.sort_uploaded import main as sort_main
            sort_main()
            log_step("pipeline", "Sorting phase completed successfully", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Sorting phase error: {e}", "error")
            return False
    
    def run_verification(self) -> bool:
        """Run verification phase"""
        log_step("pipeline", "Starting verification phase", "info")
        
        try:
            from processors.verify_and_cleanup import main as verify_main
            verify_main()
            log_step("pipeline", "Verification phase completed successfully", "success")
            return True
        except Exception as e:
            log_step("pipeline", f"Verification phase error: {e}", "error")
            return False
    
    def get_execution_stats(self):
        """Get pipeline execution statistics"""
        if not self.start_time or not self.end_time:
            return None
        
        duration = self.end_time - self.start_time
        successful_phases = sum(1 for r in self.results if r.status == PhaseStatus.SUCCESS)
        total_enabled_phases = sum(1 for r in self.results if r.status != PhaseStatus.DISABLED)
        
        return {
            'duration_seconds': duration.total_seconds() if hasattr(duration, 'total_seconds') else duration,
            'successful_phases': successful_phases,
            'total_phases': total_enabled_phases,
            'success_rate': (successful_phases / total_enabled_phases * 100) if total_enabled_phases > 0 else 0,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }


def get_phase_summary(results):
    """Generate a summary of pipeline phase results"""
    if not results:
        return "No phase data available"
    
    summary_lines = []
    for result in results:
        status_emoji = {
            PhaseStatus.SUCCESS: "✅",
            PhaseStatus.FAILED: "❌", 
            PhaseStatus.DISABLED: "⏸️",
            PhaseStatus.RUNNING: "🔄",
            PhaseStatus.PENDING: "⏳"
        }
        
        emoji = status_emoji.get(result.status, "❓")
        duration = f"{result.duration:.1f}s" if result.duration > 0 else "N/A"
        summary_lines.append(f"{emoji} {result.name}: {duration}")
    
    return "\n".join(summary_lines)


def main():
    """Main entry point with interval control"""
    import time
    from datetime import datetime, timedelta
    
    # Get configuration
    interval_minutes = int(os.getenv('PIPELINE_EXECUTION_INTERVAL_MINUTES', 60))
    execution_mode = os.getenv('PIPELINE_EXECUTION_MODE', 'continuous')
    max_executions_per_day = int(os.getenv('PIPELINE_MAX_EXECUTIONS_PER_DAY', 24))
    
    log_step("pipeline", f"Starting pipeline with {execution_mode} mode, {interval_minutes} minute intervals", "info")
    
    execution_count = 0
    start_time = datetime.now()
    
    while True:
        try:
            # Check daily execution limit
            if execution_count >= max_executions_per_day:
                log_step("pipeline", f"Daily execution limit reached ({max_executions_per_day}), waiting until tomorrow", "info")
                # Wait until next day
                tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait_seconds = (tomorrow - datetime.now()).total_seconds()
                time.sleep(wait_seconds)
                execution_count = 0
                start_time = datetime.now()
                continue
            
            # Run pipeline
            pipeline = MediaPipeline()
            success = pipeline.run()
            
            execution_count += 1
            
            # Get execution statistics
            stats = pipeline.get_execution_stats()
            if stats:
                log_step("pipeline", f"Pipeline execution #{execution_count} completed. Success: {success}, Duration: {stats['duration_seconds']:.1f}s, Success Rate: {stats['success_rate']:.1f}%", "info")
                
                # Send Telegram notification for execution completion
                from utils.telegram_notifier import send_pipeline_notification
                from datetime import datetime
                
                # Calculate next run time
                next_run_time = datetime.now().replace(microsecond=0) + timedelta(minutes=interval_minutes)
                
                if success:
                    message = f"""
✅ <b>Pipeline Execution #{execution_count} Completed Successfully</b>

⏱️ <b>Duration:</b> {stats['duration_seconds']:.1f} seconds
📊 <b>Success Rate:</b> {stats['success_rate']:.1f}% ({stats['successful_phases']}/{stats['total_phases']} phases)
🔄 <b>Next Run:</b> {next_run_time.strftime('%H:%M:%S')} (in {interval_minutes} min)
📅 <b>Daily Progress:</b> {execution_count}/{max_executions_per_day} executions
🕐 <b>Completed:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Phase Details:</b>
{get_phase_summary(pipeline.results)}
                    """
                    send_pipeline_notification(message, "success")
                else:
                    message = f"""
❌ <b>Pipeline Execution #{execution_count} Failed</b>

⏱️ <b>Duration:</b> {stats['duration_seconds']:.1f} seconds
📊 <b>Success Rate:</b> {stats['success_rate']:.1f}% ({stats['successful_phases']}/{stats['total_phases']} phases)
🔄 <b>Retry:</b> {next_run_time.strftime('%H:%M:%S')} (in {interval_minutes} min)
📅 <b>Daily Progress:</b> {execution_count}/{max_executions_per_day} executions
🕐 <b>Failed:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Phase Details:</b>
{get_phase_summary(pipeline.results)}
                    """
                    send_pipeline_notification(message, "error")
            else:
                log_step("pipeline", f"Pipeline execution #{execution_count} completed. Success: {success}", "info")
            
            # Check execution mode
            if execution_mode == 'single':
                log_step("pipeline", "Single execution mode, exiting", "info")
                sys.exit(0 if success else 1)
            
            # Wait for next execution
            if execution_mode == 'continuous':
                log_step("pipeline", f"Waiting {interval_minutes} minutes until next execution...", "info")
                time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            log_step("pipeline", "Pipeline interrupted by user", "info")
            sys.exit(0)
        except Exception as e:
            log_step("pipeline", f"Pipeline error: {e}", "error")
            if execution_mode == 'single':
                sys.exit(1)
            else:
                log_step("pipeline", f"Waiting {interval_minutes} minutes before retry...", "info")
                time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()