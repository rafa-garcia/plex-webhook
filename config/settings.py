import os
import logging
import logging.config
from pathlib import Path
from dotenv import load_dotenv

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Only load .env file in development
if os.environ.get("DOCKER_ENV") != "true":
    load_dotenv()

# Setup logging first
LOGGING_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "logging.conf")

if os.path.exists(LOGGING_CONFIG_PATH):
    logging.config.fileConfig(LOGGING_CONFIG_PATH, disable_existing_loggers=False)
else:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.warning("Logging config file not found, using basic config")

# Load and validate settings
PORT = int(os.getenv("PORT", "5000"))
PLEX_URL = os.getenv("PLEX_URL", "http://nas:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")

# Log configuration status (excluding sensitive data)
logging.info("Environment configuration:")
logging.info(f"PORT: {PORT}")
logging.info(f"PLEX_URL: {PLEX_URL}")
logging.info("PLEX_TOKEN: [present]" if PLEX_TOKEN else "PLEX_TOKEN: [missing]")

if not PLEX_TOKEN:
    raise ValueError("PLEX_TOKEN environment variable is required")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

logging.info(f"CELERY_BROKER_URL: {CELERY_BROKER_URL}")
