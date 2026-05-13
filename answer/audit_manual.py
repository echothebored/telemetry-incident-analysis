"""
Manual data audit — 5 open investigation items from triage self-challenge.
Each section answers a specific question with evidence.
"""
import pandas as pd
import numpy as np
from scipy import stats

DATA_PATH = '../question/telemetry_dataset.csv'
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
df['bin_30s'] = df['timestamp'].dt.floor('30s')
df['bin_10s'] = df['timestamp'].dt.floor('10s')

# Healthy window definition from triage
HEALTHY_START = '2025-08-12 18:56:00'
HEALTHY_END = '2025-08-12 19:01:00'
hw = df[(df['timestamp'] >= HEALTHY_START) & (df['timestamp'] < HEALTHY_END)]
hw_200 = hw[hw['response_status_code'] == 200]
HEALTHY_P95 = hw_200['duration'].quantile(0.95)

print("=" * 70)
print("AUDIT 1: PRE- vs POST-INCIDENT BASELINE COMPARISON")
print("=" * 70)
print("Question: Does the baseline differ materially between pre- and post-incident?")
print("If yes, our baseline choice matters. If no, it's robust.\n")

# Pre-incident: 18:56:00 - 19:01:00 (300s)
pre = df[(df['timestamp'] >= '2025-08-12 18:56:00') & (df['timestamp'] < '2025-08-12 19:01:00')]
pre_200 = pre[pre['response_status_code'] == 200]

# Post-incident 1: 19:02:00 - 19:04:00 (120s)
post1 = df[(df['timestamp'] >= '2025-08-12 19:02:00') & (df['timestamp'] < '2025-08-12 19:04:00')]
post1_200 = post1[post1['response_status_code'] == 200]

# Post-incident 2: 19:04:30 - 19:05:59 (90s)
post2 = df[(df['timestamp'] >= '2025-08-12 19:04:30') & (df['timestamp'] < '2025-08-12 19:06:00')]
post2_200 = post2[post2['response_status_code'] == 200]

# Combined post: 19:02:00 - 19:04:00 + 19:04:30 - 19:06:00
post_all = pd.concat([post1, post2])
post_all_200 = post_all[post_all['response_status_code'] == 200]

for label, subset, subset_200 in [
    ("Pre-incident (18:56-19:01)", pre, pre_200),
    ("Post-incident-1 (19:02-19:04)", post1, post1_200),
    ("Post-incident-2 (19:04:30-19:06)", post2, post2_200),
    ("Post-all combined", post_all, post_all_200),
]:
    n = len(subset)
    n_5xx = ((subset['response_status_code'] >= 500) & (subset['response_status_code'] < 600)).sum()
    rate = n_5xx / n * 100
    p50 = subset_200['duration'].quantile(0.5)
    p95 = subset_200['duration'].quantile(0.95)
    p99 = subset_200['duration'].quantile(0.99)
    req_rate = n / (len(subset['bin_30s'].unique()) * 30)
    print(f"  {label}:")
    print(f"    n={n:,}  5xx={n_5xx} ({rate:.2f}%)  req/s={req_rate:.1f}")
    print(f"    200-only latency: p50={p50:.0f} ({p50/1000:.1f}ms)  p95={p95:.0f} ({p95/1000:.1f}ms)  p99={p99:.0f} ({p99/1000:.1f}ms)")

# Statistical test: are pre and post 5xx rates different?
pre_5xx = ((pre['response_status_code'] >= 500) & (pre['response_status_code'] < 600)).sum()
post_5xx = ((post_all['response_status_code'] >= 500) & (post_all['response_status_code'] < 600)).sum()
# Two-proportion z-test
p1 = pre_5xx / len(pre)
p2 = post_5xx / len(post_all)
p_pooled = (pre_5xx + post_5xx) / (len(pre) + len(post_all))
se = np.sqrt(p_pooled * (1 - p_pooled) * (1/len(pre) + 1/len(post_all)))
z = (p1 - p2) / se
p_value = 2 * (1 - stats.norm.cdf(abs(z)))
print(f"\n  Two-proportion z-test (pre vs post-all):")
print(f"    Pre rate: {p1*100:.2f}%  Post rate: {p2*100:.2f}%")
print(f"    z={z:.3f}  p={p_value:.4f}")
print(f"    Difference: {(p1-p2)*100:.2f}pp  {'SIGNIFICANT' if p_value < 0.05 else 'NOT significant'} at α=0.05")

