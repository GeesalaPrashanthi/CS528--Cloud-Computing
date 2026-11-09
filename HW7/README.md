# CS528 Cloud Computing – Homework 7

## Apache Beam and Google Cloud Dataflow

### Overview

This homework extends Homework 2 by processing the previously generated 12,000 HTML files using Apache Beam and Google Cloud Dataflow.

The pipeline performs three tasks:

1. Identifies the top 5 HTML files with the most incoming links.
2. Identifies the top 5 HTML files with the most outgoing links.
3. Identifies the top 5 most frequent word trigrams (consecutive three-word sequences).

The same pipeline is executed locally using Apache Beam DirectRunner and on Google Cloud Dataflow to compare execution runtimes.

## Dataset

The dataset consists of 12,000 synthetic HTML pages generated during Homework 2.

The files are stored in Google Cloud Storage:

`gs://cs528-hw2-pgeesala/pages/`

The dataset is also available locally in the `pages/` directory from Homework 2.

## Technologies Used

- Python 3.11
- Apache Beam 2.77.0
- Google Cloud Dataflow
- Google Cloud Storage
- Google Cloud CLI

## Project Structure

```text
HW7/
├── hw7_beam.py
├── requirements.txt
├── README.md
└── .gitignore
```

The virtual environment and generated results are excluded from Git.

## Environment Setup

Navigate to the HW7 directory:

```bash
cd HW7
```

Create and activate a Python virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Authenticate with Google Cloud:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project enduring-trees-508117-p7
```

## Local Execution

Run the pipeline using Apache Beam DirectRunner with the existing local HTML files:

```bash
time python hw7_beam.py \
  --runner DirectRunner \
  --direct_running_mode=in_memory \
  --input "../pages/*.html" \
  --output "./results/local"
```

The pipeline processes the HTML files and generates results for incoming links, outgoing links, and trigrams.

The local results are written to the `results/local/` directory.

## Google Cloud Dataflow Execution

The same pipeline is executed on Google Cloud Dataflow.

GCP Project: `enduring-trees-508117-p7`

Region: `us-central1`

Input bucket: `gs://cs528-hw2-pgeesala/pages/`

Execute:

```bash
time python hw7_beam.py \
  --runner DataflowRunner \
  --project enduring-trees-508117-p7 \
  --region us-central1 \
  --temp_location gs://cs528-hw2-pgeesala/hw7/temp \
  --staging_location gs://cs528-hw2-pgeesala/hw7/staging \
  --input "gs://cs528-hw2-pgeesala/pages/*.html" \
  --output "gs://cs528-hw2-pgeesala/hw7/results" \
  --save_main_session
```

The outputs are stored in:

`gs://cs528-hw2-pgeesala/hw7/results/`

The Dataflow job completed successfully.

## Results

The pipeline generated the top 5 results for each required analysis.

| Analysis | Observed result |
|---|---|
| Maximum incoming links | 5984.html – 233 links |
| Maximum outgoing links | 9794.html – 325 links |
| Top trigram frequencies | 1,940,788 occurrences each for the five returned trigrams |

The local and cloud executions produced matching results. The full top-5 output files are available in their respective results directories.

## Runtime Comparison

| Environment | Runtime |
|---|---|
| Local Apache Beam DirectRunner | Approximately 2 min 23 sec |
| Google Cloud Dataflow | 45 min 56 sec |

The local run was faster for this dataset.

The Dataflow execution included cloud worker initialization, distributed processing, and Google Cloud Storage operations. These overheads contributed to its longer runtime.

For this workload, the additional overhead of distributed execution outweighed its performance benefits.

## Output Verification

Local results:

```bash
cat results/local/top_incoming
cat results/local/top_outgoing
cat results/local/top_trigrams
```

Download cloud results:

```bash
mkdir -p results/cloud

gcloud storage cp \
  "gs://cs528-hw2-pgeesala/hw7/results/*" \
  results/cloud/
```

View cloud results:

```bash
cat results/cloud/top_incoming
cat results/cloud/top_outgoing
cat results/cloud/top_trigrams
```

The top-5 results from the two execution environments were compared and found to match.

## Conclusion

Homework 7 demonstrates the use of Apache Beam for analyzing HTML documents and running the same data-processing pipeline using local and cloud execution engines.

Both environments successfully produced matching link-analysis and trigram outputs. The runtime comparison illustrates the overhead associated with using a managed distributed-processing service for a relatively small dataset.
