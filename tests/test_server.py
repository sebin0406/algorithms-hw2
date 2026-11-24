import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import create_server
from src.hash_table import LinearProbingHashTable
from src.shortener import URLShortener


class TestShortenerServer(unittest.TestCase):

    def setUp(self):
        self.shortener = URLShortener(bucket_count=1)
        self.server = create_server(
            host="127.0.0.1",
            port=0,
            shortener=self.shortener,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode("utf-8")
        connection.close()
        return result

    def post_url(self, url, headers=None):
        form_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            form_headers.update(headers)
        return self.request("POST", "/shorten", urlencode({"url": url}), form_headers)

    def test_home_page_has_mobile_friendly_url_form(self):
        status, headers, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('name="viewport"', body)
        self.assertIn('action="/shorten"', body)
        self.assertIn('name="url"', body)

    def test_shortens_url_and_redirects_from_generated_link(self):
        status, headers, body = self.post_url(
            "https://example.com/a?b=1",
            {
                "X-Forwarded-Host": "public.example.test",
                "X-Forwarded-Proto": "https",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn("https://public.example.test/s/0", body)

        status, redirect_headers, _ = self.request("GET", "/s/0")

        self.assertEqual(status, 302)
        self.assertEqual(redirect_headers["Location"], "https://example.com/a?b=1")

    def test_local_link_uses_request_host_and_http_scheme(self):
        status, _, body = self.post_url("http://example.com/local")

        self.assertEqual(status, 200)
        self.assertIn(f"http://127.0.0.1:{self.port}/s/0", body)

    def test_invalid_url_shows_readable_error_without_consuming_code(self):
        status, _, body = self.post_url("ftp://example.com")

        self.assertEqual(status, 400)
        self.assertIn("http:// 또는 https://", body)

        status, _, body = self.post_url("https://example.com/valid")

        self.assertEqual(status, 200)
        self.assertIn("/s/0", body)

    def test_unknown_code_returns_404_without_redirect(self):
        status, headers, _ = self.request("GET", "/s/unknown")

        self.assertEqual(status, 404)
        self.assertNotIn("Location", headers)

    def test_table_shows_both_real_chains_and_horner_calculations(self):
        self.shortener.shorten("https://example.com/first")
        self.shortener.shorten("https://example.com/second")

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("URL → 단축 코드", body)
        self.assertIn("단축 코드 → 원본 URL", body)
        self.assertIn("https://example.com/first", body)
        self.assertIn("https://example.com/second", body)
        self.assertIn("<details>", body)
        self.assertIn("Horner", body)
        self.assertIn("버킷 0", body)

    def test_linear_probing_table_shows_real_probe_paths(self):
        linear_shortener = URLShortener(
            bucket_count=2,
            hash_table_class=LinearProbingHashTable,
        )
        linear_shortener.shorten("https://example.com/first")
        linear_shortener.shorten("https://example.com/second")
        linear_server = create_server(
            host="127.0.0.1",
            port=0,
            shortener=linear_shortener,
        )
        linear_thread = threading.Thread(
            target=linear_server.serve_forever,
            daemon=True,
        )
        linear_thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1",
            linear_server.server_address[1],
        )
        try:
            connection.request("GET", "/table")
            response = connection.getresponse()
            body = response.read().decode("utf-8")
        finally:
            connection.close()
            linear_server.shutdown()
            linear_server.server_close()
            linear_thread.join()

        self.assertEqual(response.status, 200)
        self.assertIn("선형 탐사", body)
        self.assertIn("선형 탐사 경로", body)
        self.assertIn("확인한 칸 수", body)
        self.assertIn("Horner 해시 계산 과정", body)
        self.assertIn("https://example.com/first", body)
        self.assertIn("https://example.com/second", body)


if __name__ == "__main__":
    unittest.main()
