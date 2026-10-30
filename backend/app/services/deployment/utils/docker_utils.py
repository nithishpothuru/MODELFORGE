"""
Docker Utilities
Helper functions for Docker client initialization, status mapping, and log formatting.
"""

from typing import Optional, Dict, Any


def format_docker_labels(labels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Format and validate Docker labels."""
    return labels or {}


def parse_container_logs(raw_logs: bytes) -> str:
    """Decode raw Docker container logs."""
    return raw_logs.decode("utf-8", errors="replace")
