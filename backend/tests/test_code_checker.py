import tempfile
import unittest
from pathlib import Path

from app.services.ci.code_checker import CodeChecker


class TestCodeChecker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        self.checker = CodeChecker(self.project_path)

    def test_syntax_check_valid_files(self):
        code1 = "def add(a, b):\n    return a + b\n"
        code2 = "class Model:\n    def __init__(self):\n        pass\n"

        f1 = self.project_path / "mod1.py"
        f2 = self.project_path / "mod2.py"
        f1.write_text(code1)
        f2.write_text(code2)

        result = self.checker.check_syntax([f1, f2])
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.total_files, 2)
        self.assertEqual(result.valid_files, 2)
        self.assertEqual(len(result.syntax_errors), 0)

    def test_syntax_check_detects_syntax_error(self):
        broken_code = "def broken_func(:\n    return 42\n"
        f = self.project_path / "broken.py"
        f.write_text(broken_code)

        result = self.checker.check_syntax([f])
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.total_files, 1)
        self.assertEqual(result.valid_files, 0)
        self.assertEqual(len(result.syntax_errors), 1)

        err = result.syntax_errors[0]
        self.assertEqual(err.file, "broken.py")
        self.assertEqual(err.line, 1)
        self.assertTrue(bool(err.error_message))

    def test_detect_missing_undeclared_imports(self):
        code = """
import numpy as np
import scipy.stats as stats
import unregistered_library
import os  # stdlib
"""
        f = self.project_path / "app.py"
        f.write_text(code)

        declared = ["numpy"]
        local_mods = set()

        missing = self.checker.check_missing_imports([f], declared, local_mods)

        # scipy and unregistered_library should be detected as missing from requirements
        self.assertTrue(any("scipy" in m for m in missing))
        self.assertTrue(any("unregistered_library" in m for m in missing))
        # numpy is declared so it shouldn't be reported missing
        self.assertFalse(any("numpy" in m for m in missing))
        # os is stdlib so it shouldn't be reported missing
        self.assertFalse(any("os" in m for m in missing))

    def test_validate_entry_point_fastapi(self):
        details = {
            "fastapi_app_instances": ["app"],
            "has_main_guard": True,
        }
        res = self.checker.validate_entry_point("app.py", "fastapi", details, syntax_errors=[])
        self.assertEqual(res.status, "passed")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.entry_point_type, "fastapi")


if __name__ == "__main__":
    unittest.main()
