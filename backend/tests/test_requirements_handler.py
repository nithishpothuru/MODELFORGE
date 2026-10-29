import tempfile
import unittest
from pathlib import Path

from app.services.ci.requirements import RequirementsHandler


class TestRequirementsHandler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        self.handler = RequirementsHandler(self.project_path)

    def test_parse_valid_requirements(self):
        req_content = """
# Core ML stack
numpy>=1.24.0
scikit-learn==1.3.0
fastapi>=0.100.0
"""
        req_file = self.project_path / "requirements.txt"
        req_file.write_text(req_content)

        deps, syntax_errors, warnings = self.handler.parse_requirements(req_file)

        self.assertEqual(len(syntax_errors), 0)
        self.assertEqual(len(deps), 3)

        dep_dict = {d.name: d for d in deps}
        self.assertIn("numpy", dep_dict)
        self.assertEqual(dep_dict["numpy"].version_spec, ">=1.24.0")
        self.assertEqual(dep_dict["scikit-learn"].version_spec, "==1.3.0")
        self.assertFalse(dep_dict["numpy"].inferred)

    def test_detect_duplicate_and_malformed_requirements(self):
        req_content = """
numpy>=1.20.0
numpy<2.0.0
this is not a valid requirement specifier %%%
"""
        req_file = self.project_path / "requirements.txt"
        req_file.write_text(req_content)

        deps, syntax_errors, warnings = self.handler.parse_requirements(req_file)

        # Malformed line should be detected
        self.assertGreater(len(syntax_errors), 0)
        self.assertTrue(any("Malformed" in err for err in syntax_errors))

        # Duplicate package should produce a warning
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("Duplicate" in w for w in warnings))

    def test_infer_missing_requirements_with_mappings(self):
        # Create Python files with imports needing canonical mapping
        file1 = """
import cv2
import sklearn.metrics as metrics
import PIL.Image as Image
import yaml
import os  # stdlib
import sys # stdlib
"""
        file2 = """
import torch
import torchvision
from .local_module import helper  # relative import
import helper_util  # local module
"""
        (self.project_path / "train.py").write_text(file1)
        (self.project_path / "model.py").write_text(file2)
        (self.project_path / "helper_util.py").write_text("def helper(): pass")

        py_files = [
            self.project_path / "train.py",
            self.project_path / "model.py",
            self.project_path / "helper_util.py",
        ]

        inferred = self.handler.infer_dependencies_from_imports(py_files)
        inferred_names = {d.name for d in inferred}

        # Canonical mapping checks
        self.assertIn("opencv-python", inferred_names)  # mapped from cv2
        self.assertIn("scikit-learn", inferred_names)   # mapped from sklearn
        self.assertIn("Pillow", inferred_names)         # mapped from PIL
        self.assertIn("PyYAML", inferred_names)         # mapped from yaml
        self.assertIn("torch", inferred_names)
        self.assertIn("torchvision", inferred_names)

        # Standard library and local exclusions
        self.assertNotIn("os", inferred_names)
        self.assertNotIn("sys", inferred_names)
        self.assertNotIn("helper_util", inferred_names)

        # Generate requirements.txt
        gen_path = self.handler.generate_requirements_file(inferred)
        self.assertTrue(gen_path.exists())

        content = gen_path.read_text()
        self.assertIn("Automatically Inferred Requirements", content)
        self.assertIn("scikit-learn", content)
        self.assertIn("opencv-python", content)

    def test_extract_dependencies_from_pyproject_toml(self):
        pyproject_content = """
[project]
name = "my-ml-model"
version = "0.1.0"
dependencies = [
    "torch>=2.0.0",
    "transformers>=4.30.0",
]
"""
        (self.project_path / "pyproject.toml").write_text(pyproject_content)

        deps, sources = self.handler.extract_from_metadata_files()
        self.assertEqual(len(deps), 2)
        dep_dict = {d.name: d for d in deps}
        self.assertIn("torch", dep_dict)
        self.assertIn("transformers", dep_dict)
        self.assertEqual(dep_dict["torch"].version_spec, ">=2.0.0")


if __name__ == "__main__":
    unittest.main()
