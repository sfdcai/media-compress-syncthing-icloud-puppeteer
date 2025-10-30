#!/bin/bash
# Media Pipeline Startup Script
# This script ensures proper PYTHONPATH and environment setup

# Set PYTHONPATH
export PYTHONPATH="/opt/media-pipeline/scripts"

# Change to the correct directory
cd /opt/media-pipeline

# Ensure log file exists and is writable
touch /opt/media-pipeline/logs/pipeline.log 2>/dev/null || true

# Start the pipeline
exec /opt/media-pipeline/venv/bin/python /opt/media-pipeline/src/run_pipeline.py