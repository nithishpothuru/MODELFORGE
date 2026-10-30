"""
Image Service
Manages Dockerfile generation, Docker image compilation, and image repository pruning.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..core.docker_manager import DockerManager
from ..core.dockerfile_generator import DockerfileGenerator

logger = logging.getLogger(__name__)


class ImageService:
    """High-level service for generating Dockerfiles and compiling Docker images."""

    def __init__(self,
                 docker_mgr: Optional[DockerManager] = None,
                 dockerfile_gen: Optional[DockerfileGenerator] = None):
        self.docker_mgr = docker_mgr or DockerManager()
        self.dockerfile_gen = dockerfile_gen or DockerfileGenerator()

    def generate_dockerfile(self,
                            workspace_path: str,
                            framework: Optional[str] = None,
                            python_version: str = "3.11",
                            requirements_file: str = "requirements.txt",
                            entry_point: str = "main.py",
                            port: Optional[int] = None,
                            overwrite: bool = False) -> Path:
        """
        Generate a Dockerfile in the specified workspace using DockerfileGenerator.
        """
        target = Path(workspace_path).resolve() / "Dockerfile"
        return self.dockerfile_gen.generate_to_file(
            target_path=target,
            framework=framework or "fastapi",
            python_version=python_version,
            requirements_file=requirements_file,
            entry_point=entry_point,
            port=port,
            overwrite=overwrite
        )

    def build_image(self,
                    workspace_path: str,
                    image_name: str,
                    build_args: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Build a Docker image from a workspace directory.
        """
        workspace_p = Path(workspace_path).resolve()
        return self.docker_mgr.build_image(
            workspace_path=workspace_p,
            tag=image_name,
            build_args=build_args
        )

    def remove_image(self, image_name: str, force: bool = False) -> bool:
        """Delete a Docker image."""
        return self.docker_mgr.remove_image(image_name, force=force)

    def list_images(self, prefix: str = "modelforge_") -> List[Dict[str, Any]]:
        """List Docker images filtered by prefix."""
        if not self.docker_mgr.is_connected():
            return []
        try:
            images = self.docker_mgr.client.images.list()
            matched = []
            for img in images:
                tags = [t for t in img.tags if prefix in t]
                if tags:
                    matched.append({
                        "id": img.id,
                        "short_id": getattr(img, "short_id", img.id[:12]),
                        "tags": tags,
                        "size": getattr(img, "attrs", {}).get("Size", 0)
                    })
            return matched
        except Exception as exc:
            logger.warning("Failed to list Docker images: %s", exc)
            return []
