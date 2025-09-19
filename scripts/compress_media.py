import os, subprocess
from PIL import Image
from utils import log_step
from dotenv import load_dotenv

load_dotenv("config/settings.env")
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 85))
VIDEO_CRF = os.getenv("VIDEO_CRF", "28")
VIDEO_PRESET = os.getenv("VIDEO_PRESET", "fast")

def compress_image(src, dst):
    try:
        img = Image.open(src)
        img.save(dst, "JPEG", quality=JPEG_QUALITY)
        log_step("compress_image", f"Compressed {src} -> {dst}", "success")
    except Exception as e:
        log_step("compress_image", f"Failed {src}: {e}", "error")

def compress_video(src, dst):
    try:
        cmd = ["ffmpeg", "-y", "-i", src, "-c:v", "libx264", "-preset", VIDEO_PRESET, "-crf", VIDEO_CRF, dst]
        subprocess.run(cmd, check=True)
        log_step("compress_video", f"Compressed {src} -> {dst}", "success")
    except Exception as e:
        log_step("compress_video", f"Failed {src}: {e}", "error")

if __name__ == "__main__":
    in_dir = "originals"
    out_dir = "compressed"
    os.makedirs(out_dir, exist_ok=True)
    for fname in os.listdir(in_dir):
        src = os.path.join(in_dir, fname)
        dst = os.path.join(out_dir, fname)
        if fname.lower().endswith((".jpg",".jpeg",".png",".heic")):
            compress_image(src, dst)
        elif fname.lower().endswith((".mp4",".mov",".avi")):
            compress_video(src, dst)
