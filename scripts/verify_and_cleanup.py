import os, shutil
from utils import log_step

def verify_and_cleanup(batch_dir):
    try:
        for batch in os.listdir(batch_dir):
            bpath = os.path.join(batch_dir, batch)
            if os.path.isdir(bpath):
                verified = True
                for f in os.listdir(bpath):
                    if os.path.getsize(os.path.join(bpath,f)) <= 0:
                        verified = False
                        log_step("verify", f"{f} in {batch} failed size check", "error")
                if verified:
                    log_step("verify", f"{batch} verified", "success")
                    shutil.rmtree(bpath)
                    log_step("cleanup", f"{batch} cleaned up", "success")
    except Exception as e:
        log_step("verify_and_cleanup", f"Failed: {e}", "error")

if __name__ == "__main__":
    verify_and_cleanup("bridge/iphone")
    verify_and_cleanup("bridge/pixel")
