"""
Health Manager
Handles active and periodic health probing for deployed services and container readiness.
Supports FastAPI, Flask, Streamlit, and Python CLI ML applications.
Determines: Healthy, Failed, Timeout.
Includes fallback probe paths and structured logging.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

from ..config import settings

logger = logging.getLogger("deployment.health_manager")


class HealthStatus:
    """Standard health state definitions."""
    HEALTHY = "Healthy"
    FAILED = "Failed"
    TIMEOUT = "Timeout"

    # Compatibility alias
    UNHEALTHY = "Failed"


class HealthManager:
    """
    Probes and verifies health and readiness of deployed containerized services.
    Supports HTTP endpoints for web frameworks (FastAPI, Flask, Streamlit)
    and execution state inspection for CLI ML applications.
    """

    _health_records: Dict[str, Dict[str, Any]] = {}
    FALLBACK_ENDPOINTS: List[str] = ["/health", "/healthz", "/", "/docs"]

    def __init__(self,
                 default_timeout: float = settings.health_timeout_seconds,
                 default_retries: int = settings.health_default_retries,
                 default_delay: float = settings.health_default_delay):
        self.default_timeout = default_timeout
        self.default_retries = default_retries
        self.default_delay = default_delay

    @classmethod
    def store_health_state(cls, deployment_id: str, state: Dict[str, Any]) -> None:
        """Store historical or latest health evaluation for a deployment."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **state
        }
        cls._health_records[deployment_id] = record
        logger.debug("[Health Check] Stored health state for %s: %s", deployment_id, state.get("health_status"))

    @classmethod
    def get_health_state(cls, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored health evaluation for a deployment ID."""
        return cls._health_records.get(deployment_id)

    @classmethod
    def clear_health_records(cls) -> None:
        """Reset stored health evaluations (for testing)."""
        cls._health_records.clear()

    @staticmethod
    def check_http_endpoint(url: str,
                            endpoint: str = "/health",
                            timeout: float = 5.0) -> Dict[str, Any]:
        """
        Perform a single HTTP GET request to check service health.
        """
        if requests is None:
            return {
                "health_status": HealthStatus.FAILED,
                "healthy": False,
                "status_code": None,
                "message": "Requests library is not installed."
            }

        target_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            response = requests.get(target_url, timeout=timeout)
            is_healthy = (200 <= response.status_code < 400)

            try:
                data = response.json()
            except Exception:
                data = response.text[:500]

            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.FAILED

            return {
                "health_status": status,
                "healthy": is_healthy,
                "status_code": response.status_code,
                "url": target_url,
                "response": data,
                "message": "HTTP endpoint returned success" if is_healthy else f"HTTP error {response.status_code}"
            }

        except requests.exceptions.ConnectionError as exc:
            return {
                "health_status": HealthStatus.FAILED,
                "healthy": False,
                "status_code": None,
                "url": target_url,
                "error": str(exc),
                "message": "Service not responding to connection requests (connection refused)."
            }
        except requests.exceptions.Timeout as exc:
            return {
                "health_status": HealthStatus.TIMEOUT,
                "healthy": False,
                "status_code": None,
                "url": target_url,
                "error": str(exc),
                "message": f"Connection timed out after {timeout} seconds."
            }
        except requests.exceptions.RequestException as exc:
            return {
                "health_status": HealthStatus.FAILED,
                "healthy": False,
                "status_code": None,
                "url": target_url,
                "error": str(exc),
                "message": f"Health check failed with error: {exc}"
            }

    @staticmethod
    def check_cli_health(container_inspect_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate health for a Python CLI ML project by inspecting its execution state."""
        if not container_inspect_data:
            return {
                "health_status": HealthStatus.FAILED,
                "healthy": False,
                "message": "Container inspection unavailable."
            }

        status = container_inspect_data.get("status")
        state = container_inspect_data.get("state", {})
        exit_code = container_inspect_data.get("exit_code") if "exit_code" in container_inspect_data else state.get("ExitCode")
        running = container_inspect_data.get("running") if "running" in container_inspect_data else state.get("Running", False)

        if running:
            return {
                "health_status": HealthStatus.HEALTHY,
                "healthy": True,
                "message": "CLI application container is actively running.",
                "details": {"status": status}
            }

        if status == "exited" or not running:
            if exit_code == 0:
                return {
                    "health_status": HealthStatus.HEALTHY,
                    "healthy": True,
                    "message": "CLI application completed execution successfully (exit code 0).",
                    "details": {"exit_code": exit_code}
                }
            else:
                return {
                    "health_status": HealthStatus.FAILED,
                    "healthy": False,
                    "message": f"CLI application terminated with non-zero exit code: {exit_code}.",
                    "details": {"exit_code": exit_code, "error": state.get("Error")}
                }

        return {
            "health_status": HealthStatus.FAILED,
            "healthy": False,
            "message": f"Container in unexpected state: {status}.",
            "details": {"status": status}
        }

    def wait_for_ready(self,
                       framework: str,
                       url: Optional[str] = None,
                       endpoint: str = "/health",
                       retries: Optional[int] = None,
                       delay: Optional[float] = None,
                       timeout: Optional[float] = None,
                       deployment_id: Optional[str] = None,
                       container_inspect_fn: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
                       entry_point_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Wait for container startup, retry connections, and detect startup failures.
        Determines: Healthy, Failed, Timeout.
        """
        max_retries = retries or self.default_retries
        poll_delay = delay or self.default_delay
        req_timeout = timeout or self.default_timeout

        is_cli = "cli" in (framework or "").lower() or (entry_point_type in ("cli_script", "cli", "python_cli", "inference_function") if entry_point_type else False)

        logger.info(
            "[Health Check] Starting health check for framework '%s' at %s (max %d retries, %ss delay)",
            framework, url or "N/A", max_retries, poll_delay
        )

        last_result: Dict[str, Any] = {
            "health_status": HealthStatus.FAILED,
            "healthy": False,
            "message": "Health check not started."
        }

        for attempt in range(1, max_retries + 1):
            inspect_data = container_inspect_fn() if container_inspect_fn else None

            # Handle CLI ML projects
            if is_cli:
                cli_res = self.check_cli_health(inspect_data)
                cli_res["attempts"] = attempt
                if cli_res["health_status"] == HealthStatus.HEALTHY:
                    logger.info("[Health Check] CLI container verified Healthy on attempt %d", attempt)
                    if deployment_id:
                        self.store_health_state(deployment_id, cli_res)
                    return cli_res
                elif cli_res["health_status"] == HealthStatus.FAILED:
                    logger.error("[Health Check] CLI container failed: %s", cli_res.get("message"))
                    if deployment_id:
                        self.store_health_state(deployment_id, cli_res)
                    return cli_res

                last_result = cli_res
                time.sleep(poll_delay)
                continue

            # Handle web services: detect immediate container crash / exit
            if inspect_data:
                state = inspect_data.get("state", {})
                status = inspect_data.get("status")
                if status in ("exited", "dead") or (not state.get("Running", True) and state.get("ExitCode") != 0):
                    exit_code = state.get("ExitCode")
                    err_msg = f"Container terminated unexpectedly with status '{status}' (exit code: {exit_code})."
                    logger.error("[Health Check] %s", err_msg)
                    fail_result = {
                        "health_status": HealthStatus.FAILED,
                        "healthy": False,
                        "url": url,
                        "attempts": attempt,
                        "message": err_msg,
                        "details": inspect_data
                    }
                    if deployment_id:
                        self.store_health_state(deployment_id, fail_result)
                    return fail_result

            # HTTP connection probe on target endpoint
            if url:
                http_res = self.check_http_endpoint(url, endpoint, timeout=req_timeout)
                http_res["attempts"] = attempt
                if http_res["health_status"] == HealthStatus.HEALTHY:
                    logger.info("[Health Check] Container verified Healthy on attempt %d: %s%s", attempt, url, endpoint)
                    if deployment_id:
                        self.store_health_state(deployment_id, http_res)
                    return http_res

                # If primary endpoint returned 404, probe fallback paths
                if http_res.get("status_code") == 404:
                    for fb in self.FALLBACK_ENDPOINTS:
                        if fb != endpoint:
                            fb_res = self.check_http_endpoint(url, fb, timeout=req_timeout)
                            if fb_res["health_status"] == HealthStatus.HEALTHY:
                                fb_res["attempts"] = attempt
                                logger.info("[Health Check] Container verified Healthy via fallback %s%s on attempt %d", url, fb, attempt)
                                if deployment_id:
                                    self.store_health_state(deployment_id, fb_res)
                                return fb_res

                last_result = http_res

            time.sleep(poll_delay)

        # Retries exhausted -> Timeout
        logger.warning("[Health Check] Health check timed out after %d attempts for %s", max_retries, url or framework)
        timeout_result = {
            "health_status": HealthStatus.TIMEOUT,
            "healthy": False,
            "url": url,
            "attempts": max_retries,
            "message": f"Application failed health check within timeout ({max_retries} retries exhausted).",
            "last_error": last_result.get("error") or last_result.get("message")
        }
        if deployment_id:
            self.store_health_state(deployment_id, timeout_result)
        return timeout_result

    # Backward compatibility helpers
    @classmethod
    def check_endpoint(cls, url: str, endpoint: str = "/health", timeout: float = 5.0) -> Dict[str, Any]:
        return cls.check_http_endpoint(url, endpoint, timeout)

    @classmethod
    def wait_until_healthy(cls,
                           url: str,
                           endpoint: str = "/health",
                           retries: int = 15,
                           delay: float = 2.0,
                           timeout: float = 5.0,
                           container_status_fn: Optional[Callable[[], str]] = None) -> Dict[str, Any]:
        mgr = cls(default_timeout=timeout, default_retries=retries, default_delay=delay)
        def inspect_cb():
            if not container_status_fn:
                return None
            st = container_status_fn()
            return {"status": st, "state": {"Running": st == "running", "ExitCode": 0 if st == "running" else 1}}
        return mgr.wait_for_ready("fastapi", url=url, endpoint=endpoint, retries=retries, delay=delay, timeout=timeout, container_inspect_fn=inspect_cb)
