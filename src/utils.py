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
        value: Value to sanitise

    Returns:
        Sanitised string, limited to 1000 characters
    """
    if value is None:
        return ""

    # Convert to string and remove/replace potentially harmful characters
    sanitised = str(value).strip()
    # Remove angle brackets (potential HTML/XML injection)
    sanitised = re.sub(r"[<>]", "", sanitised)
    # Remove quotes and semicolons (potential script injection)
    sanitised = re.sub(r'[\'";]', "", sanitised)
    # Limit length to prevent abuse
    return sanitised[:1000]


def create_error_response(message, status_code=400, **kwargs):
    """
    Create a standardised error response.

    Args:
        message: Error message
        status_code: HTTP status code, defaults to 400
        **kwargs: Additional data to include in the response

    Returns:
        Flask response and status code
    """
    response = {"status": "error", "message": message, **kwargs}
    return jsonify(response), status_code


def create_success_response(data, message="Success", status_code=200):
    """
    Create a standardized success response.

    Args:
        data: Data to include in the response
        message: Success message, defaults to "Success"
        status_code: HTTP status code, defaults to 200

    Returns:
        Flask response and status code
    """
    response = {"status": "success", "message": message, **data}
    return jsonify(response), status_code


def create_processing_response(task, details, message="Processing"):
    """
    Create a standardized processing response for async tasks.

    Args:
        task: Celery task object with an id attribute
        details: Additional details to include in the response
        message: Processing message, defaults to "Processing"

    Returns:
        Flask response with 202 status code
    """
    response = {
        "status": "processing",
        "message": message,
        "task_id": task.id,
        **details,
    }
    return jsonify(response), 202


def log_event(event_type, data, level="info", include_stacktrace=True):
    """
    Log structured event data with additional context.

    Args:
        event_type: Type of event being logged
        data: Event data to log
        level: Logging level (debug, info, warning, error, critical)
        include_stacktrace: Whether to include stacktrace for error logs
    """
    try:
        # Ensure valid log level
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if level not in valid_levels:
            level = "info"
            logging.warning(f"Invalid log level '{level}', defaulting to 'info'")

        log_data = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        # Add stacktrace for errors if requested
        if level == "error" and include_stacktrace:
            log_data["stacktrace"] = traceback.format_exc()

        # Format as JSON for structured logging
        log_message = json.dumps(log_data, indent=2)
        getattr(logging, level.lower())(log_message)

    except Exception as e:
        # Fallback logging if structured logging fails
        logging.error(f"Logging failed: {str(e)}")
        logging.error(f"Original event: {event_type}")
        try:
            logging.error(f"Original data: {str(data)}")
        except:
            logging.error("Could not serialize original data")


def is_valid_json(json_str):
    """
    Check if a string is valid JSON.

    Args:
        json_str: JSON string to validate

    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False
