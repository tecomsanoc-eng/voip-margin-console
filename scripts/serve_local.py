"""Local dev server: serves public/ and synthesises the Supabase payload.

Lets the rebuilt UI be tested end to end without a Supabase project, and
doubles as the offline way to run the console on a machine with no internet.

    python scripts\\serve_local.py
    -> http://localhost:8000/?local

/payload.json is assembled from data/*.json in exactly the shape
get_console_payload() returns, so if the app works here it will work against
Supabase. Binds to loopback only — this serves live commercial data and must
not be reachable from the network.
"""
import io
import json
import os
import sys

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError:  # pragma: no cover - Python 2 is not supported
    sys.exit("Python 3 required.")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUBLIC = os.path.join(ROOT, "public")
DATA_DIR = os.path.join(ROOT, "data")

PORT = int(os.environ.get("PORT", "8000"))

_payload_cache = None


def read(name):
    path = os.path.join(DATA_DIR, name + ".json")
    if not os.path.isfile(path):
        raise IOError(
            "%s is missing. Run scripts/extract_from_html.py first." % path)
    with io.open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_payload():
    """Mirror get_console_payload(): same keys, same array shapes."""
    global _payload_cache
    if _payload_cache is not None:
        return _payload_cache

    payload = {
        "RAW": read("raw"),
        "TRUNK": read("trunk"),
        "CUST": read("cust"),
        "AMDATA": read("amdata"),
        "CARR": read("carr"),
        "DAILY": read("daily"),
    }
    _payload_cache = json.dumps(payload).encode("utf-8")
    return _payload_cache


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        SimpleHTTPRequestHandler.__init__(self, *a, directory=PUBLIC, **kw)

    def do_GET(self):
        if self.path.split("?")[0] in ("/payload.json", "/public/payload.json"):
            try:
                body = build_payload()
            except IOError as err:
                self.send_error(500, str(err))
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def main():
    if not os.path.isfile(os.path.join(PUBLIC, "index.html")):
        sys.exit("public/index.html missing. Run scripts/build_app.py first.")

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print("Serving %s" % PUBLIC)
    print("Open  http://localhost:%d/?local\n" % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
