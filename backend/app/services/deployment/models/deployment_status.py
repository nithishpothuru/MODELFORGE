"""
Deployment Status Model
Defines the lifecycle enumeration for ModelForge deployments.
"""

from enum import Enum


class DeploymentStatus(str, Enum):
    """
    Lifecycle states of a deployment.
    """
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    DOCKERFILE_GENERATED = "DOCKERFILE_GENERATED"
    IMAGE_BUILDING = "IMAGE_BUILDING"
    IMAGE_READY = "IMAGE_READY"
    CONTAINER_STARTING = "CONTAINER_STARTING"
    CONTAINER_RUNNING = "CONTAINER_RUNNING"
    HEALTH_CHECKING = "HEALTH_CHECKING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    REMOVED = "REMOVED"

    def is_terminal(self) -> bool:
        """Check if deployment has reached an end state."""
        return self in (DeploymentStatus.RUNNING, DeploymentStatus.FAILED, DeploymentStatus.STOPPED, DeploymentStatus.REMOVED)

    def is_active(self) -> bool:
        """Check if container is running or health checking."""
        return self in (DeploymentStatus.CONTAINER_RUNNING, DeploymentStatus.HEALTH_CHECKING, DeploymentStatus.RUNNING)
