import tempfile
import unittest
from pathlib import Path

from app.services.ci.analyzer import ProjectAnalyzer


class TestProjectAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)

    def test_ignore_virtual_envs_and_caches(self):
        # Create virtual envs and caches
        (self.project_path / ".venv" / "Lib").mkdir(parents=True)
        (self.project_path / ".venv" / "Lib" / "secret.py").write_text("evil = 1")
        (self.project_path / "__pycache__").mkdir(parents=True)
        (self.project_path / "__pycache__" / "cached.pyc").write_text("data")
        (self.project_path / ".git").mkdir(parents=True)
        (self.project_path / ".git" / "config").write_text("git config")

        # Create genuine files
        (self.project_path / "main.py").write_text("import numpy as np\nprint('hello')")
        (self.project_path / "requirements.txt").write_text("numpy\n")

        analyzer = ProjectAnalyzer(self.project_path)
        info, python_files = analyzer.scan_structure()

        self.assertEqual(info.total_python_files, 1)
        self.assertIn("main.py", info.python_files)
        self.assertNotIn(".venv/Lib/secret.py", [f.replace("\\", "/") for f in info.python_files])
        self.assertTrue(info.has_requirements)
        self.assertGreater(info.ignored_paths_count, 0)

    def test_ml_framework_detection(self):
        # Create ML project with PyTorch and Scikit-Learn
        code = """
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score
import pandas as pd
"""
        (self.project_path / "model.py").write_text(code)

        analyzer = ProjectAnalyzer(self.project_path)
        info, python_files = analyzer.scan_structure()

        self.assertTrue(info.is_ml_project)
        self.assertIn("PyTorch", info.detected_frameworks)
        self.assertIn("Scikit-learn", info.detected_frameworks)
        self.assertIn("pandas", info.detected_frameworks)

    def test_non_ml_project_distinction(self):
        # Pure web/utility script, not ML
        code = """
import os
import sys
import json

def process_data():
    return {'status': 'ok'}
"""
        (self.project_path / "script.py").write_text(code)

        analyzer = ProjectAnalyzer(self.project_path)
        info, python_files = analyzer.scan_structure()

        self.assertFalse(info.is_ml_project)
        self.assertEqual(info.detected_frameworks, [])

    def test_entry_point_detection_fastapi(self):
        code = """
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def root():
    return {'message': 'ModelForge'}
"""
        (self.project_path / "app.py").write_text(code)

        analyzer = ProjectAnalyzer(self.project_path)
        info, python_files = analyzer.scan_structure()
        entry_file, entry_type, details = analyzer.detect_main_entry_point(python_files)

        self.assertEqual(entry_file, "app.py")
        self.assertEqual(entry_type, "fastapi")
        self.assertIn("app", details["fastapi_app_instances"])

    def test_entry_point_detection_inference_function(self):
        code = """
def load_model():
    return None

def predict(input_features):
    return [0.95]
"""
        (self.project_path / "inference.py").write_text(code)

        analyzer = ProjectAnalyzer(self.project_path)
        info, python_files = analyzer.scan_structure()
        entry_file, entry_type, details = analyzer.detect_main_entry_point(python_files)

        self.assertEqual(entry_file, "inference.py")
        self.assertEqual(entry_type, "inference_function")
        self.assertIn("predict", details["inference_functions"])


if __name__ == "__main__":
    unittest.main()
