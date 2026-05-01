"""evalkit — a small, opinionated LLM evaluation framework."""
from __future__ import annotations

__version__ = "0.1.0"

from evalkit.core.case import TestCase
from evalkit.core.dataset import Dataset, load_dataset
from evalkit.core.result import CaseResult, EvaluatorResult, RunReport
from evalkit.core.runner import Runner
from evalkit.core.target import CallableTarget, HTTPTarget, ShellTarget, Target
from evalkit.evaluators.base import Evaluator

__all__ = [
    "__version__",
    "CallableTarget",
    "CaseResult",
    "Dataset",
    "Evaluator",
    "EvaluatorResult",
    "HTTPTarget",
    "Runner",
    "RunReport",
    "ShellTarget",
    "Target",
    "TestCase",
    "load_dataset",
]
