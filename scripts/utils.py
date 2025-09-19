import os, logging, time
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("config/settings.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(filename="logs/pipeline.log", level=LOG_LEVEL,
                    format="%(asctime)s [%(levelname)s] %(message)s")

def log_step(step, message, status="info"):
    logging.info(f"{step}: {message}")
    try:
        supabase.table("pipeline_logs").insert({"step": step, "message": message, "status": status}).execute()
    except Exception as e:
        logging.error(f"Supabase log failed: {e}")

def retry(max_attempts=3, delay=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts+1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    log_step(func.__name__, f"Attempt {attempt} failed: {e}", "error")
                    if attempt == max_attempts:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator
