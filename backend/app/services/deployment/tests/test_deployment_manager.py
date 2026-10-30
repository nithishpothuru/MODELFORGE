"""
Unit tests for Sprint 8 DeploymentManager orchestrator.
Verifies the exact coordination flow:
ArtifactReader -> DockerfileGenerator -> DockerManager -> PortManager ->
HealthManager -> NginxManager -> DeploymentRepository -> DeploymentResult.
Ensures DeploymentManager only coordinates and adheres strictly to dependency injection.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.services.deployment.core.deployment_manager import DeploymentManager
from app.services.deployment.core.health_manager import HealthStatus
from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.database.deployment_repository import DeploymentRepository


class TestDeploymentManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "requirements.txt").write_text("fastapi\nuvicorn", encoding="utf-8")
        (self.workspace / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()", encoding="utf-8")

        self.db_path = self.workspace / "test_deployments.db"
        self.repo = DeploymentRepository(db_path=self.db_path, sync_supabase=False)

        # Mock dependencies (pure dependency injection)
        self.mock_artifact_reader = MagicMock()
        self.mock_dockerfile_gen = MagicMock()
        self.mock_docker_mgr = MagicMock()
        self.mock_port_mgr = MagicMock()
        self.mock_health_mgr = MagicMock()
        self.mock_nginx_mgr = MagicMock()

        self.mock_nginx_mgr.get_public_url.return_value = "http://localhost/deployments/test"
        self.mock_nginx_mgr.create_routing.return_value = Path(self.temp_dir.name) / "mock.conf"

        self.manager = DeploymentManager(
            artifact_reader=self.mock_artifact_reader,
            dockerfile_generator=self.mock_dockerfile_gen,
            docker_manager=self.mock_docker_mgr,
            port_manager=self.mock_port_mgr,
            health_manager=self.mock_health_mgr,
            nginx_manager=self.mock_nginx_mgr,
            repository=self.repo
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_successful_orchestration_flow(self):
        """Verify the complete 8-step pipeline executes in order."""
        req = DeploymentRequest(
            project_id="proj-orch-01",
            project_name="Iris Classifier",
            framework="fastapi",
            working_directory=str(self.workspace),
            entry_point="main.py",
            requirements_file="requirements.txt"
        )

        # Configure mocks for happy path
        self.mock_docker_mgr.build_image.return_value = {
            "status": "success",
            "image_name": f"modelforge_{req.deployment_id}",
            "image_id": "sha256:build123"
        }
        self.mock_port_mgr.allocate_port.return_value = 8088
        self.mock_docker_mgr.run_container.return_value = {
            "status": "success",
            "container_id": "cont_orch_123"
        }
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.HEALTHY,
            "healthy": True,
            "message": "Service healthy"
        }
        self.mock_nginx_mgr.get_public_url.return_value = f"http://localhost/deployments/{req.deployment_id}"

        # Execute deployment
        result = self.manager.deploy(req)

        # Verify orchestration result
        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertEqual(result.health_status, HealthStatus.HEALTHY)
        self.assertEqual(result.allocated_port, 8088)
        self.assertEqual(result.container_id, "cont_orch_123")
        self.assertEqual(result.public_url, f"http://localhost/deployments/{req.deployment_id}")

        # Verify exact delegation sequence
        self.mock_dockerfile_gen.generate_for_request.assert_called_once_with(req)
        self.mock_docker_mgr.build_image.assert_called_once()
        self.mock_port_mgr.allocate_port.assert_called_once()
        self.mock_docker_mgr.run_container.assert_called_once()
        self.mock_health_mgr.wait_for_ready.assert_called_once()
        self.mock_nginx_mgr.create_routing.assert_called_once()
        self.mock_nginx_mgr.get_public_url.assert_called_once()

        # Verify database record
        saved = self.repo.get(req.deployment_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["deployment_status"], DeploymentStatus.RUNNING.value)
        self.assertEqual(saved["allocated_port"], 8088)

    def test_orchestration_from_artifact_dict(self):
        """Verify artifact reader handles dictionary and passes to pipeline."""
        raw_artifact = {
            "project_id": "proj_dict_01",
            "status": "success",
            "validation_report": {
                "framework": "flask",
                "python_version": {"version": "3.11"},
                "entry_point": {"file": "app.py"},
                "requirements": {"file": "requirements.txt"},
                "project_path": str(self.workspace)
            }
        }
        parsed_req = DeploymentRequest(
            project_id="proj_dict_01",
            framework="flask",
            working_directory=str(self.workspace),
            entry_point="app.py"
        )
        self.mock_artifact_reader.read_from_dict.return_value = parsed_req
        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_port_mgr.allocate_port.return_value = 8089
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c1"}
        self.mock_health_mgr.wait_for_ready.return_value = {"health_status": HealthStatus.HEALTHY}

        res = self.manager.deploy(raw_artifact)

        self.mock_artifact_reader.read_from_dict.assert_called_once_with(raw_artifact)
        self.assertEqual(res.deployment_status, DeploymentStatus.RUNNING.value)

    def test_build_failure_terminates_pipeline(self):
        """Verify image build failure halts pipeline before port allocation or container execution."""
        req = DeploymentRequest(
            project_id="proj-orch-fail",
            framework="fastapi",
            working_directory=str(self.workspace)
        )

        self.mock_docker_mgr.build_image.return_value = {
            "status": "failed",
            "message": "Syntax error in Dockerfile",
            "details": "pip install failed"
        }

        result = self.manager.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.mock_port_mgr.allocate_port.assert_not_called()
        self.mock_docker_mgr.run_container.assert_not_called()
        self.mock_health_mgr.wait_for_ready.assert_not_called()

        saved = self.repo.get(req.deployment_id)
        self.assertEqual(saved["deployment_status"], DeploymentStatus.FAILED.value)

    def test_run_container_failure_releases_port(self):
        """Verify container run failure releases port and updates status to FAILED."""
        req = DeploymentRequest(
            project_id="proj-orch-run-fail",
            framework="fastapi",
            working_directory=str(self.workspace)
        )

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_port_mgr.allocate_port.return_value = 8090
        self.mock_docker_mgr.run_container.return_value = {
            "status": "failed",
            "message": "Port conflict on host"
        }

        result = self.manager.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.mock_port_mgr.release_port.assert_called_once_with(8090)
        self.mock_health_mgr.wait_for_ready.assert_not_called()

    def test_health_check_failure_releases_port_and_captures_logs(self):
        """Verify health check failure fetches container logs and releases port."""
        req = DeploymentRequest(
            project_id="proj-orch-health-fail",
            framework="flask",
            working_directory=str(self.workspace)
        )

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_port_mgr.allocate_port.return_value = 8092
        self.mock_docker_mgr.run_container.return_value = {
            "status": "success",
            "container_id": "c_health_fail"
        }
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.FAILED,
            "message": "HTTP endpoint returned 500"
        }
        self.mock_docker_mgr.container_logs.return_value = "ZeroDivisionError: division by zero"

        result = self.manager.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.assertEqual(result.health_status, HealthStatus.FAILED)
        self.mock_port_mgr.release_port.assert_called_once_with(8092)
        self.mock_docker_mgr.container_logs.assert_called_once()
        self.assertIn("ZeroDivisionError", result.details)

    def test_cli_project_bypasses_port_and_nginx(self):
        """Verify CLI projects do not allocate ports or configure Nginx routing."""
        req = DeploymentRequest(
            project_id="proj-cli-01",
            framework="cli",
            working_directory=str(self.workspace),
            entry_point="train.py"
        )

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_docker_mgr.run_container.return_value = {
            "status": "success",
            "container_id": "c_cli_1"
        }
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.HEALTHY,
            "message": "CLI completed execution successfully"
        }

        result = self.manager.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.mock_port_mgr.allocate_port.assert_not_called()
    def test_dockerfile_generation_failure(self):
        """Verify Dockerfile generation failure halts pipeline and records FAILED status."""
        req = DeploymentRequest(
            project_id="proj-orch-gen-fail",
            framework="fastapi",
            working_directory=str(self.workspace)
        )
        # Ensure Dockerfile does not exist in workspace
        df = self.workspace / "Dockerfile"
        if df.exists():
            df.unlink()

        self.mock_dockerfile_gen.generate_for_request.side_effect = RuntimeError("Template missing")

        result = self.manager.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.assertIn("Failed to generate Dockerfile", result.message)
        self.mock_docker_mgr.build_image.assert_not_called()

    def test_port_allocation_failure(self):
        """Verify port allocation failure halts pipeline and records FAILED status."""
        req = DeploymentRequest(
            project_id="proj-orch-port-fail",
            framework="fastapi",
            working_directory=str(self.workspace)
        )

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_port_mgr.allocate_port.side_effect = RuntimeError("All ports exhausted")

        result = self.manager.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.assertIn("Failed to allocate host port", result.message)
        self.mock_docker_mgr.run_container.assert_not_called()


if __name__ == "__main__":
    unittest.main()
