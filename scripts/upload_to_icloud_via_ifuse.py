import os, subprocess, shutil
from utils import log_step

def upload_to_icloud(batch_dir):
    try:
        mount_point = "/mnt/iphone"
        os.makedirs(mount_point, exist_ok=True)
        subprocess.run(["ifuse", mount_point], check=True)
        dcim = os.path.join(mount_point, "DCIM", "100APPLE")
        os.makedirs(dcim, exist_ok=True)
        for batch in os.listdir(batch_dir):
            bpath = os.path.join(batch_dir, batch)
            if os.path.isdir(bpath):
                for f in os.listdir(bpath):
                    shutil.copy(os.path.join(bpath,f), dcim)
                log_step("upload_to_icloud", f"Uploaded {batch} to iPhone DCIM", "success")
        subprocess.run(["fusermount","-u",mount_point], check=True)
    except Exception as e:
        log_step("upload_to_icloud", f"Failed: {e}", "error")

if __name__ == "__main__":
    upload_to_icloud("bridge/iphone")
