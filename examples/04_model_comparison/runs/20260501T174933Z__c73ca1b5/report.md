# evalkit run `20260501T174933Z__c73ca1b5`

- **Started:** 2026-05-01T17:49:34+00:00
- **Finished:** 2026-05-01T17:49:34+00:00
- **Dataset:** `C:\Users\ajtam\OneDrive\Documents\Algotrading\ajay-git-repos\LLM-evaluation-framework\examples\04_model_comparison\dataset.jsonl` (15 cases)
- **Target:** `mock-a` (CallableTarget)
- **Framework version:** `0.1.0`

## Summary

| metric | value |
|---|---:|
| cases | 15 |
| passed | 13 |
| failed | 2 |
| errored | 0 |
| **pass rate** | **86.7%** |
| latency p50 | 0 ms |
| latency p95 | 0 ms |
| latency p99 | 0 ms |

## Evaluators

| evaluator | mean | pass rate | n |
|---|---:|---:|---:|
| `exact_match` | 0.867 | 86.7% | 15 |

## Failed cases


### `qa_004` — *math*

- **input:** {"prompt": "What is 17 multiplied by 23? Answer with the integer only."}
- **expected:** 391
- **output:** 397
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='391' got='397'


### `qa_015` — *physics*

- **input:** {"prompt": "What is the speed of light in a vacuum, in meters per second, in scientific notation to one decimal? E.g., 1.0e8."}
- **expected:** 3.0e8
- **output:** 3e8 m/s with units
- **exact_match** — score `0.00`, passed `False` — mismatch: expected='30e8' got='3e8 ms with units'



## All cases

| id | passed | latency (ms) | scores |
|---|:---:|---:|---|
| `qa_001` | ✓ | 0 | `exact_match`=1.00 |
| `qa_002` | ✓ | 0 | `exact_match`=1.00 |
| `qa_003` | ✓ | 0 | `exact_match`=1.00 |
| `qa_004` | ✗ | 0 | `exact_match`=0.00 |
| `qa_005` | ✓ | 0 | `exact_match`=1.00 |
| `qa_006` | ✓ | 0 | `exact_match`=1.00 |
| `qa_007` | ✓ | 0 | `exact_match`=1.00 |
| `qa_008` | ✓ | 0 | `exact_match`=1.00 |
| `qa_009` | ✓ | 0 | `exact_match`=1.00 |
| `qa_010` | ✓ | 0 | `exact_match`=1.00 |
| `qa_011` | ✓ | 0 | `exact_match`=1.00 |
| `qa_012` | ✓ | 0 | `exact_match`=1.00 |
| `qa_013` | ✓ | 0 | `exact_match`=1.00 |
| `qa_014` | ✓ | 0 | `exact_match`=1.00 |
| `qa_015` | ✗ | 0 | `exact_match`=0.00 |
