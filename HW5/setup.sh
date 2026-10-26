#!/usr/bin/env bash
# CS528 HW5 - repeatable infrastructure setup (run from hw5 on Mac or Cloud Shell)
set -Eeuo pipefail
cd "$(dirname "$0")"

# Hardcoded project ID, as explicitly required by the assignment.
PROJECT_ID='enduring-trees-508117-p7'
REGION='us-east1'
ZONE='us-east1-c'
SQL_INSTANCE='cs528-hw5-mysql'
VM_NAME='hw5-server'
SERVICE_ACCOUNT_NAME='hw5-vm-sa'
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SECRET_NAME='hw5-db-password'
DB_NAME='cs528_hw5'
FIREWALL_RULE='hw5-allow-8080'

for cmd in gcloud python3; do
  command -v "$cmd" >/dev/null || { echo "Missing required command: $cmd" >&2; exit 1; }
done
for file in startup.sh setup_schema.py server.py reporter.py requirements.txt; do
  [[ -f "$file" ]] || { echo "Missing required file: $file" >&2; exit 1; }
done

gcloud config set project "$PROJECT_ID" >/dev/null
printf 'Enabling required APIs...\n'
gcloud services enable compute.googleapis.com sqladmin.googleapis.com \
  secretmanager.googleapis.com iam.googleapis.com --project "$PROJECT_ID"

if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name='CS528 HW5 VM' --project="$PROJECT_ID"
fi
# Bucket access is intentionally limited to storage.objectViewer, not storage.admin.
for role in roles/cloudsql.client roles/storage.objectViewer roles/logging.logWriter roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" --role="$role" --quiet >/dev/null
done

# VM's startup script reads this secret. Never put the password in git or VM metadata.
if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Creating Secret Manager secret $SECRET_NAME."
  gcloud secrets create "$SECRET_NAME" --replication-policy=automatic --project="$PROJECT_ID"
  read -r -s -p 'Enter Cloud SQL root password (input hidden): ' DB_PASSWORD
  echo
  printf '%s' "$DB_PASSWORD" | gcloud secrets versions add "$SECRET_NAME" \
    --data-file=- --project="$PROJECT_ID" >/dev/null
  unset DB_PASSWORD
else
  echo "Reusing Secret Manager secret: $SECRET_NAME (verify its latest version matches current root password)."
fi

# Reuse an existing Cloud SQL instance, or create it once with the required settings.
if gcloud sql instances describe "$SQL_INSTANCE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Cloud SQL instance exists; starting it (without replacing data)."
  gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=ALWAYS \
    --project="$PROJECT_ID" --quiet
else
  echo "Cloud SQL instance absent; creating MySQL 8.4 Enterprise zonal instance."
  gcloud sql instances create "$SQL_INSTANCE" --project="$PROJECT_ID" \
    --database-version=MYSQL_8_4 --edition=ENTERPRISE \
    --cpu=4 --memory=16GiB --storage-type=SSD --storage-size=100 \
    --region="$REGION" --zone="$ZONE" --availability-type=ZONAL \
    --assign-ip --no-deletion-protection
fi

# Schema initialization is idempotent; check/create database and tables on every run.
# Uses local proxy and a temporary virtualenv. No root password is placed in arguments.
if ! command -v cloud-sql-proxy >/dev/null; then
  echo 'Install cloud-sql-proxy and add it to PATH before running setup.sh.' >&2
  exit 1
fi
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  echo 'Application Default Credentials missing. Run gcloud auth application-default login.' >&2
  exit 1
fi
LOCAL_VENV="${TMPDIR:-/tmp}/cs528-hw5-schema-venv"
python3 -m venv "$LOCAL_VENV"
"$LOCAL_VENV/bin/python" -m pip -q install pymysql
cloud-sql-proxy --port 3307 "${PROJECT_ID}:${REGION}:${SQL_INSTANCE}" >/tmp/hw5-proxy.log 2>&1 &
PROXY_PID=$!
trap 'kill "$PROXY_PID" 2>/dev/null || true' EXIT
for _ in {1..40}; do
  if (echo >/dev/tcp/127.0.0.1/3307) >/dev/null 2>&1; then break; fi
  if ! kill -0 "$PROXY_PID" 2>/dev/null; then cat /tmp/hw5-proxy.log >&2; exit 1; fi
  sleep 2
done
export DB_HOST=127.0.0.1 DB_PORT=3307 DB_USER=root DB_NAME
DB_PASSWORD="$(gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID")"
export DB_PASSWORD
"$LOCAL_VENV/bin/python" setup_schema.py
unset DB_PASSWORD
kill "$PROXY_PID" 2>/dev/null || true
wait "$PROXY_PID" 2>/dev/null || true
trap - EXIT

if ! gcloud compute firewall-rules describe "$FIREWALL_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud compute firewall-rules create "$FIREWALL_RULE" --project="$PROJECT_ID" \
    --network=default --direction=INGRESS --allow=tcp:8080 \
    --source-ranges=0.0.0.0/0 --target-tags=hw5-server
fi

# startup.sh clones from public GitHub, so ensure hw5 is pushed before invoking this.
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  STATUS="$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format='value(status)')"
  if [[ "$STATUS" == TERMINATED ]]; then
    gcloud compute instances start "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID"
  else
    echo "VM already exists (status: $STATUS); retaining it."
  fi
else
  gcloud compute instances create "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" \
    --machine-type=e2-standard-4 --image-family=debian-12 --image-project=debian-cloud \
    --service-account="$SERVICE_ACCOUNT" --scopes=cloud-platform \
    --tags=hw5-server --boot-disk-size=25GB \
    --metadata-from-file=startup-script=startup.sh
fi

SERVER_IP="$(gcloud compute instances describe "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)')"
echo "Setup commands finished. VM public IP: ${SERVER_IP}"
echo "Test URL (after startup finishes): http://${SERVER_IP}:8080/1.html"
echo 'Remember: this starts billable Cloud SQL compute and a VM. Run cleanup.sh after testing.'
