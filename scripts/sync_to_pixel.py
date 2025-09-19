import os, shutil
from dotenv import load_dotenv
from utils import log_step

load_dotenv("config/settings.env")
PIXEL_SYNC_FOLDER = os.getenv("PIXEL_SYNC_FOLDER", "/mnt/syncthing/pixel")

def sync_to_pixel(batch_dir):
    try:
        for batch in os.listdir(batch_dir):
            src = os.path.join(batch_dir, batch)
            dst = os.path.join(PIXEL_SYNC_FOLDER, batch)
            if os.path.isdir(src):
                if not os.path.exists(dst):
                    shutil.copytree(src, dst)
                log_step("sync_to_pixel", f"Synced {batch} to Pixel Syncthing folder", "success")
    except Exception as e:
        log_step("sync_to_pixel", f"Failed: {e}", "error")

if __name__ == "__main__":
    sync_to_pixel("bridge/pixel")
