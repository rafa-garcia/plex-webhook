import requests
import json
from bs4 import BeautifulSoup

IMDB_KEYWORDS_URL = "https://www.imdb.com/title/{}/keywords/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_imdb_keywords(imdb_id):
    url = IMDB_KEYWORDS_URL.format(imdb_id)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if script_tag:
            data = json.loads(script_tag.string)
            return [
                kw["node"]["keyword"]["text"]["text"]
                for kw in data["props"]["pageProps"]["contentData"]["data"]["title"][
                    "keywords"
                ]["edges"]
            ]
    except requests.exceptions.RequestException as e:
        return []
    return []
