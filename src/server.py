import argparse
import html
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.shortener import URLShortener


_STYLE = """
<style>
:root { color-scheme: light; font-family: system-ui, sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; background: #f3f6fb; color: #172033; }
main { width: min(100% - 2rem, 960px); margin: 2rem auto; }
.card { background: white; border: 1px solid #dce3ee; border-radius: 1rem;
        padding: clamp(1rem, 4vw, 2rem); box-shadow: 0 8px 24px #1720330d; }
h1, h2 { line-height: 1.2; }
nav { display: flex; gap: 1rem; margin-bottom: 1.25rem; }
a { color: #155eef; overflow-wrap: anywhere; }
label { display: block; font-weight: 650; margin-bottom: .5rem; }
input[type=url] { width: 100%; min-height: 3rem; padding: .7rem;
                  border: 1px solid #aeb9ca; border-radius: .55rem;
                  font: inherit; }
button { width: 100%; min-height: 3rem; margin-top: .8rem; border: 0;
         border-radius: .55rem; background: #155eef; color: white;
         font: inherit; font-weight: 700; cursor: pointer; }
.error { padding: .8rem; border-radius: .5rem; background: #fff0ef; color: #a32118; }
.result { margin-top: 1rem; padding: 1rem; background: #eef5ff;
          border-radius: .6rem; }
.table-wrap { overflow-x: auto; margin: 1rem 0 2rem; }
table { width: 100%; min-width: 35rem; border-collapse: collapse; background: white; }
th, td { padding: .7rem; border: 1px solid #dce3ee; text-align: left; vertical-align: top; }
th { background: #edf2fa; }
ol.chain { margin: 0; padding-left: 1.5rem; }
ol.chain > li { padding: .35rem 0 .65rem; overflow-wrap: anywhere; }
code { white-space: pre-wrap; overflow-wrap: anywhere; }
details { margin-top: .4rem; }
summary { cursor: pointer; color: #155eef; }
@media (max-width: 520px) {
  main { width: min(100% - 1rem, 960px); margin: .5rem auto; }
  nav { flex-wrap: wrap; }
}
</style>
"""

_FORM = """
<form method="post" action="/shorten">
  <label for="url">단축할 URL</label>
  <input id="url" name="url" type="url" required autocomplete="url"
         placeholder="https://example.com/long/path">
  <button type="submit">짧은 링크 만들기</button>
</form>
"""

_INVALID_URL_MESSAGE = (
    "올바른 URL을 입력해 주세요. URL은 비어 있거나 앞뒤 공백이 있을 수 없으며, "
    "http:// 또는 https://로 시작해야 합니다."
)


def _page(title, content):
    return (
        "<!doctype html><html lang=\"ko\"><head>"
        '<meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title>{_STYLE}</head>"
        f"<body><main><nav><a href=\"/\">URL 단축</a>"
        '<a href="/table">해시 테이블</a></nav>'
        f"<section class=\"card\">{content}</section></main></body></html>"
    )


def _render_horner_details(table, key):
    current = 0
    steps = []
    for character in key:
        next_value = (31 * current + ord(character)) % table.bucket_count
        steps.append(
            "<li>"
            f"c={html.escape(repr(character))}, ord(c)={ord(character)}: "
            f"(31 × {current} + {ord(character)}) mod {table.bucket_count} "
            f"= {next_value}"
            "</li>"
        )
        current = next_value

    return (
        "<details><summary>Horner 해시 계산 과정</summary>"
        f"<p>초기값 h = 0, 버킷 수 M = {table.bucket_count}</p>"
        f"<ol>{''.join(steps)}</ol>"
        f"<p>최종 버킷: {current}</p></details>"
    )


def _render_table(title, table):
    rows = []
    for bucket_index, first_node in enumerate(table.buckets):
        chain = []
        node = first_node
        while node is not None:
            key = str(node.key)
            value = str(node.value)
            chain.append(
                "<li>"
                f"<strong>키:</strong> <code>{html.escape(key)}</code><br>"
                f"<strong>값:</strong> <code>{html.escape(value)}</code>"
                f"{_render_horner_details(table, key)}"
                "</li>"
            )
            node = node.next

        chain_content = "".join(chain) if chain else "<li>비어 있음</li>"
        rows.append(
            f"<tr><th scope=\"row\">버킷 {bucket_index}</th>"
            f"<td><ol class=\"chain\">{chain_content}</ol></td></tr>"
        )

    load_factor = table.load_factor
    return (
        f"<section><h2>{title}</h2>"
        f"<p>버킷 수: {table.bucket_count} · 항목 수: {len(table)} · "
        f"적재율: {load_factor:.4f}</p>"
        "<div class=\"table-wrap\"><table><thead><tr>"
        "<th>버킷 번호</th><th>개별 체이닝 (키 → 값)</th>"
        "</tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table></div></section>"
    )


