from unittest.mock import patch
from src.utils import sanitise_string, create_error_response, log_event
from src.app import app


def test_sanitise_string():
    # Test None input
    assert sanitise_string(None) == ""

    # Test basic string
    assert sanitise_string("hello") == "hello"

    # Test string with special chars
    assert sanitise_string('<script>alert("xss")</script>') == "scriptalert(xss)/script"
    assert sanitise_string("'; DROP TABLE users; --") == " DROP TABLE users --"

    # Test length limit
    long_str = "a" * 2000
    assert len(sanitise_string(long_str)) == 1000


def test_create_error_response():
    with app.test_request_context():
        response, status_code = create_error_response("Test error", 400)
        assert status_code == 400
        assert response.json == {"status": "error", "message": "Test error"}


@patch("src.utils.logging")
def test_log_event(mock_logging):
    # Test info level logging
    log_event("test_event", {"key": "value"})
    mock_logging.info.assert_called_once()

    # Test error level with stacktrace
    with patch("src.utils.traceback.format_exc", return_value="stacktrace"):
        log_event("error_event", {"error": "test"}, level="error")
        mock_logging.error.assert_called_once()
        assert "stacktrace" in mock_logging.error.call_args[0][0]
