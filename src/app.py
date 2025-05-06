import json
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, Blueprint, request
from src.plex import validate_plex_token, validate_rating_key
from src.tasks import async_update_labels, celery
from src.utils import (
    log_event,
    sanitise_string,
    create_error_response,
    create_success_response,
    create_processing_response,
)
from src.imdb import validate_imdb_id, extract_imdb_id
from config import settings

# Initialize Flask app
app = Flask(__name__)

# Create API blueprint
api = Blueprint("api", __name__, url_prefix="/api")


# Decorators for common operations
def handle_exceptions(f):
    """Decorator to handle exceptions in route handlers."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except json.JSONDecodeError as e:
            log_event(
                "error",
                {"message": "Invalid JSON payload", "error": str(e)},
                level="error",
            )
            return create_error_response("Invalid JSON payload", 400)
        except ValueError as e:
            log_event(
                "error",
                {"message": "Validation error", "error": str(e)},
                level="error",
            )
            return create_error_response(str(e), 400)
        except Exception as e:
            log_event(
                "error",
                {"message": "Internal server error", "error": str(e)},
                level="error",
            )
            return create_error_response(f"Internal server error: {str(e)}", 500)

    return decorated_function


def validate_json_payload(f):
    """Decorator to validate JSON payload."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            log_event(
                "warning", {"message": "Missing JSON content type"}, level="warning"
            )
            return create_error_response("Content-Type must be application/json", 415)

        try:
            data = request.get_json(force=True)

            # Require a valid payload for all endpoints
            if data is None or not isinstance(data, dict):
                log_event("error", {"message": "Invalid or missing request body"})
                return create_error_response(
                    "Request body must be a valid JSON object", 400
                )

            request.parsed_data = data
            return f(*args, **kwargs)
        except Exception as e:
            log_event(
                "error",
                {"message": "Request processing failed", "error": str(e)},
                level="error",
            )
            return create_error_response("Request processing failed", 400)

    return decorated_function


# Route handlers
@api.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify service status.

    Returns:
        Tuple[Response, int]: Health status and HTTP code
    """
    services = {"celery": {"status": "unknown"}, "plex": {"status": "unknown"}}
    overall_status = "healthy"

    # Check Celery/Redis connection
    try:
        celery.control.ping(timeout=1)
        services["celery"] = {
            "status": "connected",
            "message": "Connected to Redis successfully",
        }
    except Exception as e:
        services["celery"] = {"status": "error", "message": str(e)}
        overall_status = "unhealthy"

    # Check Plex connection
    plex_status, plex_message = validate_plex_token()
    services["plex"] = {
        "status": "connected" if plex_status else "error",
        "message": plex_message,
    }
    if not plex_status:
        overall_status = "unhealthy"

    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }

    log_event(
        "health_check",
        {"status": overall_status, "services": services},
        level="error" if overall_status == "unhealthy" else "info",
    )

    if overall_status == "healthy":
        return create_success_response(data, message="All services operational")
    else:
        return create_error_response(
            "One or more services are experiencing issues", 500, **data
        )


@api.route("/plex-webhook", methods=["POST"])
@handle_exceptions
def plex_webhook():
    """
    Handle Plex webhook events and trigger IMDb label updates.

    Returns:
        Tuple[Response, int]: Response message and HTTP code
    """
    if "payload" not in request.form:
        log_event("error", {"message": "No payload in request"})
        return create_error_response("Missing payload", 400)

    data = json.loads(request.form["payload"])

    if not data or not isinstance(data, dict):
        log_event("error", {"message": "Empty or invalid payload"})
        return create_error_response("Empty or invalid payload", 400)

    log_event("webhook_received", {"data": data})

    # Validate required fields and event type
    if data.get("event") != "library.new":
        return create_error_response("Invalid or unsupported webhook event", 400)

    metadata = data.get("Metadata", {})
    imdb_id = extract_imdb_id(metadata)

    if not imdb_id:
        return create_error_response("No valid IMDb ID found", 400)

    rating_key = metadata.get("ratingKey")
    if not rating_key:
        return create_error_response("Missing Plex rating key", 400)

    if not validate_rating_key(rating_key):
        return create_error_response("Invalid rating key format", 400)

    # sanitise metadata fields
    title = sanitise_string(metadata.get("title"))
    year = metadata.get("year")

    # Queue background task
    task = async_update_labels.delay(imdb_id, rating_key)

    movie_details = {
        "movie": {
            "imdb_id": imdb_id,
            "rating_key": rating_key,
            "title": title,
            "year": year,
        }
    }

    log_event(
        "movie_processing",
        {**movie_details["movie"], "task_id": task.id},
    )

    return create_processing_response(
        task, movie_details, message=f"Processing {title} ({year})"
    )


@api.route("/update-labels/<rating_key>", methods=["POST"])
@handle_exceptions
@validate_json_payload
def update_labels(rating_key):
    """
    Manually trigger IMDb label updates for a specific Plex rating key.

    Args:
        rating_key (str): Plex rating key

    Returns:
        Tuple[Response, int]: Response message and HTTP code
    """
    if not validate_rating_key(rating_key):
        return create_error_response("Invalid rating key format", 400)

    data = request.parsed_data
    imdb_id = data.get("imdb_id", "")

    if not imdb_id:
        return create_error_response("Valid IMDb ID is required", 400)

    if not validate_imdb_id(imdb_id):
        log_event(
            "validation_error",
            {
                "message": "Invalid IMDb ID format",
                "imdb_id": imdb_id,
                "rating_key": rating_key,
            },
            level="warning",
        )
        return create_error_response("Invalid IMDb ID format", 400)

    # Queue background task
    task = async_update_labels.delay(imdb_id, rating_key)

    log_event(
        "manual_label_update",
        {"imdb_id": imdb_id, "rating_key": rating_key, "task_id": task.id},
    )

    return create_processing_response(
        task,
        {"details": {"imdb_id": imdb_id, "rating_key": rating_key}},
        message="Label update queued",
    )


# Register the API blueprint with the app
app.register_blueprint(api)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.PORT)
