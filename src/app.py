import json
from datetime import datetime
from flask import Flask, request, jsonify
from src.plex import validate_plex_token
from src.tasks import async_update_labels, celery
from src.utils import log_event, sanitise_string, create_error_response
from src.imdb import validate_imdb_id as is_valid_imdb_id, extract_imdb_id
from config import settings

# Initialize Flask app
app = Flask(__name__)


@app.route("/health", methods=["GET"])
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

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
    }

    log_event(
        "health_check",
        {"status": overall_status, "services": services},
        level="error" if overall_status == "unhealthy" else "info",
    )

    return jsonify(response), 200 if overall_status == "healthy" else 500


@app.route("/plex-webhook", methods=["POST"])
def plex_webhook():
    """
    Handle Plex webhook events and trigger IMDb label updates.

    Returns:
        Tuple[Response, int]: Response message and HTTP code
    """
    try:
        if "payload" not in request.form:
            log_event("error", {"message": "No payload in request"})
            return create_error_response("Missing payload")

        try:
            data = json.loads(request.form["payload"])
        except json.JSONDecodeError:
            log_event("error", {"message": "Invalid JSON payload"})
            return create_error_response("Invalid JSON payload")

        log_event("webhook_received", {"data": data})

        if not data or data.get("event") != "library.new":
            return create_error_response("Invalid or unsupported webhook event")

        metadata = data.get("Metadata", {})
        imdb_id = extract_imdb_id(metadata)

        if not imdb_id:
            return create_error_response("No valid IMDb ID found")

        rating_key = metadata.get("ratingKey")
        if not rating_key:
            return create_error_response("Missing Plex rating key")

        # sanitise metadata fields
        title = sanitise_string(metadata.get("title"))
        year = metadata.get("year")

        # Queue background task
        task = async_update_labels.delay(imdb_id, rating_key)

        log_event(
            "movie_processing",
            {
                "imdb_id": imdb_id,
                "rating_key": rating_key,
                "title": title,
                "year": year,
                "task_id": task.id,
            },
        )

        return (
            jsonify(
                {
                    "status": "processing",
                    "message": f"Processing {title} ({year})",
                    "task_id": task.id,
                    "movie": {
                        "imdb_id": imdb_id,
                        "rating_key": rating_key,
                        "title": title,
                        "year": year,
                    },
                }
            ),
            202,
        )

    except Exception as e:
        log_event(
            "error",
            {"message": "Webhook processing failed", "error": str(e)},
            level="error",
        )
        return create_error_response(f"Internal server error: {str(e)}", 500)


@app.route("/update-labels/<rating_key>", methods=["POST"])
def update_labels(rating_key):
    """
    Manually trigger IMDb label updates for a specific Plex rating key.

    Args:
        rating_key (str): Plex rating key

    Returns:
        Tuple[Response, int]: Response message and HTTP code
    """
    try:
        if not rating_key.isdigit():
            return create_error_response("Invalid rating key format")

        try:
            data = request.get_json()
        except json.JSONDecodeError:
            return create_error_response("Invalid JSON payload")

        if not data:
            return create_error_response("Missing request body")

        imdb_id = data.get("imdb_id")
        if not imdb_id or not is_valid_imdb_id(imdb_id):
            return create_error_response("Valid IMDb ID is required")

        # Queue background task
        task = async_update_labels.delay(imdb_id, rating_key)

        log_event(
            "manual_label_update",
            {"imdb_id": imdb_id, "rating_key": rating_key, "task_id": task.id},
        )

        return (
            jsonify(
                {
                    "status": "processing",
                    "message": "Label update queued",
                    "task_id": task.id,
                    "details": {"imdb_id": imdb_id, "rating_key": rating_key},
                }
            ),
            202,
        )

    except Exception as e:
        log_event(
            "error",
            {
                "message": "Manual label update failed",
                "error": str(e),
                "rating_key": rating_key,
            },
            level="error",
        )
        return create_error_response(f"Internal server error: {str(e)}", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.PORT)
