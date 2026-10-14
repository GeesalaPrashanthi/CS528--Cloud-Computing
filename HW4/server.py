import urllib.request
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote
from google.cloud import storage, logging as cloud_logging
from google.api_core.exceptions import NotFound

BUCKET = os.getenv("BUCKET", "cs528-hw2-pgeesala")
PORT = int(os.getenv("PORT", "8080"))

REPORTER_URL = os.getenv(
    "REPORTER_URL",
    "http://127.0.0.1:8081"
)

BANNED_COUNTRIES = {
    "north korea", "iran", "cuba", "myanmar",
    "iraq", "libya", "sudan", "zimbabwe", "syria"
}

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET)
log_client = cloud_logging.Client()
logger = log_client.logger("hw4-server")


def log_error(severity, method, path, message):
    logger.log_struct(
        {"method": method, "path": path, "message": message},
        severity=severity
    )


class RequestHandler(BaseHTTPRequestHandler):

    def send_result(self, status, content):
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def fetch_file(self, filename):
        filename = filename.strip("/")

        if filename.startswith(BUCKET + "/"):
            filename = filename[len(BUCKET) + 1:]

        if not filename.startswith("pages/"):
            filename = "pages/" + filename

        try:
            content = bucket.blob(filename).download_as_bytes()
            self.send_result(200, content)
        except NotFound:
            log_error("WARNING", self.command, filename,
                      "Requested file does not exist")
            self.send_result(404, "404 Not Found")
        
    def check_country(self):
        country = self.headers.get("X-Country", "").strip()

        if country.lower() not in BANNED_COUNTRIES:
            return False

        event = {
            "country": country,
            "ip": self.client_address[0],
            "file": self.path,
            "method": self.command
        }

        log_error(
            "CRITICAL",
            self.command,
            self.path,
            f"Forbidden request from {country}"
        )

        try:
            request = urllib.request.Request(
                REPORTER_URL,
                data=json.dumps(event).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(request, timeout=3):
                pass
        except Exception as exc:
            print(f"Reporter communication failed: {exc}", flush=True)

        self.send_result(403, "403 Forbidden")
        return True

    def do_GET(self):
        if self.check_country():
            return
        filename = unquote(urlparse(self.path).path)
        self.fetch_file(filename)

    def do_POST(self):
        if self.check_country():
            return
        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length).decode("utf-8")

        try:
            data = json.loads(payload)
            filename = data.get("file") or data.get("filename")
        except (json.JSONDecodeError, AttributeError):
            filename = payload.strip()

        if not filename:
            self.send_result(400, "Missing filename")
            return

        self.fetch_file(filename)

    def unsupported(self):
        log_error("ERROR", self.command, self.path,
                  "Unsupported HTTP method")
        self.send_result(501, "501 Not Implemented")

    do_PUT = unsupported
    do_DELETE = unsupported
    do_HEAD = unsupported
    do_CONNECT = unsupported
    do_OPTIONS = unsupported
    do_TRACE = unsupported
    do_PATCH = unsupported


class LimitedHTTPServer(HTTPServer):
    request_queue_size = 1


if __name__ == "__main__":
    server = LimitedHTTPServer(("0.0.0.0", PORT), RequestHandler)
    print(f"HW4 server running on port {PORT}", flush=True)
    server.serve_forever()

