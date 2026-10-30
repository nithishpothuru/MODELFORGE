"""
Deployment Service
Primary service facade exposed to external REST APIs.
Encapsulates all container lifecycle and orchestration details, never exposing Docker implementation.
All public operations return structured DeploymentResult models with consistent success flags.

Exposes:
- deploy()
- status()
- restart()
- stop()
- delete()
- list_deployments()
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

from ..models.deployment_request import DeploymentRequest
from ..models.deployment_artifact import DeploymentArtifact
from ..models.deployment_result import DeploymentResult
from ..models.deployment_status import DeploymentStatus
from ..core.deployment_manager import DeploymentManager
from ..core.artifact_reader import ArtifactReader
from ..core.docker_manager import DockerManager
from ..core.health_manager import HealthManager, HealthStatus
from ..database.deployment_repository import DeploymentRepository
from .monitoring_service import MonitoringService
from .cleanup_service import CleanupService

logger = logging.getLogger("deployment.service")


class DeploymentService:
    """
    Public deployment facade providing deploy, status, restart, stop, and delete APIs
    for REST controllers. Completely abstracts Docker internals and returns DeploymentResult.
    """

    def __init__(self,
                 deployment_manager: Optional[DeploymentManager] = None,
                 artifact_reader: Optional[ArtifactReader] = None,
                 monitoring_service: Optional[MonitoringService] = None,
                 cleanup_service: Optional[CleanupService] = None,
                 repository: Optional[DeploymentRepository] = None,
                 docker_manager: Optional[DockerManager] = None,
                 health_manager: Optional[HealthManager] = None):
        self.artifact_reader = artifact_reader or ArtifactReader()
        self.deployment_manager = deployment_manager or DeploymentManager(artifact_reader=self.artifact_reader)
        self.repository = repository or DeploymentRepository()
        self.docker_manager = docker_manager or DockerManager()
        self.health_manager = health_manager or HealthManager()
        self.monitoring_service = monitoring_service or MonitoringService(
            docker_manager=self.docker_manager,
            health_manager=self.health_manager,
            repository=self.repository
        )
        self.cleanup_service = cleanup_service or CleanupService(
            docker_manager=self.docker_manager,
            repository=self.repository
        )

    def deploy(self, artifact_or_request: Union[str, Path, Dict[str, Any], DeploymentRequest, DeploymentArtifact, Any]) -> DeploymentResult:
        """
        Deploy a validated ML project from project_id, validation_id, artifact path, or DeploymentRequest.
        Automatically locates validated artifacts produced by the validation backend.

        Parameters
        ----------
        artifact_or_request : Union[str, Path, Dict[str, Any], DeploymentRequest, DeploymentArtifact]

        Returns
        -------
        DeploymentResult
            Structured result containing deployment state, allocated port, and public URL.
        """
        logger.info("[Deployment] Executing deploy via DeploymentService...")

        try:
            # 1. If already a DeploymentArtifact, pass directly to DeploymentManager
            if isinstance(artifact_or_request, DeploymentArtifact):
                return self.deployment_manager.deploy(artifact_or_request)

            # 2. If already a DeploymentRequest with a valid working directory, delegate directly
            if isinstance(artifact_or_request, DeploymentRequest):
                if artifact_or_request.working_directory and Path(artifact_or_request.working_directory).exists():
                    return self.deployment_manager.deploy(artifact_or_request)

            # 3. Extract identifiers if an object with attributes was passed
            project_id = getattr(artifact_or_request, "project_id", None)
            validation_id = getattr(artifact_or_request, "validation_id", None)
            artifact_path = getattr(artifact_or_request, "artifact_path", None)
            artifact_dict = getattr(artifact_or_request, "artifact", None)
            working_dir = getattr(artifact_or_request, "working_directory", None) or getattr(artifact_or_request, "workspace_path", None)

            # If dict was passed directly
            if isinstance(artifact_or_request, dict):
                project_id = project_id or artifact_or_request.get("project_id")
                validation_id = validation_id or artifact_or_request.get("validation_id")
                artifact_path = artifact_path or artifact_or_request.get("artifact_path")
                artifact_dict = artifact_dict or artifact_or_request.get("artifact") or artifact_or_request
                working_dir = working_dir or artifact_or_request.get("working_directory") or artifact_or_request.get("workspace_path")

            # If string or Path was passed directly
            elif isinstance(artifact_or_request, (str, Path)):
                p = Path(str(artifact_or_request))
                if p.exists():
                    artifact_path = p
                else:
                    project_id = str(artifact_or_request)

            # 4. Validate presence of some identifier
            if not project_id and not validation_id and not artifact_path and not artifact_dict and not working_dir:
                return DeploymentResult(
                    deployment_id="unassigned",
                    deployment_status=DeploymentStatus.FAILED.value,
                    health_status=HealthStatus.FAILED,
                    success=False,
                    message="Missing project identifier. Please provide 'project_id' or 'validation_id'.",
                    details="Neither project_id, validation_id, artifact_path, nor artifact payload was supplied."
                )

            # Let ArtifactReader resolve the project root and metadata
            artifact = self.artifact_reader.resolve_artifact(
                project_id=project_id,
                validation_id=validation_id,
                artifact_path=artifact_path,
                artifact_dict=artifact_dict if isinstance(artifact_dict, dict) else None
            )

            # Apply explicit overrides from request if provided
            req_ep_type = getattr(artifact_or_request, "entry_point_type", None) or (artifact_or_request.get("entry_point_type") if isinstance(artifact_or_request, dict) else None)
            if req_ep_type:
                artifact.entry_point_type = req_ep_type
            req_startup_cmd = getattr(artifact_or_request, "startup_command", None) or (artifact_or_request.get("startup_command") if isinstance(artifact_or_request, dict) else None)
            if req_startup_cmd:
                artifact.startup_command = req_startup_cmd

            # Forward to DeploymentManager
            return self.deployment_manager.deploy(artifact)

        except Exception as exc:
            logger.error("[Deployment] Deployment execution failed: %s", exc, exc_info=True)
            return DeploymentResult(
                deployment_id="unassigned",
                project_id=getattr(artifact_or_request, "project_id", None) if not isinstance(artifact_or_request, dict) else artifact_or_request.get("project_id"),
                deployment_status=DeploymentStatus.FAILED.value,
                health_status=HealthStatus.FAILED,
                success=False,
                message=f"Deployment failed: {exc}",
                details=str(exc)
            )

    def status(self, deployment_id: str) -> DeploymentResult:
        """
        Fetch real-time deployment status, health evaluation, and routing metadata.
        """
        record = self.repository.get(deployment_id)
        if not record:
            return DeploymentResult(
                deployment_id=deployment_id,
                deployment_status=DeploymentStatus.FAILED.value,
                health_status=HealthStatus.FAILED,
                success=False,
                message=f"Deployment with ID '{deployment_id}' not found."
            )

        # Live health check if currently marked active
        current_status = record.get("deployment_status")
        if current_status in (DeploymentStatus.RUNNING.value, DeploymentStatus.CONTAINER_RUNNING.value):
            live_mon = self.monitoring_service.get_deployment_health(deployment_id)
            if live_mon.get("found"):
                record["health_status"] = live_mon.get("health_status", record.get("health_status"))
                if not live_mon.get("container_running"):
                    record["deployment_status"] = DeploymentStatus.STOPPED.value

        is_failed = record.get("deployment_status") in (DeploymentStatus.FAILED.value, DeploymentStatus.REMOVED.value)
        return DeploymentResult(
            deployment_id=record["deployment_id"],
            project_id=record.get("project_id"),
            project_name=record.get("project_name"),
            framework=record.get("framework"),
            image_name=record.get("image_name"),
            image_id=record.get("image_id"),
            container_id=record.get("container_id"),
            allocated_port=record.get("allocated_port"),
            deployment_status=record.get("deployment_status", DeploymentStatus.PENDING.value),
            health_status=record.get("health_status", "pending"),
            public_url=record.get("public_url"),
            message=record.get("message"),
            details=record.get("details"),
            created_at=record.get("created_at", ""),
            updated_at=record.get("updated_at"),
            success=not is_failed
        )

    def restart(self, deployment_id: str) -> DeploymentResult:
        """
        Restart a deployment container, verify its health, and update repository.
        """
        record = self.repository.get(deployment_id)
        if not record:
            return DeploymentResult(
                deployment_id=deployment_id,
                deployment_status=DeploymentStatus.FAILED.value,
                health_status=HealthStatus.FAILED,
                success=False,
                message=f"Deployment with ID '{deployment_id}' not found."
            )

        container_name = f"modelforge_{deployment_id}"
        restarted = self.docker_manager.restart_container(container_name)
        if not restarted:
            err_msg = f"Failed to restart container '{container_name}'."
            return DeploymentResult(
                deployment_id=deployment_id,
                project_id=record.get("project_id"),
                image_name=record.get("image_name"),
                container_id=record.get("container_id"),
                allocated_port=record.get("allocated_port"),
                deployment_status=DeploymentStatus.FAILED.value,
                health_status=HealthStatus.FAILED,
                success=False,
                message=err_msg
            )

        # Check health following restart
        framework = record.get("framework") or "fastapi"
        port = record.get("allocated_port")
        url = f"http://localhost:{port}" if port else None

        health_res = self.health_manager.wait_for_ready(
            framework=framework,
            url=url,
            retries=5,
            delay=0.1,
            container_inspect_fn=lambda: self.docker_manager.inspect_container(container_name)
        )

        health_eval = health_res.get("health_status", HealthStatus.FAILED)
        new_status = DeploymentStatus.RUNNING.value if health_eval == HealthStatus.HEALTHY else DeploymentStatus.FAILED.value
        msg = f"Restart completed: {health_eval}."

        self.repository.update_status(deployment_id, new_status, message=msg)
        self.repository.update_health(deployment_id, health_eval)

        logger.info("Restarted deployment %s with health %s and status %s", deployment_id, health_eval, new_status)
        return DeploymentResult(
            deployment_id=deployment_id,
            project_id=record.get("project_id"),
            project_name=record.get("project_name"),
            framework=framework,
            image_name=record.get("image_name"),
            container_id=record.get("container_id"),
            allocated_port=port,
            deployment_status=new_status,
            health_status=health_eval,
            public_url=record.get("public_url"),
            message=msg,
            success=(new_status == DeploymentStatus.RUNNING.value)
        )

    def stop(self, deployment_id: str) -> DeploymentResult:
        """
        Stop a running deployment container and update its status to STOPPED.
        """
        record = self.repository.get(deployment_id)
        if not record:
            return DeploymentResult(
                deployment_id=deployment_id,
                deployment_status=DeploymentStatus.FAILED.value,
                health_status=HealthStatus.FAILED,
                success=False,
                message=f"Deployment with ID '{deployment_id}' not found."
            )

        container_name = f"modelforge_{deployment_id}"
        stopped = self.docker_manager.stop_container(container_name)

        self.repository.update_status(
            deployment_id=deployment_id,
            status=DeploymentStatus.STOPPED.value,
            message="Deployment stopped by user request."
        )
        self.repository.update_health(deployment_id, "stopped")

        logger.info("Stopped deployment %s (container stopped: %s)", deployment_id, stopped)
        return DeploymentResult(
            deployment_id=deployment_id,
            project_id=record.get("project_id"),
            project_name=record.get("project_name"),
            framework=record.get("framework"),
            image_name=record.get("image_name"),
            container_id=record.get("container_id"),
            allocated_port=record.get("allocated_port"),
            deployment_status=DeploymentStatus.STOPPED.value,
            health_status="stopped",
            public_url=record.get("public_url"),
            message="Deployment container stopped successfully.",
            success=stopped
        )

    def delete(self, deployment_id: str) -> DeploymentResult:
        """
        Completely tear down deployment: stop and remove container, delete image,
        remove Nginx routing, release port, and mark REMOVED in repository.
        """
        record = self.repository.get(deployment_id)
        if not record:
            return DeploymentResult(
                deployment_id=deployment_id,
                deployment_status=DeploymentStatus.FAILED.value,
                health_status=HealthStatus.FAILED,
                success=False,
                message=f"Deployment with ID '{deployment_id}' not found."
            )

        cleanup_res = self.cleanup_service.cleanup_deployment(
            deployment_id=deployment_id,
            remove_image=True,
            mark_as=DeploymentStatus.REMOVED.value
        )

        logger.info("Deleted deployment %s: %s", deployment_id, cleanup_res)
        return DeploymentResult(
            deployment_id=deployment_id,
            project_id=record.get("project_id"),
            project_name=record.get("project_name"),
            framework=record.get("framework"),
            image_name=record.get("image_name"),
            container_id=record.get("container_id"),
            allocated_port=record.get("allocated_port"),
            deployment_status=DeploymentStatus.REMOVED.value,
            health_status="removed",
            public_url=None,
            message="Deployment deleted and resources cleaned up successfully.",
            details=str(cleanup_res),
            success=True
        )

    def list_deployments(self, status: Optional[str] = None) -> List[DeploymentResult]:
        """
        List all deployments, optionally filtered by status.
        """
        records = self.repository.list_all(status=status)
        results = []
        for r in records:
            is_failed = r.get("deployment_status") in (DeploymentStatus.FAILED.value, DeploymentStatus.REMOVED.value)
            results.append(DeploymentResult(
                deployment_id=r["deployment_id"],
                project_id=r.get("project_id"),
                project_name=r.get("project_name"),
                framework=r.get("framework"),
                image_name=r.get("image_name"),
                image_id=r.get("image_id"),
                container_id=r.get("container_id"),
                allocated_port=r.get("allocated_port"),
                deployment_status=r.get("deployment_status", DeploymentStatus.PENDING.value),
                health_status=r.get("health_status", "pending"),
                public_url=r.get("public_url"),
                message=r.get("message"),
                details=r.get("details"),
                created_at=r.get("created_at", ""),
                updated_at=r.get("updated_at"),
                success=not is_failed
            ))
        return results
