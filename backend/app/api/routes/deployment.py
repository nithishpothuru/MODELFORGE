import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.services.deployment.services.deployment_service import DeploymentService
from app.services.deployment.models.deployment_result import DeploymentResult

logger = logging.getLogger("deployment.route")

router = APIRouter(
    prefix="/deploy",
    tags=["Deployment"],
)

deployment_service = DeploymentService()


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
        description="Optional manual artifact or project folder path for backwards compatibility"
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


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeploymentResult)
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=DeploymentResult)
async def deploy(request: DeployRequest, response: Response):
    """
    Deploy a validated ML project using its project_id or validation_id.
    Automatically resolves artifacts produced by the validation pipeline without manual folder paths.
    """
    result = await run_in_threadpool(deployment_service.deploy, request)
    if not result.success or result.deployment_status == "FAILED":
        response.status_code = status.HTTP_400_BAD_REQUEST
    return result


@router.get("/{deployment_id}", response_model=DeploymentResult)
async def deployment_status(deployment_id: str, response: Response):
    """
    Get real-time deployment status, health evaluation, and public URL.
    """
    result = await run_in_threadpool(deployment_service.status, deployment_id)
    if not result.success:
        response.status_code = status.HTTP_404_NOT_FOUND if "not found" in (result.message or "").lower() else status.HTTP_400_BAD_REQUEST
    return result


@router.post("/{deployment_id}/restart", response_model=DeploymentResult)
async def restart_deployment(deployment_id: str, response: Response):
    """
    Restart deployment container and verify health.
    """
    result = deployment_service.restart(deployment_id)
    if not result.success:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return result


@router.post("/{deployment_id}/stop", response_model=DeploymentResult)
async def stop_deployment(deployment_id: str, response: Response):
    """
    Stop deployment container.
    """
    result = deployment_service.stop(deployment_id)
    if not result.success:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return result


@router.delete("/{deployment_id}", response_model=DeploymentResult)
async def delete_deployment(deployment_id: str, response: Response):
    """
    Completely delete deployment and reclaim all resources (container, image, port, routes).
    """
    result = deployment_service.delete(deployment_id)
    if not result.success:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return result


@router.get("", response_model=List[DeploymentResult])
@router.get("/", response_model=List[DeploymentResult])
async def list_deployments(status: Optional[str] = None):
    """
    List all deployments, optionally filtered by status.
    """
    return await run_in_threadpool(deployment_service.list_deployments, status)
