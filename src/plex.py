import requests

from requests.exceptions import RequestException, Timeout
from src.utils import log_event
from config import settings


def validate_plex_token():
    """
    Validate Plex token by making a test request to the Plex server.

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        url = f"{settings.PLEX_URL}/library/sections"
        headers = {
            "X-Plex-Token": settings.PLEX_TOKEN,
            "Accept": "application/json",
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return True, "Connected to Plex server successfully"

    except Timeout:
        return False, "Timeout connecting to Plex server"
    except RequestException as e:
        status_code = (
            getattr(e.response, "status_code", None) if hasattr(e, "response") else None
        )
        if status_code == 401:
            return False, "Invalid Plex token"
        elif status_code == 404:
            return False, "Plex server not found"
        else:
            return False, f"Failed to connect to Plex server: {str(e)}"


def validate_rating_key(rating_key):
    """
    Validate the Plex rating key format.

    Args:
        rating_key (str): The Plex rating key to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return bool(rating_key and str(rating_key).isdigit())


def update_plex_labels(rating_key, labels):
    """
    Update Plex movie labels using the Plex API.

    Args:
        rating_key (str): Plex rating key for the movie
        labels (List[str]): List of labels to apply

    Returns:
        bool: True if update was successful, False otherwise
    """
    if not validate_rating_key(rating_key):
        log_event(
            "error",
            {"message": "Invalid rating key format", "rating_key": rating_key},
        )
        return False

    if not labels or not isinstance(labels, list):
        log_event(
            "error",
            {"message": "Invalid labels format", "rating_key": rating_key},
        )
        return False

    # Filter out any empty or non-string labels
    labels = [
        str(label).strip()
        for label in labels
        if label and isinstance(label, (str, int, float))
    ]

    if not labels:
        log_event(
            "warning",
            {"message": "No valid labels to update", "rating_key": rating_key},
        )
        return False

    url = f"{settings.PLEX_URL}/library/metadata/{rating_key}"
    headers = {
        "X-Plex-Token": settings.PLEX_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Create params with validated labels
    params = {f"label[{i}].tag.tag": value for i, value in enumerate(labels)}

    try:
        response = requests.put(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        log_event(
            "plex_labels_updated",
            {
                "rating_key": rating_key,
                "labels_count": len(labels),
                "status_code": response.status_code,
            },
        )

        return True

    except Timeout:
        log_event(
            "error",
            {
                "message": "Timeout updating Plex labels",
                "rating_key": rating_key,
                "timeout": 10,
            },
        )
        return False

    except RequestException as e:
        log_event(
            "error",
            {
                "message": "Failed to update Plex labels",
                "rating_key": rating_key,
                "error": str(e),
                "status_code": (
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None
                ),
            },
        )
        return False