# Latency comparison (Mann-Whitney U — non-parametric, latency is skewed)
u_stat, u_pvalue = stats.mannwhitneyu(pre_200['duration'], post_all_200['duration'], alternative='two-sided')
print(f"\n  Mann-Whitney U test on 200-only latency (pre vs post-all):")
print(f"    U={u_stat:.0f}  p={u_pvalue:.4f}")
print(f"    {'SIGNIFICANT' if u_pvalue < 0.05 else 'NOT significant'} at α=0.05")

print("\n" + "=" * 70)
print("AUDIT 2: PER-SERVER 500 RATE THROUGH INCIDENT 1 TAIL (10s resolution)")
print("=" * 70)
print("Question: Are the elevated 500s in the tail (19:01:20-19:02:00) from")
print("service-1 (recovery dynamics) or service-2/3 (redistribution overload)?\n")

inc1_window = df[(df['timestamp'] >= '2025-08-12 19:00:30') & (df['timestamp'] < '2025-08-12 19:02:30')]
inc1_10s = inc1_window.groupby(['bin_10s', 'server_id']).agg(
    total=('timestamp', 'count'),
    err_500=('response_status_code', lambda x: (x == 500).sum()),
    err_503=('response_status_code', lambda x: (x == 503).sum()),
).reset_index()
inc1_10s['rate_500'] = (inc1_10s['err_500'] / inc1_10s['total'] * 100).round(2)

# Pivot for readability
for srv in ['service-1', 'service-2', 'service-3']:
    print(f"\n  --- {srv} ---")
    srv_data = inc1_10s[inc1_10s['server_id'] == srv].sort_values('bin_10s')
    for _, row in srv_data.iterrows():
        marker = ""
        if row['err_503'] > 0:
            marker = f"  [+{int(row['err_503'])} 503s]"
        print(f"    {row['bin_10s']}  total={int(row['total']):>4}  500={int(row['err_500']):>3} ({row['rate_500']:>5.1f}%){marker}")

print("\n" + "=" * 70)
print("AUDIT 3: GET RATIO HYPOTHESIS — RETIREMENT CHECK")
print("=" * 70)
print("Question: Does GET ratio shift during incidents? If not, retire the")
print("retry-storm-via-GET hypothesis explicitly.\n")

# GET ratio per 10s bin during incident windows
for label, start, end in [
    ("Incident 1 (19:00:30-19:02:30)", '2025-08-12 19:00:30', '2025-08-12 19:02:30'),
    ("Incident 2 (19:03:30-19:05:00)", '2025-08-12 19:03:30', '2025-08-12 19:05:00'),
]:
    window = df[(df['timestamp'] >= start) & (df['timestamp'] < end)]
    get_ratio = window.groupby('bin_10s').apply(
        lambda x: (x['request_type'] == 'GET').sum() / len(x) * 100,
        include_groups=False
    ).reset_index(name='get_pct')
    print(f"  {label}:")
    for _, row in get_ratio.iterrows():
        print(f"    {row['bin_10s']}  GET={row['get_pct']:.1f}%")

# Healthy baseline GET ratio
hw_get = (hw['request_type'] == 'GET').sum() / len(hw) * 100
print(f"\n  Healthy baseline GET ratio: {hw_get:.1f}%")

