import os
import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("httpredirect")

TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
ACESTREAM_BASE = os.getenv("URL_BASE_ACESTREAM", "")
CHANNEL_LIST_URL = os.getenv("CHANNEL_LIST_URL", "")
REDIRECT_NAME = os.getenv("REDIRECT_NAME", "")
DATABASE_URL = "sqlite:///./data/redirects.db"

os.makedirs("./data", exist_ok=True)
