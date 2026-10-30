"""
Unit tests for Sprint 1 Deployment Foundation Models:
DeploymentRequest, DeploymentResult, DeploymentStatus, and ContainerInfo.
"""

import unittest
from datetime import datetime, timezone

from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_result import DeploymentResult
from app.services.deployment.models.container_info import ContainerInfo


class TestFoundationModels(unittest.TestCase):
    def test_deployment_status_enum_values(self):
        """Ensure all required DeploymentStatus states are defined."""
        expected_states = {
            "PENDING",
            "VALIDATED",
            "DOCKERFILE_GENERATED",
            "IMAGE_BUILDING",
            "IMAGE_READY",
            "CONTAINER_STARTING",
            "CONTAINER_RUNNING",
            "HEALTH_CHECKING",
            "RUNNING",
            "FAILED",
            "STOPPED",
            "REMOVED",
        }
        actual_states = {s.value for s in DeploymentStatus}
        self.assertEqual(expected_states, actual_states)

    def test_deployment_status_helpers(self):
        """Test terminal and active state helper methods."""
        self.assertTrue(DeploymentStatus.RUNNING.is_terminal())
        self.assertTrue(DeploymentStatus.FAILED.is_terminal())
        self.assertFalse(DeploymentStatus.PENDING.is_terminal())

        self.assertTrue(DeploymentStatus.RUNNING.is_active())
        self.assertTrue(DeploymentStatus.HEALTH_CHECKING.is_active())
        self.assertFalse(DeploymentStatus.STOPPED.is_active())

    def test_deployment_request_model(self):
        """Verify DeploymentRequest instantiation and field defaults."""
        req = DeploymentRequest(
            project_id="proj_ml_99",
            project_name="Fraud Detection Model",
            framework="fastapi",
            python_version="3.11",
            entry_point="main.py",
            requirements_file="requirements.txt",
            working_directory="/app/projects/proj_ml_99",
            deployment_ready=True
        )
        self.assertEqual(req.project_id, "proj_ml_99")
        self.assertEqual(req.project_name, "Fraud Detection Model")
        self.assertEqual(req.framework, "fastapi")
        self.assertEqual(req.python_version, "3.11")
        self.assertEqual(req.entry_point, "main.py")
        self.assertEqual(req.requirements_file, "requirements.txt")
        self.assertEqual(req.working_directory, "/app/projects/proj_ml_99")
        self.assertEqual(req.workspace_path, "/app/projects/proj_ml_99")
        self.assertTrue(req.deployment_ready)
        self.assertIsNotNone(req.deployment_id)
        self.assertEqual(req.target_port, 8000)
        self.assertEqual(req.health_endpoint, "/health")
        self.assertTrue(req.enable_nginx)

    def test_deployment_result_model(self):
        """Verify DeploymentResult fields and serialization."""
        now_str = datetime.now(timezone.utc).isoformat()
        res = DeploymentResult(
            deployment_id="dep_007",
            image_name="modelforge_dep_007",
            container_id="container_sha_123",
            allocated_port=8080,
            deployment_status=DeploymentStatus.RUNNING.value,
            health_status="Healthy",
            public_url="http://localhost/deployments/dep_007",
            project_id="proj_ml_99",
            created_at=now_str
        )
        self.assertEqual(res.deployment_id, "dep_007")
        self.assertEqual(res.image_name, "modelforge_dep_007")
        self.assertEqual(res.container_id, "container_sha_123")
        self.assertEqual(res.allocated_port, 8080)
        self.assertEqual(res.host_port, 8080)
        self.assertEqual(res.deployment_status, "RUNNING")
        self.assertEqual(res.status, "RUNNING")
        self.assertEqual(res.health_status, "Healthy")
        self.assertEqual(res.public_url, "http://localhost/deployments/dep_007")

        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["deployment_id"], "dep_007")

    def test_container_info_model(self):
        """Verify ContainerInfo model instantiation and properties."""
        info = ContainerInfo(
            container_id="c_1234567890ab",
            container_name="modelforge_dep_007",
            image_name="modelforge_dep_007:latest",
            status="running",
            host_port=8080,
            target_port=8000,
            url="http://localhost:8080",
            labels={"modelforge.deployment_id": "dep_007"},
            ports={"8000/tcp": [{"HostPort": "8080"}]}
        )
        self.assertEqual(info.container_id, "c_1234567890ab")
        self.assertEqual(info.container_name, "modelforge_dep_007")
        self.assertEqual(info.status, "running")
        self.assertEqual(info.host_port, 8080)
        self.assertEqual(info.target_port, 8000)
        self.assertEqual(info.labels.get("modelforge.deployment_id"), "dep_007")


if __name__ == "__main__":
    unittest.main()
