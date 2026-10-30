"""
Unit tests for Sprint 9 DeploymentService public facade.
Verifies deploy, status, restart, stop, and delete operations.
Ensures Docker implementation details are completely abstracted and
structured DeploymentResult instances are returned across all APIs.
"""

import tempfile
import unittest
from unittest.mock import MagicMock
from pathlib import Path

from app.services.deployment.services.deployment_service import DeploymentService
from app.services.deployment.core.health_manager import HealthStatus
from app.services.deployment.models.deployment_request import DeploymentRequest
from app.services.deployment.models.deployment_result import DeploymentResult
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.database.deployment_repository import DeploymentRepository


class TestDeploymentService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / "test_service.db"
        self.repo = DeploymentRepository(db_path=self.db_path, sync_supabase=False)

        self.mock_deploy_mgr = MagicMock()
        self.mock_docker_mgr = MagicMock()
        self.mock_health_mgr = MagicMock()

        self.service = DeploymentService(
            deployment_manager=self.mock_deploy_mgr,
            repository=self.repo,
            docker_manager=self.mock_docker_mgr,
            health_manager=self.mock_health_mgr
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_deploy_delegates_to_deployment_manager(self):
        expected_result = DeploymentResult(
            deployment_id="dep-serv-01",
            deployment_status=DeploymentStatus.RUNNING.value,
            health_status=HealthStatus.HEALTHY,
            allocated_port=8080,
            public_url="http://localhost/deployments/dep-serv-01"
        )
        self.mock_deploy_mgr.deploy.return_value = expected_result

        res = self.service.deploy({"project_id": "p1", "working_directory": str(self.workspace)})
        self.assertIsInstance(res, DeploymentResult)
        self.assertEqual(res.deployment_id, "dep-serv-01")
        self.assertEqual(res.deployment_status, DeploymentStatus.RUNNING.value)
        self.mock_deploy_mgr.deploy.assert_called_once()

    def test_stop_deployment(self):
        # Seed record in database
        self.repo.save({
            "deployment_id": "dep-stop-01",
            "project_id": "p-stop",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8080
        })

        self.mock_docker_mgr.stop_container.return_value = True

        res = self.service.stop("dep-stop-01")
        self.assertIsInstance(res, DeploymentResult)
        self.assertTrue(res.success)
        self.assertTrue(res["success"])
        self.assertEqual(res.deployment_status, DeploymentStatus.STOPPED.value)
        self.assertEqual(res["status"], DeploymentStatus.STOPPED.value)

        saved = self.repo.get("dep-stop-01")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.STOPPED.value)

    def test_restart_deployment(self):
        self.repo.save({
            "deployment_id": "dep-restart-01",
            "project_id": "p-restart",
            "deployment_status": DeploymentStatus.STOPPED.value,
            "allocated_port": 8085,
            "framework": "fastapi"
        })

        self.mock_docker_mgr.restart_container.return_value = True
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.HEALTHY,
            "healthy": True,
            "message": "Service healthy"
        }

        res = self.service.restart("dep-restart-01")
        self.assertIsInstance(res, DeploymentResult)
        self.assertTrue(res.success)
        self.assertTrue(res["success"])
        self.assertEqual(res.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertEqual(res.health_status, HealthStatus.HEALTHY)

        saved = self.repo.get("dep-restart-01")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.RUNNING.value)

    def test_delete_deployment(self):
        self.repo.save({
            "deployment_id": "dep-del-01",
            "project_id": "p-del",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8090
        })

        self.mock_docker_mgr.stop_container.return_value = True
        self.mock_docker_mgr.remove_container.return_value = True
        self.mock_docker_mgr.remove_image.return_value = True

        res = self.service.delete("dep-del-01")
        self.assertIsInstance(res, DeploymentResult)
        self.assertTrue(res.success)
        self.assertTrue(res["success"])
        self.assertEqual(res.deployment_status, DeploymentStatus.REMOVED.value)

        saved = self.repo.get("dep-del-01")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.REMOVED.value)

    def test_status_query(self):
        self.repo.save({
            "deployment_id": "dep-status-01",
            "project_id": "p-status",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "health_status": HealthStatus.HEALTHY,
            "allocated_port": 8095,
            "public_url": "http://localhost/deployments/dep-status-01"
        })

        self.mock_docker_mgr.inspect_container.return_value = {
            "status": "running",
            "running": True
        }
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.HEALTHY,
            "healthy": True
        }

        result = self.service.status("dep-status-01")
        self.assertIsInstance(result, DeploymentResult)
        self.assertEqual(result.deployment_id, "dep-status-01")
        self.assertEqual(result.deployment_status, DeploymentStatus.RUNNING.value)
        self.assertEqual(result.health_status, HealthStatus.HEALTHY)
        self.assertEqual(result.allocated_port, 8095)

    def test_operations_on_non_existent_deployment(self):
        """Operations on non-existent deployments must return clean DeploymentResult with success=False."""
        status_res = self.service.status("non_existent")
        self.assertIsInstance(status_res, DeploymentResult)
        self.assertFalse(status_res.success)
        self.assertEqual(status_res.deployment_status, DeploymentStatus.FAILED.value)

        stop_res = self.service.stop("non_existent")
        self.assertIsInstance(stop_res, DeploymentResult)
        self.assertFalse(stop_res.success)

        restart_res = self.service.restart("non_existent")
        self.assertIsInstance(restart_res, DeploymentResult)
        self.assertFalse(restart_res.success)

        delete_res = self.service.delete("non_existent")
        self.assertIsInstance(delete_res, DeploymentResult)
        self.assertFalse(delete_res.success)

    def test_list_deployments(self):
        self.repo.save({"deployment_id": "d1", "deployment_status": DeploymentStatus.RUNNING.value})
        self.repo.save({"deployment_id": "d2", "deployment_status": DeploymentStatus.STOPPED.value})

        all_deps = self.service.list_deployments()
        self.assertEqual(len(all_deps), 2)
        for d in all_deps:
            self.assertIsInstance(d, DeploymentResult)

        running_deps = self.service.list_deployments(status=DeploymentStatus.RUNNING.value)
        self.assertEqual(len(running_deps), 1)
        self.assertEqual(running_deps[0].deployment_id, "d1")


if __name__ == "__main__":
    unittest.main()
