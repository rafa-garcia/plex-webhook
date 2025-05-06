import requests
import json
import time
from functools import lru_cache
from bs4 import BeautifulSoup
from requests.exceptions import RequestException, Timeout
from src.utils import log_event

IMDB_KEYWORDS_URL = "https://www.imdb.com/title/{}/keywords/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

# Rate limiting settings
RATE_LIMIT_CALLS = 10  # Number of calls
RATE_LIMIT_PERIOD = 60  # Time period in seconds
last_calls = []


def is_rate_limited():
    """
    Check if we're currently rate limited.

    Returns:
        bool: True if rate limited, False otherwise
    """
    global last_calls
    now = time.time()

    # Remove calls older than our time period
    last_calls = [call for call in last_calls if call > now - RATE_LIMIT_PERIOD]

    # Check if we've hit our rate limit
    return len(last_calls) >= RATE_LIMIT_CALLS


def extract_imdb_id(metadata):
    """
    Extract IMDb ID from Plex metadata.

    Args:
        metadata (Dict[str, Any]): Plex metadata

    Returns:
        Optional[str]: IMDb ID if found and valid, None otherwise
    """
    try:
        for guid in metadata.get("Guid", []):
            if isinstance(guid, dict) and guid.get("id", "").startswith("imdb://"):
                imdb_id = guid["id"].split("imdb://")[1]
                if validate_imdb_id(imdb_id):
                    return imdb_id
    except Exception as e:
        log_event(
            "error",
            {
                "message": "Failed to extract IMDb ID",
                "error": str(e),
                "metadata": metadata,
            },
        )
    return None


def validate_imdb_id(imdb_id):
    """
    Validate IMDb ID format.

    Args:
        imdb_id (str): IMDb ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return bool(
        imdb_id
        and imdb_id.startswith("tt")
        and len(imdb_id) >= 7
        and imdb_id[2:].isdigit()
    )


@lru_cache(maxsize=1000)
def get_imdb_keywords(imdb_id):
    """
    Fetch IMDb keywords for a given IMDb ID with caching and rate limiting.

    Args:
        imdb_id (str): IMDb ID to fetch keywords for

    Returns:
        List[str]: List of keywords, empty list if none found or error occurs
    """
    if not validate_imdb_id(imdb_id):
        log_event("error", {"message": "Invalid IMDb ID format", "imdb_id": imdb_id})
        return []

    if is_rate_limited():
        log_event(
            "warning",
            {"message": "Rate limit reached for IMDb API", "imdb_id": imdb_id},
        )
        time.sleep(2)  # Brief pause to help avoid rate limiting

    url = IMDB_KEYWORDS_URL.format(imdb_id)
    start_time = time.time()

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        # Record this call for rate limiting
        last_calls.append(time.time())

        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

        if not script_tag:
            log_event(
                "error",
                {
                    "message": "IMDb page changed - no __NEXT_DATA__ found",
                    "imdb_id": imdb_id,
                },
            )
            return []

        try:
            data = json.loads(script_tag.string)
            keywords = [
                kw["node"]["keyword"]["text"]["text"]
                for kw in data["props"]["pageProps"]["contentData"]["data"]["title"][
                    "keywords"
                ]["edges"]
            ]

            log_event(
                "imdb_keywords_fetched",
                {
                    "imdb_id": imdb_id,
                    "keywords_count": len(keywords),
                    "response_time": round(time.time() - start_time, 2),
                },
            )

            return keywords

        except (KeyError, json.JSONDecodeError) as e:
            log_event(
                "error",
                {
                    "message": "Failed to parse IMDb response",
                    "imdb_id": imdb_id,
                    "error": str(e),
                },
            )
            return []

    except Timeout:
        log_event(
            "error",
            {
                "message": "Timeout fetching IMDb keywords",
                "imdb_id": imdb_id,
                "timeout": 15,
            },
        )
        return []

    except RequestException as e:
        log_event(
            "error",
            {
                "message": "Failed to fetch IMDb keywords",
                "imdb_id": imdb_id,
                "error": str(e),
                "status_code": (
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None
                ),
            },
        )
        return []
