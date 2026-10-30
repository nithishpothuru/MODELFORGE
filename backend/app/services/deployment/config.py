"""
Deployment Configuration
Central settings for Docker, Nginx, port ranges, database paths, and timeouts.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DEPLOYMENT_DIR = Path(__file__).resolve().parent


class DeploymentSettings(BaseSettings):
    """Configuration settings for the ModelForge Deployment Platform."""

    # Storage and Database
    db_path: Path = Field(
        default=BASE_DEPLOYMENT_DIR / "deployments.db",
        description="Path to SQLite database file for deployments"
    )
    templates_dir: Path = Field(
        default=BASE_DEPLOYMENT_DIR / "templates",
        description="Directory containing Dockerfile templates"
    )

    # Port Management
    port_range_start: int = Field(
        default=8000,
        description="Beginning of host port allocation pool"
    )
    port_range_end: int = Field(
        default=9000,
        description="End of host port allocation pool"
    )

    # Health Checking
    health_timeout_seconds: float = Field(
        default=5.0,
        description="HTTP request timeout for health checks"
    )
    health_default_retries: int = Field(
        default=10,
        description="Maximum attempts when polling for container readiness"
    )
    health_default_delay: float = Field(
        default=2.0,
        description="Delay in seconds between health check polling attempts"
    )

    # Nginx Configuration
    nginx_conf_dir: Path = Field(
        default=BASE_DEPLOYMENT_DIR / "nginx" / "conf.d",
        description="Directory where Nginx site configuration files are written"
    )
    nginx_base_domain: Optional[str] = Field(
        default="localhost",
        description="Base domain for routing (e.g. 'modelforge.local' or 'localhost')"
    )
    public_url_scheme: str = Field(
        default="http",
        description="Public URL scheme ('http' or 'https')"
    )
    public_base_url: Optional[str] = Field(
        default=None,
        description="Optional public base URL override (e.g. 'http://deployments.modelforge.local')"
    )

    # Docker Engine Defaults
    docker_container_prefix: str = Field(
        default="modelforge_",
        description="Prefix prepended to container names"
    )
    docker_image_prefix: str = Field(
        default="modelforge_",
        description="Prefix prepended to image tags"
    )
    default_python_version: str = Field(
        default="3.11",
        description="Fallback Python version when not specified"
    )

    class Config:
        env_prefix = "MODELFORGE_DEPLOY_"
        extra = "ignore"


settings = DeploymentSettings()
