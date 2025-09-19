import os, shutil
from dotenv import load_dotenv
from utils import log_step

load_dotenv("config/settings.env")

MAX_BATCH_SIZE_GB = int(os.getenv("MAX_BATCH_SIZE_GB", 5))
MAX_BATCH_FILES = int(os.getenv("MAX_BATCH_FILES", 500))

def prepare_batches(src_dir, dst_dir, batch_type):
    files = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir,f))]
    files.sort()
    batch, batch_size, batch_count = [], 0, 0
    for f in files:
        path = os.path.join(src_dir, f)
        size_gb = os.path.getsize(path)/(1024**3)
        batch.append(f)
        batch_size += size_gb
        if len(batch) >= MAX_BATCH_FILES or batch_size >= MAX_BATCH_SIZE_GB:
            batch_count += 1
            out_path = os.path.join(dst_dir, f"batch_{batch_count}")
            os.makedirs(out_path, exist_ok=True)
            for bf in batch:
                shutil.copy(os.path.join(src_dir,bf), out_path)
            log_step("prepare_batches", f"Prepared batch_{batch_count} with {len(batch)} files for {batch_type}", "success")
            batch, batch_size = [], 0
    if batch:
        batch_count += 1
        out_path = os.path.join(dst_dir, f"batch_{batch_count}")
        os.makedirs(out_path, exist_ok=True)
        for bf in batch:
            shutil.copy(os.path.join(src_dir,bf), out_path)
        log_step("prepare_batches", f"Prepared batch_{batch_count} with {len(batch)} files for {batch_type}", "success")

if __name__ == "__main__":
    prepare_batches("compressed", "bridge/iphone", "iphone")
    prepare_batches("originals", "bridge/pixel", "pixel")
