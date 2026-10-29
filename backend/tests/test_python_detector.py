import tempfile
import unittest
from pathlib import Path

from app.services.ci.python_detector import PythonVersionDetector


class TestPythonVersionDetector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        self.detector = PythonVersionDetector(self.project_path)

    def test_detect_from_pyproject_pep621(self):
        (self.project_path / "pyproject.toml").write_text("""
[project]
name = "my-model"
version = "0.1.0"
requires-python = ">=3.10"
""", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(info.version, "3.10")
        self.assertFalse(info.is_inferred)
        self.assertEqual(info.source, "pyproject.toml")
        self.assertEqual(len(info.conflicts), 0)

    def test_detect_from_pyproject_poetry(self):
        (self.project_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "poetry-model"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.12"
numpy = "^1.26"
""", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(info.version, "3.12")
        self.assertFalse(info.is_inferred)
        self.assertEqual(info.source, "pyproject.toml")

    def test_detect_from_pipfile(self):
        (self.project_path / "Pipfile").write_text("""
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
scikit-learn = "*"

[requires]
python_version = "3.10"
""", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(info.version, "3.10")
        self.assertFalse(info.is_inferred)
        self.assertEqual(info.source, "Pipfile")

    def test_detect_from_python_version_file(self):
        (self.project_path / ".python-version").write_text("3.11.4\n", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(info.version, "3.11")
        self.assertFalse(info.is_inferred)
        self.assertEqual(info.source, ".python-version")

    def test_detect_from_dockerfile(self):
        (self.project_path / "Dockerfile").write_text("""
FROM python:3.9-slim
WORKDIR /app
COPY . /app
CMD ["python", "main.py"]
""", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(info.version, "3.9")
        self.assertFalse(info.is_inferred)
        self.assertEqual(info.source, "Dockerfile")

    def test_detect_from_runtime_txt(self):
        (self.project_path / "runtime.txt").write_text("python-3.12.1\n", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(info.version, "3.12")
        self.assertFalse(info.is_inferred)
        self.assertEqual(info.source, "runtime.txt")

    def test_conflicting_declarations_detected(self):
        # pyproject.toml specifies 3.11, but .python-version specifies 3.9
        (self.project_path / "pyproject.toml").write_text("""
[project]
name = "conflicted-model"
requires-python = ">=3.11"
""", encoding="utf-8")
        (self.project_path / ".python-version").write_text("3.9\n", encoding="utf-8")

        info = self.detector.detect_version()
        self.assertEqual(len(info.conflicts), 1)
        self.assertIn("Conflicting Python version declaration", info.conflicts[0])
        self.assertIn("pyproject.toml", info.conflicts[0])
        self.assertIn(".python-version", info.conflicts[0])

    def test_infer_version_default_candidate_when_undeclared(self):
        # No version declared anywhere
        py_file = self.project_path / "script.py"
        py_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

        info = self.detector.detect_version(python_files=[py_file])
        self.assertTrue(info.is_inferred)
        self.assertIn(info.version, ["3.10", "3.11", "3.12"])
        self.assertIn("inferred", info.source)

    def test_infer_version_from_modern_syntax_match_case(self):
        # Python code uses match/case (introduced in 3.10)
        py_file = self.project_path / "handler.py"
        py_file.write_text("""
def process_command(cmd):
    match cmd:
        case 'start':
            return True
        case _:
            return False
""", encoding="utf-8")

        info = self.detector.detect_version(python_files=[py_file])
        self.assertTrue(info.is_inferred)
        # Should be at least 3.10
        minor = int(info.version.split(".")[1])
        self.assertGreaterEqual(minor, 10)
        self.assertIn(">= 3.10", info.source)

    def test_infer_version_from_heavy_ml_packages(self):
        # When project uses modern deep learning packages
        py_file = self.project_path / "train.py"
        py_file.write_text("import torch\nprint(torch.__version__)\n", encoding="utf-8")

        info = self.detector.detect_version(
            python_files=[py_file],
            detected_packages=["torch", "transformers"],
        )
        self.assertTrue(info.is_inferred)
        minor = int(info.version.split(".")[1])
        self.assertGreaterEqual(minor, 10)


if __name__ == "__main__":
    unittest.main()
