# CS528 Homework 3 - Microservices with Google Cloud

This repository contains the two Python services created for CS528 Homework 3.

## Architecture

- **Service 1** runs as an HTTP Google Cloud Function.
  - Supports `GET` and `POST` requests.
  - Reads HTML files from `gs://cs528-hw2-pgeesala/pages/`.
  - Returns `404` for missing files.
  - Returns `501` for unsupported HTTP methods.
  - Reads the `X-country` header.
  - Returns `400` for assignment-defined forbidden countries and publishes the event to Pub/Sub.
- **Service 2** runs locally.
  - Subscribes to `forbidden-requests-sub`.
  - Prints forbidden-request events to standard output.
  - Appends events to `gs://cs528-hw2-pgeesala/forbidden_requests/forbidden_requests.log`.

## Google Cloud Resources

- Project: `enduring-trees-508117-p7`
- Region: `us-central1`
- Bucket: `cs528-hw2-pgeesala`
- Service account: `hw3-service@enduring-trees-508117-p7.iam.gserviceaccount.com`
- Pub/Sub topic: `forbidden-requests`
- Pub/Sub subscription: `forbidden-requests-sub`
- Cloud Function: `file-service`

## Service 1

### Requirements

```text
functions-framework
google-cloud-storage
google-cloud-pubsub
```

### Deploy

Run from the `service1` directory:

```bash
gcloud functions deploy file-service \
  --gen2 \
  --runtime=python312 \
  --region=us-central1 \
  --source=. \
  --entry-point=file_service \
  --trigger-http \
  --allow-unauthenticated \
  --service-account=hw3-service@enduring-trees-508117-p7.iam.gserviceaccount.com
```

### Test GET

```bash
curl -i \
  https://us-central1-enduring-trees-508117-p7.cloudfunctions.net/file-service/1.html
```

Expected status: `200`.

### Test POST

```bash
curl -i \
  -X POST \
  https://us-central1-enduring-trees-508117-p7.cloudfunctions.net/file-service \
  -H "Content-Type: application/json" \
  -d '{"file":"1.html"}'
```

Expected status: `200`.

### Test Missing File

```bash
curl -i \
  https://us-central1-enduring-trees-508117-p7.cloudfunctions.net/file-service/missing.html
```

Expected status: `404`.

### Test Unsupported Method

```bash
curl -i \
  -X PUT \
  https://us-central1-enduring-trees-508117-p7.cloudfunctions.net/file-service/1.html
```

Expected status: `501`.

### Test Forbidden Country

```bash
curl -i \
  https://us-central1-enduring-trees-508117-p7.cloudfunctions.net/file-service/1.html \
  -H "X-country: Iran"
```

Expected status: `400`.

## Service 2

### Requirements

```text
google-cloud-storage
google-cloud-pubsub
```

### Local Authentication

Service 2 uses service-account impersonation rather than a downloaded service-account key.

```bash
gcloud iam service-accounts add-iam-policy-binding \
  hw3-service@enduring-trees-508117-p7.iam.gserviceaccount.com \
  --member="user:pgeesala@bu.edu" \
  --role="roles/iam.serviceAccountTokenCreator"
```

```bash
gcloud auth application-default login \
  --impersonate-service-account=hw3-service@enduring-trees-508117-p7.iam.gserviceaccount.com
```

### Run Service 2

```bash
cd service2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python subscriber.py
```

Service 2 should print each forbidden request received from Pub/Sub.

### Verify GCS Log

```bash
gcloud storage cat \
  gs://cs528-hw2-pgeesala/forbidden_requests/forbidden_requests.log
```

## Provided 100-Request Client

The macOS client was run with:

```bash
./http-client \
  -d us-central1-enduring-trees-508117-p7.cloudfunctions.net \
  -b none \
  -w file-service \
  -n 100 \
  -i 12000 \
  -s
```

## Notes

- Homework 2 HTML files are stored under `pages/` in the Cloud Storage bucket.
- Error requests are recorded using both print statements and structured logging.
