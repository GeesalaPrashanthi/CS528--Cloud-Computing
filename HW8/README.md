# CS528 Cloud Computing — Homework 8

## Overview
This project extends HW4 by deploying two Python HTTP servers in different Google Cloud zones behind a regional external passthrough network load balancer.

Both servers support GET and POST requests, return the `X-Server-Zone` response header, and expose `/healthz` for health checks.

## Architecture
- GCP Project: enduring-trees-508117-p7
- Region: us-central1
- Server A: hw8-server-a (us-central1-a)
- Server B: hw8-server-b (us-central1-b)
- Reporter: hw8-reporter
- Machine type: e2-micro
- Target pool: hw8-target-pool
- Health check: hw8-health-check (HTTP, port 8080)
- Load balancer port: 8080
- Cloud Storage: gs://cs528-hw2-pgeesala

## Project Files
- server.py — HTTP server supporting GET, POST, zone headers and health checks
- client.py — HTTP client with zone tracking and CSV logging
- reporter.py — Forbidden-country reporting service
- server-startup.sh — Server startup configuration
- reporter-startup.sh — Reporter startup configuration
- deploy-hw8.sh — Creates the three VMs
- setup-load-balancer.sh — Configures the health check, target pool, IP and forwarding rule
- requirements.txt — Python dependencies
- results/ — Test results

## Deployment

Configure Google Cloud authentication and select the project.

```bash
gcloud auth login
gcloud config set project enduring-trees-508117-p7