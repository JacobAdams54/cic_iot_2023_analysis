# CICIoT2023 Paper Benchmark Reimplementation

This repository now includes a demo-safe implementation path for the paper's ML benchmarking stage using the provided CSV features.

Scope for this phase:
- Included: ML benchmarking on provided CSV features.
- Not included: pcap to feature extraction.
- Evaluation order: binary, then grouped 8-class, then fine-grained multi-class.

## 1. Local Safety Rules

The local workflow is intentionally capped to avoid crashes:
- Limit number of files per run.
- Limit rows per file.
- Save artifacts after each run.
- Increase scale in one axis at a time.

Docker limits are configured in docker-compose.

## 2. Start Notebook Environment

```bash
docker compose up --build
```

Open JupyterLab at `http://localhost:8888`.

## 3. Run Notebooks in Order

1. `notebooks/00_discovery.ipynb`
2. `notebooks/01_benchmark_baseline.ipynb`

`01_benchmark_baseline.ipynb` executes the paper model set:
- Logistic Regression
- Perceptron
- AdaBoost
- Random Forest
- DNN proxy using scikit-learn MLP

## 4. Where Results Are Saved

All run outputs are written under `outputs/runs/<task>_<timestamp>/`:
- `metrics.csv`
- `classification_reports.json`
- `run_summary.json`
- `best_model.joblib`

## 5. Suggested Local to HPC Progression

1. Validate all three tasks on tiny demo caps.
2. Increase rows per file and record runtime/memory.
3. Increase file count and record runtime/memory.
4. Move full-data runs to HPC only.

## 6. Implementation Code

Reusable benchmark functions are in:
- `src/cic_iot_benchmark.py`

This module handles:
- merged-file discovery
- capped loading
- label mapping for three tasks
- feature preparation
- training/evaluation of the five benchmark models
- artifact persistence
