from celery import Celery
from src.imdb import get_imdb_keywords
from src.plex import update_plex_labels
from config import settings

celery = Celery("tasks", broker=settings.CELERY_BROKER_URL)


@celery.task
def async_update_labels(imdb_id, rating_key):
    labels = get_imdb_keywords(imdb_id)
    update_plex_labels(rating_key, labels)
    return {
        "status": "success",
        "message": f"Handled {imdb_id} with rating key {rating_key}",
    }
