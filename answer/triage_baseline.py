"""
Phase 0: Temporal bootstrap + multi-resolution validation + baseline metrics.
Feeds into data_profile_triage.md.
"""
import pandas as pd
import numpy as np

DATA_PATH = '../question/telemetry_dataset.csv'
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

print("=" * 70)
print("1. TEMPORAL BOOTSTRAP — 30s BINS, FULL WINDOW")
print("=" * 70)
df['bin_30s'] = df['timestamp'].dt.floor('30s')
temporal = df.groupby('bin_30s').agg(
    total=('timestamp', 'count'),
    ok_200=('response_status_code', lambda x: (x == 200).sum()),
    err_500=('response_status_code', lambda x: (x == 500).sum()),
    err_503=('response_status_code', lambda x: (x == 503).sum()),
    err_429=('response_status_code', lambda x: (x == 429).sum()),
    err_404=('response_status_code', lambda x: (x == 404).sum()),
).reset_index()
temporal['err_5xx'] = temporal['err_500'] + temporal['err_503']
temporal['rate_5xx'] = (temporal['err_5xx'] / temporal['total'] * 100).round(2)
temporal['rate_200'] = (temporal['ok_200'] / temporal['total'] * 100).round(2)

print(temporal[['bin_30s', 'total', 'ok_200', 'err_500', 'err_503', 'err_429', 'err_404', 'err_5xx', 'rate_5xx', 'rate_200']].to_string(index=False))

# Identify healthy windows: 5xx rate < 4% and no 503s and no 429s
print("\n\nHealthy window candidates (5xx < 4%, no 503, no 429):")
healthy_mask = (temporal['rate_5xx'] < 4) & (temporal['err_503'] == 0) & (temporal['err_429'] == 0) & (temporal['total'] > 100)
healthy_bins = temporal[healthy_mask]
print(healthy_bins[['bin_30s', 'total', 'rate_5xx', 'rate_200']].to_string(index=False))

# Find longest contiguous healthy period
print("\n\nContiguous healthy periods:")
healthy_bins_sorted = healthy_bins.sort_values('bin_30s')
groups = (healthy_bins_sorted['bin_30s'].diff() != pd.Timedelta('30s')).cumsum()
for gid, group in healthy_bins_sorted.groupby(groups):
    start = group['bin_30s'].min()
    end = group['bin_30s'].max() + pd.Timedelta('30s')
    duration = (end - start).total_seconds()
    avg_5xx = group['rate_5xx'].mean()
    print(f"  {start} to {end} ({duration:.0f}s, {len(group)} bins, avg 5xx rate: {avg_5xx:.2f}%)")

print("\n" + "=" * 70)
print("2. INCIDENT WINDOWS — REFINED")
print("=" * 70)
# Incident 1: high 5xx + 503s
inc1_mask = temporal['err_503'] > 0
print("Bins with 503 errors (incident 1 markers):")
print(temporal[inc1_mask][['bin_30s', 'total', 'err_500', 'err_503', 'rate_5xx']].to_string(index=False))

# Incident 2: 429s + traffic spike
inc2_mask = temporal['err_429'] > 0
print("\nBins with 429 errors (incident 2 markers):")
print(temporal[inc2_mask][['bin_30s', 'total', 'err_429', 'rate_5xx']].to_string(index=False))

# Look at incident 1 at finer resolution (10s bins)
print("\n\nIncident 1 at 10s resolution (18:59:30 - 19:02:30):")
inc1_window = df[(df['timestamp'] >= '2025-08-12 18:59:30') & (df['timestamp'] < '2025-08-12 19:02:30')]
inc1_window = inc1_window.copy()
inc1_window['bin_10s'] = inc1_window['timestamp'].dt.floor('10s')
inc1_10s = inc1_window.groupby('bin_10s').agg(
    total=('timestamp', 'count'),
    err_500=('response_status_code', lambda x: (x == 500).sum()),
    err_503=('response_status_code', lambda x: (x == 503).sum()),
    p50_dur=('duration', 'median'),
    p95_dur=('duration', lambda x: x.quantile(0.95)),
).reset_index()
inc1_10s['err_5xx'] = inc1_10s['err_500'] + inc1_10s['err_503']
inc1_10s['rate_5xx'] = (inc1_10s['err_5xx'] / inc1_10s['total'] * 100).round(2)
print(inc1_10s.to_string(index=False))