def _valid_authority(value):
    if not value:
        return None

    authority = value.split(",", 1)[0].strip()
    if not authority or any(
        character.isspace()
        or ord(character) < 0x20
        or character in "/\\@?#<>\"'"
        for character in authority
    ):
        return None

    try:
        parsed = urlsplit(f"//{authority}")
        if (
            parsed.hostname is None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        parsed.port
    except ValueError:
        return None

    return authority


def _request_origin(handler):
    authority = _valid_authority(handler.headers.get("X-Forwarded-Host"))
    if authority is None:
        authority = _valid_authority(handler.headers.get("Host"))
    if authority is None:
        authority = f"localhost:{handler.server.server_port}"

    forwarded_protocol = handler.headers.get("X-Forwarded-Proto", "")
    protocol = forwarded_protocol.split(",", 1)[0].strip().lower()
    if protocol not in ("http", "https"):
        protocol = "http"

    return f"{protocol}://{authority}"


def create_server(host="0.0.0.0", port=8000, shortener=None):
    if shortener is None:
        shortener = URLShortener()

    class ShortenerRequestHandler(BaseHTTPRequestHandler):
        def _send_html(self, status, document):
            body = document.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _show_home(self, error=None, submitted_url=""):
            error_markup = ""
            if error:
                error_markup = (
                    f'<p class="error" role="alert">{html.escape(error)}</p>'
                )
            submitted_markup = ""
            if submitted_url:
                submitted_markup = (
                    "<p>입력한 URL: "
                    f"<code>{html.escape(submitted_url)}</code></p>"
                )
            content = (
                "<h1>URL 단축기</h1>"
                "<p>긴 URL을 입력해 짧은 링크를 만들어 보세요.</p>"
                f"{error_markup}{_FORM}{submitted_markup}"
            )
            self._send_html(200 if error is None else 400, _page("URL 단축기", content))

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                self._show_home()
                return

            if path == "/table":
                content = (
                    "<h1>현재 해시 테이블</h1>"
                    + _render_table(
                        "URL → 단축 코드",
                        shortener.url_to_code,
                    )
                    + _render_table(
                        "단축 코드 → 원본 URL",
                        shortener.code_to_url,
                    )
                )
                self._send_html(200, _page("해시 테이블", content))
                return

            if path.startswith("/s/"):
                code = unquote(path[len("/s/"):])
                try:
                    original_url = shortener.expand(code)
                except KeyError:
                    self._send_html(
                        404,
                        _page(
                            "링크를 찾을 수 없음",
                            "<h1>링크를 찾을 수 없습니다</h1>"
                            "<p>코드가 없거나 만료되었을 수 있습니다.</p>",
                        ),
                    )
                    return

                if any(ord(character) < 0x20 or ord(character) == 0x7f
                       for character in original_url):
                    self._send_html(
                        400,
                        _page(
                            "잘못된 링크",
                            "<h1>잘못된 링크</h1><p>이 링크로 이동할 수 없습니다.</p>",
                        ),
                    )
                    return

                self.send_response(302)
                self.send_header("Location", original_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            self._send_html(
                404,
                _page("페이지를 찾을 수 없음", "<h1>페이지를 찾을 수 없습니다</h1>"),
            )

        def do_POST(self):
            if urlsplit(self.path).path != "/shorten":
                self._send_html(
                    404,
                    _page("페이지를 찾을 수 없음", "<h1>페이지를 찾을 수 없습니다</h1>"),
                )
                return

            content_type = self.headers.get("Content-Type", "")
            if not content_type.lower().startswith("application/x-www-form-urlencoded"):
                self._show_home("폼 데이터를 읽을 수 없습니다.")
                return

            try:
                content_length = int(self.headers.get("Content-Length", ""))
                if content_length < 0:
                    raise ValueError
            except ValueError:
                self._show_home("요청 데이터의 길이가 올바르지 않습니다.")
                return

            try:
                form = parse_qs(
                    self.rfile.read(content_length).decode("utf-8"),
                    keep_blank_values=True,
                )
            except UnicodeDecodeError:
                self._show_home(_INVALID_URL_MESSAGE)
                return

            urls = form.get("url", [])
            url = urls[0] if urls else ""
            if any(ord(character) < 0x20 or ord(character) == 0x7f for character in url):
                self._show_home(_INVALID_URL_MESSAGE, url)
                return

            try:
                code = shortener.shorten(url)
            except ValueError:
                self._show_home(_INVALID_URL_MESSAGE, url)
                return

            short_link = f"{_request_origin(self)}/s/{code}"
            content = (
                "<h1>짧은 링크가 준비됐습니다</h1>"
                "<p>아래 링크를 열면 원래 URL로 이동합니다.</p>"
                "<div class=\"result\"><p>단축 코드: "
                f"<code>{html.escape(code)}</code></p>"
                f'<p><a href="{html.escape(short_link, quote=True)}">'
                f"{html.escape(short_link)}</a></p></div>"
                f"<p>원래 URL: <code>{html.escape(url)}</code></p>"
                f"{_FORM}"
            )
            self._send_html(200, _page("짧은 링크 생성", content))

    return ThreadingHTTPServer((host, port), ShortenerRequestHandler)


def main():
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)
    print(f"URL shortener listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping URL shortener.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
