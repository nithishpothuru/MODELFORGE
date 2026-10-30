"""
Deployment Request Model
Represents the input payload for triggering a new deployment.
Supports project_id, validation_id, artifact_path, and direct artifact dictionary.
"""

from typing import Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator


class DeploymentRequest(BaseModel):
    """Specification of a deployment to be built, orchestrated, and run."""

    project_id: Optional[str] = Field(
        default=None,
        description="Unique identifier of the validated project from validation backend"
    )
    validation_id: Optional[str] = Field(
        default=None,
        description="Validation report ID (alias to project_id)"
    )
    artifact_path: Optional[str] = Field(
        default=None,
        description="Optional manual path to artifact or project directory for backwards compatibility"
    )
    artifact: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Direct validation artifact dictionary"
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Human-readable project or model name"
    )
    framework: str = Field(
        default="fastapi",
        description="Target framework: 'fastapi', 'flask', 'streamlit', 'cli', etc."
    )
    python_version: str = Field(
        default="3.11",
        description="Python runtime version, e.g. '3.10', '3.11'"
    )
    entry_point: str = Field(
        default="main.py",
        description="Main execution script or ASGI/WSGI entry point"
    )
    entry_point_type: Optional[str] = Field(
        default=None,
        description="Detected entry point type: 'fastapi', 'flask', 'cli_script', etc."
    )
    startup_command: Optional[str] = Field(
        default=None,
        description="Explicit or computed container startup command"
    )
    requirements_file: str = Field(
        default="requirements.txt",
        description="Path or filename of dependency specification"
    )
    working_directory: Optional[str] = Field(
        default=None,
        description="Absolute or relative path to the project workspace directory"
    )
    deployment_ready: bool = Field(
        default=True,
        description="Flag indicating if the artifact is validated and ready for deployment"
    )
    deployment_id: str = Field(
        default_factory=lambda: uuid4().hex[:8],
        description="Unique identifier for this deployment run"
    )

    # Runtime and infrastructure settings
    target_port: int = Field(
        default=8000,
        description="Internal container port the application listens on"
    )
    host_port: Optional[int] = Field(
        default=None,
        description="Host port to bind. If None, dynamically allocated."
    )
    port: Optional[int] = Field(
        default=None,
        description="Alias for host_port"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to pass into the container"
    )
    memory_limit: Optional[str] = Field(
        default=None,
        description="Memory limit for container, e.g. '512m' or '1g'"
    )
    cpu_limit: Optional[float] = Field(
        default=None,
        description="CPU limit fraction (e.g. 1.0 = 1 CPU core)"
    )
    health_endpoint: str = Field(
        default="/health",
        description="HTTP path for health checks"
    )
    health_retries: int = Field(
        default=10,
        description="Number of retry attempts for health verification"
    )
    health_delay: float = Field(
        default=2.0,
        description="Seconds to wait between health verification attempts"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom Docker labels to attach to container and image"
    )
    enable_nginx: bool = Field(
        default=True,
        description="Whether to generate and configure Nginx reverse proxy routing"
    )
    domain_name: Optional[str] = Field(
        default=None,
        description="Optional custom domain or subdomain for reverse proxy routing"
    )

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        """Allow workspace_path as alias for working_directory, validation_id for project_id, port for host_port."""
        if isinstance(data, dict):
            # Port aliases
            if "port" in data and ("host_port" not in data or data["host_port"] is None):
                data["host_port"] = data["port"]
            elif "host_port" in data and ("port" not in data or data["port"] is None):
                data["port"] = data["host_port"]

            # Working directory aliases
            if "workspace_path" in data and "working_directory" not in data:
                data["working_directory"] = data["workspace_path"]
            elif "working_directory" in data and "workspace_path" not in data:
                data["workspace_path"] = data["working_directory"]

            # Project / validation id alias
            if not data.get("project_id") and data.get("validation_id"):
                data["project_id"] = data["validation_id"]
            elif not data.get("project_id") and data.get("id"):
                data["project_id"] = data["id"]
        return data

    @property
    def workspace_path(self) -> Optional[str]:
        """Convenience accessor for working directory."""
        return self.working_directory
