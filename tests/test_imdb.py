from src.imdb import get_imdb_keywords


def test_get_imdb_keywords():
    keywords = get_imdb_keywords("tt0111161")
    assert isinstance(keywords, list)
