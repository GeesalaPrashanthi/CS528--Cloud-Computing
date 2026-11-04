#!/usr/bin/env bash
# Remote worker; invoked by setup.sh on the temporary GCP VM.
set -euo pipefail
cd "$(dirname "$0")"
export PROJECT_ID="${PROJECT_ID:-enduring-trees-508117-p7}"
export DB_NAME=cs528_hw6
export INSTANCE_CONNECTION_NAME="$PROJECT_ID:us-east1:cs528-hw5-mysql"
export DB_PASSWORD
DB_PASSWORD="$(gcloud secrets versions access latest --secret=hw5-db-password --project="$PROJECT_ID")"
trap 'unset DB_PASSWORD' EXIT
VENV="${VENV_DIR:-.venv}"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -r requirements.txt
mkdir -p data evidence
if [[ ! -f data/requests.csv ]]; then
 gcloud storage cp gs://cs528-hw2-pgeesala/hw6/data/requests.csv data/requests.csv
fi
"$VENV/bin/python" -c 'import hashlib,json; from pathlib import Path; m=json.loads(Path("evidence/data_manifest.json").read_text()); assert hashlib.sha256(Path("data/requests.csv").read_bytes()).hexdigest()==m["sha256"], "Dataset checksum mismatch"'
"$VENV/bin/python" setup_schema.py --apply --input-csv data/requests.csv
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 "$VENV/bin/python" train_models.py --upload --prefix hw6 | tee evidence/model_results.txt
