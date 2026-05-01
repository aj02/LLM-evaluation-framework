"""Scaffold a starter project for `evalkit init`."""
from __future__ import annotations

import json
from pathlib import Path

STARTER_DATASET = [
    {
        "id": "greet_world",
        "input": {"text": "hello"},
        "expected": "hello world",
        "metadata": {"category": "smoke"},
    },
    {
        "id": "greet_friend",
        "input": {"text": "hi"},
        "expected": "hi friend",
        "metadata": {"category": "smoke"},
    },
]

STARTER_TARGET_YAML = """\
# Replace with your real endpoint, then run:
#   evalkit run dataset.jsonl --target target.yaml
type: http
name: my-system
url: http://localhost:8000/respond
method: POST
headers:
  content-type: application/json
payload_template: '{"text": {{ input.text | tojson }}}'
response_path: answer
timeout_s: 30
"""


def scaffold_starter(cwd: Path, *, force: bool = False) -> list[Path]:
    """Create dataset.jsonl and target.yaml in cwd. Returns paths created."""
    written: list[Path] = []
    ds_path = cwd / "dataset.jsonl"
    tg_path = cwd / "target.yaml"

    for path in (ds_path, tg_path):
        if path.exists() and not force:
            raise FileExistsError(f"{path} already exists (use --force to overwrite)")

    with ds_path.open("w", encoding="utf-8") as f:
        for case in STARTER_DATASET:
            f.write(json.dumps(case) + "\n")
    written.append(ds_path)

    tg_path.write_text(STARTER_TARGET_YAML, encoding="utf-8")
    written.append(tg_path)
    return written
