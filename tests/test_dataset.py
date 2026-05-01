from __future__ import annotations

import json
from pathlib import Path

import pytest

from evalkit.core.dataset import load_dataset


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_load_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "ds.jsonl"
    _write_jsonl(p, [
        {"id": "a", "input": {"q": 1}, "expected": "x"},
        {"id": "b", "input": {"q": 2}, "expected": "y", "metadata": {"tag": "smoke"}},
    ])
    ds = load_dataset(p)
    assert len(ds) == 2
    assert ds.cases[0].id == "a"
    assert ds.cases[1].metadata == {"tag": "smoke"}


def test_load_json_list(tmp_path: Path) -> None:
    p = tmp_path / "ds.json"
    p.write_text(json.dumps([
        {"id": "a", "input": "hi", "expected": "yo"},
    ]), encoding="utf-8")
    ds = load_dataset(p)
    assert ds.cases[0].input == "hi"


def test_load_json_wrapped(tmp_path: Path) -> None:
    p = tmp_path / "ds.json"
    p.write_text(json.dumps({"cases": [
        {"id": "a", "input": "hi"},
    ]}), encoding="utf-8")
    ds = load_dataset(p)
    assert len(ds) == 1


def test_load_csv(tmp_path: Path) -> None:
    p = tmp_path / "ds.csv"
    p.write_text("id,input,expected\nq1,hello,world\n", encoding="utf-8")
    ds = load_dataset(p)
    assert ds.cases[0].id == "q1"
    assert ds.cases[0].input == "hello"


def test_duplicate_id_rejected(tmp_path: Path) -> None:
    p = tmp_path / "ds.jsonl"
    _write_jsonl(p, [
        {"id": "a", "input": 1},
        {"id": "a", "input": 2},
    ])
    with pytest.raises(ValueError, match="duplicate"):
        load_dataset(p)


def test_missing_id_rejected(tmp_path: Path) -> None:
    p = tmp_path / "ds.jsonl"
    p.write_text(json.dumps({"input": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required 'id'"):
        load_dataset(p)


def test_unknown_extension(tmp_path: Path) -> None:
    p = tmp_path / "ds.txt"
    p.write_text("anything", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_dataset(p)
