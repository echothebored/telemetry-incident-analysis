"""
URL-level deep dive: check for error clustering at individual URL level,
dominant client endpoint patterns, and incident-window URL behavior.
"""
import pandas as pd
import numpy as np

DATA_PATH = '../question/telemetry_dataset.csv'
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

# Endpoint grouping
df['endpoint_group'] = df['request_url'].apply(
    lambda x: '/'.join(x.split('/')[:2]) + '/{id}' if len(x.split('/')) > 2 else x
)
# Finer grouping: /users/{id} vs /users/{id}/posts
def fine_group(url):
    parts = url.strip('/').split('/')
    if len(parts) == 1:
        return '/' + parts[0]  # /users, /posts
    elif len(parts) == 2:
        return '/' + parts[0] + '/{id}'  # /users/{id}, /posts/{id}
    elif len(parts) == 3:
        return '/' + parts[0] + '/{id}/' + parts[2]  # /users/{id}/posts
    return url

df['endpoint_fine'] = df['request_url'].apply(fine_group)

print("=" * 70)
print("1. FINE-GRAINED ENDPOINT GROUPS")
print("=" * 70)
print(df['endpoint_fine'].value_counts().to_string())

print("\n" + "=" * 70)
print("2. ERROR DISTRIBUTION BY FINE ENDPOINT GROUP")
print("=" * 70)
ct = pd.crosstab(df['endpoint_fine'], df['response_status_code'])
print(ct.to_string())
print("\nError rates per group:")
for ep in ct.index:
    total = ct.loc[ep].sum()
    e5xx = ct.loc[ep][[c for c in ct.columns if c >= 500]].sum()
    e404 = ct.loc[ep].get(404, 0)
    e429 = ct.loc[ep].get(429, 0)
    print(f"  {ep}: 5xx={e5xx/total*100:.2f}% 404={e404/total*100:.2f}% 429={e429/total*100:.2f}% (n={total})")

print("\n" + "=" * 70)
print("3. 404 ERROR CONCENTRATION — WHICH URLS GET 404s?")
print("=" * 70)
err404 = df[df['response_status_code'] == 404]
print(f"Total 404s: {len(err404)}")
print(f"Unique URLs with 404: {err404['request_url'].nunique()}")
print(f"\nTop 404 URLs:")
print(err404['request_url'].value_counts().head(30).to_string())
print(f"\n404 by endpoint group:")
print(err404['endpoint_fine'].value_counts().to_string())
print(f"\n404 by request type:")
print(err404['request_type'].value_counts().to_string())

print("\n" + "=" * 70)
print("4. 500 ERROR CONCENTRATION — DO SPECIFIC URLs CLUSTER?")
print("=" * 70)
err500 = df[df['response_status_code'] == 500]
print(f"Total 500s: {len(err500)}")
print(f"Unique URLs with 500: {err500['request_url'].nunique()}")
# Check if any specific URL has disproportionate 500s
url_500_counts = err500['request_url'].value_counts()
print(f"\nURL 500 count distribution:")
print(url_500_counts.describe().to_string())
print(f"\nTop 20 URLs by 500 count:")
print(url_500_counts.head(20).to_string())
# Compare to overall URL distribution
url_total = df['request_url'].value_counts()
top_500_urls = url_500_counts.head(20).index
for url in top_500_urls:
    total = url_total.get(url, 0)
    errs = url_500_counts.get(url, 0)
    rate = errs / total * 100 if total > 0 else 0
    print(f"  {url}: {errs}/{total} = {rate:.1f}% error rate")

print("\n" + "=" * 70)
print("5. 503 ERROR CONCENTRATION")
print("=" * 70)
err503 = df[df['response_status_code'] == 503]
print(f"Total 503s: {len(err503)}")
print(f"Unique URLs with 503: {err503['request_url'].nunique()}")
print(f"\nTop 20 URLs by 503 count:")
url_503_counts = err503['request_url'].value_counts()
print(url_503_counts.head(20).to_string())
print(f"\n503 by endpoint group:")
print(err503['endpoint_fine'].value_counts().to_string())