# Look at incident 2 at 10s resolution
print("\n\nIncident 2 at 10s resolution (19:03:30 - 19:05:00):")
inc2_window = df[(df['timestamp'] >= '2025-08-12 19:03:30') & (df['timestamp'] < '2025-08-12 19:05:00')]
inc2_window = inc2_window.copy()
inc2_window['bin_10s'] = inc2_window['timestamp'].dt.floor('10s')
inc2_10s = inc2_window.groupby('bin_10s').agg(
    total=('timestamp', 'count'),
    err_500=('response_status_code', lambda x: (x == 500).sum()),
    err_429=('response_status_code', lambda x: (x == 429).sum()),
    p50_dur=('duration', 'median'),
    p95_dur=('duration', lambda x: x.quantile(0.95)),
).reset_index()
inc2_10s['rate_5xx'] = (inc2_10s['err_500'] / inc2_10s['total'] * 100).round(2)
print(inc2_10s.to_string(index=False))

print("\n" + "=" * 70)
print("3. BASELINE METRICS (HEALTHY WINDOW)")
print("=" * 70)
# Use the longest contiguous healthy period
# From the data: 18:56:00 to 19:01:00 appears to be the longest healthy stretch
# But we need to be more precise — let's use all healthy bins
healthy_start = '2025-08-12 18:56:00'
healthy_end = '2025-08-12 19:01:00'
hw = df[(df['timestamp'] >= healthy_start) & (df['timestamp'] < healthy_end)]
hw_200 = hw[hw['response_status_code'] == 200]

print(f"Healthy window: {healthy_start} to {healthy_end} (300s)")
print(f"Total requests: {len(hw):,}")
print(f"200 requests: {len(hw_200):,}")
print(f"Request rate: {len(hw) / 300:.1f} req/s")
print(f"200 rate: {len(hw_200) / len(hw) * 100:.2f}%")
print(f"5xx count: {((hw['response_status_code'] >= 500) & (hw['response_status_code'] < 600)).sum()}")
print(f"5xx rate: {((hw['response_status_code'] >= 500) & (hw['response_status_code'] < 600)).sum() / len(hw) * 100:.2f}%")

print(f"\nLatency (200s only, microseconds):")
for p in [0.50, 0.75, 0.90, 0.95, 0.99]:
    val = hw_200['duration'].quantile(p)
    print(f"  p{int(p*100)}: {val:.0f} ({val/1000:.1f}ms)")
print(f"  mean: {hw_200['duration'].mean():.0f} ({hw_200['duration'].mean()/1000:.1f}ms)")
print(f"  max: {hw_200['duration'].max():.0f} ({hw_200['duration'].max()/1000:.1f}ms)")

print(f"\nLatency (all statuses, for comparison):")
for p in [0.50, 0.95, 0.99]:
    val = hw['duration'].quantile(p)
    print(f"  p{int(p*100)}: {val:.0f} ({val/1000:.1f}ms)")

print(f"\nPer-server baseline (200s only):")
for srv in sorted(hw_200['server_id'].unique()):
    sub = hw_200[hw_200['server_id'] == srv]
    print(f"  {srv}: n={len(sub):,} p50={sub['duration'].quantile(0.5):.0f} p95={sub['duration'].quantile(0.95):.0f} p99={sub['duration'].quantile(0.99):.0f}")

