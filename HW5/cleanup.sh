#!/usr/bin/env bash
# CS528 HW5 - tear down billable HW5 infrastructure while preserving the SQL database.
# Run from hw5 on your Mac or Cloud Shell. Idempotent where resources are absent.
set -Eeuo pipefail
cd "$(dirname "$0")"

PROJECT_ID='enduring-trees-508117-p7'
ZONE='us-east1-c'
SQL_INSTANCE='cs528-hw5-mysql'
VM_NAME='hw5-server'
FIREWALL_RULE='hw5-allow-8080'
SERVICE_ACCOUNT_NAME='hw5-vm-sa'
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

command -v gcloud >/dev/null || { echo 'gcloud is required' >&2; exit 1; }

# Always pass the hardcoded project, never rely on the grader's configured project.
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Deleting HW5 VM: $VM_NAME"
  gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet
else
  echo "HW5 VM $VM_NAME already absent."
fi

if gcloud compute firewall-rules describe "$FIREWALL_RULE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Deleting HW5 firewall rule: $FIREWALL_RULE"
  gcloud compute firewall-rules delete "$FIREWALL_RULE" --project="$PROJECT_ID" --quiet
else
  echo "HW5 firewall rule already absent."
fi

# setup.sh uses an ephemeral external VM IP, not a reserved static IP.
# If you manually reserve any HW5 static IP, release it here by name:
# gcloud compute addresses delete <hw5-address-name> --region=us-east1 --project="$PROJECT_ID" --quiet

# The SQL instance MUST NOT be deleted; stop its compute billing instead.
if gcloud sql instances describe "$SQL_INSTANCE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Stopping Cloud SQL instance (preserving databases and tables): $SQL_INSTANCE"
  gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=NEVER \
    --project="$PROJECT_ID" --quiet
else
  echo "Cloud SQL instance $SQL_INSTANCE not found; skipping."
fi

# Keep the service account and DB-password secret so setup.sh can reuse them.
# They do not run compute resources; permissions can be audited separately.

# The assignment explicitly calls for revoking application-default credentials
# if application-default login was used. This affects LOCAL user ADC credentials
# and may require re-login for other projects later.
echo 'Revoking local application-default credentials, if any...'
gcloud auth application-default revoke --quiet 2>/dev/null || true

echo 'HW5 cleanup finished. Cloud SQL storage/backups and any retained public IP-related charges may continue.'
echo 'Check Cloud SQL instance status and Compute Engine instance list in the console.'
