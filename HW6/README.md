# CS528 Homework 6

Final results: **100% country accuracy** and **33.82% income accuracy**, each evaluated on 20,000 held-out requests. `HW6_Report.docx` contains the configuration, migration SQL, model explanation, screenshots and verified automation outcome. Export the reviewed Word report to PDF for submission.

## Required files

- `train_models.py` — both models and prediction uploads.
- `db.py` — database connection helper.
- `schema.sql` and `setup_schema.py` — 3NF schema, migration and verification.
- `setup.sh`, `startup.sh`, `cleanup.sh` — complete VM lifecycle.
- `requirements.txt` — runtime dependencies.
- `evidence/data_manifest.json` — dataset checksum required by the automation.

Local datasets, predictions, virtual environments, separate screenshot images, experimental scripts and report-generation files are intentionally omitted. All five screenshots remain embedded in the Word report.

## Automated execution

Authenticate `gcloud` with access to project `enduring-trees-508117-p7`, then run from this folder:

```bash
bash setup.sh
```

This starts SQL, creates a temporary e2-medium VM, installs dependencies, downloads/checksums the source dataset, verifies the schema, runs both models, uploads and prints the complete GCS outputs, deletes its temporary VM and stops SQL. It resumes the hourly SQL shutdown scheduler. The full workflow was verified with exit code 0.

This command creates billable resources. The caller needs VM/SQL management permissions and permission to use the VM service account and scheduler. The VM identity needs Cloud SQL connectivity, access to Secret Manager secret `hw5-db-password` and read/write access to the homework bucket. No credentials are stored in source files. `SSH_KEY_FILE` can override the default Google Compute Engine SSH key path.

## Optional local execution

From this folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p data
gcloud storage cp gs://cs528-hw2-pgeesala/hw6/data/requests.csv data/requests.csv
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python train_models.py \
  --input-csv data/requests.csv --output-dir outputs
```

CSV mode requires no database connection and does not upload without `--upload`. These commands recreate the local data and environment only if needed.

## Configuration and stored outputs

Cloud SQL instance: `cs528-hw5-mysql`; database: `cs528_hw6`; region: `us-east1`; VM zone: `us-east1-b`.

The source table is `requests_source`. The normalized tables are `countries`, `clients` and `requests`; models read the `request_details` JOIN view. Live checks found 100,000 requests, 197 countries, 77,629 clients and zero reconstruction differences.

Canonical GCS objects:

```text
gs://cs528-hw2-pgeesala/hw6/data/requests.csv
gs://cs528-hw2-pgeesala/hw6/country_predictions.csv
gs://cs528-hw2-pgeesala/hw6/income_predictions.csv
gs://cs528-hw2-pgeesala/hw6/metrics.json
```

Evidence records the completed run rather than live resource state. The report explains why the client's random income assignment yields approximately one-third expected accuracy, with development-only Random Forest/XGBoost comparisons kept separate from final testing.

GitHub submission path: https://github.com/GeesalaPrashanthi/CS528--Cloud-Computing/tree/main/HW6

Push only after approval. Keep generated data, outputs, environments and credentials out of Git.
