"""
Deployment Schemas
Exports the request and response schemas for ModelForge deployment endpoints.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_result import DeploymentResult, DeploymentResponse
from app.services.deployment.models.deployment_artifact import DeploymentArtifact

class DeployRequest(BaseModel):
    project_id: Optional[str] = Field(
        default=None,
        description="Validated project ID from validation backend (Recommended)"
    )
    validation_id: Optional[str] = Field(
        default=None,
        description="Validation report ID (alias to project_id)"
    )
    artifact_path: Optional[str] = Field(
        default=None,
        description="Optional manual artifact or project folder path"
    )
    artifact: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional direct validation artifact payload dictionary"
    )
    port: Optional[int] = Field(
        default=None,
        description="Optional host port allocation override"
    )
    env_vars: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Optional environment variables to inject into container"
    )
    entry_point_type: Optional[str] = Field(
        default=None,
        description="Detected or specified entry point type: 'fastapi', 'flask', 'cli_script', etc."
    )
    startup_command: Optional[str] = Field(
        default=None,
        description="Explicit or computed container startup command"
    )

__all__ = [
    "DeployRequest",
    "DeploymentRequest",
    "DeploymentResult",
    "DeploymentResponse",
    "DeploymentArtifact",
]

