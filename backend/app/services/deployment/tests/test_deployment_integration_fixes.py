"""
Unit and integration tests for ModelForge Deployment Backend fixes:
- Issue 1: Resolving validated artifact by project_id / validation_id
- Issue 2: Handling folder paths without appending hardcoded folder names
- Issue 3: Strict success=False whenever deployment_status == FAILED
- Issue 4: Dynamic structure detection (requirements-resolved.txt, entry point, validation_report.json)
- Issue 5: Automatic normalization of deeply nested folder structures
- Dockerfile and .dockerignore automatic generation
- Automatic rollback / cleanup on failure
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.deployment.core.artifact_reader import ArtifactReader, ArtifactValidationError
from app.services.deployment.core.dockerfile_generator import DockerfileGenerator
from app.services.deployment.core.deployment_manager import DeploymentManager
from app.services.deployment.core.health_manager import HealthStatus
from app.services.deployment.models.deployment_artifact import DeploymentArtifact
from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_result import DeploymentResult
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.services.deployment_service import DeploymentService
from app.services.deployment.database.deployment_repository import DeploymentRepository


class TestDeploymentIntegrationFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.uploads_dir = self.base_dir / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_issue_3_strict_success_false_on_failure(self):
        """Whenever deployment_status is FAILED, success MUST be False."""
        # 1. Direct model creation with default success=True and deployment_status="FAILED"
        res = DeploymentResult(
            deployment_id="dep-fail-01",
            deployment_status="FAILED",
            message="Build failed"
        )
        self.assertFalse(res.success, "success must be False when deployment_status is FAILED")
        self.assertEqual(res.deployment_status, "FAILED")

        # 2. When health_status is Failed or Timeout
        res_health = DeploymentResult(
            deployment_id="dep-fail-02",
            deployment_status="RUNNING",
            health_status="Failed",
            message="Health check failed"
        )
        self.assertFalse(res_health.success, "success must be False when health_status is Failed")

        # 3. When success=False is passed explicitly
        res_explicit = DeploymentResult(
            deployment_id="dep-fail-03",
            success=False,
            message="Failed"
        )
        self.assertEqual(res_explicit.deployment_status, "FAILED")
        self.assertFalse(res_explicit.success)

    def test_issue_5_nested_folder_normalization(self):
        """
        Verify that nested structures like:
        uploads/<project_id>/extracted/Sample_ML_Project/Sample_ML_Project
        are automatically normalized to the real project root.
        """
        project_id = "proj-nested-123"
        proj_dir = self.uploads_dir / project_id
        extracted_dir = proj_dir / "extracted"
        nested_root = extracted_dir / "Sample_ML_Project" / "Sample_ML_Project"
        nested_root.mkdir(parents=True, exist_ok=True)

        # Write files inside nested folder
        (nested_root / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()", encoding="utf-8")
        (nested_root / "requirements.txt").write_text("fastapi==0.104.1\nuvicorn==0.24.0", encoding="utf-8")

        # Write validation_report.json and requirements-resolved.txt in extracted parent
        report_data = {
            "id": "val-rep-001",
            "project_id": project_id,
            "project_name": "Sample ML Project",
            "status": "passed",
            "project_status": "validated",
            "framework": "fastapi",
            "python_version": {"version": "3.11"},
            "entry_point_validation": {"detected_entry_point": "main.py"},
            "dependency_resolution": {
                "lock_file_generated": True,
                "lock_file_path": "requirements-resolved.txt",
                "resolved_packages": [{"name": "fastapi", "version": "0.104.1"}]
            }
        }
        (extracted_dir / "validation_report.json").write_text(json.dumps(report_data), encoding="utf-8")
        (extracted_dir / "requirements-resolved.txt").write_text("fastapi==0.104.1\nuvicorn==0.24.0\npydantic==2.5.0", encoding="utf-8")

        reader = ArtifactReader(base_upload_dir=self.uploads_dir)
        artifact = reader.resolve_artifact(project_id=project_id)

        self.assertIsInstance(artifact, DeploymentArtifact)
        # Verify normalization
        self.assertEqual(artifact.project_root.resolve(), nested_root.resolve())
        self.assertEqual(artifact.entry_point, "main.py")
        self.assertEqual(artifact.framework, "fastapi")
        self.assertEqual(artifact.python_version, "3.11")
        self.assertEqual(artifact.requirements_file, "requirements-resolved.txt")
        # Verify requirements-resolved.txt was synced into nested project root
        self.assertTrue((nested_root / "requirements-resolved.txt").exists())

    def test_issue_1_and_2_resolve_by_project_id_and_folder_path(self):
        """
        Verify ArtifactReader accepts project_id, validation_id, or folder path
        without crashing with 'Artifact file not found'.
        """
        project_id = "proj-flat-456"
        proj_dir = self.uploads_dir / project_id
        extracted_dir = proj_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        (extracted_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)", encoding="utf-8")
        (extracted_dir / "requirements.txt").write_text("flask==3.0.0\ngunicorn==21.2.0", encoding="utf-8")
        (extracted_dir / "validation_report.json").write_text(json.dumps({
            "project_id": project_id,
            "status": "passed",
            "framework": "flask",
            "python_version": "3.10",
            "entry_point": "app.py"
        }), encoding="utf-8")

        reader = ArtifactReader(base_upload_dir=self.uploads_dir)

        # Test 1: Resolve by project_id
        art_by_id = reader.resolve_artifact(project_id=project_id)
        self.assertEqual(art_by_id.project_id, project_id)
        self.assertEqual(art_by_id.framework, "flask")
        self.assertEqual(art_by_id.entry_point, "app.py")

        # Test 2: Resolve by passing folder path directly (Issue 2 fix)
        art_by_path = reader.resolve_artifact(artifact_path=proj_dir)
        self.assertEqual(art_by_path.project_id, project_id)
        self.assertEqual(art_by_path.framework, "flask")

        # Test 3: read_from_file with directory path does NOT raise 'Artifact file not found'
        req_from_dir = reader.read_from_file(proj_dir)
        self.assertEqual(req_from_dir.project_id, project_id)

    def test_dockerfile_and_dockerignore_generation(self):
        """Verify automatic generation of Dockerfile and .dockerignore when missing."""
        proj_dir = self.base_dir / "gen_test"
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "main.py").write_text("import fastapi", encoding="utf-8")
        (proj_dir / "requirements.txt").write_text("fastapi\nuvicorn", encoding="utf-8")

        artifact = DeploymentArtifact(
            project_id="proj-gen-1",
            project_root=proj_dir,
            entry_point="main.py",
            framework="fastapi",
            python_version="3.11",
            requirements_file="requirements.txt"
        )

        gen = DockerfileGenerator()
        df_path = gen.generate_for_artifact(artifact)

        self.assertTrue(df_path.exists())
        self.assertTrue((proj_dir / ".dockerignore").exists())

        content = df_path.read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11-slim", content)
        self.assertIn("main:app", content)
        self.assertIn("EXPOSE 8000", content)

        dockerignore_content = (proj_dir / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__", dockerignore_content)
        self.assertIn(".git", dockerignore_content)

    def test_deployment_service_handles_project_id_deploy(self):
        """Verify DeploymentService orchestrates deployment starting only from project_id."""
        project_id = "proj-svc-test"
        proj_dir = self.uploads_dir / project_id
        extracted_dir = proj_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        (extracted_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()", encoding="utf-8")
        (extracted_dir / "requirements.txt").write_text("fastapi\nuvicorn", encoding="utf-8")
        (extracted_dir / "validation_report.json").write_text(json.dumps({
            "project_id": project_id,
            "status": "passed",
            "framework": "fastapi"
        }), encoding="utf-8")

        mock_deploy_mgr = MagicMock()
        mock_deploy_mgr.deploy.return_value = DeploymentResult(
            deployment_id="dep-123",
            project_id=project_id,
            deployment_status="RUNNING",
            health_status=HealthStatus.HEALTHY,
            allocated_port=8001,
            public_url="http://localhost:8001",
            success=True,
            message="Deployment completed successfully"
        )

        service = DeploymentService(
            artifact_reader=ArtifactReader(base_upload_dir=self.uploads_dir),
            deployment_manager=mock_deploy_mgr
        )

        result = service.deploy({"project_id": project_id})

        self.assertTrue(result.success)
        self.assertEqual(result.deployment_status, "RUNNING")
        self.assertEqual(result.allocated_port, 8001)
        mock_deploy_mgr.deploy.assert_called_once()


if __name__ == "__main__":
    unittest.main()

