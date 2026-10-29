import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.ci.pipeline import CIPipeline
from app.services.ci.validator import DryRunValidator
from app.services.project_service import project_service


class TestDependencyResolution(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        # Use DryRunValidator for fast, deterministic unit testing
        self.validator = DryRunValidator()
        self.pipeline = CIPipeline(validator=self.validator)

    async def _run_pipeline(self, project_id: str, extract_dir: Path):
        return await self.pipeline.run_pipeline(
            project_id=project_id,
            extract_dir=extract_dir,
        )

    def test_missing_requirements_generates_pinned_file(self):
        import asyncio

        # 1. Project directory with unpinned imports
        proj_dir = self.temp_path / "proj_no_req"
        proj_dir.mkdir(parents=True)
        (proj_dir / "main.py").write_text("""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
""", encoding="utf-8")

        # 2. Run pipeline
        report = asyncio.run(self._run_pipeline("test-proj-1", proj_dir))

        # 3. Assertions
        self.assertIn(report.status.value, ["passed", "warning"])
        self.assertEqual(report.project_status.value, "validated")
        self.assertFalse(report.requirements_existed)
        self.assertTrue(report.requirements_generated)

        # Check Python version stage
        self.assertTrue(report.python_version.is_inferred)
        self.assertIn(report.python_version.version, ["3.10", "3.11", "3.12"])

        # Check resolution stage
        self.assertEqual(report.dependency_resolution.status, "passed")
        self.assertTrue(report.dependency_resolution.lock_file_generated)
        self.assertEqual(report.dependency_resolution.lock_file_path, "requirements.txt")
        self.assertGreater(len(report.dependency_resolution.resolved_packages), 0)

        # Check actual generated requirements.txt file on disk
        req_file = proj_dir / "requirements.txt"
        self.assertTrue(req_file.exists())
        req_content = req_file.read_text(encoding="utf-8")

        # Must be strictly pinned (package==version), not unpinned
        self.assertIn("numpy==", req_content)
        self.assertIn("pandas==", req_content)
        self.assertIn("scikit-learn==", req_content)
        self.assertIn("Target Python Version:", req_content)

    def test_existing_requirements_preserved_without_overwriting(self):
        import asyncio

        # 1. Project directory with an existing unpinned requirements.txt
        proj_dir = self.temp_path / "proj_with_req"
        proj_dir.mkdir(parents=True)
        (proj_dir / "main.py").write_text("import joblib\n", encoding="utf-8")
        original_req_text = "# Original developer requirements\njoblib\n"
        (proj_dir / "requirements.txt").write_text(original_req_text, encoding="utf-8")

        # 2. Run pipeline
        report = asyncio.run(self._run_pipeline("test-proj-2", proj_dir))

        # 3. Assertions
        self.assertEqual(report.status.value, "passed")
        self.assertTrue(report.requirements_existed)
        self.assertFalse(report.requirements_generated)

        # Original requirements.txt MUST be preserved exactly!
        current_req_text = (proj_dir / "requirements.txt").read_text(encoding="utf-8")
        self.assertEqual(current_req_text, original_req_text)

        # A separate resolved file must be generated
        resolved_file = proj_dir / "requirements-resolved.txt"
        self.assertTrue(resolved_file.exists())
        resolved_content = resolved_file.read_text(encoding="utf-8")
        self.assertIn("joblib==", resolved_content)
        self.assertEqual(report.dependency_resolution.lock_file_path, "requirements-resolved.txt")

    def test_existing_pinned_requirements_retained(self):
        import asyncio

        # 1. Project directory with exact pin
        proj_dir = self.temp_path / "proj_pinned"
        proj_dir.mkdir(parents=True)
        (proj_dir / "app.py").write_text("import fastapi\n", encoding="utf-8")
        (proj_dir / "requirements.txt").write_text("fastapi==0.104.1\n", encoding="utf-8")

        # 2. Run pipeline
        report = asyncio.run(self._run_pipeline("test-proj-3", proj_dir))

        self.assertEqual(report.status.value, "passed")
        # Pinned version fastapi==0.104.1 must be retained in resolution
        resolved_dict = {p.name: p.version for p in report.dependency_resolution.resolved_packages}
        self.assertEqual(resolved_dict.get("fastapi"), "0.104.1")

    def test_resolver_conflict_reported(self):
        import asyncio

        # 1. Project directory with conflicting version constraints
        proj_dir = self.temp_path / "proj_conflict"
        proj_dir.mkdir(parents=True)
        (proj_dir / "main.py").write_text("import scikit_learn\n", encoding="utf-8")
        # Conflicting declarations for the same package
        (proj_dir / "requirements.txt").write_text("scikit-learn==1.2.0\nscikit-learn==1.5.0\n", encoding="utf-8")

        # 2. Run pipeline
        report = asyncio.run(self._run_pipeline("test-proj-conflict", proj_dir))

        # 3. Assertions
        self.assertEqual(report.status.value, "failed")
        self.assertEqual(report.project_status.value, "validation_failed")
        self.assertEqual(report.dependency_resolution.status, "failed")
        self.assertGreater(len(report.dependency_resolution.conflicts), 0)
        self.assertTrue(any("conflicting" in c.lower() for c in report.dependency_resolution.conflicts))
        # Must not generate lock file on failure
        self.assertFalse(report.dependency_resolution.lock_file_generated)

    def test_structured_validation_report_complete_stages(self):
        import asyncio

        proj_dir = self.temp_path / "proj_complete"
        proj_dir.mkdir(parents=True)
        (proj_dir / "pyproject.toml").write_text("""
[project]
requires-python = ">=3.11"
""", encoding="utf-8")
        (proj_dir / "main.py").write_text("""
from fastapi import FastAPI
app = FastAPI()
""", encoding="utf-8")
        (proj_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

        report = asyncio.run(self._run_pipeline("test-proj-complete", proj_dir))

        # Check all 8 required stages in report
        # 1. Python version detection
        self.assertEqual(report.python_version.version, "3.11")
        self.assertFalse(report.python_version.is_inferred)
        self.assertEqual(report.python_version.source, "pyproject.toml")

        # 2. Dependency discovery
        self.assertGreater(len(report.dependencies), 0)

        # 3. Dependency resolution
        self.assertEqual(report.dependency_resolution.status, "passed")

        # 4. Dependency validation
        self.assertEqual(report.dependency_validation.status, "passed")

        # 5. Syntax check
        self.assertEqual(report.syntax_validation.status, "passed")

        # 6. Import checks
        self.assertEqual(report.import_validation.status, "passed")

        # 7. Entry point check
        self.assertEqual(report.entry_point_validation.status, "passed")
        self.assertEqual(report.entry_point_validation.detected_entry_point, "main.py")

        # Check summary formatting
        self.assertIn("Python 3.11", report.summary)
        self.assertIn("Validation", report.summary)


if __name__ == "__main__":
    unittest.main()
