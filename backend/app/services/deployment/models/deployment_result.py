"""
Deployment Result Model
Represents the comprehensive outcome of a deployment pipeline execution.
Ensures consistency: whenever deployment_status is FAILED, success is always False.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator


class DeploymentResult(BaseModel):
    """The outcome and metadata resulting from a deployment operation."""

    deployment_id: str = Field(
        default="unassigned",
        description="Unique deployment identifier"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Associated project ID"
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Human-readable project name"
    )
    image_name: Optional[str] = Field(
        default=None,
        description="Generated Docker image tag or name"
    )
    image_id: Optional[str] = Field(
        default=None,
        description="Generated Docker image ID"
    )
    container_id: Optional[str] = Field(
        default=None,
        description="Docker container ID"
    )
    allocated_port: Optional[int] = Field(
        default=None,
        description="Allocated host port assigned to the service"
    )
    deployment_status: str = Field(
        default="PENDING",
        description="Status from DeploymentStatus enum (e.g. RUNNING, FAILED, STOPPED)"
    )
    health_status: str = Field(
        default="pending",
        description="Current health evaluation ('Healthy', 'Failed', 'Timeout', 'pending')"
    )
    public_url: Optional[str] = Field(
        default=None,
        description="Public URL routed through reverse proxy or gateway"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of deployment record creation"
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="Timestamp of last update"
    )
    success: bool = Field(
        default=True,
        description="Whether operation succeeded"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable summary or status description"
    )
    details: Optional[str] = Field(
        default=None,
        description="Detailed diagnostic output or error trace"
    )
    framework: Optional[str] = Field(
        default=None,
        description="Framework of the deployed service"
    )
    entry_point_type: Optional[str] = Field(
        default=None,
        description="The detected entry point type (fastapi, flask, cli_script, etc.)"
    )
    startup_command: Optional[str] = Field(
        default=None,
        description="The selected container startup command"
    )

    @model_validator(mode="after")
    def enforce_status_and_success_consistency(self):
        """
        Enforce strict consistency between deployment_status, health_status, and success:
        Whenever deployment fails, success must be False.
        """
        status_upper = (self.deployment_status or "").upper()
        health_upper = (self.health_status or "").upper()

        if status_upper in ("FAILED",) or health_upper in ("FAILED", "TIMEOUT", "UNHEALTHY"):
            self.success = False
        elif not self.success:
            if status_upper not in ("FAILED", "STOPPED", "REMOVED"):
                self.deployment_status = "FAILED"
        return self

    # Aliases for compatibility
    @property
    def status(self) -> str:
        return self.deployment_status

    @property
    def host_port(self) -> Optional[int]:
        return self.allocated_port

    def __getitem__(self, item: str) -> Any:
        """Allow dictionary-style subscripting for backwards compatibility."""
        if hasattr(self, item):
            return getattr(self, item)
        d = self.model_dump()
        if item in d:
            return d[item]
        raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item) or item in self.model_dump()

    def get(self, item: str, default: Any = None) -> Any:
        """Allow dict-style get method."""
        try:
            return self[item]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Convert result model to dictionary."""
        return self.model_dump()


# Convenience alias for OpenAPI / schema response naming
DeploymentResponse = DeploymentResult
