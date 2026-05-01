from __future__ import annotations

from pathlib import Path

import pytest

from evalkit.core.case import TestCase
from evalkit.core.dataset import Dataset
from evalkit.core.runner import Runner
from evalkit.core.target import CallableTarget
from evalkit.evaluators.exact_match import ExactMatchEvaluator


@pytest.mark.asyncio
async def test_run_callable_target(tmp_path: Path) -> None:
    def fn(inp):  # type: ignore[no-untyped-def]
        return f"hello {inp['name']}"

    target = CallableTarget(fn)
    ds = Dataset(
        name="t",
        cases=[
            TestCase(id="a", input={"name": "world"}, expected="hello world"),
            TestCase(id="b", input={"name": "world"}, expected="bye world"),
        ],
        source_path=str(tmp_path / "ds.jsonl"),
    )
    runner = Runner(target=target, evaluators=[ExactMatchEvaluator()], runs_root=tmp_path)
    rep = await runner.run(ds)

    assert rep.n_cases == 2
    assert rep.n_passed == 1
    assert rep.n_failed == 1
    assert rep.n_errored == 0
    # snapshot files
    rd = tmp_path / rep.run_id
    assert (rd / "dataset.json").exists()
    assert (rd / "target.json").exists()
    assert (rd / "results.jsonl").exists()
    assert (rd / "summary.json").exists()


@pytest.mark.asyncio
async def test_target_error_recorded(tmp_path: Path) -> None:
    def fn(_):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    target = CallableTarget(fn)
    ds = Dataset(
        cases=[TestCase(id="a", input="x", expected="y")],
        source_path=str(tmp_path / "ds.jsonl"),
    )
    rep = await Runner(target=target, evaluators=[ExactMatchEvaluator()], runs_root=tmp_path).run(ds)
    assert rep.n_errored == 1
    assert rep.cases[0].error is not None
    assert "boom" in rep.cases[0].error


@pytest.mark.asyncio
async def test_async_callable(tmp_path: Path) -> None:
    async def fn(inp):  # type: ignore[no-untyped-def]
        return inp["x"]

    target = CallableTarget(fn)
    ds = Dataset(
        cases=[TestCase(id="a", input={"x": "hi"}, expected="hi")],
        source_path=str(tmp_path / "ds.jsonl"),
    )
    rep = await Runner(target=target, evaluators=[ExactMatchEvaluator()], runs_root=tmp_path).run(ds)
    assert rep.n_passed == 1
