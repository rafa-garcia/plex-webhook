import os
import logging
import logging.config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load other environment settings
PLEX_URL = os.getenv("PLEX_URL", "http://nas:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "your_default_token_here")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Define logging config file path
LOGGING_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "logging.conf")


def setup_logging():
    """Load logging configuration from a file."""
    if os.path.exists(LOGGING_CONFIG_PATH):
        logging.config.fileConfig(LOGGING_CONFIG_PATH)
    else:
        logging.basicConfig(
            filename="logs/webhook.log",
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        logging.warning("Logging config file not found, using basic config.")


# Initialize logging when settings are loaded
setup_logging()

# Global logger
logger = logging.getLogger(__name__)
