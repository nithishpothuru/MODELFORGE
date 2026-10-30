import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.deployment.models.deployment_result import DeploymentResult
from app.services.deployment.core.health_manager import HealthStatus

client = TestClient(app)


class TestDeploymentAPIRoutes(unittest.TestCase):
    def test_deploy_with_missing_identifier(self):
        """When neither project_id, validation_id, nor artifact_path is sent, returns 400 with success=False."""
        response = client.post("/api/v1/deploy", json={})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["deployment_status"], "FAILED")
        self.assertIn("Missing", data["message"])

    def test_deploy_with_nonexistent_project_id(self):
        """When project_id does not exist, returns 400 with success=False and clear error."""
        response = client.post("/api/v1/deploy", json={"project_id": "nonexistent-project-999"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["deployment_status"], "FAILED")
        self.assertIn("not found", data["message"].lower())

    @patch("app.api.routes.deployment.deployment_service.deploy")
    def test_deploy_success_with_project_id(self, mock_deploy):
        """When project_id is deployed successfully, returns 201 with success=True and deployment details."""
        mock_deploy.return_value = DeploymentResult(
            deployment_id="dep-api-123",
            project_id="proj-valid-001",
            project_name="Sample ML Project",
            image_name="modelforge_proj_valid_001",
            image_id="sha256:abc1234",
            container_id="cont-5678",
            allocated_port=8001,
            deployment_status="RUNNING",
            health_status="Healthy",
            public_url="http://localhost:8001",
            success=True,
            message="Deployment completed successfully"
        )

        response = client.post("/api/v1/deploy", json={"project_id": "proj-valid-001"})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["deployment_status"], "RUNNING")
        self.assertEqual(data["health_status"], "Healthy")
        self.assertEqual(data["allocated_port"], 8001)
        self.assertEqual(data["public_url"], "http://localhost:8001")

    @patch("app.api.routes.deployment.deployment_service.deploy")
    def test_deploy_success_with_validation_id(self, mock_deploy):
        """When validation_id is provided, router accepts and processes it."""
        mock_deploy.return_value = DeploymentResult(
            deployment_id="dep-api-456",
            project_id="proj-from-val-002",
            deployment_status="RUNNING",
            health_status="Healthy",
            allocated_port=8002,
            public_url="http://localhost:8002",
            success=True,
            message="Deployment completed successfully"
        )

        response = client.post("/api/v1/deploy", json={"validation_id": "val-rep-002"})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["deployment_status"], "RUNNING")
        self.assertEqual(data["allocated_port"], 8002)


if __name__ == "__main__":
    unittest.main()

