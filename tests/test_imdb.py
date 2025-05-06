from unittest.mock import patch, MagicMock
import json
from src.imdb import get_imdb_keywords


def test_get_imdb_keywords_success():
    mock_data = {
        "props": {
            "pageProps": {
                "contentData": {
                    "data": {
                        "title": {
                            "keywords": {
                                "edges": [
                                    {"node": {"keyword": {"text": {"text": "prison"}}}},
                                    {"node": {"keyword": {"text": {"text": "escape"}}}},
                                    {
                                        "node": {
                                            "keyword": {"text": {"text": "friendship"}}
                                        }
                                    },
                                ]
                            }
                        }
                    }
                }
            }
        }
    }

    mock_html = f"""
    <html>
    <script id="__NEXT_DATA__" type="application/json">
    {json.dumps(mock_data)}
    </script>
    </html>
    """

    with patch("src.imdb.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        keywords = get_imdb_keywords("tt0111161")
        assert keywords == ["prison", "escape", "friendship"]


def test_get_imdb_keywords_no_keywords():
    mock_data = {
        "props": {
            "pageProps": {
                "contentData": {"data": {"title": {"keywords": {"edges": []}}}}
            }
        }
    }

    mock_html = f"""
    <html>
    <script id="__NEXT_DATA__" type="application/json">
    {json.dumps(mock_data)}
    </script>
    </html>
    """

    with patch("src.imdb.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        keywords = get_imdb_keywords("tt0000000")
        assert keywords == []


def test_get_imdb_keywords_error():
    with patch("src.imdb.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception(
            "Failed to fetch IMDb page"
        )
        mock_get.return_value = mock_response

        keywords = get_imdb_keywords("invalid_id")
        assert keywords == []


def test_get_imdb_keywords_invalid_input():
    keywords = get_imdb_keywords("")
    assert keywords == []

    keywords = get_imdb_keywords(None)
    assert keywords == []
