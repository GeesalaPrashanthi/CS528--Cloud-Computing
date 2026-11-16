#!/bin/bash
set -euo pipefail

REGION="us-central1"

gcloud compute http-health-checks describe hw8-health-check \
  >/dev/null 2>&1 || \
gcloud compute http-health-checks create hw8-health-check \
  --port=8080 \
  --request-path=/healthz \
  --check-interval=5s \
  --timeout=3s \
  --healthy-threshold=2 \
  --unhealthy-threshold=2

gcloud compute target-pools describe hw8-target-pool \
  --region="$REGION" >/dev/null 2>&1 || \
gcloud compute target-pools create hw8-target-pool \
  --region="$REGION" \
  --http-health-check=hw8-health-check

gcloud compute target-pools add-instances hw8-target-pool \
  --instances=hw8-server-a \
  --instances-zone=us-central1-a \
  --region="$REGION"

gcloud compute target-pools add-instances hw8-target-pool \
  --instances=hw8-server-b \
  --instances-zone=us-central1-b \
  --region="$REGION"

gcloud compute addresses describe hw8-lb-ip \
  --region="$REGION" >/dev/null 2>&1 || \
gcloud compute addresses create hw8-lb-ip \
  --region="$REGION"

gcloud compute forwarding-rules describe hw8-lb-rule \
  --region="$REGION" >/dev/null 2>&1 || \
gcloud compute forwarding-rules create hw8-lb-rule \
  --region="$REGION" \
  --ports=8080 \
  --address=hw8-lb-ip \
  --target-pool=hw8-target-pool

echo "Load balancer configuration complete."
