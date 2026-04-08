from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
TRAINING_ROOT = DATA_ROOT / "TrainingData"
MERGED_ROOT = DATA_ROOT / "CIC_IOT_Dataset_2023"


def find_first_csv(folder: Path) -> Path:
    csv_files = sorted(
        path for path in folder.rglob("*.csv") if ":Zone.Identifier" not in path.name
    )
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found under {folder}")
    return csv_files[0]


def describe_csv(csv_path: Path, label: str) -> None:
    df = pd.read_csv(csv_path)

    print(f"\n=== {label} ===")
    print(f"File: {csv_path}")
    print("df.columns.tolist() =")
    print(df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df.head(5).to_string(index=False))


def main() -> None:
    training_csv = find_first_csv(TRAINING_ROOT)
    merged_csv = find_first_csv(MERGED_ROOT)

    describe_csv(training_csv, "Training CSV")
    describe_csv(merged_csv, "Merged Test CSV")


if __name__ == "__main__":
    main()
