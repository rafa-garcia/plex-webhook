import pytest
from unittest.mock import patch, Mock
import requests
from src.plex import validate_plex_token, validate_rating_key, update_plex_labels


def test_validate_rating_key():
    # Valid cases
    assert validate_rating_key("123") is True
    assert validate_rating_key("1") is True
    assert validate_rating_key(123) is True  # Numeric input

    # Invalid cases
    assert validate_rating_key("") is False
    assert validate_rating_key(None) is False
    assert validate_rating_key("abc") is False
    assert validate_rating_key("123abc") is False


@pytest.mark.parametrize(
    "status_code,expected_result,expected_message",
    [
        (200, True, "Connected to Plex server successfully"),
        (401, False, "Invalid Plex token"),
        (404, False, "Plex server not found"),
        (503, False, "Failed to connect to Plex server"),
    ],
)
@patch("src.plex.requests.get")
def test_validate_plex_token(mock_get, status_code, expected_result, expected_message):
    # Configure mock response
    mock_resp = Mock()
    mock_resp.status_code = status_code

    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None

    mock_get.return_value = mock_resp

    result, message = validate_plex_token()

    assert result is expected_result
    assert expected_message in message


@patch("src.plex.requests.put")
def test_update_plex_labels_success(mock_put):
    # Configure successful mock response
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_put.return_value = mock_resp

    result = update_plex_labels("123", ["label1", "label2"])
    assert result is True
    mock_put.assert_called_once()


@patch("src.plex.requests.put")
def test_update_plex_labels_timeout(mock_put):
    # Simulate timeout exception
    mock_put.side_effect = requests.exceptions.Timeout()

    result = update_plex_labels("123", ["label1"])
    assert result is False


@patch("src.plex.requests.put")
def test_update_plex_labels_auth_error(mock_put):
    # Mock auth error response
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_resp
    )
    mock_put.return_value = mock_resp

    result = update_plex_labels("123", ["label1"])
    assert result is False
