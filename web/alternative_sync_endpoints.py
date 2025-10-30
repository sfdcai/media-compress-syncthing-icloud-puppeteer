#!/usr/bin/env python3
"""
Alternative sync verification endpoints for web dashboard
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.append('/opt/media-pipeline')

def get_alternative_sync_status():
    """Get sync status using alternative methods"""
    try:
        from modified_sync_system import ModifiedSyncSystem
        
        sync_system = ModifiedSyncSystem()
        report = sync_system.generate_sync_report()
        
        return {
            'success': True,
            'data': report
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'message': f'Failed to get sync status: {e}'
            }
        }

def get_file_verification_methods():
    """Get available file verification methods"""
    try:
        from alternative_sync_verification import AlternativeSyncVerifier
        
        verifier = AlternativeSyncVerifier()
        
        # Run quick checks for each method
        methods = {
            'file_tracking': {
                'name': 'File Pipeline Tracking',
                'description': 'Track files through different pipeline stages',
                'status': 'available'
            },
            'upload_timestamps': {
                'name': 'Upload Timestamp Analysis',
                'description': 'Analyze upload patterns and timestamps',
                'status': 'available'
            },
            'syncthing_status': {
                'name': 'Syncthing Status Check',
                'description': 'Check Syncthing sync status and health',
                'status': 'available'
            },
            'file_size_analysis': {
                'name': 'File Size Analysis',
                'description': 'Analyze file sizes and patterns',
                'status': 'available'
            },
            'upload_log_analysis': {
                'name': 'Upload Log Analysis',
                'description': 'Analyze upload logs for sync patterns',
                'status': 'available'
            }
        }
        
        return {
            'success': True,
            'data': {
                'methods': methods,
                'total_methods': len(methods),
                'available_methods': len([m for m in methods.values() if m['status'] == 'available'])
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': {'methods': [], 'total_methods': 0, 'available_methods': 0}
        }

def run_verification_method(method_name: str):
    """Run a specific verification method"""
    try:
        from alternative_sync_verification import AlternativeSyncVerifier
        
        verifier = AlternativeSyncVerifier()
        
        if method_name == 'file_tracking':
            result = verifier.method1_file_tracking()
        elif method_name == 'upload_timestamps':
            result = verifier.method2_upload_timestamps()
        elif method_name == 'syncthing_status':
            result = verifier.method3_syncthing_status()
        elif method_name == 'file_size_analysis':
            result = verifier.method4_file_size_analysis()
        elif method_name == 'upload_log_analysis':
            result = verifier.method5_upload_log_analysis()
        else:
            return {
                'success': False,
                'error': f'Unknown method: {method_name}'
            }
        
        return {
            'success': True,
            'data': {
                'method': method_name,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': {
                'method': method_name,
                'result': None,
                'timestamp': datetime.now().isoformat()
            }
        }

def get_sync_summary():
    """Get a quick sync status summary"""
    try:
        from modified_sync_system import ModifiedSyncSystem
        
        sync_system = ModifiedSyncSystem()
        verification = sync_system.verify_sync_status()
        syncthing_status = sync_system.check_syncthing_health()
        
        # Count different statuses
        status_counts = {}
        for filename, file_status in verification.get('sync_status', {}).items():
            status = file_status.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        summary = {
            'total_files': verification['total_pixel_files'],
            'tracked_uploads': verification['tracked_uploads'],
            'syncthing_running': syncthing_status['syncthing_running'],
            'status_breakdown': status_counts,
            'last_updated': datetime.now().isoformat()
        }
        
        return {
            'success': True,
            'data': summary
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': {
                'total_files': 0,
                'tracked_uploads': 0,
                'syncthing_running': False,
                'status_breakdown': {},
                'last_updated': datetime.now().isoformat()
            }
        }