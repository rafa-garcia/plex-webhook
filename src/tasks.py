from celery import Celery
from celery.exceptions import MaxRetriesExceededError
from src.imdb import get_imdb_keywords
from src.plex import update_plex_labels
from src.utils import log_event
from config import settings

celery = Celery("tasks", broker=settings.CELERY_BROKER_URL)
celery.conf.task_routes = {"tasks.async_update_labels": {"queue": "labels"}}
celery.conf.task_default_retry_delay = 300  # 5 minutes
celery.conf.task_max_retries = 3


@celery.task(bind=True, max_retries=3, default_retry_delay=300)
def async_update_labels(self, imdb_id, rating_key):
    """
    Asynchronously fetch IMDb keywords and update Plex labels.

    Args:
        imdb_id (str): IMDb ID of the movie
        rating_key (str): Plex rating key for the movie

    Returns:
        dict: Status of the operation
    """
    try:
        log_event(
            "task_started",
            {
                "imdb_id": imdb_id,
                "rating_key": rating_key,
                "attempt": self.request.retries + 1,
            },
        )

        # Get IMDb keywords
        labels = get_imdb_keywords(imdb_id)
        if not labels:
            raise ValueError(f"No keywords found for IMDb ID: {imdb_id}")

        # Limit number of labels to prevent oversized requests
        labels = labels[:50]  # Reasonable limit for Plex

        # Update Plex labels
        success = update_plex_labels(rating_key, labels)
        if not success:
            raise Exception(
                f"Failed to update Plex labels for rating key: {rating_key}"
            )

        log_event(
            "task_completed",
            {
                "imdb_id": imdb_id,
                "rating_key": rating_key,
                "labels_count": len(labels),
            },
        )

        return {
            "status": "success",
            "message": f"Updated {len(labels)} labels for {imdb_id}",
            "labels": labels,
        }

    except Exception as exc:
        log_event(
            "task_error",
            {
                "imdb_id": imdb_id,
                "rating_key": rating_key,
                "error": str(exc),
                "attempt": self.request.retries + 1,
            },
        )

        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            log_event(
                "task_failed",
                {
                    "imdb_id": imdb_id,
                    "rating_key": rating_key,
                    "final_error": str(exc),
                },
            )
            raise
