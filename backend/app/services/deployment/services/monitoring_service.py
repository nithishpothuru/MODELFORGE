"""
Monitoring Service
Monitors active deployments, detects unhealthy containers, triggers automated restarts,
persists health and lifecycle updates in DeploymentRepository, generates deployment metrics,
and provides future-ready scaling hooks and concurrency.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from ..models.deployment_status import DeploymentStatus
from ..core.docker_manager import DockerManager
from ..core.health_manager import HealthManager, HealthStatus
from ..database.deployment_repository import DeploymentRepository

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Monitors deployment health and container status, detects unhealthy containers,
    triggers automated restarts for failed instances, updates the deployment repository,
    generates system and container metrics, and supports future scaling.
    """

    def __init__(self,
                 docker_manager: Optional[DockerManager] = None,
                 health_manager: Optional[HealthManager] = None,
                 repository: Optional[DeploymentRepository] = None,
                 max_workers: int = 5,
                 max_restart_attempts: int = 3):
        self.docker_manager = docker_manager or DockerManager()
        self.health_manager = health_manager or HealthManager()
        self.repository = repository or DeploymentRepository()
        self.max_workers = max_workers
        self.max_restart_attempts = max_restart_attempts
        # In-memory tracking of restart counts per deployment
        self._restart_counts: Dict[str, int] = {}
        # In-memory replica mapping for future scaling
        self._replica_state: Dict[str, int] = {}

    def get_deployment_health(self, deployment_id: str) -> Dict[str, Any]:
        """
        Check immediate container execution state and health responsiveness.

        Parameters
        ----------
        deployment_id : str

        Returns
        -------
        Dict[str, Any]
            Health evaluation details including container_status and health_status.
        """
        record = self.repository.get(deployment_id)
        if not record:
            return {
                "deployment_id": deployment_id,
                "found": False,
                "error": f"Deployment '{deployment_id}' not found."
            }

        container_name = f"modelforge_{deployment_id}"
        inspect_data = self.docker_manager.inspect_container(container_name)

        if not inspect_data:
            return {
                "deployment_id": deployment_id,
                "found": True,
                "container_running": False,
                "health_status": HealthStatus.FAILED,
                "message": "Container not found on Docker engine."
            }

        framework = record.get("framework") or "fastapi"
        port = record.get("allocated_port")
        url = f"http://localhost:{port}" if port else None

        health_res = self.health_manager.wait_for_ready(
            framework=framework,
            url=url,
            retries=1,
            delay=0.05,
            container_inspect_fn=lambda: inspect_data
        )

        health_eval = health_res.get("health_status", HealthStatus.FAILED)

        return {
            "deployment_id": deployment_id,
            "project_id": record.get("project_id"),
            "found": True,
            "container_status": inspect_data.get("status"),
            "container_running": inspect_data.get("running", False),
            "health_status": health_eval,
            "message": health_res.get("message")
        }

    def detect_unhealthy_containers(self) -> List[Dict[str, Any]]:
        """
        Scan all active deployments and detect which ones are failing health or exited.

        Returns
        -------
        List[Dict[str, Any]]
            List of unhealthy deployment diagnostics.
        """
        active_deployments = self.repository.list_all()
        unhealthy = []

        for record in active_deployments:
            dep_id = record.get("deployment_id")
            current_status = record.get("deployment_status")

            # Check deployments expected to be running
            if current_status in (
                DeploymentStatus.RUNNING.value,
                DeploymentStatus.CONTAINER_RUNNING.value,
                DeploymentStatus.HEALTH_CHECKING.value
            ):
                health = self.get_deployment_health(dep_id)
                is_running = health.get("container_running", False)
                h_status = health.get("health_status")

                if not is_running or h_status in (HealthStatus.FAILED, HealthStatus.TIMEOUT, HealthStatus.UNHEALTHY):
                    unhealthy.append({
                        "deployment_id": dep_id,
                        "project_id": record.get("project_id"),
                        "container_status": health.get("container_status"),
                        "health_status": h_status,
                        "container_running": is_running,
                        "message": health.get("message")
                    })

        return unhealthy

    def restart_failed_containers(self, unhealthy_list: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Restart detected failed containers, respecting max restart attempts,
        and update repository status accordingly.

        Returns
        -------
        List[Dict[str, Any]]
            Summary of restart actions per deployment.
        """
        targets = unhealthy_list if unhealthy_list is not None else self.detect_unhealthy_containers()
        results = []

        for item in targets:
            dep_id = item["deployment_id"]
            current_attempts = self._restart_counts.get(dep_id, 0)
            container_name = f"modelforge_{dep_id}"

            if current_attempts >= self.max_restart_attempts:
                msg = f"Max restart attempts ({self.max_restart_attempts}) reached for {dep_id}."
                logger.error(msg)
                self.repository.update_status(dep_id, DeploymentStatus.FAILED.value, message=msg)
                self.repository.update_health(dep_id, HealthStatus.FAILED)
                results.append({
                    "deployment_id": dep_id,
                    "restarted": False,
                    "error": msg,
                    "attempts": current_attempts
                })
                continue

            logger.warning("Attempting automated restart for failed container: %s (attempt %d/%d)",
                           dep_id, current_attempts + 1, self.max_restart_attempts)

            restart_success = self.docker_manager.restart_container(container_name)
            self._restart_counts[dep_id] = current_attempts + 1

            if restart_success:
                # Re-verify health
                post_health = self.get_deployment_health(dep_id)
                post_status = post_health.get("health_status")
                new_status = DeploymentStatus.RUNNING.value if post_status == HealthStatus.HEALTHY else DeploymentStatus.FAILED.value

                self.repository.update_status(dep_id, new_status, message=f"Auto-restart executed: {post_status}")
                self.repository.update_health(dep_id, post_status)

                results.append({
                    "deployment_id": dep_id,
                    "restarted": True,
                    "post_restart_health": post_status,
                    "status": new_status,
                    "attempts": self._restart_counts[dep_id]
                })
            else:
                msg = f"Docker engine failed to restart container '{container_name}'."
                self.repository.update_status(dep_id, DeploymentStatus.FAILED.value, message=msg)
                results.append({
                    "deployment_id": dep_id,
                    "restarted": False,
                    "error": msg,
                    "attempts": self._restart_counts[dep_id]
                })

        return results

    def monitor_deployment(self, deployment_id: str, auto_restart: bool = True) -> Dict[str, Any]:
        """
        Examine a specific deployment. If unhealthy or stopped unexpectedly,
        optionally restarts container, updates status, and persists in repository.
        """
        health_info = self.get_deployment_health(deployment_id)
        if not health_info.get("found"):
            return health_info

        container_name = f"modelforge_{deployment_id}"
        health_status = health_info.get("health_status")
        container_running = health_info.get("container_running", False)
        restarted = False

        if (not container_running or health_status in (HealthStatus.UNHEALTHY, HealthStatus.FAILED, HealthStatus.TIMEOUT)) and auto_restart:
            restarts = self.restart_failed_containers([health_info])
            if restarts and restarts[0].get("restarted"):
                restarted = True
                health_info = self.get_deployment_health(deployment_id)
                health_status = health_info.get("health_status")
                container_running = health_info.get("container_running", False)

        # Update and persist monitoring state
        if container_running and health_status == HealthStatus.HEALTHY:
            new_status = DeploymentStatus.RUNNING.value
        elif container_running:
            new_status = DeploymentStatus.CONTAINER_RUNNING.value
        else:
            new_status = DeploymentStatus.FAILED.value

        self.repository.update_status(deployment_id, new_status, message=f"Monitored: {health_status}")
        self.repository.update_health(deployment_id, health_status)

        return {
            "deployment_id": deployment_id,
            "deployment_status": new_status,
            "health_status": health_status,
            "container_running": container_running,
            "restarted": restarted,
            "message": health_info.get("message")
        }

    def monitor_all_active(self, auto_restart: bool = True) -> List[Dict[str, Any]]:
        """
        Scan all active deployments in database, detect failures, and optionally restart.
        Uses ThreadPoolExecutor to support concurrent scaling across large container sets.
        """
        active_records = self.repository.list_all()
        target_ids = [
            r["deployment_id"] for r in active_records
            if r.get("deployment_status") in (
                DeploymentStatus.RUNNING.value,
                DeploymentStatus.CONTAINER_RUNNING.value,
                DeploymentStatus.HEALTH_CHECKING.value
            )
        ]

        if not target_ids:
            return []

        def worker(dep_id: str) -> Dict[str, Any]:
            return self.monitor_deployment(dep_id, auto_restart=auto_restart)

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(target_ids) or 1)) as executor:
            results = list(executor.map(worker, target_ids))

        return results

    def monitor_active_deployments(self, auto_restart: bool = True) -> List[Dict[str, Any]]:
        """Alias for monitor_all_active()."""
        return self.monitor_all_active(auto_restart=auto_restart)

    def generate_deployment_metrics(self, deployment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate operational metrics for a specific deployment or the entire platform.

        Parameters
        ----------
        deployment_id : Optional[str]

        Returns
        -------
        Dict[str, Any]
            Detailed metrics including counts, health ratios, and replica stats.
        """
        all_records = self.repository.list_all()

        if deployment_id:
            record = self.repository.get(deployment_id)
            if not record:
                return {"error": f"Deployment '{deployment_id}' not found."}

            container_name = f"modelforge_{deployment_id}"
            inspect_data = self.docker_manager.inspect_container(container_name) or {}
            restarts = self._restart_counts.get(deployment_id, 0)
            replicas = self._replica_state.get(deployment_id, 1)

            return {
                "deployment_id": deployment_id,
                "project_id": record.get("project_id"),
                "framework": record.get("framework"),
                "status": record.get("deployment_status"),
                "health": record.get("health_status"),
                "allocated_port": record.get("allocated_port"),
                "public_url": record.get("public_url"),
                "restart_count": restarts,
                "replicas": replicas,
                "container_running": inspect_data.get("running", False),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at")
            }

        # Aggregate platform metrics
        total = len(all_records)
        status_counts: Dict[str, int] = {}
        health_counts: Dict[str, int] = {}
        framework_counts: Dict[str, int] = {}

        for r in all_records:
            st = r.get("deployment_status", "UNKNOWN")
            ht = r.get("health_status", "UNKNOWN")
            fw = r.get("framework", "UNKNOWN")

            status_counts[st] = status_counts.get(st, 0) + 1
            health_counts[ht] = health_counts.get(ht, 0) + 1
            framework_counts[fw] = framework_counts.get(fw, 0) + 1

        active_count = sum(
            status_counts.get(s, 0) for s in (
                DeploymentStatus.RUNNING.value,
                DeploymentStatus.CONTAINER_RUNNING.value
            )
        )
        healthy_count = health_counts.get(HealthStatus.HEALTHY, 0)
        health_ratio = round((healthy_count / active_count * 100), 2) if active_count > 0 else 0.0

        return {
            "total_deployments": total,
            "active_deployments": active_count,
            "healthy_deployments": healthy_count,
            "failed_deployments": status_counts.get(DeploymentStatus.FAILED.value, 0),
            "stopped_deployments": status_counts.get(DeploymentStatus.STOPPED.value, 0),
            "health_ratio_percentage": health_ratio,
            "status_breakdown": status_counts,
            "health_breakdown": health_counts,
            "framework_breakdown": framework_counts
        }

    # Future scaling support
    def evaluate_scaling(self, deployment_id: str, current_load: float = 0.0, threshold: float = 80.0) -> Dict[str, Any]:
        """
        Evaluate scaling requirements for an active deployment based on resource load.

        Parameters
        ----------
        deployment_id : str
        current_load : float
            Current simulated or actual resource utilization percentage (0-100).
        threshold : float
            Upper threshold for scale-up.

        Returns
        -------
        Dict[str, Any]
            Scaling recommendation and desired replica count.
        """
        current_replicas = self._replica_state.get(deployment_id, 1)

        if current_load > threshold:
            action = "SCALE_UP"
            desired_replicas = current_replicas + 1
        elif current_load < (threshold / 2) and current_replicas > 1:
            action = "SCALE_DOWN"
            desired_replicas = max(1, current_replicas - 1)
        else:
            action = "STEADY"
            desired_replicas = current_replicas

        return {
            "deployment_id": deployment_id,
            "current_replicas": current_replicas,
            "desired_replicas": desired_replicas,
            "scale_action": action,
            "current_load": current_load,
            "threshold": threshold
        }

    def scale_deployment(self, deployment_id: str, target_replicas: int) -> Dict[str, Any]:
        """
        Update desired replica state for future cluster / horizontal scaling.

        Parameters
        ----------
        deployment_id : str
        target_replicas : int

        Returns
        -------
        Dict[str, Any]
        """
        if target_replicas < 1:
            raise ValueError("Target replicas must be at least 1.")

        old_replicas = self._replica_state.get(deployment_id, 1)
        self._replica_state[deployment_id] = target_replicas

        logger.info("Scaled deployment %s from %d to %d replicas", deployment_id, old_replicas, target_replicas)
        return {
            "deployment_id": deployment_id,
            "previous_replicas": old_replicas,
            "current_replicas": target_replicas,
            "scaled": True
        }
