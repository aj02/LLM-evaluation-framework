# evalkit run `20260501T174925Z__ce6584fa`

- **Started:** 2026-05-01T17:49:25+00:00
- **Finished:** 2026-05-01T17:49:25+00:00
- **Dataset:** `C:\Users\ajtam\OneDrive\Documents\Algotrading\ajay-git-repos\LLM-evaluation-framework\examples\01_quickstart\dataset.jsonl` (5 cases)
- **Target:** `uppercase` (CallableTarget)
- **Framework version:** `0.1.0`

## Summary

| metric | value |
|---|---:|
| cases | 5 |
| passed | 5 |
| failed | 0 |
| errored | 0 |
| **pass rate** | **100.0%** |
| latency p50 | 0 ms |
| latency p95 | 0 ms |
| latency p99 | 0 ms |

## Evaluators

| evaluator | mean | pass rate | n |
|---|---:|---:|---:|
| `exact_match` | 1.000 | 100.0% | 5 |

## Failed cases


*(none — every case passed)*

## All cases

| id | passed | latency (ms) | scores |
|---|:---:|---:|---|
| `smoke_hello` | ✓ | 0 | `exact_match`=1.00 |
| `smoke_world` | ✓ | 0 | `exact_match`=1.00 |
| `smoke_punct` | ✓ | 0 | `exact_match`=1.00 |
| `smoke_mixed` | ✓ | 0 | `exact_match`=1.00 |
| `smoke_empty` | ✓ | 0 | `exact_match`=1.00 |
