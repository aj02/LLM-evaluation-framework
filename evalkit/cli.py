"""evalkit CLI."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from evalkit import __version__

console = Console()


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="evalkit — small, opinionated LLM evaluation framework.",
)
@click.version_option(__version__, prog_name="evalkit")
def cli() -> None:
    """evalkit command-line entry point."""


# ---------------------------------------------------------------------------
# evalkit run
# ---------------------------------------------------------------------------
@cli.command(help="Run a dataset against a target.")
@click.argument("dataset_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--target", "-t", "target_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True,
    help="Path to a target config (YAML/JSON).",
)
@click.option(
    "--evaluators", "-e", "evaluator_names",
    multiple=True, default=("exact_match",),
    help="Evaluator names to apply (repeatable). Built-ins: "
         "exact_match, regex_match, semantic_similarity, retrieval, llm_judge, latency.",
)
@click.option("--concurrency", "-c", type=int, default=4, show_default=True)
@click.option(
    "--runs-root", type=click.Path(path_type=Path), default=Path("runs"), show_default=True,
    help="Directory under which run folders are written.",
)
@click.option("--judge-model", default="anthropic:claude-sonnet-4-6", show_default=True)
@click.option("--judge-rubric", default=None, type=str)
@click.option(
    "--report/--no-report", default=True, show_default=True,
    help="Generate markdown + HTML report at the end.",
)
def run(
    dataset_path: Path,
    target_path: Path,
    evaluator_names: tuple[str, ...],
    concurrency: int,
    runs_root: Path,
    judge_model: str,
    judge_rubric: str | None,
    report: bool,
) -> None:
    from evalkit.core.dataset import load_dataset
    from evalkit.core.runner import Runner
    from evalkit.core.target import load_target_config
    from evalkit.evaluators.exact_match import ExactMatchEvaluator
    from evalkit.evaluators.latency import LatencyEvaluator
    from evalkit.evaluators.llm_judge import LLMJudgeEvaluator
    from evalkit.evaluators.regex_match import RegexMatchEvaluator
    from evalkit.evaluators.retrieval import RetrievalEvaluator
    from evalkit.evaluators.semantic_similarity import SemanticSimilarityEvaluator

    builders: dict[str, object] = {
        "exact_match": ExactMatchEvaluator(),
        "regex_match": RegexMatchEvaluator(),
        "semantic_similarity": SemanticSimilarityEvaluator(),
        "retrieval": RetrievalEvaluator(),
        "latency": LatencyEvaluator(),
        "llm_judge": LLMJudgeEvaluator(
            judge_model=judge_model,
            rubric=judge_rubric,
        ),
    }
    evaluators = []
    for name in evaluator_names:
        if name not in builders:
            console.print(f"[red]unknown evaluator:[/red] {name}")
            sys.exit(2)
        evaluators.append(builders[name])

    dataset = load_dataset(dataset_path)
    target = load_target_config(target_path)
    console.print(
        f"[bold]evalkit[/bold] running [cyan]{len(dataset)}[/cyan] cases "
        f"against [cyan]{target.summary().get('name', 'target')}[/cyan] "
        f"with [cyan]{', '.join(e.name for e in evaluators)}[/cyan]"
    )

    runner = Runner(target=target, evaluators=evaluators, concurrency=concurrency, runs_root=runs_root, console=console)
    rep = asyncio.run(runner.run(dataset))

    _print_summary(rep)

    if report:
        from evalkit.reports.html import render_dashboard
        from evalkit.reports.markdown import render_markdown
        run_dir = runs_root / rep.run_id
        render_markdown(rep, run_dir / "report.md")
        render_dashboard(rep, run_dir / "dashboard.html")
        console.print(f"\n[green]wrote[/green] {run_dir / 'report.md'}")
        console.print(f"[green]wrote[/green] {run_dir / 'dashboard.html'}")
    console.print(f"\n[bold green]done[/bold green] run_id=[cyan]{rep.run_id}[/cyan]")


# ---------------------------------------------------------------------------
# evalkit compare
# ---------------------------------------------------------------------------
@cli.command(help="Compare two runs.")
@click.argument("run_id_a")
@click.argument("run_id_b")
@click.option("--runs-root", type=click.Path(path_type=Path), default=Path("runs"), show_default=True)
@click.option("--format", "fmt", type=click.Choice(["markdown", "json", "table"]), default="table")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Write output to this path instead of stdout.")
def compare(run_id_a: str, run_id_b: str, runs_root: Path, fmt: str, out: Path | None) -> None:
    from evalkit.core.compare import compare_runs, format_comparison_markdown, format_comparison_table
    from evalkit.core.storage import load_report

    rep_a = load_report(run_id_a, runs_root)
    rep_b = load_report(run_id_b, runs_root)
    diff = compare_runs(rep_a, rep_b)
    if fmt == "json":
        text = json.dumps(diff.model_dump(mode="json"), indent=2)
    elif fmt == "markdown":
        text = format_comparison_markdown(diff)
    else:
        text = format_comparison_table(diff)
    if out is None:
        # rich.Console handles unicode on Windows where click.echo + cp1252 don't.
        console.print(text, markup=False, highlight=False)
    else:
        out.write_text(text, encoding="utf-8")
        console.print(f"[green]wrote[/green] {out}")


# ---------------------------------------------------------------------------
# evalkit report
# ---------------------------------------------------------------------------
@cli.command(help="Regenerate a report for an existing run.")
@click.argument("run_id")
@click.option("--format", "fmt", type=click.Choice(["markdown", "html", "json"]), default="markdown")
@click.option("--runs-root", type=click.Path(path_type=Path), default=Path("runs"), show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def report(run_id: str, fmt: str, runs_root: Path, out: Path | None) -> None:
    from evalkit.core.storage import load_report, run_path
    from evalkit.reports.html import render_dashboard
    from evalkit.reports.json_export import write_json_report
    from evalkit.reports.markdown import render_markdown

    rep = load_report(run_id, runs_root)
    run_dir = run_path(run_id, runs_root)

    if fmt == "markdown":
        target = out or run_dir / "report.md"
        render_markdown(rep, target)
    elif fmt == "html":
        target = out or run_dir / "dashboard.html"
        render_dashboard(rep, target)
    else:
        target = out or run_dir / "report.json"
        write_json_report(rep, target)
    console.print(f"[green]wrote[/green] {target}")


# ---------------------------------------------------------------------------
# evalkit list-runs
# ---------------------------------------------------------------------------
@cli.command("list-runs", help="Show recent runs.")
@click.option("--runs-root", type=click.Path(path_type=Path), default=Path("runs"), show_default=True)
@click.option("--limit", "-n", type=int, default=20, show_default=True)
def list_runs(runs_root: Path, limit: int) -> None:
    from evalkit.core.storage import list_runs as _list_runs
    from evalkit.core.storage import load_report

    ids = _list_runs(runs_root, limit=limit)
    if not ids:
        console.print("[yellow]no runs found[/yellow]")
        return

    table = Table(title="evalkit runs", show_lines=False)
    table.add_column("run_id", style="cyan")
    table.add_column("when", style="dim")
    table.add_column("dataset")
    table.add_column("target")
    table.add_column("n", justify="right")
    table.add_column("pass%", justify="right", style="green")

    for run_id in ids:
        try:
            rep = load_report(run_id, runs_root)
            table.add_row(
                run_id,
                rep.started_at.isoformat(timespec="seconds"),
                Path(rep.dataset_path).name if rep.dataset_path else "?",
                rep.target_summary.get("name", "?"),
                str(rep.n_cases),
                f"{rep.pass_rate * 100:.1f}",
            )
        except Exception as e:  # noqa: BLE001
            table.add_row(run_id, "[red]bad[/red]", "?", "?", "?", f"[red]{e}[/red]")
    console.print(table)


# ---------------------------------------------------------------------------
# evalkit init
# ---------------------------------------------------------------------------
@cli.command(help="Scaffold a starter dataset.jsonl + target.yaml in the current directory.")
@click.option("--force", is_flag=True, help="Overwrite existing files.")
def init(force: bool) -> None:
    from evalkit.core.scaffold import scaffold_starter
    written = scaffold_starter(Path.cwd(), force=force)
    for path in written:
        console.print(f"[green]created[/green] {path}")
    console.print(
        "\n[bold]next:[/bold] run [cyan]evalkit run dataset.jsonl --target target.yaml[/cyan]"
    )


def _print_summary(rep: object) -> None:
    """Pretty terminal summary of a RunReport."""
    from evalkit.core.result import RunReport
    if not isinstance(rep, RunReport):  # safety
        return
    table = Table(title=f"summary — {rep.run_id}")
    table.add_column("metric")
    table.add_column("value", justify="right")
    table.add_row("cases", str(rep.n_cases))
    table.add_row("passed", f"{rep.n_passed}")
    table.add_row("failed", f"{rep.n_failed}")
    table.add_row("errored", f"{rep.n_errored}")
    table.add_row("pass rate", f"{rep.pass_rate * 100:.1f}%")
    if rep.latency_ms:
        table.add_row("latency p50", f"{rep.latency_ms.get('p50', 0):.0f} ms")
        table.add_row("latency p95", f"{rep.latency_ms.get('p95', 0):.0f} ms")
    console.print(table)

    if rep.aggregate_metrics:
        et = Table(title="evaluators")
        et.add_column("name")
        et.add_column("mean", justify="right")
        et.add_column("pass rate", justify="right")
        et.add_column("n", justify="right")
        for m in rep.aggregate_metrics:
            et.add_row(m.name, f"{m.mean:.3f}", f"{m.pass_rate * 100:.1f}%", str(m.n))
        console.print(et)


if __name__ == "__main__":
    cli()
