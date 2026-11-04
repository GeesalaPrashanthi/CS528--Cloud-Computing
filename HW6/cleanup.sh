#!/usr/bin/env bash
# Deletes only a VM labeled as owned by HW6 setup. Preserves database contents.
set -u
PROJECT="${PROJECT_ID:-enduring-trees-508117-p7}"
VM="${VM_NAME:-}"
rc=0
if [[ -n "$VM" ]]; then
 if instance="$(gcloud compute instances list --project="$PROJECT" --filter="name=$VM" --format=json)"; then
  label="$(printf '%s' "$instance" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print("missing" if not rows else rows[0].get("labels",{}).get("managed-by","unowned"))')"
  if [[ "$label" == hw6-setup ]]; then
   gcloud compute instances delete "$VM" --zone=us-east1-b --project="$PROJECT" --quiet || rc=1
  elif [[ "$label" != missing ]]; then
   echo 'Refusing to delete a VM not owned by HW6 setup' >&2;rc=1
  fi
 else
  echo 'Could not verify VM ownership; cleanup requires attention' >&2;rc=1
 fi
fi
gcloud sql instances patch cs528-hw5-mysql --activation-policy=NEVER --project="$PROJECT" --quiet || rc=1
if [[ "${RESUME_SCHEDULER:-1}" == 1 ]]; then
 gcloud scheduler jobs resume hw5-hourly-sql-stop --location=us-east1 --project="$PROJECT" || rc=1
fi
exit "$rc"
