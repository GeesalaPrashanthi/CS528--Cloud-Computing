
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class ReporterHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        try:
            event = json.loads(data)
            print(
                f"FORBIDDEN REQUEST: Country={event.get('country')}, "
                f"IP={event.get('ip')}, File={event.get('file')}",
                flush=True
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Reported")
        except (ValueError, UnicodeDecodeError):
            self.send_response(400)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8081), ReporterHandler)
    print("Country reporting service running on port 8081", flush=True)
    server.serve_forever()

