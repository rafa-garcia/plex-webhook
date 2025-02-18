import re


def is_valid_imdb_id(imdb_id):
    return bool(re.match(r"tt\d{7,8}$", imdb_id))
