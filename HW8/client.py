import argparse
import csv
import time
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

parser = argparse.ArgumentParser()
parser.add_argument("--ip", default="136.71.104.228")
parser.add_argument(
    "--method",
    choices=["HEALTH", "GET", "POST"],
    default="HEALTH"
)
parser.add_argument("--file", default="1.html")
parser.add_argument("--country", default="")
parser.add_argument("--duration", type=int, default=240)
parser.add_argument("--output", default="results/failover.csv")
args = parser.parse_args()

output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)

url = (
    f"http://{args.ip}:8080/healthz"
    if args.method == "HEALTH"
    else f"http://{args.ip}:8080/{args.file}"
)
counts = Counter()
errors = 0
total = 0

print(f"Testing {url}")
print("Sending one GET request per second. Press Ctrl+C to stop.")
print("Timestamp | Status | Zone | Latency")

with output.open("w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow([
        "timestamp_utc", "status", "zone",
        "latency_ms", "error"
    ])

    start = time.monotonic()
    next_request = start

    try:
        while time.monotonic() - start < args.duration:
            now = datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            )
            t0 = time.monotonic()

            status = "ERROR"
            zone = "unknown"
            error = ""

            try:
                headers = {}

                if args.country:
                    headers["X-Country"] = args.country

                if args.method == "POST":
                    headers["Content-Type"] = "application/json"
                    req = urllib.request.Request(
                        url,
                        data=json.dumps({"file": args.file}).encode("utf-8"),
                        headers=headers,
                        method="POST"
                    )
                else:
                    req = urllib.request.Request(
                        url,
                        headers=headers,
                        method="GET"
                    )
                with urllib.request.urlopen(
                    req, timeout=3
                ) as response:
                    status = response.status
                    zone = response.headers.get(
                        "X-Server-Zone", "unknown"
                    )
                    response.read()

            except urllib.error.HTTPError as exc:
                status = exc.code
                zone = exc.headers.get(
                    "X-Server-Zone", "unknown"
                )
                error = str(exc)

            except Exception as exc:
                error = str(exc)
                errors += 1

            latency = round(
                (time.monotonic() - t0) * 1000, 2
            )

            total += 1
            if status == 200:
                counts[zone] += 1

            writer.writerow([
                now, status, zone, latency, error
            ])
            file.flush()

            print(
                f"{now} | {status} | "
                f"{zone} | {latency} ms",
                flush=True
            )

            next_request += 1
            time.sleep(
                max(0, next_request - time.monotonic())
            )

    except KeyboardInterrupt:
        print("\nClient stopped manually.")

print("\n===== SUMMARY =====")
print(f"Total requests: {total}")
print(f"Connection errors: {errors}")

successful = sum(counts.values())

for zone, count in sorted(counts.items()):
    percentage = (
        count / successful * 100 if successful else 0
    )
    print(f"{zone}: {count} ({percentage:.2f}%)")

print(f"Results saved to: {output}")
