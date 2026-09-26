## Overview

This project generates 12,000 HTML files, stores them in Google Cloud Storage, and analyzes the graph using Python.

The program:
- calculates incoming and outgoing link statistics
- computes PageRank and prints the top 5 pages
- computes closeness centrality
- runs independent tests
- prints total runtime

No graph libraries are used.

## Files

- `generate-content.py` - provided file generator
- `graph_analysis.py` - main analysis code
- `requirements.txt` - required Python package

## Google Cloud Storage

Bucket:

```text
gs://cs528-hw2-pgeesala
```

## Generate the Dataset

```bash
mkdir pages
cd pages
python3 ../generate-content.py -n 12000 -m 327
ls | wc -l
cd ..
```

## Make the Bucket Public

```bash
gcloud storage buckets add-iam-policy-binding gs://cs528-hw2-pgeesala \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

## Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

```bash
python graph_analysis.py
```

## Run in Cloud Shell

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install google-cloud-storage
python graph_analysis.py
```

## Run on e2-medium VM

Create the VM:

```bash
gcloud compute instances create cs528-hw2-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium
```

Connect:

```bash
gcloud compute ssh cs528-hw2-vm --zone=us-central1-a
```

Install dependencies:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv

python3 -m venv .venv
source .venv/bin/activate
pip install google-cloud-storage
```

Run:
```bash
python graph_analysis.py
```

Delete the VM after collecting the results:
```bash
gcloud compute instances delete cs528-hw2-vm \
  --zone=us-central1-a
```