import requests
from config import settings


def update_plex_labels(movie_id, labels):
    url = f"{settings.PLEX_URL}/library/metadata/{movie_id}"
    headers = {"X-Plex-Token": settings.PLEX_TOKEN, "Accept": "application/json"}
    params = {f"label[{i}].tag.tag": value for i, value in enumerate(labels)}

    try:
        response = requests.put(url, headers=headers, params=params, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False
