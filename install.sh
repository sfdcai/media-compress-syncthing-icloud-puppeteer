#!/bin/bash
set -e
echo "[INFO] Installing dependencies..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg ifuse pm2 icloudpd syncthing
echo "[INFO] Creating virtual environment..."
python3 -m venv /opt/media-pipeline/venv
source /opt/media-pipeline/venv/bin/activate
pip install pillow python-dotenv requests supabase
echo "[INFO] Setting up directories..."
mkdir -p /opt/media-pipeline/{originals,compressed,bridge/iphone,bridge/pixel,logs}
echo "[INFO] Copying configs and scripts..."
cp -r config /opt/media-pipeline/
cp -r supabase /opt/media-pipeline/
cp -r scripts /opt/media-pipeline/
echo "[INFO] Installation complete. Configure config/settings.env before running."
