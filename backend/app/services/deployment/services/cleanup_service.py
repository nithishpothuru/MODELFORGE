"""
Cleanup Service
Handles resource reclamation and rollback:
- Stop containers
- Delete containers
- Delete Docker images
- Delete Nginx configuration
- Release ports
- Update deployment repository
- Support rollback on deployment/update failures
"""

import logging
from typing import Optional, Dict, Any, List

from ..models.deployment_status import DeploymentStatus
from ..core.docker_manager import DockerManager
from ..core.port_manager import PortManager
from ..core.nginx_manager import NginxManager
from ..database.deployment_repository import DeploymentRepository

logger = logging.getLogger(__name__)


class CleanupService:
    """
    Orchestrates teardown, resource cleanup, and failure rollback across Docker,
    Nginx, PortManager, and the deployment database repository.
    """

    def __init__(self,
                 docker_manager: Optional[DockerManager] = None,
                 port_manager: Optional[PortManager] = None,
                 nginx_manager: Optional[NginxManager] = None,
                 repository: Optional[DeploymentRepository] = None):
        self.docker_manager = docker_manager or DockerManager()
        self.port_manager = port_manager or PortManager()
        self.nginx_manager = nginx_manager or NginxManager()
        self.repository = repository or DeploymentRepository()

    def stop_containers(self, deployment_id: str, timeout: int = 5) -> bool:
        """Stop container for the given deployment."""
        container_name = f"modelforge_{deployment_id}"
        return self.docker_manager.stop_container(container_name, timeout=timeout)

    def delete_containers(self, deployment_id: str, force: bool = True) -> bool:
        """Delete container for the given deployment."""
        container_name = f"modelforge_{deployment_id}"
        return self.docker_manager.remove_container(container_name, force=force)

    def delete_images(self, image_name: str, force: bool = True) -> bool:
        """Delete Docker image."""
        return self.docker_manager.remove_image(image_name, force=force)

    def delete_nginx_config(self, deployment_id: str) -> bool:
        """Delete Nginx reverse proxy configuration and reload."""
        return self.nginx_manager.delete_routes(deployment_id)

    def release_ports(self, port: int) -> bool:
        """Release allocated host port in PortManager."""
        return self.port_manager.release_port(port)

    def cleanup_deployment(self,
                           deployment_id: str,
                           remove_image: bool = True,
                           mark_as: str = DeploymentStatus.REMOVED.value) -> Dict[str, Any]:
        """
        Tear down all resources associated with a specific deployment:
        1. Stop container.
        2. Delete container.
        3. Delete Docker image (if remove_image is True).
        4. Delete Nginx routes.
        5. Release allocated host port.
        6. Update repository status to REMOVED or STOPPED.

        Parameters
        ----------
        deployment_id : str
        remove_image : bool
        mark_as : str
            Status to assign in repository ('REMOVED' or 'STOPPED').

        Returns
        -------
        Dict[str, Any]
            Summary of all reclaimed resources.
        """
        container_name = f"modelforge_{deployment_id}"
        image_name = f"modelforge_{deployment_id}".lower()

        record = self.repository.get(deployment_id)
        host_port = record.get("allocated_port") if record else None
        if not host_port and record:
            host_port = record.get("host_port")

        logger.info("Starting cleanup for deployment: %s", deployment_id)

        # 1. Stop container
        c_stopped = self.stop_containers(deployment_id)

        # 2. Delete container
        c_removed = self.delete_containers(deployment_id)

        # 3. Delete image
        img_removed = False
        if remove_image:
            img_removed = self.delete_images(image_name)

        # 4. Delete Nginx routing
        nginx_removed = self.delete_nginx_config(deployment_id)

        # 5. Release allocated port
        port_released = None
        if host_port:
            self.release_ports(host_port)
            port_released = host_port

        # 6. Update repository
        self.repository.update_status(
            deployment_id,
            status=mark_as,
            message=f"Deployment torn down and cleaned up ({mark_as})."
        )
        self.repository.update_health(deployment_id, "removed" if mark_as == DeploymentStatus.REMOVED.value else "stopped")

        return {
            "deployment_id": deployment_id,
            "container_stopped": c_stopped,
            "container_deleted": c_removed,
            "image_deleted": img_removed,
            "nginx_route_deleted": nginx_removed,
            "port_released": port_released,
            "deployment_status": mark_as
        }

    def rollback(self,
                 deployment_id: str,
                 error_message: Optional[str] = None,
                 allocated_port: Optional[int] = None,
                 remove_container: bool = True,
                 remove_image: bool = False,
                 remove_nginx: bool = True) -> Dict[str, Any]:
        """
        Rollback partially created resources when a deployment or update fails.

        Parameters
        ----------
        deployment_id : str
        error_message : Optional[str]
            Reason for rollback.
        allocated_port : Optional[int]
            Port to release if one was allocated during the failed flow.
        remove_container : bool
            Whether to stop and remove container.
        remove_image : bool
            Whether to delete built Docker image.
        remove_nginx : bool
            Whether to delete any created Nginx route.

        Returns
        -------
        Dict[str, Any]
            Summary of rollback actions performed.
        """
        logger.warning("Initiating rollback for deployment %s due to failure: %s", deployment_id, error_message)

        c_stopped = False
        c_removed = False
        img_removed = False
        nginx_removed = False
        port_released = None

        # 1. Stop and delete container
        if remove_container:
            c_stopped = self.stop_containers(deployment_id)
            c_removed = self.delete_containers(deployment_id)

        # 2. Delete image
        if remove_image:
            image_name = f"modelforge_{deployment_id}".lower()
            img_removed = self.delete_images(image_name)

        # 3. Delete Nginx config
        if remove_nginx:
            nginx_removed = self.delete_nginx_config(deployment_id)

        # 4. Release port
        target_port = allocated_port
        if not target_port:
            record = self.repository.get(deployment_id)
            if record:
                target_port = record.get("allocated_port") or record.get("host_port")

        if target_port:
            self.release_ports(target_port)
            port_released = target_port

        # 5. Update deployment repository
        msg = f"Rolled back due to error: {error_message}" if error_message else "Deployment rolled back."
        self.repository.update_status(
            deployment_id,
            status=DeploymentStatus.FAILED.value,
            message=msg
        )
        self.repository.update_health(deployment_id, "failed")

        return {
            "deployment_id": deployment_id,
            "rolled_back": True,
            "container_stopped": c_stopped,
            "container_deleted": c_removed,
            "image_deleted": img_removed,
            "nginx_route_deleted": nginx_removed,
            "port_released": port_released,
            "error_message": error_message,
            "deployment_status": DeploymentStatus.FAILED.value
        }

    def cleanup_all(self, prefix: str = "modelforge_") -> Dict[str, Any]:
        """
        Batch cleanup of all deployments.
        """
        deployments = self.repository.list_all()
        cleaned: List[Dict[str, Any]] = []

        for dep in deployments:
            dep_id = dep.get("deployment_id")
            if dep_id:
                res = self.cleanup_deployment(dep_id, remove_image=True)
                cleaned.append(res)

        return {
            "count": len(cleaned),
            "cleaned": cleaned
        }
