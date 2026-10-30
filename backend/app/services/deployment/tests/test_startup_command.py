"""
Tests for Dynamic Container Startup Command Selection
Verifies all 7 rules:
1. entry_point_type == "fastapi" -> start using uvicorn
2. entry_point_type == "flask" -> start using python app.py (or detected Flask entry)
3. entry_point_type == "cli_script" -> start using python <detected_entry_point> (predict.py, train.py)
4. Never hardcode uvicorn for every project
5. Dockerfile generation uses the selected startup command
6. Return the chosen startup command in deployment response and logs
7. Ensure existing FastAPI deployments continue to work
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.deployment.core.artifact_reader import ArtifactReader
from app.services.deployment.core.dockerfile_generator import DockerfileGenerator
from app.services.deployment.core.deployment_manager import DeploymentManager
from app.services.deployment.core.health_manager import HealthStatus
from app.services.deployment.models.deployment_artifact import DeploymentArtifact
from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_result import DeploymentResult
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.services.deployment_service import DeploymentService


class TestDynamicStartupCommand(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "requirements.txt").write_text("numpy\npandas\n", encoding="utf-8")

        self.mock_docker_mgr = MagicMock()
        self.mock_port_mgr = MagicMock()
        self.mock_health_mgr = MagicMock()
        self.mock_nginx_mgr = MagicMock()
        self.mock_repo = MagicMock()

        self.deploy_mgr = DeploymentManager(
            docker_manager=self.mock_docker_mgr,
            port_manager=self.mock_port_mgr,
            health_manager=self.mock_health_mgr,
            nginx_manager=self.mock_nginx_mgr,
            repository=self.mock_repo
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # Rule 1: FastAPI -> uvicorn
    # =========================================================================
    def test_fastapi_selects_uvicorn(self):
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type="fastapi",
            entry_point="main.py",
            port=8000
        )
        self.assertEqual(ep_type, "fastapi")
        self.assertEqual(cmd, "uvicorn main:app --host 0.0.0.0 --port 8000")

    def test_fastapi_custom_module_and_port(self):
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type="fastapi",
            entry_point="src/server.py",
            port=8080
        )
        self.assertEqual(ep_type, "fastapi")
        self.assertEqual(cmd, "uvicorn src.server:app --host 0.0.0.0 --port 8080")

    # =========================================================================
    # Rule 2: Flask -> python app.py (or detected Flask entry)
    # =========================================================================
    def test_flask_selects_python_entry_point(self):
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type="flask",
            entry_point="app.py",
            port=5000
        )
        self.assertEqual(ep_type, "flask")
        self.assertEqual(cmd, "python app.py")

    def test_flask_custom_entry_point(self):
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type="flask",
            entry_point="web_entry.py",
            port=5000
        )
        self.assertEqual(ep_type, "flask")
        self.assertEqual(cmd, "python web_entry.py")

    # =========================================================================
    # Rule 3: CLI Script -> python <detected_entry_point>
    # =========================================================================
    def test_cli_predict_script(self):
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type="cli_script",
            entry_point="predict.py"
        )
        self.assertEqual(ep_type, "cli_script")
        self.assertEqual(cmd, "python predict.py")

    def test_cli_train_script(self):
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type="cli_script",
            entry_point="train.py"
        )
        self.assertEqual(ep_type, "cli_script")
        self.assertEqual(cmd, "python train.py")

    def test_cli_inferred_from_entry_point_name(self):
        """When entry_point_type is omitted, predict.py and train.py default to cli_script."""
        ep_type, cmd = ArtifactReader.select_startup_command(
            entry_point_type=None,
            entry_point="predict.py"
        )
        self.assertEqual(ep_type, "cli_script")
        self.assertEqual(cmd, "python predict.py")

        ep_type2, cmd2 = ArtifactReader.select_startup_command(
            entry_point_type=None,
            entry_point="train.py"
        )
        self.assertEqual(ep_type2, "cli_script")
        self.assertEqual(cmd2, "python train.py")

    # =========================================================================
    # Rule 5: Dockerfile generation uses the selected startup command
    # =========================================================================
    def test_dockerfile_generation_for_cli_predict(self):
        generator = DockerfileGenerator()
        content = generator.generate(
            framework="cli",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="predict.py",
            entry_point_type="cli_script",
            startup_command="python predict.py"
        )
        self.assertIn('CMD ["python", "predict.py"]', content)
        self.assertNotIn("uvicorn", content)
        self.assertNotIn("EXPOSE", content)

    def test_dockerfile_generation_for_cli_train(self):
        generator = DockerfileGenerator()
        content = generator.generate(
            framework="cli",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="train.py",
            entry_point_type="cli_script",
            startup_command="python train.py"
        )
        self.assertIn('CMD ["python", "train.py"]', content)
        self.assertNotIn("uvicorn", content)

    def test_dockerfile_generation_for_flask_app(self):
        generator = DockerfileGenerator()
        content = generator.generate(
            framework="flask",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="app.py",
            port=5000,
            entry_point_type="flask",
            startup_command="python app.py"
        )
        self.assertIn('CMD ["python", "app.py"]', content)
        self.assertNotIn("uvicorn", content)

    def test_dockerfile_generation_for_fastapi_app(self):
        generator = DockerfileGenerator()
        content = generator.generate(
            framework="fastapi",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="main.py",
            port=8000,
            entry_point_type="fastapi",
            startup_command="uvicorn main:app --host 0.0.0.0 --port 8000"
        )
        self.assertIn("uvicorn", content)
        self.assertIn("main:app", content)
        self.assertIn("8000", content)

    # =========================================================================
    # Rule 6: Return chosen startup command in deployment response and logs
    # =========================================================================
    def test_deployment_response_contains_startup_command_for_cli(self):
        (self.workspace / "predict.py").write_text("print('Predicting...')\n", encoding="utf-8")

        self.mock_docker_mgr.build_image.return_value = {"status": "success", "image_id": "img-cli-1"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c-cli-1"}
        self.mock_health_mgr.wait_for_ready.return_value = {"health_status": HealthStatus.HEALTHY, "healthy": True}

        artifact = DeploymentArtifact(
            project_id="proj-cli-predict",
            project_name="Predict ML",
            project_root=self.workspace,
            entry_point="predict.py",
            entry_point_type="cli_script",
            startup_command="python predict.py",
            framework="cli",
            python_version="3.11",
            dependencies=["numpy"],
            requirements_file="requirements.txt",
            has_dockerfile=False
        )

        with self.assertLogs("deployment.manager", level="INFO") as log_capture:
            result = self.deploy_mgr.deploy(artifact)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertTrue(result.success)
        self.assertEqual(result.entry_point_type, "cli_script")
        self.assertEqual(result.startup_command, "python predict.py")
        self.assertIsNone(result.allocated_port)

        # Verify log output mentions the startup command
        has_log = any("[Startup Command]" in msg and "python predict.py" in msg for msg in log_capture.output)
        self.assertTrue(has_log, f"Startup command not logged. Logs: {log_capture.output}")

    def test_deployment_response_contains_startup_command_for_flask(self):
        (self.workspace / "app.py").write_text("print('Flask app')\n", encoding="utf-8")

        self.mock_docker_mgr.build_image.return_value = {"status": "success", "image_id": "img-flask-1"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c-flask-1"}
        self.mock_port_mgr.allocate_port.return_value = 5001
        self.mock_nginx_mgr.get_public_url.return_value = "http://localhost:5001"
        self.mock_health_mgr.wait_for_ready.return_value = {"health_status": HealthStatus.HEALTHY, "healthy": True}

        artifact = DeploymentArtifact(
            project_id="proj-flask-app",
            project_name="Flask API",
            project_root=self.workspace,
            entry_point="app.py",
            entry_point_type="flask",
            startup_command="python app.py",
            framework="flask",
            python_version="3.11",
            dependencies=["flask"],
            requirements_file="requirements.txt",
            has_dockerfile=False
        )

        with self.assertLogs("deployment.manager", level="INFO") as log_capture:
            result = self.deploy_mgr.deploy(artifact)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertTrue(result.success)
        self.assertEqual(result.entry_point_type, "flask")
        self.assertEqual(result.startup_command, "python app.py")
        self.assertEqual(result.allocated_port, 5001)

        has_log = any("[Startup Command]" in msg and "python app.py" in msg for msg in log_capture.output)
        self.assertTrue(has_log)

    def test_deployment_response_contains_startup_command_for_fastapi(self):
        (self.workspace / "main.py").write_text("print('FastAPI app')\n", encoding="utf-8")

        self.mock_docker_mgr.build_image.return_value = {"status": "success", "image_id": "img-fastapi-1"}
        self.mock_docker_mgr.run_container.return_value = {"status": "success", "container_id": "c-fastapi-1"}
        self.mock_port_mgr.allocate_port.return_value = 8001
        self.mock_nginx_mgr.get_public_url.return_value = "http://localhost:8001"
        self.mock_health_mgr.wait_for_ready.return_value = {"health_status": HealthStatus.HEALTHY, "healthy": True}

        artifact = DeploymentArtifact(
            project_id="proj-fastapi-app",
            project_name="FastAPI Service",
            project_root=self.workspace,
            entry_point="main.py",
            entry_point_type="fastapi",
            startup_command="uvicorn main:app --host 0.0.0.0 --port 8000",
            framework="fastapi",
            python_version="3.11",
            dependencies=["fastapi", "uvicorn"],
            requirements_file="requirements.txt",
            has_dockerfile=False
        )

        with self.assertLogs("deployment.manager", level="INFO") as log_capture:
            result = self.deploy_mgr.deploy(artifact)

        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertTrue(result.success)
        self.assertEqual(result.entry_point_type, "fastapi")
        self.assertEqual(result.startup_command, "uvicorn main:app --host 0.0.0.0 --port 8000")

        has_log = any("[Startup Command]" in msg and "uvicorn" in msg for msg in log_capture.output)
        self.assertTrue(has_log)


if __name__ == "__main__":
    unittest.main()

