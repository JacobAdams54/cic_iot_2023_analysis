from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Perceptron
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


RANDOM_STATE = 42
BENIGN_MARKERS = {"benign", "normal"}


@dataclass(frozen=True)
class DemoConfig:
    data_dir: Path
    max_files: int = 2
    rows_per_file: int = 25_000
    test_size: float = 0.2
    random_state: int = RANDOM_STATE


GROUP_8_PATTERNS = {
    "DDoS": [r"\bddos\b"],
    "DoS": [r"\bdos\b"],
    "Recon": [r"recon", r"scan"],
    "Web-Based": [r"http", r"xss", r"sql", r"browser", r"uploading", r"backdoor"],
    "Brute Force": [r"brute", r"dictionary"],
    "Spoofing": [r"spoof", r"arp", r"dns"],
    "Mirai": [r"mirai", r"greip", r"greeth", r"udpplain"],
}


def set_global_seed(seed: int = RANDOM_STATE) -> None:
    np.random.seed(seed)


def ensure_output_dirs(base_dir: Path = Path("outputs")) -> Dict[str, Path]:
    paths = {
        "base": base_dir,
        "runs": base_dir / "runs",
        "schemas": base_dir / "schemas",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def discover_merged_files(data_dir: Path) -> List[Path]:
    return sorted(data_dir.glob("Merged*.csv"))


def load_capped_data(
    file_paths: List[Path], max_files: int, rows_per_file: int
) -> Tuple[pd.DataFrame, List[Path]]:
    selected = file_paths[:max_files]
    if not selected:
        raise ValueError("No merged CSV files found. Check your data path.")

    frames: List[pd.DataFrame] = []
    for path in selected:
        frame = pd.read_csv(path, nrows=rows_per_file, low_memory=False)
        frame["__source_file"] = path.name
        frames.append(frame)

    return pd.concat(frames, ignore_index=True), selected


def infer_label_column(df: pd.DataFrame) -> str:
    candidates = ["label", "attack", "attack_type", "category", "class", "target"]
    lower_to_real = {c.lower(): c for c in df.columns}

    for candidate in candidates:
        if candidate in lower_to_real:
            return lower_to_real[candidate]

    for col in df.columns:
        lowered = col.lower()
        if "label" in lowered or "attack" in lowered or "class" in lowered:
            return col

    raise ValueError(
        "Unable to infer label column. Please set label column manually in the notebook."
    )


def map_binary_labels(raw_labels: pd.Series) -> pd.Series:
    normalized = raw_labels.astype(str).str.strip().str.lower()
    return np.where(normalized.isin(BENIGN_MARKERS), "Benign", "Attack")


def map_grouped_8_labels(raw_labels: pd.Series) -> pd.Series:
    normalized = raw_labels.astype(str).str.strip().str.lower()

    grouped = []
    for value in normalized:
        if value in BENIGN_MARKERS:
            grouped.append("Benign")
            continue

        assigned = None
        for group_name, patterns in GROUP_8_PATTERNS.items():
            if any(re.search(pattern, value) for pattern in patterns):
                assigned = group_name
                break

        grouped.append(assigned if assigned else "OtherAttack")

    return pd.Series(grouped, index=raw_labels.index)


def map_fine_grained_labels(raw_labels: pd.Series) -> pd.Series:
    return raw_labels.astype(str).str.strip()


def prepare_feature_frame(
    df: pd.DataFrame, label_col: str
) -> Tuple[pd.DataFrame, List[str]]:
    excluded_exact = {
        label_col,
        "__source_file",
        "Timestamp",
        "timestamp",
        "ts",
        "flow_id",
        "Flow_ID",
    }

    excluded = [col for col in df.columns if col in excluded_exact]
    features = df.drop(columns=excluded, errors="ignore").copy()

    drop_high_cardinality = []
    for col in features.columns:
        if features[col].dtype == "object":
            unique_count = features[col].nunique(dropna=True)
            if unique_count > 64:
                drop_high_cardinality.append(col)

    if drop_high_cardinality:
        features = features.drop(columns=drop_high_cardinality)

    features = pd.get_dummies(features, dummy_na=True)
    features = features.replace([np.inf, -np.inf], np.nan).fillna(0)

    return features, drop_high_cardinality


def train_and_evaluate_models(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float,
    random_state: int,
) -> Tuple[pd.DataFrame, Dict[str, Pipeline], Dict[str, dict]]:
    stratify_y = y if y.nunique() > 1 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_y,
    )

    models: Dict[str, Pipeline] = {
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=500, random_state=random_state, n_jobs=-1
                    ),
                ),
            ]
        ),
        "Perceptron": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", Perceptron(max_iter=1000, random_state=random_state)),
            ]
        ),
        "AdaBoost": Pipeline(
            [
                (
                    "model",
                    AdaBoostClassifier(n_estimators=80, random_state=random_state),
                ),
            ]
        ),
        "RandomForest": Pipeline(
            [
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=200,
                        max_depth=20,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "DNN(MLP)": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=(128, 64),
                        max_iter=40,
                        random_state=random_state,
                        early_stopping=True,
                    ),
                ),
            ]
        ),
    }

    rows = []
    reports: Dict[str, dict] = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        rows.append(
            {
                "model": name,
                "accuracy": accuracy_score(y_test, predictions),
                "precision_macro": precision_score(
                    y_test, predictions, average="macro", zero_division=0
                ),
                "recall_macro": recall_score(
                    y_test, predictions, average="macro", zero_division=0
                ),
                "f1_macro": f1_score(
                    y_test, predictions, average="macro", zero_division=0
                ),
                "f1_weighted": f1_score(
                    y_test, predictions, average="weighted", zero_division=0
                ),
            }
        )

        reports[name] = classification_report(
            y_test, predictions, output_dict=True, zero_division=0
        )

    result_df = (
        pd.DataFrame(rows)
        .sort_values(by="f1_macro", ascending=False)
        .reset_index(drop=True)
    )
    return result_df, models, reports


