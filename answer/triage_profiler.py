"""
Triage script: extract key profiler findings for signal vs noise evaluation.
Outputs structured summary to stdout for manual triage.
"""
import pandas as pd
import numpy as np

DATA_PATH = '../question/telemetry_dataset.csv'
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

print("=" * 70)
print("SECTION 1: DATASET OVERVIEW")
print("=" * 70)
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds():.1f} seconds")
print(f"\nMissing values per column:")
print(df.isnull().sum().to_string())
print(f"\nDuplicate rows: {df.duplicated().sum()}")

print("\n" + "=" * 70)
print("SECTION 2: CATEGORICAL VARIABLE SUMMARIES")
print("=" * 70)

for col in ['server_id', 'request_type', 'response_status_code', 'agent_name',
            'client_device_type', 'geographic_region', 'request_url']:
    print(f"\n--- {col} ---")
    vc = df[col].value_counts()
    print(vc.to_string())
    print(f"  Unique: {df[col].nunique()}")

print("\n" + "=" * 70)
print("SECTION 3: NUMERIC VARIABLE SUMMARIES")
print("=" * 70)

for col in ['duration', 'response_size', 'request_size']:
    print(f"\n--- {col} ---")
    desc = df[col].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.90, 0.95, 0.99])
    print(desc.to_string())
    print(f"  Zeros: {(df[col] == 0).sum()}")
    print(f"  Negatives: {(df[col] < 0).sum()}")

print("\n" + "=" * 70)
print("SECTION 4: UNIQUE ID ANALYSIS")
print("=" * 70)
print(f"Unique client_ids: {df['client_id'].nunique():,}")
print(f"Unique request_ids: {df['request_id'].nunique():,}")
print(f"Unique response_ids: {df['response_id'].nunique():,}")
print(f"request_id duplicates: {df['request_id'].duplicated().sum()}")
print(f"response_id duplicates: {df['response_id'].duplicated().sum()}")

print("\n" + "=" * 70)
print("SECTION 5: STATUS CODE BY SERVER")
print("=" * 70)
ct = pd.crosstab(df['server_id'], df['response_status_code'])
print(ct.to_string())
print("\nRow percentages:")
print(ct.div(ct.sum(axis=1), axis=0).round(4).to_string())

print("\n" + "=" * 70)
print("SECTION 6: STATUS CODE BY ENDPOINT")
print("=" * 70)
# Group parameterized endpoints
df['endpoint_group'] = df['request_url'].apply(
    lambda x: '/'.join(x.split('/')[:2]) + '/{id}' if len(x.split('/')) > 2 else x
)
ct2 = pd.crosstab(df['endpoint_group'], df['response_status_code'])
print(ct2.to_string())

print("\n" + "=" * 70)
print("SECTION 7: DURATION BY STATUS CODE")
print("=" * 70)
for status in sorted(df['response_status_code'].unique()):
    subset = df[df['response_status_code'] == status]['duration']
    print(f"\n--- Status {status} (n={len(subset):,}) ---")
    print(f"  p50={subset.quantile(0.5):.0f}  p95={subset.quantile(0.95):.0f}  p99={subset.quantile(0.99):.0f}  max={subset.max():.0f}")

print("\n" + "=" * 70)
print("SECTION 8: TEMPORAL PATTERNS — 30s BINS")
print("=" * 70)
df['bin_30s'] = df['timestamp'].dt.floor('30s')
temporal = df.groupby('bin_30s').agg(
    total=('timestamp', 'count'),
    error_5xx=('response_status_code', lambda x: (x >= 500).sum()),
    error_429=('response_status_code', lambda x: (x == 429).sum()),
    error_404=('response_status_code', lambda x: (x == 404).sum()),
    p50_duration=('duration', 'median'),
    p95_duration=('duration', lambda x: x.quantile(0.95)),
    p99_duration=('duration', lambda x: x.quantile(0.99)),
).reset_index()
temporal['error_rate_5xx'] = (temporal['error_5xx'] / temporal['total'] * 100).round(2)
temporal['error_rate_429'] = (temporal['error_429'] / temporal['total'] * 100).round(2)
print(temporal.to_string(index=False))

print("\n" + "=" * 70)
print("SECTION 9: DURATION BY SERVER AND STATUS 200")
print("=" * 70)
ok = df[df['response_status_code'] == 200]
for srv in sorted(ok['server_id'].unique()):
    subset = ok[ok['server_id'] == srv]['duration']
    print(f"  {srv}: p50={subset.quantile(0.5):.0f}  p95={subset.quantile(0.95):.0f}  p99={subset.quantile(0.99):.0f}  n={len(subset):,}")

print("\n" + "=" * 70)
print("SECTION 10: CLIENT CONCENTRATION")
print("=" * 70)
client_counts = df['client_id'].value_counts()
print(f"Total unique clients: {len(client_counts):,}")
print(f"Top 10 clients account for: {client_counts.head(10).sum():,} requests ({client_counts.head(10).sum()/len(df)*100:.1f}%)")
print(f"Top 100 clients account for: {client_counts.head(100).sum():,} requests ({client_counts.head(100).sum()/len(df)*100:.1f}%)")
print(f"\nRequests per client distribution:")
print(client_counts.describe().to_string())
print(f"\nTop 20 clients:")
print(client_counts.head(20).to_string())

print("\n" + "=" * 70)
print("SECTION 11: REQUEST TYPE BY TIME AND SERVER")
print("=" * 70)
rt = pd.crosstab(df['server_id'], df['request_type'])
print(rt.to_string())
print("\nGET ratio per server:")
print((rt['GET'] / rt.sum(axis=1) * 100).round(2).to_string())

# GET ratio over time
get_temporal = df.groupby('bin_30s').apply(
    lambda x: (x['request_type'] == 'GET').sum() / len(x) * 100
).reset_index(name='get_pct')
print("\nGET % per 30s bin:")
print(get_temporal.to_string(index=False))

print("\n" + "=" * 70)
print("SECTION 12: GEOGRAPHIC PATTERNS")
print("=" * 70)
geo = pd.crosstab(df['geographic_region'], df['server_id'])
print("Requests by region x server:")
print(geo.to_string())
print("\nRegion x server (row %):")
print(geo.div(geo.sum(axis=1), axis=0).round(4).to_string())

# Latency by region (200s only)
print("\nLatency by region (200s only):")
for region in sorted(ok['geographic_region'].unique()):
    subset = ok[ok['geographic_region'] == region]['duration']
    print(f"  {region}: p50={subset.quantile(0.5):.0f}  p95={subset.quantile(0.95):.0f}  n={len(subset):,}")

print("\n" + "=" * 70)
print("SECTION 13: AGENT TYPE BEHAVIOR")
print("=" * 70)
agent_status = pd.crosstab(df['agent_name'], df['response_status_code'])
print(agent_status.to_string())
print("\n5xx rate per agent:")
for agent in agent_status.index:
    total = agent_status.loc[agent].sum()
    err5xx = agent_status.loc[agent][[c for c in agent_status.columns if c >= 500]].sum()
    print(f"  {agent}: {err5xx/total*100:.2f}% ({err5xx:.0f}/{total})")
