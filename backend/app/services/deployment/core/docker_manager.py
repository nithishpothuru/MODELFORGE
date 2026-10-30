"""
Docker Manager
Low-level client wrapper for managing Docker images, containers, and lifecycle events
using the Docker SDK for Python. Subprocess is strictly forbidden here.
Includes structured logging and failure cleanup routines.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

try:
    import docker
    from docker.errors import DockerException, APIError, BuildError, NotFound
except ImportError:
    docker = None
    DockerException = Exception
    APIError = Exception
    BuildError = Exception
    NotFound = Exception

logger = logging.getLogger("deployment.docker_manager")


class DockerManager:
    """
    Manages Docker engine interactions, image compilation, and container operations
    strictly via Docker SDK for Python.
    """

    def __init__(self, client: Optional[Any] = None):
        """
        Initialize Docker SDK client connection.
        Supports dependency injection for mocking/testing.
        """
        self.client = client
        if self.client is None and docker is not None:
            try:
                self.client = docker.from_env()
            except DockerException as exc:
                logger.warning("Docker engine not reachable: %s", exc)

    def is_connected(self) -> bool:
        """Check if Docker engine is reachable."""
        if not self.client:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def build_image(self,
                    workspace_path: Union[str, Path],
                    tag: str,
                    dockerfile: str = "Dockerfile",
                    build_args: Optional[Dict[str, str]] = None,
                    rm: bool = True) -> Dict[str, Any]:
        """
        Build a Docker image from a workspace directory.
        """
        if not self.is_connected():
            logger.error("[Image Build] Docker daemon is not running or not accessible.")
            return {
                "status": "failed",
                "stage": "docker_engine",
                "message": "Docker daemon is not running or not accessible.",
                "build_logs": []
            }

        workspace_p = Path(workspace_path).resolve()
        dockerfile_p = workspace_p / dockerfile
        if not dockerfile_p.exists():
            logger.error("[Image Build] Dockerfile does not exist at %s", dockerfile_p)
            return {
                "status": "failed",
                "stage": "dockerfile_check",
                "message": f"Dockerfile does not exist at {dockerfile_p}",
                "build_logs": []
            }

        clean_tag = tag.lower().strip()
        logger.info("[Image Build] Building Docker image '%s' from context: %s", clean_tag, workspace_p)

        try:
            image, build_logs_stream = self.client.images.build(
                path=str(workspace_p),
                dockerfile=dockerfile,
                tag=clean_tag,
                buildargs=build_args or {},
                rm=rm,
                forcerm=True
            )

            formatted_logs: List[str] = []
            for item in build_logs_stream:
                if isinstance(item, dict) and "stream" in item:
                    line = item["stream"].strip()
                    if line:
                        formatted_logs.append(line)

            logger.info("[Image Build] Successfully built image '%s' (ID: %s)", clean_tag, image.id)
            return {
                "status": "success",
                "image_name": clean_tag,
                "image_id": image.id,
                "short_id": getattr(image, "short_id", image.id[:12]),
                "tags": getattr(image, "tags", [clean_tag]),
                "build_logs": formatted_logs
            }

        except BuildError as exc:
            logs = []
            for item in getattr(exc, "build_log", []):
                if isinstance(item, dict) and "stream" in item:
                    line = item["stream"].strip()
                    if line:
                        logs.append(line)
            detail_msg = "\n".join(logs)
            logger.error("[Image Build] Build error for '%s': %s", clean_tag, detail_msg)
            return {
                "status": "failed",
                "stage": "docker_build",
                "message": "Docker image build failed.",
                "details": detail_msg,
                "build_logs": logs
            }
        except (APIError, DockerException) as exc:
            logger.error("[Image Build] Docker API error for '%s': %s", clean_tag, exc)
            return {
                "status": "failed",
                "stage": "docker_api",
                "message": str(exc),
                "build_logs": []
            }
        except Exception as exc:
            logger.error("[Image Build] Unexpected error building '%s': %s", clean_tag, exc)
            return {
                "status": "failed",
                "stage": "unknown",
                "message": str(exc),
                "build_logs": []
            }

    def run_container(self,
                      image_name: str,
                      container_name: str,
                      host_port: Optional[int] = None,
                      target_port: int = 8000,
                      env_vars: Optional[Dict[str, str]] = None,
                      labels: Optional[Dict[str, str]] = None,
                      memory_limit: Optional[str] = None,
                      cpu_limit: Optional[float] = None,
                      restart_policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a Docker container from an image.
        """
        if not self.is_connected():
            logger.error("[Container Start] Docker daemon is not reachable.")
            return {
                "status": "failed",
                "stage": "docker_engine",
                "message": "Docker daemon is not reachable."
            }

        try:
            # Check if container name already exists, if so remove it
            try:
                existing = self.client.containers.get(container_name)
                logger.info("[Cleanup] Found existing container '%s', removing...", container_name)
                existing.remove(force=True)
            except (NotFound, Exception):
                pass

            port_mapping = {}
            if host_port is not None:
                port_mapping = {f"{target_port}/tcp": host_port}

            extra_kwargs: Dict[str, Any] = {}
            if memory_limit:
                extra_kwargs["mem_limit"] = memory_limit
            if cpu_limit:
                extra_kwargs["nano_cpus"] = int(cpu_limit * 1_000_000_000)

            default_restart = restart_policy or {"Name": "on-failure", "MaximumRetryCount": 3}

            logger.info("[Container Start] Running container '%s' (image: %s, port: %s)", container_name, image_name, host_port)

            container = self.client.containers.run(
                image=image_name,
                name=container_name,
                detach=True,
                ports=port_mapping if port_mapping else None,
                environment=env_vars or {},
                labels=labels or {},
                restart_policy=default_restart,
                **extra_kwargs
            )

            result: Dict[str, Any] = {
                "status": "success",
                "container_id": container.id,
                "container_name": container.name,
                "host_port": host_port,
                "target_port": target_port if host_port else None,
            }
            if host_port:
                result["url"] = f"http://localhost:{host_port}"
            logger.info("[Container Start] Container '%s' is up (ID: %s)", container_name, container.id[:12])
            return result

        except (APIError, DockerException) as exc:
            logger.error("[Container Start] Failed to start '%s': %s", container_name, exc)
            return {
                "status": "failed",
                "stage": "container_run",
                "message": str(exc)
            }
        except Exception as exc:
            logger.error("[Container Start] Unexpected error starting '%s': %s", container_name, exc)
            return {
                "status": "failed",
                "stage": "unknown",
                "message": str(exc)
            }

    def stop_container(self, container_id_or_name: str, timeout: int = 10) -> bool:
        """Stop a running container."""
        if not self.is_connected():
            return False
        try:
            container = self.client.containers.get(container_id_or_name)
            container.stop(timeout=timeout)
            logger.info("[Cleanup] Successfully stopped container: %s", container_id_or_name)
            return True
        except Exception as exc:
            logger.warning("[Cleanup] Error stopping container %s: %s", container_id_or_name, exc)
            return False

    def restart_container(self, container_id_or_name: str, timeout: int = 10) -> bool:
        """Restart a container."""
        if not self.is_connected():
            return False
        try:
            container = self.client.containers.get(container_id_or_name)
            container.restart(timeout=timeout)
            logger.info("Successfully restarted container: %s", container_id_or_name)
            return True
        except Exception as exc:
            logger.warning("Error restarting container %s: %s", container_id_or_name, exc)
            return False

    def remove_container(self, container_id_or_name: str, force: bool = True) -> bool:
        """Remove a container."""
        if not self.is_connected():
            return False
        try:
            container = self.client.containers.get(container_id_or_name)
            container.remove(force=force)
            logger.info("[Cleanup] Successfully removed container: %s", container_id_or_name)
            return True
        except NotFound:
            return True
        except Exception as exc:
            logger.warning("[Cleanup] Error removing container %s: %s", container_id_or_name, exc)
            return False

    def remove_image(self, image_id_or_name: str, force: bool = False) -> bool:
        """Remove a Docker image."""
        if not self.is_connected():
            return False
        try:
            self.client.images.remove(image=image_id_or_name, force=force)
            logger.info("[Cleanup] Successfully removed image: %s", image_id_or_name)
            return True
        except Exception as exc:
            logger.warning("[Cleanup] Error removing image %s: %s", image_id_or_name, exc)
            return False

    def cleanup_resources(self, container_id_or_name: Optional[str] = None, image_tag_or_id: Optional[str] = None) -> None:
        """
        Safely clean up partially created container and dangling image on deployment failure.
        """
        logger.info("[Cleanup] Performing automatic failure cleanup...")
        if container_id_or_name:
            self.remove_container(container_id_or_name, force=True)
        if image_tag_or_id:
            self.remove_image(image_tag_or_id, force=True)

    def inspect_container(self, container_id_or_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve low-level container status inspection."""
        if not self.is_connected():
            return None
        try:
            container = self.client.containers.get(container_id_or_name)
            container.reload()
            attrs = container.attrs or {}
            state = attrs.get("State", {})
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "running": state.get("Running", False),
                "exit_code": state.get("ExitCode"),
                "error": state.get("Error"),
                "started_at": state.get("StartedAt"),
                "finished_at": state.get("FinishedAt"),
                "state": state,
                "ports": attrs.get("NetworkSettings", {}).get("Ports", {}),
                "labels": attrs.get("Config", {}).get("Labels", {}),
            }
        except Exception as exc:
            logger.warning("Error inspecting container %s: %s", container_id_or_name, exc)
            return None

    def container_logs(self, container_id_or_name: str, tail: int = 100) -> str:
        """Fetch stdout and stderr logs from container."""
        if not self.is_connected():
            return ""
        try:
            container = self.client.containers.get(container_id_or_name)
            raw = container.logs(tail=tail)
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="replace")
            return str(raw)
        except Exception as exc:
            return f"Error retrieving logs: {exc}"

    def get_container_logs(self, container_id_or_name: str, tail: int = 100) -> str:
        """Alias for container_logs."""
        return self.container_logs(container_id_or_name, tail=tail)

    def list_containers(self, all: bool = False, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List containers, optionally filtered by name prefix."""
        if not self.is_connected():
            return []
        try:
            containers = self.client.containers.list(all=all)
            results = []
            for c in containers:
                if prefix and not c.name.startswith(prefix):
                    continue
                results.append({
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags if c.image and getattr(c.image, "tags", None) else [str(c.image)],
                })
            return results
        except Exception as exc:
            logger.warning("Error listing containers: %s", exc)
            return []