def run_benchmark_task(
    df: pd.DataFrame,
    label_col: str,
    task: str,
    test_size: float,
    random_state: int,
) -> Tuple[pd.DataFrame, Dict[str, Pipeline], Dict[str, dict], pd.Series, List[str]]:
    if task == "binary":
        y = pd.Series(map_binary_labels(df[label_col]), index=df.index)
    elif task == "grouped_8":
        y = map_grouped_8_labels(df[label_col])
    elif task == "fine_34":
        y = map_fine_grained_labels(df[label_col])
    else:
        raise ValueError("task must be one of: binary, grouped_8, fine_34")

    X, dropped_cols = prepare_feature_frame(df, label_col)
    result_df, models, reports = train_and_evaluate_models(
        X, y, test_size=test_size, random_state=random_state
    )
    return result_df, models, reports, y, dropped_cols


def save_run_artifacts(
    output_root: Path,
    task: str,
    result_df: pd.DataFrame,
    reports: Dict[str, dict],
    models: Dict[str, Pipeline],
    selected_files: List[Path],
    label_distribution: pd.Series,
    dropped_columns: List[str],
    feature_columns: List[str],
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / "runs" / f"{task}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    result_df.to_csv(run_dir / "metrics.csv", index=False)

    summary = {
        "task": task,
        "selected_files": [path.name for path in selected_files],
        "label_distribution": label_distribution.to_dict(),
        "dropped_high_cardinality_columns": dropped_columns,
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (run_dir / "classification_reports.json").write_text(
        json.dumps(reports, indent=2), encoding="utf-8"
    )

    best_model_name = result_df.iloc[0]["model"]
    joblib.dump(models[best_model_name], run_dir / "best_model.joblib")

    return run_dir