print("\n" + "=" * 70)
print("6. DOMINANT CLIENT (yNGr0ru8jkXx) — ENDPOINT BEHAVIOR")
print("=" * 70)
dom = df[df['client_id'] == 'yNGr0ru8jkXx']
print(f"Total requests: {len(dom)}")
print(f"Unique URLs: {dom['request_url'].nunique()}")
print(f"\nEndpoint distribution:")
print(dom['endpoint_fine'].value_counts().to_string())
print(f"\nRequest type distribution:")
print(dom['request_type'].value_counts().to_string())
print(f"\nStatus code distribution:")
print(dom['response_status_code'].value_counts().to_string())
print(f"\nTime range: {dom['timestamp'].min()} to {dom['timestamp'].max()}")
# Temporal pattern
dom['bin_30s'] = dom['timestamp'].dt.floor('30s')
dom_temporal = dom.groupby('bin_30s').size()
print(f"\nRequests per 30s bin:")
print(dom_temporal.to_string())
print(f"\nAgent: {dom['agent_name'].unique()}")
print(f"Device: {dom['client_device_type'].unique()}")
print(f"Region: {dom['geographic_region'].unique()}")
print(f"Server distribution:")
print(dom['server_id'].value_counts().to_string())

print("\n" + "=" * 70)
print("7. INCIDENT WINDOW URL PATTERNS")
print("=" * 70)
# Incident 1: 19:01:00 - 19:01:30
inc1 = df[(df['timestamp'] >= '2025-08-12 19:01:00') & (df['timestamp'] < '2025-08-12 19:02:00')]
healthy = df[(df['timestamp'] >= '2025-08-12 18:58:00') & (df['timestamp'] < '2025-08-12 18:59:00')]

print("--- Incident 1 (19:01:00-19:02:00) ---")
print(f"Total requests: {len(inc1)}")
print(f"Endpoint distribution:")
inc1_ep = inc1['endpoint_fine'].value_counts(normalize=True) * 100
print(inc1_ep.to_string())
print(f"\nStatus codes:")
print(inc1['response_status_code'].value_counts().to_string())
print(f"\nErrors by endpoint:")
inc1_err = inc1[inc1['response_status_code'] >= 500]
print(inc1_err['endpoint_fine'].value_counts().to_string())
print(f"\nErrors by server:")
print(inc1_err['server_id'].value_counts().to_string())

# Incident 2: 19:04:00 - 19:04:30
inc2 = df[(df['timestamp'] >= '2025-08-12 19:04:00') & (df['timestamp'] < '2025-08-12 19:04:30')]
print(f"\n--- Incident 2 (19:04:00-19:04:30) ---")
print(f"Total requests: {len(inc2)}")
print(f"Endpoint distribution:")
inc2_ep = inc2['endpoint_fine'].value_counts(normalize=True) * 100
print(inc2_ep.to_string())
print(f"\nStatus codes:")
print(inc2['response_status_code'].value_counts().to_string())
print(f"\nErrors by endpoint:")
inc2_err = inc2[inc2['response_status_code'] >= 500]
print(inc2_err['endpoint_fine'].value_counts().to_string())
print(f"\n429s by endpoint:")
inc2_429 = inc2[inc2['response_status_code'] == 429]
print(inc2_429['endpoint_fine'].value_counts().to_string())
print(f"\n429s by client (top 10):")
print(inc2_429['client_id'].value_counts().head(10).to_string())

print(f"\n--- Healthy reference (18:58:00-18:59:00) ---")
print(f"Total requests: {len(healthy)}")
print(f"Endpoint distribution:")
healthy_ep = healthy['endpoint_fine'].value_counts(normalize=True) * 100
print(healthy_ep.to_string())

print("\n" + "=" * 70)
print("8. PER-URL ERROR RATE — ANY OUTLIERS?")
print("=" * 70)
# Only look at URLs with enough traffic to be meaningful (>=10 requests)
url_stats = df.groupby('request_url').agg(
    total=('response_status_code', 'count'),
    errors_5xx=('response_status_code', lambda x: (x >= 500).sum())
).reset_index()
url_stats['error_rate'] = url_stats['errors_5xx'] / url_stats['total'] * 100
high_traffic = url_stats[url_stats['total'] >= 10].sort_values('error_rate', ascending=False)
print(f"URLs with >=10 requests: {len(high_traffic)}")
print(f"\nTop 20 by error rate (min 10 requests):")
print(high_traffic.head(20).to_string(index=False))
print(f"\nError rate distribution (URLs with >=10 requests):")
print(high_traffic['error_rate'].describe().to_string())

# Collection endpoints specifically
print(f"\nCollection endpoint error rates:")
for ep in ['/users', '/posts']:
    subset = df[df['request_url'] == ep]
    e5xx = (subset['response_status_code'] >= 500).sum()
    print(f"  {ep}: {e5xx}/{len(subset)} = {e5xx/len(subset)*100:.2f}%")
