import io
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.services.storage_service import StorageService, storage_service


class TestStorageSafety(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = StorageService()
        self.storage.upload_dir = Path(self.temp_dir)

    def test_safe_filename(self):
        self.assertEqual(self.storage._safe_filename("model.pkl"), "model.pkl")
        self.assertEqual(self.storage._safe_filename("path/to/archive.zip"), "archive.zip")
        self.assertEqual(self.storage._safe_filename("C:\\Users\\test\\file.zip"), "file.zip")

        with self.assertRaises(ValueError):
            self.storage._safe_filename("")
        with self.assertRaises(ValueError):
            self.storage._safe_filename("..")
        with self.assertRaises(ValueError):
            self.storage._safe_filename(".")

    def test_corrupted_zip_rejected(self):
        corrupted_bytes = b"PK\x03\x04this is definitely not a valid zip archive!"
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(corrupted_bytes)
        self.assertIn("not a valid ZIP archive", str(ctx.exception))

    def test_empty_zip_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            pass
        buf.seek(0)
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(buf.getvalue())
        self.assertIn("empty", str(ctx.exception).lower())

    def test_path_traversal_dot_dot_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.py", "print('hacked')")
        buf.seek(0)
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(buf.getvalue())
        self.assertIn("unsafe file path", str(ctx.exception))

    def test_path_traversal_absolute_path_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("/etc/passwd", "root:x:0:0")
        buf.seek(0)
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(buf.getvalue())
        self.assertIn("unsafe file path", str(ctx.exception))

    def test_path_traversal_drive_letter_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("C:/Windows/System32/evil.dll", "data")
        buf.seek(0)
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(buf.getvalue())
        self.assertIn("unsafe file path", str(ctx.exception))

    def test_symlink_archive_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            info = zipfile.ZipInfo("symlink_target")
            # Set UNIX symlink attribute
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, "/etc/shadow")
        buf.seek(0)
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(buf.getvalue())
        self.assertIn("symbolic link", str(ctx.exception).lower())

    def test_null_byte_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("test_file.py", "print(1)")
        raw_data = buf.getvalue().replace(b"test_file.py", b"test_\x00le.py")
        with self.assertRaises(ValueError) as ctx:
            self.storage._validate_zip(raw_data)
        self.assertTrue(any(msg in str(ctx.exception) for msg in ["unsafe file path", "not a valid ZIP archive"]))

    def test_valid_zip_extraction(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("main.py", "print('hello world')")
            zf.writestr("model/weights.bin", b"binarydata")
        buf.seek(0)

        # Validate
        self.storage._validate_zip(buf.getvalue())

        # Save to temp file and extract
        zip_file = Path(self.temp_dir) / "test.zip"
        zip_file.write_bytes(buf.getvalue())

        extract_dir = Path(self.temp_dir) / "extracted"
        extracted_files = self.storage.extract_zip(zip_file, extract_to=extract_dir)

        self.assertIn("main.py", [f.replace("\\", "/") for f in extracted_files])
        self.assertIn("model/weights.bin", [f.replace("\\", "/") for f in extracted_files])
        self.assertTrue((extract_dir / "main.py").exists())
        self.assertTrue((extract_dir / "model" / "weights.bin").exists())


if __name__ == "__main__":
    unittest.main()
