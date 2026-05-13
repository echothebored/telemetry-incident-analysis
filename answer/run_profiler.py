"""
One-shot script: generate ydata-profiling HTML report for telemetry dataset.
Not part of the reproducible notebook — this is exploratory tooling.
Output: supporting/data_profile_report.html
"""
import pandas as pd
from ydata_profiling import ProfileReport
from pathlib import Path

DATA_PATH = Path('../question/telemetry_dataset.csv')
OUTPUT_PATH = Path('supporting/data_profile_report.html')

# Load data
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

print(f"Loaded {len(df):,} rows, {len(df.columns)} columns")
print(f"Columns: {list(df.columns)}")
print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Run profiler — full mode, time-series aware
profile = ProfileReport(
    df,
    title="Telemetry Dataset Profile",
    tsmode=True,
    sortby="timestamp",
    explorative=True,
    missing_diagrams={"bar": True, "matrix": True, "heatmap": True},
    correlations={
        "auto": {"calculate": True},
        "pearson": {"calculate": True},
        "spearman": {"calculate": True},
        "phi_k": {"calculate": True},
    },
)

profile.to_file(OUTPUT_PATH)
print(f"\nProfile report saved to {OUTPUT_PATH}")