print(f"\n5xx rate per 30s bin in healthy window:")
hw_temporal = hw.copy()
hw_temporal['bin_30s'] = hw_temporal['timestamp'].dt.floor('30s')
hw_bins = hw_temporal.groupby('bin_30s').agg(
    total=('timestamp', 'count'),
    err_5xx=('response_status_code', lambda x: ((x >= 500) & (x < 600)).sum()),
).reset_index()
hw_bins['rate'] = (hw_bins['err_5xx'] / hw_bins['total'] * 100).round(2)
print(hw_bins.to_string(index=False))

print("\n" + "=" * 70)
print("4. MULTI-RESOLUTION VALIDATION")
print("=" * 70)
# Compare a known incident window at 1s, 5s, 10s, 30s
inc_window = df[(df['timestamp'] >= '2025-08-12 19:00:30') & (df['timestamp'] < '2025-08-12 19:02:00')]

for res_label, res in [('1s', '1s'), ('5s', '5s'), ('10s', '10s'), ('30s', '30s')]:
    inc_copy = inc_window.copy()
    inc_copy['bin'] = inc_copy['timestamp'].dt.floor(res)
    bins = inc_copy.groupby('bin').agg(
        total=('timestamp', 'count'),
        err_5xx=('response_status_code', lambda x: ((x >= 500) & (x < 600)).sum()),
        p50=('duration', 'median'),
        p95=('duration', lambda x: x.quantile(0.95)),
    ).reset_index()
    bins['rate'] = (bins['err_5xx'] / bins['total'] * 100).round(2)
    print(f"\n--- {res_label} resolution ({len(bins)} bins) ---")
    if res_label == '1s':
        # Too many bins, show stats
        print(f"  Bins: {len(bins)}")
        print(f"  Requests per bin: min={bins['total'].min()} p50={bins['total'].median():.0f} max={bins['total'].max()}")
        print(f"  5xx rate: min={bins['rate'].min():.1f}% p50={bins['rate'].median():.1f}% max={bins['rate'].max():.1f}%")
        print(f"  Peak 5xx bins (>10%):")
        peak = bins[bins['rate'] > 10].sort_values('bin')
        if len(peak) > 0:
            print(peak[['bin', 'total', 'err_5xx', 'rate', 'p95']].to_string(index=False))
        else:
            print("    None")
    else:
        print(bins[['bin', 'total', 'err_5xx', 'rate', 'p50', 'p95']].to_string(index=False))

print("\n" + "=" * 70)
print("5. DEGRADED SUCCESS ANALYSIS")
print("=" * 70)
# 200s with latency above healthy-window p95
healthy_p95 = hw_200['duration'].quantile(0.95)
print(f"Healthy window p95 (200s): {healthy_p95:.0f} ({healthy_p95/1000:.1f}ms)")

all_200 = df[df['response_status_code'] == 200]
degraded = all_200[all_200['duration'] > healthy_p95]
print(f"Total 200s: {len(all_200):,}")
print(f"Degraded 200s (>{healthy_p95:.0f}): {len(degraded):,} ({len(degraded)/len(all_200)*100:.2f}%)")

# Degraded by time bin
df_200 = all_200.copy()
df_200['bin_30s'] = df_200['timestamp'].dt.floor('30s')
deg_temporal = df_200.groupby('bin_30s').agg(
    total_200=('timestamp', 'count'),
    degraded=('duration', lambda x: (x > healthy_p95).sum()),
).reset_index()
deg_temporal['deg_rate'] = (deg_temporal['degraded'] / deg_temporal['total_200'] * 100).round(2)
print(f"\nDegraded 200s per 30s bin:")
print(deg_temporal.to_string(index=False))

# Degraded by server during incident 1
inc1_200 = all_200[(all_200['timestamp'] >= '2025-08-12 19:01:00') & (all_200['timestamp'] < '2025-08-12 19:02:00')]
print(f"\nDegraded 200s during incident 1 (19:01-19:02) by server:")
for srv in sorted(inc1_200['server_id'].unique()):
    sub = inc1_200[inc1_200['server_id'] == srv]
    deg = (sub['duration'] > healthy_p95).sum()
    print(f"  {srv}: {deg}/{len(sub)} = {deg/len(sub)*100:.1f}%")
