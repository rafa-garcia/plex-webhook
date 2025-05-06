from datetime import datetime, timezone
import json
import logging
import re
import traceback

from flask import jsonify


def sanitise_string(value):
    """
    Convert any value to a string and remove potentially harmful characters.

    Args:
        value (Any): Value to sanitise

    Returns:
        str: sanitised string
    """
    if value is None:
        return ""

    # Convert to string and remove/replace potentially harmful characters
    sanitised = str(value).strip()
    sanitised = re.sub(r"[<>]", "", sanitised)  # Remove angle brackets
    sanitised = re.sub(r'[\'";]', "", sanitised)  # Remove quotes and semicolons
    return sanitised[:1000]  # Limit length to prevent abuse


def create_error_response(message, status_code):
    """
    Create a standardised error response.

    Args:
        message (str): Error message
        status_code (int): HTTP status code

    Returns:
        Tuple[Response, int]: Flask response and status code
    """
    return jsonify({"status": "error", "message": message}), status_code


def log_event(event_type, data, level="info"):
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
