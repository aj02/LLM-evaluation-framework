"""Core models and orchestration for evalkit."""
from evalkit.core.case import TestCase
from evalkit.core.dataset import Dataset, load_dataset
from evalkit.core.result import CaseResult, EvaluatorResult, RunReport
from evalkit.core.runner import Runner
from evalkit.core.target import CallableTarget, HTTPTarget, ShellTarget, Target

__all__ = [
    "CallableTarget",
    "CaseResult",
    "Dataset",
    "EvaluatorResult",
    "HTTPTarget",
    "Runner",
    "RunReport",
    "ShellTarget",
    "Target",
    "TestCase",
    "load_dataset",
]
