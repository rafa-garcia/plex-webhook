import logging
import json
import traceback
from typing import Any, Dict
from datetime import datetime


def log_event(event_type: str, data: Dict[str, Any], level: str = "info") -> None:
    """
    Log structured event data with additional context.

    Args:
        event_type (str): Type of event being logged
        data (Dict[str, Any]): Event data to log
        level (str): Logging level (debug, info, warning, error, critical)
    """
    try:
        log_data = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        if level == "error" and "error" in data:
            log_data["stacktrace"] = traceback.format_exc()

        log_message = json.dumps(log_data, indent=2)

        getattr(logging, level.lower())(log_message)

    except Exception as e:
        # Fallback logging if structured logging fails
        logging.error(f"Logging failed: {str(e)}")
        logging.error(f"Original event: {event_type}")
        logging.error(f"Original data: {str(data)}")