# Per-server GET ratio during incident 1 (is service-1 different?)
inc1_full = df[(df['timestamp'] >= '2025-08-12 19:01:00') & (df['timestamp'] < '2025-08-12 19:02:00')]
for srv in ['service-1', 'service-2', 'service-3']:
    sub = inc1_full[inc1_full['server_id'] == srv]
    get_r = (sub['request_type'] == 'GET').sum() / len(sub) * 100
    print(f"  Incident 1 GET ratio on {srv}: {get_r:.1f}% (n={len(sub)})")

print("\n" + "=" * 70)
print("AUDIT 4: BASELINE 5xx RATE — CONFIDENCE INTERVAL + POISSON CHECK")
print("=" * 70)
print("Question: Is the bin-to-bin variation (2.70%-3.62%) real variation")
print("or just Poisson noise around a stable underlying rate?\n")

# Per-30s-bin 5xx counts in healthy window
hw_bins = hw.groupby('bin_30s').agg(
    total=('timestamp', 'count'),
    err_5xx=('response_status_code', lambda x: ((x >= 500) & (x < 600)).sum()),
).reset_index()
hw_bins['rate'] = hw_bins['err_5xx'] / hw_bins['total'] * 100

observed_rates = hw_bins['rate'].values
observed_counts = hw_bins['err_5xx'].values
observed_totals = hw_bins['total'].values

# Overall rate
overall_rate = hw_bins['err_5xx'].sum() / hw_bins['total'].sum()
print(f"  Overall healthy 5xx rate: {overall_rate*100:.3f}%")
print(f"  Per-bin rates: {', '.join(f'{r:.2f}%' for r in observed_rates)}")
print(f"  Per-bin counts: {', '.join(str(int(c)) for c in observed_counts)}")

# Wilson score interval for overall rate
n_total = hw_bins['total'].sum()
n_success = hw_bins['err_5xx'].sum()
z_val = 1.96  # 95% CI
p_hat = n_success / n_total
ci_denom = 1 + z_val**2 / n_total
ci_center = (p_hat + z_val**2 / (2 * n_total)) / ci_denom
ci_margin = z_val * np.sqrt(p_hat * (1 - p_hat) / n_total + z_val**2 / (4 * n_total**2)) / ci_denom
print(f"\n  Wilson 95% CI for overall rate: [{(ci_center - ci_margin)*100:.3f}%, {(ci_center + ci_margin)*100:.3f}%]")

# Chi-square test for homogeneity across bins
# H0: all bins have the same underlying 5xx rate
expected_counts = observed_totals * overall_rate
chi2 = np.sum((observed_counts - expected_counts)**2 / expected_counts)
dof = len(observed_counts) - 1
chi2_pvalue = 1 - stats.chi2.cdf(chi2, dof)
print(f"\n  Chi-square test for homogeneity across 10 bins:")
print(f"    χ²={chi2:.3f}  df={dof}  p={chi2_pvalue:.4f}")
print(f"    {'REJECT H0: rates differ across bins' if chi2_pvalue < 0.05 else 'FAIL TO REJECT H0: variation is consistent with Poisson noise'}")

# What would Poisson predict?
mean_count = observed_counts.mean()
poisson_std = np.sqrt(mean_count)
print(f"\n  Mean 5xx count per bin: {mean_count:.1f}")
print(f"  Poisson predicted std: {poisson_std:.1f}")
print(f"  Observed std: {observed_counts.std():.1f}")
print(f"  Observed range: {observed_counts.min()}–{observed_counts.max()}")
print(f"  Poisson 95% range (approx): {mean_count - 2*poisson_std:.0f}–{mean_count + 2*poisson_std:.0f}")

print("\n" + "=" * 70)
print("AUDIT 5: INCIDENT 2 — 500s FROM BURST CLIENT OR LEGITIMATE USERS?")
print("=" * 70)
print("Question: During the 19:04:00 burst, are the 268 500 errors from the")
print("burst client (yNGr0ru8jkXx) or from legitimate users being crowded out?\n")

inc2 = df[(df['timestamp'] >= '2025-08-12 19:04:00') & (df['timestamp'] < '2025-08-12 19:04:30')]
inc2_500 = inc2[inc2['response_status_code'] == 500]
burst_client = 'yNGr0ru8jkXx'

