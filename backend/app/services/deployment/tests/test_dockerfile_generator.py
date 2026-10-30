"""
Unit tests for Sprint 2 DockerfileGenerator.
Verifies template rendering for FastAPI, Flask, and Python CLI ML projects.
"""

import tempfile
import unittest
from pathlib import Path

from app.services.deployment.core.dockerfile_generator import DockerfileGenerator
from app.services.deployment.models.deployment_request import DeploymentRequest


class TestDockerfileGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = DockerfileGenerator()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_generate_fastapi_dockerfile(self):
        content = self.generator.generate(
            framework="fastapi",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="main.py",
            port=8000,
            health_endpoint="/health"
        )
        self.assertIn("FROM python:3.11-slim", content)
        self.assertIn("WORKDIR /app", content)
        self.assertIn("COPY requirements.txt .", content)
        self.assertIn("RUN pip install --no-cache-dir -r requirements.txt", content)
        self.assertIn("COPY . .", content)
        self.assertIn("EXPOSE 8000", content)
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("main:app", content)
        self.assertIn("uvicorn", content)

    def test_generate_flask_dockerfile(self):
        content = self.generator.generate(
            framework="flask",
            python_version="3.10",
            requirements_file="requirements-resolved.txt",
            entry_point="app.py",
            port=5000,
            health_endpoint="/health"
        )
        self.assertIn("FROM python:3.10-slim", content)
        self.assertIn("COPY requirements-resolved.txt .", content)
        self.assertIn("EXPOSE 5000", content)
        self.assertIn("app:app", content)
        self.assertIn("gunicorn", content)

    def test_generate_cli_dockerfile(self):
        content = self.generator.generate(
            framework="cli",
            python_version="3.12",
            requirements_file="requirements.txt",
            entry_point="train_model.py"
        )
        self.assertIn("FROM python:3.12-slim", content)
        self.assertIn("COPY requirements.txt .", content)
        self.assertIn("WORKDIR /app", content)
        self.assertIn('CMD ["python", "train_model.py"]', content)
        # CLI projects do not expose a web port by default
        self.assertNotIn("EXPOSE", content)

    def test_module_formatting(self):
        self.assertEqual(self.generator._format_app_module("main.py"), "main:app")
        self.assertEqual(self.generator._format_app_module("src/server.py"), "src.server:app")
        self.assertEqual(self.generator._format_app_module("custom_module:my_application"), "custom_module:my_application")

    def test_generate_dockerfile_with_working_directory(self):
        """Test generating Dockerfile using framework, python_version, requirements, entry_point, working_directory."""
        dockerfile_path = self.generator.generate_dockerfile(
            framework="fastapi",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="api.py",
            working_directory=self.workspace,
            port=8080
        )
        self.assertTrue(dockerfile_path.exists())
        self.assertEqual(dockerfile_path, self.workspace / "Dockerfile")
        content = dockerfile_path.read_text(encoding="utf-8")
        self.assertIn("api:app", content)
        self.assertIn("EXPOSE 8080", content)

    def test_no_overwrite_existing_dockerfile(self):
        """Verify existing Dockerfile is preserved when overwrite=False."""
        df = self.workspace / "Dockerfile"
        df.write_text("# Existing Custom Dockerfile\nFROM ubuntu:latest", encoding="utf-8")

        res_path = self.generator.generate_dockerfile(
            framework="flask",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="app.py",
            working_directory=self.workspace,
            overwrite=False
        )
        content = res_path.read_text(encoding="utf-8")
        self.assertIn("# Existing Custom Dockerfile", content)

    def test_overwrite_existing_dockerfile(self):
        """Verify Dockerfile is overwritten when overwrite=True."""
        df = self.workspace / "Dockerfile"
        df.write_text("# Existing Custom Dockerfile\nFROM ubuntu:latest", encoding="utf-8")

        res_path = self.generator.generate_dockerfile(
            framework="flask",
            python_version="3.11",
            requirements_file="requirements.txt",
            entry_point="app.py",
            working_directory=self.workspace,
            overwrite=True
        )
        content = res_path.read_text(encoding="utf-8")
        self.assertIn("gunicorn", content)
        self.assertNotIn("FROM ubuntu:latest", content)

    def test_generate_for_request(self):
        req = DeploymentRequest(
            project_id="proj-dock-001",
            framework="flask",
            python_version="3.10",
            entry_point="wsgi.py",
            requirements_file="requirements.txt",
            working_directory=str(self.workspace)
        )
        dockerfile = self.generator.generate_for_request(req)
        self.assertTrue(dockerfile.exists())
        saved_text = dockerfile.read_text(encoding="utf-8")
        self.assertIn("wsgi:app", saved_text)


if __name__ == "__main__":
    unittest.main()
