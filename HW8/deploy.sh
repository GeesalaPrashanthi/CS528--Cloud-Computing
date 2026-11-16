
#!/bin/bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-enduring-trees-508117-p7}"
ZONE="${ZONE:-us-central1-a}"
REGION="${ZONE%-*}"
BUCKET="${BUCKET:-cs528-hw2-pgeesala}"
SERVER_SA="hw4-server-sa@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "$PROJECT_ID"

# Reserve a static external IP if necessary
if ! gcloud compute addresses describe hw4-server-ip \
    --region="$REGION" >/dev/null 2>&1; then
    gcloud compute addresses create hw4-server-ip \
        --region="$REGION"
fi

SERVER_IP=$(gcloud compute addresses describe hw4-server-ip \
    --region="$REGION" --format="value(address)")

# Firewall: public access to web server
if ! gcloud compute firewall-rules describe hw4-allow-server \
    >/dev/null 2>&1; then
    gcloud compute firewall-rules create hw4-allow-server \
        --network=default \
        --allow=tcp:8080 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=hw4-server
fi

# Firewall: private access to reporter
if ! gcloud compute firewall-rules describe hw4-allow-reporter \
    >/dev/null 2>&1; then
    gcloud compute firewall-rules create hw4-allow-reporter \
        --network=default \
        --allow=tcp:8081 \
        --source-tags=hw4-server \
        --target-tags=hw4-reporter
fi

# Create reporter first
if ! gcloud compute instances describe hw4-reporter \
    --zone="$ZONE" >/dev/null 2>&1; then
    gcloud compute instances create hw4-reporter \
        --zone="$ZONE" \
        --machine-type=e2-micro \
        --image-family=debian-12 \
        --image-project=debian-cloud \
        --tags=hw4-reporter \
        --metadata-from-file=startup-script=reporter-startup.sh
fi

REPORTER_IP=$(gcloud compute instances describe hw4-reporter \
    --zone="$ZONE" \
    --format="value(networkInterfaces[0].networkIP)")

# Set reporter address in the server startup script
sed "s|Environment=REPORTER_URL=.*|Environment=REPORTER_URL=http://${REPORTER_IP}:8081|" \
    server-startup.sh > server-startup-deploy.sh

# Create web server with dedicated service account
if ! gcloud compute instances describe hw4-server \
    --zone="$ZONE" >/dev/null 2>&1; then
    gcloud compute instances create hw4-server \
        --zone="$ZONE" \
        --machine-type=e2-micro \
        --image-family=debian-12 \
        --image-project=debian-cloud \
        --address="$SERVER_IP" \
        --service-account="$SERVER_SA" \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --tags=hw4-server \
        --metadata-from-file=startup-script=server-startup-deploy.sh
fi

echo "Deployment commands completed."
echo "Server IP: $SERVER_IP"
echo "Reporter internal IP: $REPORTER_IP"
echo "Server URL: http://${SERVER_IP}:8080/1.html"
gcloud compute instances list \
    --filter="name=(hw4-server OR hw4-reporter)"

