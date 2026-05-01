# 01 — Quickstart

A 5-minute "hello world" eval against a fake target. The "system under test"
is a Python function that uppercases its input text.

## What this shows
- The smallest possible evalkit setup: dataset + target + evaluator.
- How `CallableTarget` lets you point the framework at any Python function.
- What a full run looks like end-to-end (dataset snapshot, results.jsonl,
  summary.json, report.md, dashboard.html).

## Run

```bash
python examples/01_quickstart/run.py
```

You should see ~5 cases pass and a `runs/` folder appear next to this README.

## Files
- [`dataset.jsonl`](dataset.jsonl) — 5 smoke cases (`text → TEXT`)
- [`run.py`](run.py) — Python entry point using `CallableTarget`
- [`target.yaml`](target.yaml) — optional CLI target (subprocess) you can
  use with `evalkit run` once step 3 lands
