"""
Container Service
High-level service managing container lifecycle, execution, logging, and inspection.
"""

import logging
from typing import Optional, Dict, Any, List

from ..core.docker_manager import DockerManager
from ..models.container_info import ContainerInfo

logger = logging.getLogger(__name__)


class ContainerService:
    """Manages container runtime lifecycle and status queries for deployments."""

    def __init__(self, docker_mgr: Optional[DockerManager] = None):
        self.docker_mgr = docker_mgr or DockerManager()

    def start_container(self,
                        deployment_id: str,
                        image_name: str,
                        host_port: Optional[int] = None,
                        target_port: int = 8000,
                        env_vars: Optional[Dict[str, str]] = None,
                        labels: Optional[Dict[str, str]] = None,
                        memory_limit: Optional[str] = None,
                        cpu_limit: Optional[float] = None) -> Dict[str, Any]:
        """
        Start a new container for a deployment.
        """
        container_name = f"modelforge_{deployment_id}"
        all_labels = {
            "modelforge.deployment_id": deployment_id,
            **(labels or {})
        }

        return self.docker_mgr.run_container(
            image_name=image_name,
            container_name=container_name,
            host_port=host_port,
            target_port=target_port,
            env_vars=env_vars,
            labels=all_labels,
            memory_limit=memory_limit,
            cpu_limit=cpu_limit
        )

    def stop_container(self, deployment_id: str) -> bool:
        """Stop a running container by deployment ID."""
        container_name = f"modelforge_{deployment_id}"
        return self.docker_mgr.stop_container(container_name)

    def restart_container(self, deployment_id: str) -> bool:
        """Restart a container by deployment ID."""
        container_name = f"modelforge_{deployment_id}"
        return self.docker_mgr.restart_container(container_name)

    def delete_container(self, deployment_id: str, force: bool = True) -> bool:
        """Remove a container by deployment ID."""
        container_name = f"modelforge_{deployment_id}"
        return self.docker_mgr.remove_container(container_name, force=force)

    def get_container_info(self, deployment_id: str) -> Optional[ContainerInfo]:
        """Inspect container runtime details and return ContainerInfo model."""
        container_name = f"modelforge_{deployment_id}"
        inspect_data = self.docker_mgr.inspect_container(container_name)
        if not inspect_data:
            return None

        ports_raw = inspect_data.get("ports", {})
        host_port = None
        for port_key, mappings in ports_raw.items():
            if mappings and len(mappings) > 0:
                try:
                    host_port = int(mappings[0].get("HostPort"))
                    break
                except (ValueError, TypeError):
                    pass

        return ContainerInfo(
            container_id=inspect_data.get("id", ""),
            container_name=inspect_data.get("name", container_name).lstrip("/"),
            image_name=inspect_data.get("state", {}).get("Image", ""),
            status=inspect_data.get("status", "unknown"),
            host_port=host_port,
            url=f"http://localhost:{host_port}" if host_port else None,
            created_at=inspect_data.get("created"),
            labels=inspect_data.get("labels", {}),
            ports=ports_raw
        )

    def get_logs(self, deployment_id: str, tail: int = 100) -> str:
        """Retrieve stdout/stderr logs for a deployment's container."""
        container_name = f"modelforge_{deployment_id}"
        return self.docker_mgr.container_logs(container_name, tail=tail)

    def list_containers(self, prefix: str = "modelforge_") -> List[Dict[str, Any]]:
        """List all active containers created by ModelForge."""
        return self.docker_mgr.list_containers(all=True, prefix=prefix)
