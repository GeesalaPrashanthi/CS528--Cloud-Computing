"""HW5 web server: HW4 behavior plus SQL logging and high-resolution timings."""
import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import pymysql
from google.api_core.exceptions import NotFound
from google.cloud import logging as cloud_logging, storage

BUCKET = os.getenv('BUCKET', 'cs528-hw2-pgeesala')
PORT = int(os.getenv('PORT', '8080'))
REPORTER_URL = os.getenv('REPORTER_URL', 'http://127.0.0.1:8081')
DB_CONFIG = dict(host=os.getenv('DB_HOST', '127.0.0.1'), port=int(os.getenv('DB_PORT', '3307')),
                 user=os.getenv('DB_USER', 'root'), password=os.environ['DB_PASSWORD'],
                 database=os.getenv('DB_NAME', 'cs528_hw5'), charset='utf8mb4',
                 autocommit=True, connect_timeout=10, read_timeout=15, write_timeout=15)
BANNED_COUNTRIES = {'north korea', 'iran', 'cuba', 'myanmar', 'iraq', 'libya', 'sudan', 'zimbabwe', 'syria'}
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET)
log_client = cloud_logging.Client()
logger = log_client.logger('hw5-server')
_thread_db = threading.local()
_stats_lock = threading.Lock()
_stats = {'headers': [0, 0], 'storage': [0, 0], 'response': [0, 0], 'database': [0, 0]}


def record_timing(stage, start_ns):
    elapsed = time.perf_counter_ns() - start_ns
    with _stats_lock:
        _stats[stage][0] += 1
        _stats[stage][1] += elapsed
        if stage == 'database' and _stats[stage][0] % 1000 == 0:
            print('Timing averages (ms): ' + ', '.join(
                f'{key}={total / count / 1e6:.3f}' for key, (count, total) in _stats.items() if count),
                flush=True)


def get_db():
    conn = getattr(_thread_db, 'conn', None)
    if conn is None:
        conn = pymysql.connect(**DB_CONFIG)
        _thread_db.conn = conn
    else:
        conn.ping(reconnect=True)
    return conn


def log_request(metadata, status):
    """Write EVERY handled HTTP request; non-200 requests additionally enter errors."""
    start = time.perf_counter_ns()
    request_time = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO requests
                (request_time,country,client_ip,gender,age,income,is_banned,time_of_day,requested_file,http_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (request_time, metadata['country'], metadata['client_ip'], metadata['gender'],
                 metadata['age'], metadata['income'], metadata['is_banned'], metadata['time_of_day'],
                 metadata['requested_file'], status))
            if status != 200:
                cur.execute('''INSERT INTO request_errors (request_time,requested_file,error_code)
                               VALUES (%s,%s,%s)''', (request_time, metadata['requested_file'], status))
    except Exception as exc:
        print(f'DATABASE LOGGING FAILURE: {exc}', flush=True)
        raise
    finally:
        record_timing('database', start)


def cloud_error(severity, method, path, message):
    logger.log_struct({'method': method, 'path': path, 'message': message}, severity=severity)


def notify_reporter(event):
    try:
        req = urllib.request.Request(REPORTER_URL, data=json.dumps(event).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=3):
            pass
    except Exception as exc:
        print(f'Reporter communication failed: {exc}', flush=True)


class RequestHandler(BaseHTTPRequestHandler):
    def extract_metadata(self):
        start = time.perf_counter_ns()
        def header(*names):
            for name in names:
                value = self.headers.get(name)
                if value is not None:
                    return value.strip()
            return None
        country = header('X-Country', 'Country')
        age = header('X-Age', 'Age')
        metadata = {'country': country, 'client_ip': header('X-Forwarded-For') or self.client_address[0],
                    'gender': header('X-Gender', 'Gender'), 'age': age,
                    'income': header('X-Income', 'Income'),
                    'is_banned': bool(country and country.lower() in BANNED_COUNTRIES),
                    'time_of_day': header('X-Time-Of-Day', 'X-Time', 'Time-Of-Day'),
                    'requested_file': unquote(urlparse(self.path).path)}
        record_timing('headers', start)
        return metadata

    def send_result(self, status, content):
        start = time.perf_counter_ns()
        if isinstance(content, str):
            content = content.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        record_timing('response', start)

    def fetch_file(self, filename):
        start = time.perf_counter_ns()
        filename = filename.strip('/')
        if filename.startswith(BUCKET + '/'):
            filename = filename[len(BUCKET) + 1:]
        if not filename.startswith('pages/'):
            filename = 'pages/' + filename
        try:
            content = bucket.blob(filename).download_as_bytes()
            status = 200
        except NotFound:
            cloud_error('WARNING', self.command, filename, 'Requested file does not exist')
            content, status = '404 Not Found', 404
        finally:
            record_timing('storage', start)
        self.send_result(status, content)
        return status

    def handle_request(self):
        metadata = self.extract_metadata()
        status = None
        try:
            if metadata['is_banned']:
                cloud_error('CRITICAL', self.command, self.path,
                            f"Forbidden request from {metadata['country']}")
                notify_reporter({'country': metadata['country'], 'ip': metadata['client_ip'],
                                 'file': self.path, 'method': self.command})
                status = 403
                self.send_result(status, '403 Forbidden')
            elif self.command == 'GET':
                status = self.fetch_file(metadata['requested_file'])
            elif self.command == 'POST':
                length = int(self.headers.get('Content-Length', 0))
                payload = self.rfile.read(length).decode('utf-8')
                try:
                    obj = json.loads(payload)
                    filename = (obj.get('file') or obj.get('filename')) if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    filename = payload.strip()
                if filename:
                    metadata['requested_file'] = filename
                    status = self.fetch_file(filename)
                else:
                    status = 400
                    self.send_result(status, 'Missing filename')
            else:
                cloud_error('ERROR', self.command, self.path, 'Unsupported HTTP method')
                status = 501
                self.send_result(status, '501 Not Implemented')
        except Exception as exc:
            print(f'Request failure: {exc}', flush=True)
            if status is None:
                status = 500
                try:
                    self.send_result(status, '500 Internal Server Error')
                except Exception:
                    pass
        finally:
            if status is not None:
                log_request(metadata, status)

    do_GET = handle_request
    do_POST = handle_request
    do_PUT = handle_request
    do_DELETE = handle_request
    do_HEAD = handle_request
    do_CONNECT = handle_request
    do_OPTIONS = handle_request
    do_TRACE = handle_request
    do_PATCH = handle_request


class HW5Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


if __name__ == '__main__':
    print(f'HW5 server running on port {PORT}', flush=True)
    HW5Server(('0.0.0.0', PORT), RequestHandler).serve_forever()
