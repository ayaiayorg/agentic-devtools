"""Context retrieval layer for AI agent invocations.

Aggregates project metadata, issue details, relevant code files, recent
Git changes, test coverage gaps, and documentation into a structured
:class:`AgentContext` object.
"""

from .models import AgentContext
from .nodes import retrieve_context_node
from .retriever import IssueContextRetriever

__all__ = ["AgentContext", "IssueContextRetriever", "retrieve_context_node"]
