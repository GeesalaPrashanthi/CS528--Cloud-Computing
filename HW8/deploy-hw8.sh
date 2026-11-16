#!/bin/bash
set -euo pipefail

PROJECT="enduring-trees-508117-p7"
REGION="us-central1"
SA="hw8-server-sa@${PROJECT}.iam.gserviceaccount.com"

gcloud config set project "$PROJECT"

# Create reporter VM
gcloud compute instances create hw8-reporter \
  --zone="${REGION}-a" \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --tags=hw8-reporter \
  --metadata-from-file=startup-script=reporter-startup.sh

# Retrieve reporter private IP
REPORTER_IP=$(gcloud compute instances describe hw8-reporter \
  --zone="${REGION}-a" \
  --format="value(networkInterfaces[0].networkIP)")

echo "Reporter private IP: $REPORTER_IP"

# Configure the server startup script
sed "s|Environment=REPORTER_URL=.*|Environment=REPORTER_URL=http://${REPORTER_IP}:8081|" \
  server-startup.sh > server-startup-deploy.sh

# Create web server A
gcloud compute instances create hw8-server-a \
  --zone="${REGION}-a" \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --service-account="$SA" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=hw8-server \
  --metadata-from-file=startup-script=server-startup-deploy.sh

# Create web server B
gcloud compute instances create hw8-server-b \
  --zone="${REGION}-b" \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --service-account="$SA" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=hw8-server \
  --metadata-from-file=startup-script=server-startup-deploy.sh

echo "HW8 VM creation commands completed."

gcloud compute instances list \
  --filter="name~^hw8-" \
  --format="table(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"
