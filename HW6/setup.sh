#!/usr/bin/env bash
# Starts SQL, creates a temporary VM, runs ML, prints GCS files, then cleans up.
set -euo pipefail
cd "$(dirname "$0")"
export PROJECT_ID="${PROJECT_ID:-enduring-trees-508117-p7}"
export VM_NAME="hw6-run-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
export RESUME_SCHEDULER=1
SERVICE_ACCOUNT="${VM_SERVICE_ACCOUNT:-564644496048-compute@developer.gserviceaccount.com}"
SSH_OPTIONS=(--ssh-key-file="${SSH_KEY_FILE:-$HOME/.ssh/google_compute_engine}")
armed=0
finish() {
 rc=$?;trap - EXIT INT TERM
 if (( armed )); then bash cleanup.sh || rc=1;fi
 exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
command -v gcloud >/dev/null
mkdir -p evidence
state="$(gcloud scheduler jobs describe hw5-hourly-sql-stop --location=us-east1 --project="$PROJECT_ID" --format='value(state)')"
if [[ "$state" == ENABLED ]]; then
 gcloud scheduler jobs pause hw5-hourly-sql-stop --location=us-east1 --project="$PROJECT_ID"
 RESUME_SCHEDULER=1
fi
armed=1
gcloud sql instances patch cs528-hw5-mysql --activation-policy=ALWAYS --project="$PROJECT_ID" --quiet
gcloud compute instances create "$VM_NAME" --project="$PROJECT_ID" --zone=us-east1-b \
 --machine-type=e2-medium --image-family=debian-12 --image-project=debian-cloud \
 --service-account="$SERVICE_ACCOUNT" --scopes=cloud-platform --boot-disk-size=10GB \
 --labels=assignment=cs528-hw6,managed-by=hw6-setup --quiet
gcloud compute instances describe "$VM_NAME" --project="$PROJECT_ID" --zone=us-east1-b --format=json > evidence/automation_vm.json
ready=0
for attempt in $(seq 1 36);do
 if gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone=us-east1-b --quiet "${SSH_OPTIONS[@]}" --command=true;then ready=1;break;fi
 sleep 5
done
(( ready )) || { echo 'SSH did not become ready' >&2;exit 1; }
gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone=us-east1-b --quiet "${SSH_OPTIONS[@]}" \
 --command='sudo apt-get update -qq && sudo apt-get install -y python3-venv python3-pip && mkdir -p ~/HW6/evidence'
gcloud compute scp train_models.py db.py schema.sql setup_schema.py requirements.txt startup.sh \
 "$VM_NAME:HW6/" --project="$PROJECT_ID" --zone=us-east1-b --quiet "${SSH_OPTIONS[@]}"
gcloud compute scp evidence/data_manifest.json "$VM_NAME:HW6/evidence/" --project="$PROJECT_ID" --zone=us-east1-b --quiet "${SSH_OPTIONS[@]}"
gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone=us-east1-b --quiet "${SSH_OPTIONS[@]}" \
 --command="cd ~/HW6 && PROJECT_ID='$PROJECT_ID' timeout 1200 bash startup.sh"
if [[ "${HW6_SCREENSHOT_PAUSE:-0}" == 1 ]]; then
 echo "Capture the RUNNING VM in GCP now: $VM_NAME (us-east1-b)."
 read -r -p 'Press Enter to print outputs and clean up: ' _
fi
gcloud compute scp "$VM_NAME:HW6/evidence/schema_verification.json" "$VM_NAME:HW6/evidence/model_results.txt" evidence/ --project="$PROJECT_ID" --zone=us-east1-b --quiet "${SSH_OPTIONS[@]}"
for file in country_predictions.csv income_predictions.csv metrics.json;do
 gcloud storage cat "gs://cs528-hw2-pgeesala/hw6/$file"
done
