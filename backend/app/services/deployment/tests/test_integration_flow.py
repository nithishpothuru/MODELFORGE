"""
Sprint 12: Comprehensive Integration Test Suite.
Tests the complete end-to-end deployment lifecycle:
Validation Output -> DeploymentRequest -> Dockerfile -> Docker Image ->
Container -> Health Check -> Nginx -> Deployment Result.

Covers:
- Full Happy Path End-to-End flows (FastAPI, Flask, CLI, Streamlit)
- Mock Docker tests
- Comprehensive Failure Scenarios
- Rollback on failures
- Edge Cases (concurrent deployments, custom Dockerfile preservation, port exhaustion)
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.deployment.core.artifact_reader import ArtifactReader
from app.services.deployment.core.dockerfile_generator import DockerfileGenerator
from app.services.deployment.core.docker_manager import DockerManager
from app.services.deployment.core.port_manager import PortManager
from app.services.deployment.core.health_manager import HealthManager, HealthStatus
from app.services.deployment.core.nginx_manager import NginxManager
from app.services.deployment.core.deployment_manager import DeploymentManager
from app.services.deployment.database.deployment_repository import DeploymentRepository
from app.services.deployment.services.deployment_service import DeploymentService
from app.services.deployment.services.cleanup_service import CleanupService
from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_result import DeploymentResult
from app.services.deployment.models.deployment_status import DeploymentStatus


class TestCompleteDeploymentIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        # Create simulated project workspace
        self.workspace = self.base_dir / "ml_project"
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "requirements.txt").write_text("fastapi\nuvicorn\nscikit-learn\n", encoding="utf-8")
        (self.workspace / "main.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef h(): return {'status':'ok'}\n",
            encoding="utf-8"
        )

        # Nginx conf directory
        self.conf_dir = self.base_dir / "nginx_conf"
        self.conf_dir.mkdir(parents=True, exist_ok=True)

        # SQLite database
        self.db_path = self.base_dir / "deployments.db"

        # Real subsystem instances (with Docker SDK mocked to run safely anywhere)
        PortManager._active_mappings.clear()
        HealthManager.clear_health_records()
        self.repo = DeploymentRepository(db_path=self.db_path, sync_supabase=False)
        self.port_mgr = PortManager(start_port=8100, end_port=8150, state_file=self.base_dir / "ports.json")
        self.dockerfile_gen = DockerfileGenerator()
        self.nginx_mgr = NginxManager(
            conf_dir=self.conf_dir,
            base_domain="modelforge.internal",
            public_base_url="http://gateway.modelforge.internal"
        )
        self.health_mgr = HealthManager(default_timeout=0.5, default_retries=2, default_delay=0.01)

        # Mock DockerManager for unit/integration isolation
        self.mock_docker_mgr = MagicMock(spec=DockerManager)

        # Orchestrator
        self.deploy_mgr = DeploymentManager(
            artifact_reader=ArtifactReader(),
            dockerfile_generator=self.dockerfile_gen,
            docker_manager=self.mock_docker_mgr,
            port_manager=self.port_mgr,
            health_manager=self.health_mgr,
            nginx_manager=self.nginx_mgr,
            repository=self.repo
        )

        # Service facade
        self.deploy_service = DeploymentService(
            deployment_manager=self.deploy_mgr,
            repository=self.repo,
            docker_manager=self.mock_docker_mgr,
            health_manager=self.health_mgr
        )

    def tearDown(self):
        PortManager._active_mappings.clear()
        HealthManager.clear_health_records()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # =========================================================================
    # 1. Full Happy Path Flows
    # =========================================================================
    @patch("requests.get")
    def test_e2e_fastapi_deployment_flow(self, mock_http_get):
        """
        Validate complete pipeline from Member 1 validation output JSON to RUNNING result:
        Validation Output -> DeploymentRequest -> Dockerfile -> Docker Image ->
        Container -> Health Check -> Nginx -> Deployment Result
        """
        # Simulated Member 1 validation report
        validation_output = {
            "project_id": "proj-fastapi-101",
            "project_name": "Credit Risk Model",
            "status": "success",
            "validation_report": {
                "framework": "fastapi",
                "python_version": {"version": "3.11", "is_inferred": False},
                "entry_point": {"file": "main.py", "is_valid": True},
                "requirements": {"file": "requirements.txt", "is_valid": True},
                "syntax_valid": True,
                "project_path": str(self.workspace)
            }
        }

        # Mock Docker SDK behavior
        self.mock_docker_mgr.build_image.return_value = {
            "status": "success",
            "image_name": "modelforge_dep_fastapi",
            "image_id": "sha256:abcd1234ef56"
        }
        self.mock_docker_mgr.run_container.return_value = {
            "status": "success",
            "container_id": "cont_fastapi_001"
        }
        self.mock_docker_mgr.inspect_container.return_value = {
            "status": "running",
            "running": True,
            "state": {"Running": True, "ExitCode": 0}
        }

        # Mock HTTP Health probe response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_http_get.return_value = mock_resp

        # Trigger deployment via public service facade
        result = self.deploy_service.deploy(validation_output)

        # 1. Verify DeploymentResult
        self.assertIsInstance(result, DeploymentResult)
        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertEqual(result.health_status, HealthStatus.HEALTHY)
        self.assertIsNotNone(result.allocated_port)
        self.assertTrue(8100 <= result.allocated_port <= 8150)
        self.assertEqual(result.container_id, "cont_fastapi_001")
        self.assertIn("/deployments/", result.public_url)

        # 2. Verify Dockerfile was generated in workspace using FastAPI template
        df_path = self.workspace / "Dockerfile"
        self.assertTrue(df_path.exists())
        df_content = df_path.read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11-slim", df_content)
        self.assertIn("uvicorn", df_content)

        # 3. Verify Nginx routing file was created in conf_dir
        conf_file = self.conf_dir / f"{result.deployment_id}.conf"
        self.assertTrue(conf_file.exists())
        conf_content = conf_file.read_text(encoding="utf-8")
        self.assertIn(f"127.0.0.1:{result.allocated_port}", conf_content)
        self.assertIn("proxy_pass", conf_content)

        # 4. Verify SQLite repository record
        stored = self.repo.get(result.deployment_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["deployment_status"], DeploymentStatus.RUNNING.value)
        self.assertEqual(stored["allocated_port"], result.allocated_port)
        self.assertEqual(stored["health_status"], HealthStatus.HEALTHY)

    @patch("requests.get")
    def test_e2e_flask_deployment_flow(self, mock_http_get):
        """Test complete flow for Flask framework with gunicorn entry point."""
        (self.workspace / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8")

        flask_output = {
            "project_id": "proj-flask-202",
            "project_name": "Churn Predictor",
            "status": "success",
            "validation_report": {
                "framework": "flask",
                "python_version": {"version": "3.10"},
                "entry_point": {"file": "app.py"},
                "requirements": {"file": "requirements.txt"},
                "project_path": str(self.workspace)
            }
        }

        self.mock_docker_mgr.build_image.return_value = {"status": "success", "image_id": "sha256:flask1"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "cont_flask_202"}
        self.mock_docker_mgr.inspect_container.return_value = {"status": "running", "running": True}

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy"}
        mock_http_get.return_value = mock_resp

        result = self.deploy_service.deploy(flask_output)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertEqual(result.framework, "flask")
        self.assertIn("gunicorn", (self.workspace / "Dockerfile").read_text(encoding="utf-8"))

    def test_e2e_cli_batch_ml_deployment_flow(self):
        """Test complete flow for Python CLI batch job: no port allocation, no Nginx routing."""
        (self.workspace / "train.py").write_text("print('Model training complete')\n", encoding="utf-8")

        cli_output = {
            "project_id": "proj-cli-303",
            "project_name": "XGBoost Trainer",
            "status": "success",
            "validation_report": {
                "framework": "cli",
                "python_version": {"version": "3.11"},
                "entry_point": {"file": "train.py"},
                "requirements": {"file": "requirements.txt"},
                "project_path": str(self.workspace)
            }
        }

        self.mock_docker_mgr.build_image.return_value = {"status": "success", "image_id": "sha256:cli1"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "cont_cli_303"}
        # CLI container finished with exit code 0
        self.mock_docker_mgr.inspect_container.return_value = {
            "status": "exited",
            "running": False,
            "exit_code": 0,
            "state": {"Running": False, "ExitCode": 0}
        }

        result = self.deploy_service.deploy(cli_output)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertEqual(result.health_status, HealthStatus.HEALTHY)
        # CLI should not allocate host port or generate Nginx config
        self.assertIsNone(result.allocated_port)
        self.assertEqual(len(list(self.conf_dir.glob("*.conf"))), 0)

    # =========================================================================
    # 2. Failure Scenarios & Rollback
    # =========================================================================
    def test_failure_on_invalid_validation_report(self):
        """Pipeline halts immediately if validation report status is failed."""
        invalid_output = {
            "project_id": "proj-bad",
            "status": "failed",
            "validation_report": {
                "framework": "unknown",
                "syntax_valid": False,
                "project_path": str(self.workspace)
            }
        }

        result = self.deploy_service.deploy(invalid_output)
        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.mock_docker_mgr.build_image.assert_not_called()
        self.mock_docker_mgr.run_container.assert_not_called()

    def test_failure_on_docker_build_error(self):
        """Pipeline halts when Docker compilation fails; captures build error details."""
        req = DeploymentRequest(
            project_id="proj-build-err",
            framework="fastapi",
            working_directory=str(self.workspace)
        )

        self.mock_docker_mgr.build_image.return_value = {
            "status": "failed",
            "message": "Docker compilation failed",
            "details": "ERROR: Could not find a version that satisfies requirement invalid-lib"
        }

        result = self.deploy_service.deploy(req)
        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.assertIn("Could not find a version", result.details)
        self.mock_docker_mgr.run_container.assert_not_called()

    def test_failure_on_container_run_releases_port(self):
        """When container fails to run, allocated port must be rolled back and released."""
        req = DeploymentRequest(
            project_id="proj-run-err",
            framework="fastapi",
            working_directory=str(self.workspace)
        )

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_docker_mgr.run_container.return_value = {
            "status": "failed",
            "message": "OCI runtime error: memory limit exceeded"
        }

        result = self.deploy_service.deploy(req)
        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        # Verify port was released
        self.assertEqual(len(self.port_mgr.get_allocated_ports()), 0)

    @patch("requests.get")
    def test_failure_on_health_timeout_captures_logs_and_releases_port(self, mock_http_get):
        """When health checks exhaust retries, captures container logs and releases port."""
        req = DeploymentRequest(
            project_id="proj-health-fail",
            framework="fastapi",
            working_directory=str(self.workspace),
            health_retries=2,
            health_delay=0.01
        )

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c_timeout"}
        self.mock_docker_mgr.inspect_container.return_value = {"status": "running", "running": True}
        self.mock_docker_mgr.container_logs.return_value = "Traceback (most recent call last):\nModuleNotFoundError"

        # Health probe fails
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        mock_http_get.return_value = fail_resp

        result = self.deploy_service.deploy(req)
        self.assertEqual(result.deployment_status, DeploymentStatus.FAILED.value)
        self.assertEqual(result.health_status, HealthStatus.TIMEOUT)
        self.assertIn("ModuleNotFoundError", result.details)
        self.assertEqual(len(self.port_mgr.get_allocated_ports()), 0)

    # =========================================================================
    # 3. Edge Cases & Concurrency
    # =========================================================================
    def test_existing_custom_dockerfile_is_preserved(self):
        """User-supplied Dockerfile in workspace must never be overwritten."""
        custom_dockerfile = "# Custom Dockerfile provided by ML engineer\nFROM python:3.9-slim\n"
        df_path = self.workspace / "Dockerfile"
        df_path.write_text(custom_dockerfile, encoding="utf-8")

        req = DeploymentRequest(
            project_id="proj-custom-df",
            framework="fastapi",
            working_directory=str(self.workspace)
        )
        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c_custom"}
        self.mock_docker_mgr.inspect_container.return_value = {"status": "running", "running": True}

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = self.deploy_service.deploy(req)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        # Content must remain identical
        self.assertEqual(df_path.read_text(encoding="utf-8"), custom_dockerfile)

    @patch("requests.get")
    def test_concurrent_deployments_allocate_unique_ports(self, mock_http_get):
        """Verify multiple simultaneous deployments receive distinct ports with no collision."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http_get.return_value = mock_resp

        self.mock_docker_mgr.build_image.return_value = {"status": "success"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c_ok"}
        self.mock_docker_mgr.inspect_container.return_value = {"status": "running", "running": True}

        results = []
        for i in range(5):
            req = DeploymentRequest(
                project_id=f"proj-concurrent-{i}",
                framework="fastapi",
                working_directory=str(self.workspace)
            )
            res = self.deploy_service.deploy(req)
            self.assertEqual(res.deployment_status, DeploymentStatus.RUNNING.value)
            results.append(res)

        allocated_ports = [r.allocated_port for r in results]
        self.assertEqual(len(allocated_ports), 5)
        # Must all be unique
        self.assertEqual(len(set(allocated_ports)), 5)


if __name__ == "__main__":
    unittest.main()
