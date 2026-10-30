"""
Container Information Model
Represents runtime details and state of a Docker container.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ContainerInfo(BaseModel):
    """Metadata and inspection state for a Docker container."""
    container_id: str = Field(..., description="Docker container ID")
    container_name: str = Field(..., description="Docker container name")
    image_name: str = Field(..., description="Docker image tag used")
    image_id: Optional[str] = Field(default=None, description="Docker image ID")
    status: str = Field(..., description="Current status: running, exited, paused, etc.")
    host_port: Optional[int] = Field(default=None, description="Mapped host port")
    target_port: int = Field(default=8000, description="Internal container port")
    url: Optional[str] = Field(default=None, description="Direct URL to access container")
    created_at: Optional[str] = Field(default=None, description="Container creation timestamp")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")
    ports: Dict[str, Any] = Field(default_factory=dict, description="Full Docker port bindings map")
    memory_usage: Optional[str] = Field(default=None, description="Current memory consumption")
    cpu_percent: Optional[float] = Field(default=None, description="Current CPU utilization percent")
