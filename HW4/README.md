# CS528 Homework 4: VM-based HTTP Services

This folder contains the VM-based version of the HTTP file service and forbidden-country reporter from HW3. The web server uses Python's standard-library `http.server` (not Flask).

## Architecture

- `hw4-server`: Compute Engine `e2-micro` running `server.py` on TCP port 8080; assigned a reserved static public IP and a dedicated service account.
- `hw4-reporter`: Compute Engine `e2-micro` running `reporter.py` on TCP port 8081; the server communicates with it over the internal VPC network.
- `hw4-client`: separate Debian 13 VM running the supplied Linux HTTP client for 100-file and concurrent-load tests.
- Cloud Storage bucket: `gs://cs528-hw2-pgeesala`, object directory `pages/`.

## Files

| File | Purpose |
| --- | --- |
| `server.py` | GET/POST object serving, 404/501 handling, Cloud Logging, forbidden-country notification |
| `reporter.py` | Receives forbidden-request POST events and prints an event message |
| `requirements.txt` | Google Cloud Python client libraries |
| `server-startup.sh` | Installs dependencies and launches server as a `systemd` service |
| `reporter-startup.sh` | Installs and launches reporter as a `systemd` service |
| `deploy.sh` | Creates or reuses the service VMs, static IP, and relevant firewall rules |

## Prerequisites

1. Install and authenticate the Google Cloud CLI: `gcloud auth login`.
2. Use or create the GCP project, and enable Compute Engine, IAM, Cloud Logging, Cloud Monitoring and Cloud Storage APIs.
3. Ensure the HW2 bucket and the `pages/` objects exist.
4. Create a dedicated web-server service account, and grant only these required roles:
   - `roles/storage.objectViewer` **on the bucket**
   - `roles/logging.logWriter` on the project
   - `roles/monitoring.metricWriter` on the project (for Ops Agent metrics)
5. Ensure the executing identity can create Compute Engine resources and attach the dedicated service account. The script assumes the `default` VPC exists and the service account has already been created.

Example setup (adapt project and bucket if needed):

```bash
export PROJECT_ID=enduring-trees-508117-p7
export BUCKET=cs528-hw2-pgeesala
export SERVER_SA=hw4-server-sa@$PROJECT_ID.iam.gserviceaccount.com
gcloud config set project "$PROJECT_ID"
gcloud services enable compute.googleapis.com iam.googleapis.com logging.googleapis.com monitoring.googleapis.com storage.googleapis.com
gcloud iam service-accounts create hw4-server-sa --display-name='HW4 Web Server'
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member="serviceAccount:$SERVER_SA" --role=roles/storage.objectViewer
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SERVER_SA" --role=roles/logging.logWriter
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SERVER_SA" --role=roles/monitoring.metricWriter
```

If the service account already exists, skip the creation command.

## Deploy

From the HW4 directory:

```bash
chmod +x deploy.sh
PROJECT_ID=enduring-trees-508117-p7 ZONE=us-central1-a ./deploy.sh
```

The script creates the reporter first and inserts its internal IP into the web server's startup configuration. It is intended to be idempotent for already-created instances. **Caution:** a run against existing instances checks/reuses them; it does not redeploy modified Python source to those instances. Fresh creation through this wrapper was not separately verified during the assignment.

## Test HTTP requests

Replace `SERVER_IP` with the reserved address printed by `deploy.sh`:

```bash
export SERVER_IP=35.238.120.191
curl -i http://$SERVER_IP:8080/1.html
curl -i -X POST http://$SERVER_IP:8080/ -H 'Content-Type: application/json' -d '{"file":"1.html"}'
curl -i http://$SERVER_IP:8080/nonexistent99999.html
curl -i -X PUT http://$SERVER_IP:8080/1.html
curl -i http://$SERVER_IP:8080/1.html -H 'X-Country: Iran'
```

Expected statuses: 200, 200, 404, 501, and 403 respectively. The `X-Country` header is a controlled **client-supplied country test signal**, not validated IP geolocation.

## Provided client

Run on a **different Debian 13 VM** (the supplied Linux binary required glibc 2.38+). Example command:

```bash
./http-client -d 35.238.120.191 -p 8080 -b cs528-hw2-pgeesala -w pages -n 100 -i 12000 -t 5 -v
```

For stress testing, launch at most **four concurrent client processes**, use a short timeout (`-t 2` in this experiment), and record successes, permission-denied responses, and connection/timeout failures separately. Metrics can be exported from Cloud Monitoring for the `hw4-server` instance.

## Logs

Logs Explorer query:

```text
logName="projects/enduring-trees-508117-p7/logs/hw4-server"
```

- Missing object: `WARNING` / HTTP 404
- Unsupported method: `ERROR` / HTTP 501
- Forbidden-country header: `CRITICAL` / HTTP 403, plus a POST notification to the reporter VM

Reporter output: `sudo journalctl -u hw4-reporter -n 30 --no-pager`.

## Results and limitations

The initial 100-request run produced 95 HTTP 200 responses and 5 HTTP 403 responses. Under 1, 2, 3, and 4 client processes (100 requests each), the summary of timeout/connection-error lines was 0, 0, 0, and 14 respectively, excluding expected 403 responses. Values are based on textual counts from client logs, so the error-line count is not independently verified as a count of unique failed requests.

See the HW4 report for CPU, memory and network graphs calculated from Cloud Monitoring CSV exports. Account-level Billing Overview totals are not an exact stress-test-specific cost.

## Cleanup

After collecting all screenshots, logs and cost information, delete the temporary instances and release the static IP if it is no longer needed. This stops ongoing VM and external IP charges.
