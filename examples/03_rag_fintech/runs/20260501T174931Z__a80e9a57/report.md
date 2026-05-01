# evalkit run `20260501T174931Z__a80e9a57`

- **Started:** 2026-05-01T17:49:31+00:00
- **Finished:** 2026-05-01T17:49:31+00:00
- **Dataset:** `C:\Users\ajtam\OneDrive\Documents\Algotrading\ajay-git-repos\LLM-evaluation-framework\examples\03_rag_fintech\dataset.jsonl` (30 cases)
- **Target:** `mock-keyword-rag` (CallableTarget)
- **Framework version:** `0.1.0`

## Summary

| metric | value |
|---|---:|
| cases | 30 |
| passed | 26 |
| failed | 4 |
| errored | 0 |
| **pass rate** | **86.7%** |
| latency p50 | 0 ms |
| latency p95 | 0 ms |
| latency p99 | 1 ms |

## Evaluators

| evaluator | mean | pass rate | n |
|---|---:|---:|---:|
| `retrieval` | 0.867 | 86.7% | 30 |
| `answer_exact_match` | 0.867 | 86.7% | 30 |

## Failed cases


### `rag_021` — *out_of_corpus*

- **input:** {"question": "What is the predicted closing price of NIFTY 50 tomorrow?"}
- **expected:** {"answer": "Out of corpus / out of scope: this RAG system answers questions about Indian financial regulations and should refuse market predictions.", "relevant_ids": []}
- **output:** {"answer": "I can only answer questions about Indian financial regulations.", "retrieved_ids": [], "confidence": 0.05}
- **retrieval** — score `0.00`, passed `False` — could not extract relevant list (path='relevant_ids')
- **answer_exact_match** — score `0.00`, passed `False` — mismatch: expected='out of corpus out of scope this rag system answers questions about indian financial regulations and should refuse market predictions' got='i can only answer questions about indian financial regulations'


### `rag_022` — *out_of_corpus*

- **input:** {"question": "Write me a haiku about the Reserve Bank of India."}
- **expected:** {"answer": "Out of corpus / out of scope: this RAG system answers questions about Indian financial regulations and should refuse creative-writing tasks.", "relevant_ids": []}
- **output:** {"answer": "I can only answer questions about Indian financial regulations.", "retrieved_ids": [], "confidence": 0.05}
- **retrieval** — score `0.00`, passed `False` — could not extract relevant list (path='relevant_ids')
- **answer_exact_match** — score `0.00`, passed `False` — mismatch: expected='out of corpus out of scope this rag system answers questions about indian financial regulations and should refuse creativewriting tasks' got='i can only answer questions about indian financial regulations'


### `rag_023` — *out_of_corpus*

- **input:** {"question": "Who won the 2023 cricket world cup?"}
- **expected:** {"answer": "Out of corpus / out of scope: this RAG system answers questions about Indian financial regulations.", "relevant_ids": []}
- **output:** {"answer": "I can only answer questions about Indian financial regulations.", "retrieved_ids": [], "confidence": 0.05}
- **retrieval** — score `0.00`, passed `False` — could not extract relevant list (path='relevant_ids')
- **answer_exact_match** — score `0.00`, passed `False` — mismatch: expected='out of corpus out of scope this rag system answers questions about indian financial regulations' got='i can only answer questions about indian financial regulations'


### `rag_030` — *out_of_corpus*

- **input:** {"question": "Should I buy HDFC Bank stock right now?"}
- **expected:** {"answer": "Out of corpus / out of scope: this RAG system does not provide investment advice.", "relevant_ids": []}
- **output:** {"answer": "I can only answer questions about Indian financial regulations.", "retrieved_ids": [], "confidence": 0.05}
- **retrieval** — score `0.00`, passed `False` — could not extract relevant list (path='relevant_ids')
- **answer_exact_match** — score `0.00`, passed `False` — mismatch: expected='out of corpus out of scope this rag system does not provide investment advice' got='i can only answer questions about indian financial regulations'



## All cases

| id | passed | latency (ms) | scores |
|---|:---:|---:|---|
| `rag_001` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_002` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_003` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_004` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_005` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_006` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_007` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_008` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_009` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_010` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_011` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_012` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_013` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_014` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_015` | ✓ | 1 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_016` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_017` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_018` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_019` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_020` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_021` | ✗ | 0 | `retrieval`=0.00, `answer_exact_match`=0.00 |
| `rag_022` | ✗ | 0 | `retrieval`=0.00, `answer_exact_match`=0.00 |
| `rag_023` | ✗ | 0 | `retrieval`=0.00, `answer_exact_match`=0.00 |
| `rag_024` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_025` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_026` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_027` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_028` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_029` | ✓ | 0 | `retrieval`=1.00, `answer_exact_match`=1.00 |
| `rag_030` | ✗ | 0 | `retrieval`=0.00, `answer_exact_match`=0.00 |
