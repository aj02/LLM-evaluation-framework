# evalkit run `20260501T184813Z__cf5a6c61`

- **Started:** 2026-05-01T18:48:13+00:00
- **Finished:** 2026-05-01T18:48:13+00:00
- **Dataset:** `/app/examples/04_model_comparison/dataset.jsonl` (15 cases)
- **Target:** `mock-b` (CallableTarget)
- **Framework version:** `0.1.0`

## Summary

| metric | value |
|---|---:|
| cases | 15 |
| passed | 12 |
| failed | 3 |
| errored | 0 |
| **pass rate** | **80.0%** |
| latency p50 | 0 ms |
| latency p95 | 0 ms |
| latency p99 | 0 ms |

## Evaluators

| evaluator | mean | pass rate | n |
|---|---:|---:|---:|
| `exact_match` | 0.800 | 80.0% | 15 |

## Failed cases


### `qa_005` — *math*

- **input:** {"prompt": "What is the smallest prime number greater than 100? Answer with the integer only."}
- **expected:** 101
- **output:** 103
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='101' got='103'


### `qa_009` — *art*

- **input:** {"prompt": "Who painted the Mona Lisa? Answer with the artist's full name only."}
- **expected:** Leonardo da Vinci
- **output:** Da Vinci
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='leonardo da vinci' got='da vinci'


### `qa_011` — *chemistry*

- **input:** {"prompt": "What is the chemical formula for water?"}
- **expected:** H2O
- **output:** water (H2O)
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='h2o' got='water h2o'



## All cases

| id | passed | latency (ms) | scores |
|---|:---:|---:|---|
| `qa_001` | ✓ | 0 | `exact_match`=1.00 |
| `qa_002` | ✓ | 0 | `exact_match`=1.00 |
| `qa_003` | ✓ | 0 | `exact_match`=1.00 |
| `qa_004` | ✓ | 0 | `exact_match`=1.00 |
| `qa_005` | ✗ | 0 | `exact_match`=0.00 |
| `qa_006` | ✓ | 0 | `exact_match`=1.00 |
| `qa_007` | ✓ | 0 | `exact_match`=1.00 |
| `qa_008` | ✓ | 0 | `exact_match`=1.00 |
| `qa_009` | ✗ | 0 | `exact_match`=0.00 |
| `qa_010` | ✓ | 0 | `exact_match`=1.00 |
| `qa_011` | ✗ | 0 | `exact_match`=0.00 |
| `qa_012` | ✓ | 0 | `exact_match`=1.00 |
| `qa_013` | ✓ | 0 | `exact_match`=1.00 |
| `qa_014` | ✓ | 0 | `exact_match`=1.00 |
| `qa_015` | ✓ | 0 | `exact_match`=1.00 |
