import os, subprocess
from utils import log_step

NAS = os.getenv("NAS_MOUNT", "originals")

def main():
    try:
        cmd = ["icloudpd", "--directory", NAS, "--username", os.getenv("ICLOUD_USERNAME")]
        log_step("download_from_icloud", "Starting iCloud download")
        subprocess.run(cmd, check=True)
        log_step("download_from_icloud", "Completed iCloud download", "success")
    except Exception as e:
        log_step("download_from_icloud", f"Failed: {e}", "error")

if __name__ == "__main__":
    main()
