import json
from unittest.mock import patch, MagicMock
import pytest
from src.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestHealthCheck:
    @patch("src.app.celery.control.ping")
    @patch("src.app.validate_plex_token")
    def test_health_check_success(self, mock_plex, mock_celery, client):
        # Mock successful services
        mock_celery.return_value = [{"ok": "pong"}]
        mock_plex.return_value = (True, "Connected")

        # Make request
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data["status"] == "success"
        assert data["message"] == "All services operational"
        assert data["services"]["celery"]["status"] == "connected"
        assert data["services"]["plex"]["status"] == "connected"

    @patch("src.app.celery.control.ping")
    @patch("src.app.validate_plex_token")
    def test_health_check_celery_failure(self, mock_plex, mock_celery, client):
        # Mock failing Celery
        mock_celery.side_effect = Exception("Connection failed")
        mock_plex.return_value = (True, "Connected")

        # Make request
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert response.status_code == 500
        assert data["status"] == "error"
        assert "One or more services" in data["message"]
        assert data["services"]["celery"]["status"] == "error"

    @patch("src.app.celery.control.ping")
    @patch("src.app.validate_plex_token")
    def test_health_check_plex_failure(self, mock_plex, mock_celery, client):
        # Mock failing Plex
        mock_celery.return_value = [{"ok": "pong"}]
        mock_plex.return_value = (False, "Connection failed")

        # Make request
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert response.status_code == 500
        assert data["status"] == "error"
        assert "One or more services" in data["message"]
        assert data["services"]["plex"]["status"] == "error"


class TestPlexWebhook:
    @patch("src.app.async_update_labels.delay")
    @patch("src.app.extract_imdb_id")
    def test_plex_webhook_success(self, mock_extract, mock_task, client):
        # Mock task and IMDB ID extraction
        mock_task.return_value = MagicMock(id="task-123")
        mock_extract.return_value = "tt123"

        # Test payload
        payload = {
            "event": "library.new",
            "Metadata": {"ratingKey": "456", "title": "Test Movie", "year": 2023},
        }

        # Make request
        response = client.post(
            "/api/plex-webhook",
            data={"payload": json.dumps(payload)},
            content_type="multipart/form-data",
        )
        data = json.loads(response.data)

        assert response.status_code == 202
        assert data["status"] == "processing"
        assert data["task_id"] == "task-123"
        assert data["movie"]["title"] == "Test Movie"

    def test_plex_webhook_missing_payload(self, client):
        # Make request without payload
        response = client.post("/api/plex-webhook")
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Missing payload" in data["message"]

    def test_plex_webhook_invalid_event(self, client):
        # Test payload with invalid event
        payload = {
            "event": "not.library.new",
            "Metadata": {"ratingKey": "456", "title": "Test Movie"},
        }

        # Make request
        response = client.post(
            "/api/plex-webhook",
            data={"payload": json.dumps(payload)},
            content_type="multipart/form-data",
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Invalid or unsupported" in data["message"]

    def test_plex_webhook_empty_payload(self, client):
        # Make request with empty payload
        response = client.post(
            "/api/plex-webhook",
            data={"payload": "{}"},
            content_type="multipart/form-data",
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Empty or invalid payload" in data["message"]


class TestUpdateLabels:
    @patch("src.app.async_update_labels.delay")
    def test_update_labels_success(self, mock_task, client):
        # Mock task
        mock_task.return_value = MagicMock(id="task-456")

        # Test payload
        payload = {"imdb_id": "tt1234567"}

        # Make request
        response = client.post(
            "/api/update-labels/789", json=payload, content_type="application/json"
        )
        data = json.loads(response.data)

        assert response.status_code == 202
        assert data["status"] == "processing"
        assert data["task_id"] == "task-456"
        assert data["details"]["imdb_id"] == "tt1234567"
        assert data["details"]["rating_key"] == "789"

    def test_update_labels_invalid_rating_key(self, client):
        # Make request with invalid rating key
        response = client.post(
            "/api/update-labels/abc",
            json={"imdb_id": "tt123"},
            content_type="application/json",
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Invalid rating key format" in data["message"]

    def test_update_labels_missing_imdb_id(self, client):
        # Make request with empty payload - imdb_id is required
        response = client.post(
            "/api/update-labels/123",
            json={"other_field": "value"},
            content_type="application/json",
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Valid IMDb ID is required" in data["message"]

    def test_update_labels_empty_payload(self, client):
        # Make request with empty JSON object
        response = client.post(
            "/api/update-labels/123",
            json={},
            content_type="application/json",
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Valid IMDb ID is required" in data["message"]

    def test_update_labels_null_payload(self, client):
        # Make request with null payload
        response = client.post(
            "/api/update-labels/123", data="null", content_type="application/json"
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "valid JSON object" in data["message"]

    def test_update_labels_invalid_content_type(self, client):
        # Make request with wrong content-type
        response = client.post(
            "/api/update-labels/123",
            data=json.dumps({"imdb_id": "tt1234567"}),
            content_type="text/plain",
        )
        data = json.loads(response.data)

        assert response.status_code == 415
        assert data["status"] == "error"
        assert "Content-Type" in data["message"]

    @patch("src.app.validate_imdb_id")
    def test_update_labels_invalid_imdb_format(self, mock_validate, client):
        # Mock IMDB ID validation failure
        mock_validate.return_value = False

        # Make request with invalid IMDB ID
        response = client.post(
            "/api/update-labels/123",
            json={"imdb_id": "invalid-id"},
            content_type="application/json",
        )
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["status"] == "error"
        assert "Invalid IMDb ID format" in data["message"]
