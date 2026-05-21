"""LangGraph-based PR review orchestration subpackage.

This package provides the LangGraph pipeline for reviewing pull requests,
including state schema, graph nodes, graph builder, and runner.

The package is activated when the user passes ``--engine langchain``
(or ``--use-langchain``) to ``agdt-initiate-pull-request-review-workflow``.
"""

from .preflight import validate_langchain_dependencies
from .runner import run_langchain_review

__all__ = [
    "run_langchain_review",
    "validate_langchain_dependencies",
]
