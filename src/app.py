from flask import Flask, request, jsonify
from src.tasks import async_update_labels
from src.utils import is_valid_imdb_id, log_event
import logging
import json

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify API and Redis connectivity.
    """
    try:
        # Simple Redis connectivity check
        from celery.result import AsyncResult

        AsyncResult("test")  # This will fail if Celery/Redis is down

        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/plex-webhook", methods=["POST"])
def plex_webhook():
    """
    Handles Plex webhook events and triggers IMDb label updates.
    """
    try:
        if "payload" not in request.form:
            log_event("error", "No payload found in request")
            return jsonify({"status": "error", "message": "Invalid request"}), 400

        payload = request.form["payload"]
        data = json.loads(payload)

        log_event("plex_webhook_received", data)

        if not data or data.get("event") != "library.new":
            log_event("error", "Invalid webhook event")
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        metadata = data.get("Metadata", {})
        imdb_id = next(
            (
                guid["id"].split("imdb://")[1]
                for guid in metadata.get("Guid", [])
                if guid["id"].startswith("imdb://")
            ),
            None,
        )

        if imdb_id and is_valid_imdb_id(imdb_id):
            rating_key = metadata.get("ratingKey")
            title = metadata.get("title")
            year = metadata.get("year")

            async_update_labels.delay(imdb_id, rating_key)  # Run in background

            log_event(
                "movie_added",
                {
                    "imdb_id": imdb_id,
                    "rating_key": rating_key,
                    "title": title,
                    "year": year,
                },
            )
            return (
                jsonify(
                    {"message": f"Processing IMDb ID: {imdb_id}, {title} ({year})"}
                ),
                202,
            )

        return jsonify({"error": "No valid IMDb ID found"}), 400

    except json.JSONDecodeError:
        log_event("error", "Invalid JSON payload")
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    except Exception as e:
        log_event("error_processing_webhook", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/set-labels/<rating_key>", methods=["POST"])
def set_labels(rating_key):
    """
    Manually triggers IMDb label updates for a specific Plex rating key.
    """
    try:
        data = request.get_json()
        imdb_id = data.get("imdb_id")

        if not imdb_id or not is_valid_imdb_id(imdb_id):
            return jsonify({"error": "Valid IMDb ID is required"}), 400

        async_update_labels.delay(imdb_id, rating_key)  # Run in background
        log_event("set_labels", {"imdb_id": imdb_id, "rating_key": rating_key})
        return (
            jsonify({"message": f"Processing IMDb ID {imdb_id} in the background"}),
            202,
        )

    except json.JSONDecodeError:
        log_event("error", "Invalid JSON payload in set-labels")
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    except Exception as e:
        log_event("error_set_labels", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
