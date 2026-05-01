# 02 — News sentiment classifier

Evaluates a financial-news sentiment classifier (separate repo) on 20
labelled Indian-market headlines. Categories are spread across
earnings, regulatory, macro, M&A, governance, and credit, with explicit
difficulty labels (easy/medium/hard) so the report can show where the
classifier struggles.

## What this shows
- `HTTPTarget` against a live localhost service.
- Dataset metadata used to slice by `category` and `difficulty`.
- A graceful **fallback to a keyword-based mock** when the real service
  is not running, so this example always produces a report.

## Run

```bash
# If your sentiment analyzer is running on localhost:8000:
python examples/02_news_sentiment/run.py

# Or use the CLI directly:
evalkit run examples/02_news_sentiment/dataset.jsonl \
  --target examples/02_news_sentiment/target.yaml \
  --evaluators exact_match
```

If `localhost:8000/health` is not reachable, the Python entry point falls
back to a simple keyword classifier so you can see a full run.

## Files
- [`dataset.jsonl`](dataset.jsonl) — 20 labelled headlines
- [`target.yaml`](target.yaml) — HTTPTarget config for the live service
- [`run.py`](run.py) — Python entry point with HTTP→mock fallback
- `runs/` — committed run output (regenerate with the script)

## Real vs mock
The committed `runs/` folder uses the **mock** classifier. With the real
analyzer, results — including category breakdowns and latency — replace
these. See the README at the repo root for live numbers from the SEBI/RBI
RAG eval (example 03), which is the headline benchmark.
