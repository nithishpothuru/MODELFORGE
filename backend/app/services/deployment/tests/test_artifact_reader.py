"""
Unit tests for ArtifactReader.
"""

import json
import tempfile
import unittest
from pathlib import Path

from app.services.deployment.core.artifact_reader import ArtifactReader, ArtifactValidationError
from app.services.deployment.models.deployment_request import DeploymentRequest


class TestArtifactReader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        (self.workspace / "requirements.txt").write_text("numpy\npandas", encoding="utf-8")
        (self.workspace / "main.py").write_text("print('hello')", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_from_valid_dict(self):
        data = {
            "project_id": "proj-123",
            "project_name": "Test ML Model",
            "working_directory": str(self.workspace),
            "framework": "fastapi",
            "python_version": "3.11",
            "entry_point": "main.py",
            "requirements_file": "requirements.txt",
            "status": "passed"
        }
        req = ArtifactReader.read_from_dict(data)
        self.assertIsInstance(req, DeploymentRequest)
        self.assertEqual(req.project_id, "proj-123")
        self.assertEqual(req.project_name, "Test ML Model")
        self.assertEqual(req.framework, "fastapi")
        self.assertEqual(req.python_version, "3.11")
        self.assertEqual(req.entry_point, "main.py")
        self.assertEqual(req.working_directory, str(self.workspace.resolve()))
        self.assertTrue(req.deployment_ready)

    def test_read_from_file(self):
        artifact_path = self.workspace / "validation_report.json"
        report_data = {
            "project_id": "proj-file-456",
            "status": "passed",
            "project_status": "validated",
            "working_directory": str(self.workspace),
            "framework": "flask",
            "python_version": {"version": "3.10"},
            "entry_point_validation": {"detected_entry_point": "app.py"},
            "dependency_resolution": {"lock_file_path": "requirements.txt"}
        }
        artifact_path.write_text(json.dumps(report_data), encoding="utf-8")

        req = ArtifactReader.read_from_file(artifact_path)
        self.assertEqual(req.project_id, "proj-file-456")
        self.assertEqual(req.framework, "flask")
        self.assertEqual(req.python_version, "3.10")
        self.assertEqual(req.entry_point, "app.py")

    def test_read_from_json_string(self):
        json_str = json.dumps({
            "project_id": "proj-json-789",
            "working_directory": str(self.workspace),
            "framework": "cli",
            "status": "passed"
        })
        req = ArtifactReader.read_from_json(json_str)
        self.assertEqual(req.project_id, "proj-json-789")
        self.assertEqual(req.framework, "cli")

    def test_missing_project_id_raises_error(self):
        data = {
            "working_directory": str(self.workspace),
            "status": "passed"
        }
        with self.assertRaises(ArtifactValidationError):
            ArtifactReader.read_from_dict(data)

    def test_missing_working_directory_raises_error(self):
        data = {
            "project_id": "proj-no-dir",
            "status": "passed"
        }
        with self.assertRaises(ArtifactValidationError):
            ArtifactReader.read_from_dict(data)

    def test_failed_validation_status_raises_error(self):
        data = {
            "project_id": "proj-failed",
            "working_directory": str(self.workspace),
            "status": "failed"
        }
        with self.assertRaises(ArtifactValidationError):
            ArtifactReader.read_from_dict(data)

    def test_nonexistent_directory_raises_error(self):
        data = {
            "project_id": "proj-fake-dir",
            "working_directory": "/non/existent/path/xyz123",
            "status": "passed"
        }
        with self.assertRaises(ArtifactValidationError):
            ArtifactReader.read_from_dict(data)


if __name__ == "__main__":
    unittest.main()
