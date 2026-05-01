#!/bin/sh
# evalkit container entrypoint.
#
# Routes the first arg to a subcommand:
#
#   demo     — runs all four examples in mock-mode + writes reports to /app/runs
#   tests    — runs pytest
#   shell    — drops into /bin/sh
#   evalkit  — pass-through to the evalkit CLI (e.g. `evalkit run ...`)
#   <other>  — exec as-is so users can `python ...` or any binary on PATH
#
# Default (no args) is "demo".

set -eu

cmd="${1:-demo}"

case "$cmd" in
    demo)
        echo ">> evalkit demo — running all four examples"
        echo
        for ex in 01_quickstart 02_news_sentiment 03_rag_fintech 04_model_comparison; do
            echo "==> examples/$ex"
            python "/app/examples/$ex/run.py" || {
                echo "!! example $ex failed"
                exit 1
            }
            echo
        done
        echo ">> done. Reports under /app/examples/*/runs/"
        echo "   (mount a volume on /app/examples to get them out, or use"
        echo "    'docker compose run --rm cli evalkit list-runs' against your own runs/)."
        ;;
    tests|test)
        exec pytest -q "${@:-}"
        ;;
    shell|bash|sh)
        exec /bin/sh
        ;;
    evalkit)
        # Pass remaining args through to the CLI.
        shift
        exec evalkit "$@"
        ;;
    --help|-h|help)
        cat <<'EOF'
evalkit container

Usage: docker run --rm [-v ...] [-e ...] evalkit [COMMAND] [ARGS...]

Commands:
  demo                 Run all four bundled examples (default).
  tests                Run pytest inside the container.
  shell                Drop into /bin/sh for poking around.
  evalkit ARGS...      Run the evalkit CLI with the given args.
  <anything else>      exec'd directly (e.g. `python -c '...'`).

Volumes you may want to mount:
  -v "$PWD/runs:/app/runs"          retrieve your own runs/ output
  -v "$PWD/datasets:/app/datasets"  point at your dataset.jsonl files

Environment variables:
  ANTHROPIC_API_KEY    enables the LLM judge (otherwise skipped)
  OPENAI_API_KEY       same for OpenAI-backed judges
  EVALKIT_JUDGE        override default judge model (e.g. "openai:gpt-4o-mini")
EOF
        ;;
    *)
        # Anything else: run it directly.
        exec "$@"
        ;;
esac
