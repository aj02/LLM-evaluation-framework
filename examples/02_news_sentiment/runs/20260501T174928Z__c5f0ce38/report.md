# evalkit run `20260501T174928Z__c5f0ce38`

- **Started:** 2026-05-01T17:49:28+00:00
- **Finished:** 2026-05-01T17:49:28+00:00
- **Dataset:** `C:\Users\ajtam\OneDrive\Documents\Algotrading\ajay-git-repos\LLM-evaluation-framework\examples\02_news_sentiment\dataset.jsonl` (20 cases)
- **Target:** `mock-keyword-sentiment` (CallableTarget)
- **Framework version:** `0.1.0`

## Summary

| metric | value |
|---|---:|
| cases | 20 |
| passed | 16 |
| failed | 4 |
| errored | 0 |
| **pass rate** | **80.0%** |
| latency p50 | 0 ms |
| latency p95 | 0 ms |
| latency p99 | 0 ms |

## Evaluators

| evaluator | mean | pass rate | n |
|---|---:|---:|---:|
| `exact_match` | 0.800 | 80.0% | 20 |

## Failed cases


### `ns_003` — *macro*

- **input:** {"headline": "RBI keeps repo rate unchanged at 6.50%", "body": "The Reserve Bank of India's MPC voted 5-1 to hold the policy repo rate steady, citing balanced risks to inflation and growth."}
- **expected:** neutral
- **output:** positive
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='neutral' got='positive'


### `ns_007` — *credit*

- **input:** {"headline": "ICICI Bank reports asset-quality stress in unsecured retail book", "body": "ICICI Bank flagged rising delinquencies in its personal-loan and credit-card portfolio, with 30+ DPD trending up over three quarters."}
- **expected:** negative
- **output:** neutral
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='negative' got='neutral'


### `ns_019` — *policy*

- **input:** {"headline": "Indian railways announces fare hike for AC classes", "body": "Indian Railways announced a 10-15% fare hike for AC classes, effective next month, the first revision in three years."}
- **expected:** neutral
- **output:** negative
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='neutral' got='negative'


### `ns_020` — *credit*

- **input:** {"headline": "Vedanta delays demerger; bondholders flag refinancing risk", "body": "Vedanta Resources delayed its planned demerger by six months. Bondholders raised concerns over upcoming USD 3.2 bn debt maturities."}
- **expected:** negative
- **output:** neutral
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='negative' got='neutral'



## All cases

| id | passed | latency (ms) | scores |
|---|:---:|---:|---|
| `ns_001` | ✓ | 0 | `exact_match`=1.00 |
| `ns_002` | ✓ | 0 | `exact_match`=1.00 |
| `ns_003` | ✗ | 0 | `exact_match`=0.00 |
| `ns_004` | ✓ | 0 | `exact_match`=1.00 |
| `ns_005` | ✓ | 0 | `exact_match`=1.00 |
| `ns_006` | ✓ | 0 | `exact_match`=1.00 |
| `ns_007` | ✗ | 0 | `exact_match`=0.00 |
| `ns_008` | ✓ | 0 | `exact_match`=1.00 |
| `ns_009` | ✓ | 0 | `exact_match`=1.00 |
| `ns_010` | ✓ | 0 | `exact_match`=1.00 |
| `ns_011` | ✓ | 0 | `exact_match`=1.00 |
| `ns_012` | ✓ | 0 | `exact_match`=1.00 |
| `ns_013` | ✓ | 0 | `exact_match`=1.00 |
| `ns_014` | ✓ | 0 | `exact_match`=1.00 |
| `ns_015` | ✓ | 0 | `exact_match`=1.00 |
| `ns_016` | ✓ | 0 | `exact_match`=1.00 |
| `ns_017` | ✓ | 0 | `exact_match`=1.00 |
| `ns_018` | ✓ | 0 | `exact_match`=1.00 |
| `ns_019` | ✗ | 0 | `exact_match`=0.00 |
| `ns_020` | ✗ | 0 | `exact_match`=0.00 |
