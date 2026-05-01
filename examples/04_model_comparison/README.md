# 04 — Model comparison (Claude vs GPT-4o-mini)

Runs the same 15-question QA dataset against two LLMs and produces a
side-by-side comparison report. This is the framework's killer use case:
**catching regressions when you change models or prompts.**

## What this shows
- Two `Runner` invocations against two different `CallableTarget`s
  wrapping `evalkit.llm.build_client(...)`.
- `evalkit.core.compare.compare_runs` producing a markdown table with
  per-evaluator deltas and a list of flipped cases.
- The HTML dashboard for run B includes a "vs previous run" comparison.

## Run

```bash
# Live (requires both keys):
ANTHROPIC_API_KEY=sk-ant-... OPENAI_API_KEY=sk-... \
  python examples/04_model_comparison/run.py

# Mock fallback runs automatically if either key is missing:
python examples/04_model_comparison/run.py
```

Or use the CLI for each target separately, then `evalkit compare`:

```bash
evalkit run examples/04_model_comparison/dataset.jsonl \
  --target examples/04_model_comparison/target_claude.yaml
evalkit run examples/04_model_comparison/dataset.jsonl \
  --target examples/04_model_comparison/target_gpt4.yaml
evalkit compare <run_id_claude> <run_id_gpt4> --format markdown
```

## Files
- [`dataset.jsonl`](dataset.jsonl) — 15 short QA cases (geography, math, science)
- [`target_claude.yaml`](target_claude.yaml) — HTTPTarget for Anthropic API
- [`target_gpt4.yaml`](target_gpt4.yaml) — HTTPTarget for OpenAI API
- [`run.py`](run.py) — Python entry point with mock fallback
- `runs/` — committed runs A, B, and `comparison.md`

## Mock-mode example output

When running without API keys, two distinct mocks produce slightly
different answers. The comparison reveals 5 flipped cases out of 15:

```
target_a (mock-a): pass 86.7%
target_b (mock-b): pass 80.0%

delta pass-rate: -6.7pp (5 cases flipped)
  qa_004 improved: False -> True
  qa_005 regressed: True -> False
  qa_009 regressed: True -> False
  qa_011 regressed: True -> False
  qa_015 improved: False -> True
```

This is the core regression-detection signal: not just "B is 6.7pp worse"
but "here are the **specific** cases that broke."
