"""
Deployment Artifact Model
Represents the normalized, validated project package produced by the CI validation pipeline
and consumed directly by the Deployment Backend.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeploymentArtifact(BaseModel):
    """
    Validated artifact specification consumed by DeploymentManager.
    Guarantees normalized project paths, resolved dependencies, detected entry point,
    and entry point type.
    """

    project_id: str = Field(
        ...,
        description="Unique identifier of the project"
    )
    project_name: str = Field(
        default="ModelForge Project",
        description="Human-readable project or model name"
    )
    project_root: Path = Field(
        ...,
        description="Normalized absolute path to the real project root directory"
    )
    entry_point: str = Field(
        default="main.py",
        description="Relative entry point file (e.g. 'main.py', 'predict.py', 'app.py') relative to project_root"
    )
    entry_point_path: Optional[Path] = Field(
        default=None,
        description="Absolute path to the resolved entry point script"
    )
    entry_point_type: Optional[str] = Field(
        default="fastapi",
        description="Detected entry point type: 'fastapi', 'flask', 'cli_script', 'streamlit', etc."
    )
    startup_command: Optional[str] = Field(
        default=None,
        description="Container startup command selected based on entry_point_type"
    )
    framework: str = Field(
        default="fastapi",
        description="Target framework: 'fastapi', 'flask', 'streamlit', 'cli', etc."
    )
    python_version: str = Field(
        default="3.11",
        description="Python runtime version, e.g. '3.10', '3.11'"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Resolved or declared package requirements"
    )
    requirements_file: str = Field(
        default="requirements.txt",
        description="Filename of the requirements file within project_root ('requirements-resolved.txt' or 'requirements.txt')"
    )
    has_dockerfile: bool = Field(
        default=False,
        description="Whether a Dockerfile exists within project_root"
    )
    dockerfile_path: Optional[Path] = Field(
        default=None,
        description="Path to existing Dockerfile if present"
    )
    validation_report: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validation report metadata from the validation backend"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional project metadata"
    )

    class Config:
        arbitrary_types_allowed = True
