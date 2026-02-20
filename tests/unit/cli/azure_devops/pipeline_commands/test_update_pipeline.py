"""
Tests for Azure DevOps pipeline commands (list_pipelines, get_pipeline_id, create_pipeline, update_pipeline).
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops




