# CS528 Homework 2

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

Expected file count:

```text
12000
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

## Results

### Link Statistics

Outgoing links:

```text
Average: 161.7323
Median: 163.0
Maximum: 325
Minimum: 0
Quintiles: [63, 130, 195, 259]
```

Incoming links:

```text
Average: 161.7323
Median: 162.0
Maximum: 233
Minimum: 115
Quintiles: [151, 159, 165, 172]
```

### Top 5 Pages by PageRank

```text
9970  0.0001963367
4807  0.0001843420
369   0.0001783498
4724  0.0001675921
1000  0.0001619014
```

### Closeness Centrality

```text
Page with best closeness centrality: 7263
Closeness centrality score: 0.504795961295751
```

### Tests

```text
PageRank test passed
Closeness centrality test passed
```

### Runtime Comparison

| Environment | Runtime |
|---|---:|
| Local machine | 2871.66 seconds |
| Google Cloud Shell | 2361.81 seconds |
| e2-medium VM | 5042.66 seconds |

The Cloud Shell run used files copied to local Cloud Shell storage because direct object-by-object reads from Google Cloud Storage were significantly slower and produced occasional timeout errors.