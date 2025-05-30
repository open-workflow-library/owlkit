"""
OWLKit - Open Workflow Library Toolkit

A comprehensive toolkit for managing CWL workflows, Docker images,
and Seven Bridges platform integration.
"""

__version__ = "0.1.0"
__author__ = "OWL Team"
__email__ = "hoot@promptable.ai"

from .docker.ghcr import GHCRManager
from .config import ConfigManager

__all__ = ["GHCRManager", "ConfigManager"]