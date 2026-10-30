"""
File Utilities
Helper functions for managing files, paths, and temp directories.
"""

from pathlib import Path
from typing import Union
import shutil


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating parent directories if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def remove_directory(path: Union[str, Path]) -> None:
    """Safely remove a directory and its contents."""
    p = Path(path)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
