"""CLI script to generate default synthetic dataset for CloudLog Analytics."""

import os
from cloudlog.generator import save_synthetic_dataset_to_file

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "sample_logs.csv")
    save_synthetic_dataset_to_file(out_file, row_count=5000, seed=42)
    print(f"Generated default dataset with 5,000 rows at: {os.path.abspath(out_file)}")
