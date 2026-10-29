import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.ci.validator import DryRunValidator
from app.services.project_service import project_service


class TestCIPipelineAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Use fast, deterministic DryRunValidator for unit testing
        project_service.ci_pipeline.validator = DryRunValidator()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def test_validation_missing_upload_error(self):
        # 1. Create a project
        create_res = self.client.post("/api/v1/projects", json={
            "title": "Unuploaded Model",
            "framework": "Scikit-learn",
        })
        self.assertEqual(create_res.status_code, 201)
        project_id = create_res.json()["id"]

        # 2. Try validating without uploading/extracting
        val_res = self.client.post(f"/api/v1/projects/{project_id}/validate")
        self.assertEqual(val_res.status_code, 400)
        self.assertIn("no extracted files", val_res.json()["detail"].lower())

    def test_validation_not_found(self):
        val_res = self.client.post("/api/v1/projects/non-existent-id/validate")
        self.assertEqual(val_res.status_code, 404)

        get_res = self.client.get("/api/v1/projects/non-existent-id/validation")
        self.assertEqual(get_res.status_code, 404)

    def test_full_pipeline_with_existing_requirements(self):
        # 1. Create project
        create_res = self.client.post("/api/v1/projects", json={
            "title": "Iris Classifier",
            "framework": "Scikit-learn",
        })
        project_id = create_res.json()["id"]

        # 2. Setup project extraction directory
        proj_dir = self.temp_path / project_id
        proj_dir.mkdir(parents=True)
        (proj_dir / "main.py").write_text("""
from fastapi import FastAPI
import numpy as np
from sklearn.linear_model import LogisticRegression

app = FastAPI()

@app.get('/predict')
def predict():
    return {'pred': 1}
""")
        (proj_dir / "requirements.txt").write_text("""
fastapi>=0.100.0
numpy>=1.24.0
scikit-learn>=1.3.0
""")
        project_service._projects[project_id]["extracted_path"] = str(proj_dir)
        project_service._projects[project_id]["status"] = "uploaded"

        # 3. Validate
        val_res = self.client.post(f"/api/v1/projects/{project_id}/validate")
        self.assertEqual(val_res.status_code, 200)
        report = val_res.json()

        self.assertEqual(report["project_id"], project_id)
        self.assertIn(report["status"], ["passed", "warning"])
        self.assertEqual(report["project_status"], "validated")
        self.assertTrue(report["requirements_existed"])
        self.assertFalse(report["requirements_generated"])
        self.assertEqual(report["syntax_validation"]["status"], "passed")
        self.assertEqual(report["entry_point_validation"]["entry_point_type"], "fastapi")
        self.assertEqual(report["entry_point_validation"]["detected_entry_point"], "main.py")

        # 4. Check project status update
        proj_get = self.client.get(f"/api/v1/projects/{project_id}")
        self.assertEqual(proj_get.json()["status"], "validated")
        self.assertEqual(proj_get.json()["main_file"], "main.py")

        # 5. Fetch latest validation via GET /validation
        get_val = self.client.get(f"/api/v1/projects/{project_id}/validation")
        self.assertEqual(get_val.status_code, 200)
        self.assertEqual(get_val.json()["id"], report["id"])

    def test_full_pipeline_with_missing_requirements_inference(self):
        # 1. Create project
        create_res = self.client.post("/api/v1/projects", json={
            "title": "Vision Model No Req",
        })
        project_id = create_res.json()["id"]

        # 2. Setup project extraction directory without requirements.txt
        proj_dir = self.temp_path / project_id
        proj_dir.mkdir(parents=True)
        (proj_dir / "predict.py").write_text("""
import cv2
import torch
import torchvision
import numpy as np

def predict(img):
    return [0.9]
""")
        project_service._projects[project_id]["extracted_path"] = str(proj_dir)
        project_service._projects[project_id]["status"] = "uploaded"

        # 3. Validate
        val_res = self.client.post(f"/api/v1/projects/{project_id}/validate")
        self.assertEqual(val_res.status_code, 200)
        report = val_res.json()

        self.assertFalse(report["requirements_existed"])
        self.assertTrue(report["requirements_generated"])
        self.assertEqual(report["project_status"], "validated")

        # Check generated requirements.txt file exists on disk
        req_file = proj_dir / "requirements.txt"
        self.assertTrue(req_file.exists())
        req_text = req_file.read_text()
        self.assertIn("opencv-python", req_text)
        self.assertIn("torch", req_text)
        self.assertIn("torchvision", req_text)

    def test_full_pipeline_with_syntax_error_failure(self):
        # 1. Create project
        create_res = self.client.post("/api/v1/projects", json={
            "title": "Broken Syntax Project",
        })
        project_id = create_res.json()["id"]

        # 2. Setup directory with a syntax error
        proj_dir = self.temp_path / project_id
        proj_dir.mkdir(parents=True)
        (proj_dir / "app.py").write_text("def broken_syntax(:\n    pass")
        (proj_dir / "requirements.txt").write_text("fastapi\n")

        project_service._projects[project_id]["extracted_path"] = str(proj_dir)
        project_service._projects[project_id]["status"] = "uploaded"

        # 3. Validate
        val_res = self.client.post(f"/api/v1/projects/{project_id}/validate")
        self.assertEqual(val_res.status_code, 200)
        report = val_res.json()

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["project_status"], "validation_failed")
        self.assertEqual(report["syntax_validation"]["status"], "failed")
        self.assertGreater(len(report["errors"]), 0)

        # 4. Check project status reflects failure
        proj_get = self.client.get(f"/api/v1/projects/{project_id}")
        self.assertEqual(proj_get.json()["status"], "validation_failed")


if __name__ == "__main__":
    unittest.main()
