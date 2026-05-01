# 03 — RAG over Indian financial regulations (SEBI / RBI)

The headline benchmark for this framework: a RAG system answering questions
about SEBI, RBI, and IBC regulations. 30 questions across three categories:

| category        | n  | what's tested |
|-----------------|---:|---|
| `lookup`        | 13 | single-fact retrieval ("What is the LCR requirement?") |
| `multi_doc`     | 11 | synthesis across multiple regulations |
| `out_of_corpus` |  3 | questions the system should *refuse* (predictions, advice) |
| difficulty: easy |  9 | |
| difficulty: medium | 13 | |
| difficulty: hard | 8 | |

## Three evaluators, three failure modes

The evaluator stack is designed so each evaluator catches a distinct
kind of break:

| evaluator             | catches                                              |
|-----------------------|------------------------------------------------------|
| `retrieval`           | "we never pulled the right docs"                     |
| `answer_exact_match`  | "we had the docs but botched the surface answer"     |
| `llm_judge`           | "the docs and answer surface look fine but the synthesis is wrong / hedged / hallucinated" |

The retrieval evaluator reads `expected.relevant_ids` and the target's
`retrieved_ids` field, and reports recall@5, precision@5, and MRR. Pass
threshold is recall ≥ 0.6.

The LLM judge uses a 3-criterion rubric (factual accuracy, completeness,
refusal-appropriateness) and a calibrated 1-5 scale. Pass threshold is 4.

## Run

```bash
# Make sure the SEBI/RBI RAG service is up at localhost:8001
# (separate repo). Then:
ANTHROPIC_API_KEY=sk-ant-... python examples/03_rag_fintech/run.py

# Or use the CLI:
evalkit run examples/03_rag_fintech/dataset.jsonl \
  --target examples/03_rag_fintech/target.yaml \
  --evaluators retrieval --evaluators llm_judge
```

If `localhost:8001/ask` isn't reachable, the script falls back to a
keyword-matching mock so you still see a full run. **Do not interpret mock
numbers as the RAG system's quality** — they exist purely to demonstrate
the framework.

If `ANTHROPIC_API_KEY` is unset, the LLM judge is skipped (not silently
zeroed out) — only `retrieval` and `answer_exact_match` run.

## Files
- [`dataset.jsonl`](dataset.jsonl) — 30 questions with relevant_ids
- [`target.yaml`](target.yaml) — HTTPTarget for the RAG service
- [`run.py`](run.py) — Python entry point with mock fallback
- `runs/` — committed run output (currently MOCK; replace with real)
