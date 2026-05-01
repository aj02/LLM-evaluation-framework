"""Dataset loading: JSON, JSONL, CSV."""
from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from evalkit.core.case import TestCase


class Dataset(BaseModel):
    """A collection of TestCase objects."""

    model_config = ConfigDict(extra="forbid")

    name: str = "unnamed"
    cases: list[TestCase] = Field(default_factory=list)
    source_path: str | None = None

    def __iter__(self) -> Iterator[TestCase]:  # type: ignore[override]
        return iter(self.cases)

    def __len__(self) -> int:
        return len(self.cases)


def _coerce_record(raw: dict[str, Any], *, drop_empty_strings: bool = False) -> TestCase:
    """Map a raw dict (from JSONL/CSV) onto the TestCase schema.

    drop_empty_strings: only set when reading CSV — there an unfilled cell
        becomes an empty string, which we want to treat as missing. JSON
        records already have explicit values; an explicit ``""`` there is
        meaningful and must be preserved.
    """
    if drop_empty_strings:
        cleaned = {k: v for k, v in raw.items() if v not in ("", None)}
    else:
        cleaned = {k: v for k, v in raw.items() if v is not None}
    if "id" not in cleaned:
        raise ValueError(f"record missing required 'id' field: {raw!r}")
    if "input" not in cleaned:
        raise ValueError(f"record missing required 'input' field: id={cleaned.get('id')!r}")
    return TestCase.model_validate(cleaned)


def _load_jsonl(path: Path) -> list[TestCase]:
    cases: list[TestCase] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {e.msg}") from e
            cases.append(_coerce_record(raw))
    return cases


def _load_json(path: Path) -> list[TestCase]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "cases" in data:
        records = data["cases"]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError(f"{path}: expected list or {{'cases': [...]}}, got {type(data).__name__}")
    return [_coerce_record(r) for r in records]


def _load_csv(path: Path) -> list[TestCase]:
    cases: list[TestCase] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # CSV strings need to be parsed as JSON when they look structured.
            for key in ("input", "expected", "metadata", "evaluators"):
                if key in row and isinstance(row[key], str) and row[key].strip().startswith(("{", "[")):
                    try:
                        row[key] = json.loads(row[key])
                    except json.JSONDecodeError:
                        pass
            cases.append(_coerce_record(row, drop_empty_strings=True))
    return cases


def load_dataset(path: str | Path, name: str | None = None) -> Dataset:
    """Load a dataset from a file. Format inferred from extension."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"dataset not found: {p}")

    suffix = p.suffix.lower()
    if suffix == ".jsonl":
        cases = _load_jsonl(p)
    elif suffix == ".json":
        cases = _load_json(p)
    elif suffix == ".csv":
        cases = _load_csv(p)
    else:
        raise ValueError(f"unsupported dataset extension: {suffix!r} (expected .jsonl, .json, .csv)")

    seen: set[str] = set()
    for c in cases:
        if c.id in seen:
            raise ValueError(f"duplicate case id in {p}: {c.id!r}")
        seen.add(c.id)

    return Dataset(name=name or p.stem, cases=cases, source_path=str(p))
