from unittest.mock import patch
import pytest
from src.tasks import async_update_labels


@patch("src.tasks.update_plex_labels")
@patch("src.tasks.get_imdb_keywords")
def test_task_success(mock_keywords, mock_update):
    mock_keywords.return_value = ["keyword1", "keyword2"]
    mock_update.return_value = True

    result = async_update_labels.apply(args=("tt1234567", "456")).get()

    assert result["status"] == "success"
    assert "Updated 2 labels" in result["message"]
    assert result["labels"] == ["keyword1", "keyword2"]


@patch("src.tasks.get_imdb_keywords")
def test_task_no_keywords(mock_keywords):
    mock_keywords.return_value = []

    with pytest.raises(ValueError):
        async_update_labels.apply(args=("tt1234567", "456")).get()


@patch("src.tasks.update_plex_labels")
@patch("src.tasks.get_imdb_keywords")
def test_task_update_failure(mock_keywords, mock_update):
    mock_keywords.return_value = ["keyword1"]
    mock_update.return_value = False

    with pytest.raises(Exception):
        async_update_labels.apply(args=("tt1234567", "456")).get()