burst_500 = inc2_500[inc2_500['client_id'] == burst_client]
legit_500 = inc2_500[inc2_500['client_id'] != burst_client]

print(f"  Total 500s in incident 2 window: {len(inc2_500)}")
print(f"  From burst client ({burst_client}): {len(burst_500)}")
print(f"  From other clients: {len(legit_500)}")

# What's the expected 500 count from legitimate traffic?
legit_traffic = inc2[inc2['client_id'] != burst_client]
burst_traffic = inc2[inc2['client_id'] == burst_client]
print(f"\n  Traffic breakdown:")
print(f"    Burst client: {len(burst_traffic)} requests, {len(burst_500)} 500s ({len(burst_500)/len(burst_traffic)*100:.2f}% rate)")
print(f"    Legitimate: {len(legit_traffic)} requests, {len(legit_500)} 500s ({len(legit_500)/len(legit_traffic)*100:.2f}% rate)")

# Compare legitimate 500 rate to baseline
baseline_rate = overall_rate * 100
print(f"    Baseline 5xx rate: {baseline_rate:.2f}%")
print(f"    Expected legitimate 500s at baseline rate: {len(legit_traffic) * overall_rate:.0f}")

# Latency comparison: did legitimate users experience worse latency?
legit_200_inc2 = inc2[(inc2['client_id'] != burst_client) & (inc2['response_status_code'] == 200)]
legit_200_healthy = hw_200[hw_200['client_id'] != burst_client]  # exclude burst client from baseline too

print(f"\n  Legitimate user 200-only latency during incident 2:")
print(f"    p50={legit_200_inc2['duration'].quantile(0.5):.0f} ({legit_200_inc2['duration'].quantile(0.5)/1000:.1f}ms)")
print(f"    p95={legit_200_inc2['duration'].quantile(0.95):.0f} ({legit_200_inc2['duration'].quantile(0.95)/1000:.1f}ms)")
print(f"    p99={legit_200_inc2['duration'].quantile(0.99):.0f} ({legit_200_inc2['duration'].quantile(0.99)/1000:.1f}ms)")
print(f"  Healthy baseline (excl burst client):")
print(f"    p50={legit_200_healthy['duration'].quantile(0.5):.0f} ({legit_200_healthy['duration'].quantile(0.5)/1000:.1f}ms)")
print(f"    p95={legit_200_healthy['duration'].quantile(0.95):.0f} ({legit_200_healthy['duration'].quantile(0.95)/1000:.1f}ms)")
print(f"    p99={legit_200_healthy['duration'].quantile(0.99):.0f} ({legit_200_healthy['duration'].quantile(0.99)/1000:.1f}ms)")

# Degraded 200 rate for legitimate users
deg_inc2 = (legit_200_inc2['duration'] > HEALTHY_P95).sum()
deg_baseline = (legit_200_healthy['duration'] > HEALTHY_P95).sum()
print(f"\n  Degraded 200s (>{HEALTHY_P95:.0f}μs):")
print(f"    Incident 2 legitimate: {deg_inc2}/{len(legit_200_inc2)} = {deg_inc2/len(legit_200_inc2)*100:.2f}%")
print(f"    Healthy baseline: {deg_baseline}/{len(legit_200_healthy)} = {deg_baseline/len(legit_200_healthy)*100:.2f}%")

# Burst client status code breakdown
print(f"\n  Burst client full status breakdown:")
print(burst_traffic['response_status_code'].value_counts().to_string())
print(f"  Burst client latency (200s only):")
burst_200 = burst_traffic[burst_traffic['response_status_code'] == 200]
if len(burst_200) > 0:
    print(f"    p50={burst_200['duration'].quantile(0.5):.0f} ({burst_200['duration'].quantile(0.5)/1000:.1f}ms)")
    print(f"    p95={burst_200['duration'].quantile(0.95):.0f} ({burst_200['duration'].quantile(0.95)/1000:.1f}ms)")
