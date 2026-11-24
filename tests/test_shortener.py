import unittest

from src.hash_table import HashTable, LinearProbingHashTable
from src.shortener import URLShortener


class TestURLShortener(unittest.TestCase):
    hash_table_class = HashTable

    def setUp(self):
        self.shortener = URLShortener(
            bucket_count=128,
            hash_table_class=self.hash_table_class,
        )

    def test_shortens_and_expands_urls_with_sequential_base62_codes(self):
        first_url = "https://example.com/a"
        second_url = "http://example.org/b"

        first_code = self.shortener.shorten(first_url)
        second_code = self.shortener.shorten(second_url)

        self.assertEqual(first_code, "0")
        self.assertEqual(second_code, "1")
        self.assertEqual(self.shortener.expand(first_code), first_url)
        self.assertEqual(self.shortener.expand(second_code), second_url)

    def test_duplicate_url_reuses_code_without_consuming_an_id(self):
        url = "https://example.com/repeated"

        first_code = self.shortener.shorten(url)
        repeated_code = self.shortener.shorten(url)
        next_code = self.shortener.shorten("https://example.org/new")

        self.assertEqual(first_code, repeated_code)
        self.assertEqual(next_code, "1")

    def test_codes_cross_base62_digit_boundary(self):
        codes = []
        for identifier in range(64):
            codes.append(self.shortener.shorten(f"https://example.com/{identifier}"))

        self.assertEqual(codes[0], "0")
        self.assertEqual(codes[61], "Z")
        self.assertEqual(codes[62], "10")
        self.assertEqual(codes[63], "11")

    def test_scheme_is_case_insensitive_and_only_http_s_is_allowed(self):
        self.assertEqual(self.shortener.shorten("HTTP://example.com"), "0")
        self.assertEqual(self.shortener.shorten("HtTpS://example.org"), "1")

        with self.assertRaises(ValueError):
            self.shortener.shorten("ftp://example.com")

    def test_rejects_empty_and_surrounding_whitespace(self):
        for url in ["", " https://example.com", "https://example.com "]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.shortener.shorten(url)

        self.assertEqual(self.shortener.shorten("https://example.com"), "0")

    def test_accepts_long_urls_without_an_application_length_limit(self):
        url = "https://example.com/" + "a" * 10_000

        code = self.shortener.shorten(url)

        self.assertEqual(self.shortener.expand(code), url)

    def test_uses_two_hash_tables_for_bidirectional_lookup(self):
        url = "https://example.com"
        code = self.shortener.shorten(url)

        self.assertIsInstance(self.shortener.url_to_code, self.hash_table_class)
        self.assertIsInstance(self.shortener.code_to_url, self.hash_table_class)
        self.assertEqual(self.shortener.url_to_code.get(url), code)
        self.assertEqual(self.shortener.code_to_url.get(code), url)

    def test_expand_raises_for_unknown_code(self):
        with self.assertRaises(KeyError):
            self.shortener.expand("unknown")


class TestLinearProbingURLShortener(TestURLShortener):
    hash_table_class = LinearProbingHashTable


if __name__ == "__main__":
    unittest.main()
