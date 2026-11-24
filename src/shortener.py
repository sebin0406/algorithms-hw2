from src.base62 import encode
from src.hash_table import HashTable


class URLShortener:
    """Stores URL/code mappings and assigns sequential Base62 codes."""

    def __init__(self, bucket_count=16):
        self.url_to_code = HashTable(bucket_count)
        self.code_to_url = HashTable(bucket_count)
        self._next_id = 0

    def shorten(self, url):
        if not isinstance(url, str) or not url or url != url.strip():
            raise ValueError("url must be a non-empty string without surrounding whitespace")

        normalized_url = url.lower()
        if not (
            normalized_url.startswith("http://")
            or normalized_url.startswith("https://")
        ):
            raise ValueError("url must use the http or https scheme")

        if self.url_to_code.contains(url):
            return self.url_to_code.get(url)

        code = encode(self._next_id)
        self.url_to_code.put(url, code)
        self.code_to_url.put(code, url)
        self._next_id += 1
        return code

    def expand(self, code):
        if not self.code_to_url.contains(code):
            raise KeyError(code)
        return self.code_to_url.get(code)
