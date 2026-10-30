"""
Unit tests for Sprint 11 CleanupService.
Verifies container stopping, container deletion, Docker image deletion,
Nginx route deletion, port release, repository status updates,
and rollback on deployment failures.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.services.deployment.services.cleanup_service import CleanupService
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.database.deployment_repository import DeploymentRepository


class TestCleanupService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_cleanup.db"
        self.repo = DeploymentRepository(db_path=self.db_path, sync_supabase=False)

        self.mock_docker_mgr = MagicMock()
        self.mock_port_mgr = MagicMock()
        self.mock_nginx_mgr = MagicMock()

        self.service = CleanupService(
            docker_manager=self.mock_docker_mgr,
            port_manager=self.mock_port_mgr,
            nginx_manager=self.mock_nginx_mgr,
            repository=self.repo
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_cleanup_deployment_full(self):
        """Verify full teardown of container, image, routing, port, and repository update."""
        self.repo.save({
            "deployment_id": "dep_clean_01",
            "project_id": "proj_1",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8080
        })

        self.mock_docker_mgr.stop_container.return_value = True
        self.mock_docker_mgr.remove_container.return_value = True
        self.mock_docker_mgr.remove_image.return_value = True
        self.mock_nginx_mgr.delete_routes.return_value = True
        self.mock_port_mgr.release_port.return_value = True

        res = self.service.cleanup_deployment("dep_clean_01", remove_image=True)

        self.assertTrue(res["container_stopped"])
        self.assertTrue(res["container_deleted"])
        self.assertTrue(res["image_deleted"])
        self.assertTrue(res["nginx_route_deleted"])
        self.assertEqual(res["port_released"], 8080)
        self.assertEqual(res["deployment_status"], DeploymentStatus.REMOVED.value)

        # Verify calls
        self.mock_docker_mgr.stop_container.assert_called_once_with("modelforge_dep_clean_01", timeout=5)
        self.mock_docker_mgr.remove_container.assert_called_once_with("modelforge_dep_clean_01", force=True)
        self.mock_docker_mgr.remove_image.assert_called_once_with("modelforge_dep_clean_01", force=True)
        self.mock_nginx_mgr.delete_routes.assert_called_once_with("dep_clean_01")
        self.mock_port_mgr.release_port.assert_called_once_with(8080)

        # Verify DB status
        saved = self.repo.get("dep_clean_01")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.REMOVED.value)

    def test_cleanup_deployment_retain_image(self):
        """Verify cleanup can retain Docker image when remove_image is False."""
        self.repo.save({
            "deployment_id": "dep_clean_retain",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8085
        })

        res = self.service.cleanup_deployment("dep_clean_retain", remove_image=False)
        self.assertFalse(res["image_deleted"])
        self.mock_docker_mgr.remove_image.assert_not_called()

    def test_rollback_on_failure(self):
        """Verify rollback cleans up partial resources and updates status to FAILED."""
        self.repo.save({
            "deployment_id": "dep_rollback_01",
            "deployment_status": DeploymentStatus.CONTAINER_STARTING.value,
            "allocated_port": 8090
        })

        self.mock_docker_mgr.stop_container.return_value = True
        self.mock_docker_mgr.remove_container.return_value = True
        self.mock_docker_mgr.remove_image.return_value = True
        self.mock_nginx_mgr.delete_routes.return_value = True
        self.mock_port_mgr.release_port.return_value = True

        res = self.service.rollback(
            deployment_id="dep_rollback_01",
            error_message="Container startup timeout",
            allocated_port=8090,
            remove_container=True,
            remove_image=True,
            remove_nginx=True
        )

        self.assertTrue(res["rolled_back"])
        self.assertTrue(res["container_stopped"])
        self.assertTrue(res["container_deleted"])
        self.assertTrue(res["image_deleted"])
        self.assertEqual(res["port_released"], 8090)
        self.assertEqual(res["deployment_status"], DeploymentStatus.FAILED.value)

        saved = self.repo.get("dep_rollback_01")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.FAILED.value)
        self.assertIn("Container startup timeout", saved["message"])

    def test_individual_cleanup_helpers(self):
        """Verify individual helper methods for granular teardown."""
        self.mock_docker_mgr.stop_container.return_value = True
        self.mock_docker_mgr.remove_container.return_value = True
        self.mock_docker_mgr.remove_image.return_value = True
        self.mock_nginx_mgr.delete_routes.return_value = True
        self.mock_port_mgr.release_port.return_value = True

        self.assertTrue(self.service.stop_containers("dep_help"))
        self.assertTrue(self.service.delete_containers("dep_help"))
        self.assertTrue(self.service.delete_images("img_help"))
        self.assertTrue(self.service.delete_nginx_config("dep_help"))
        self.assertTrue(self.service.release_ports(9000))

    def test_cleanup_all(self):
        """Verify batch cleanup of multiple deployments."""
        self.repo.save({"deployment_id": "d_all_1", "deployment_status": "RUNNING"})
        self.repo.save({"deployment_id": "d_all_2", "deployment_status": "STOPPED"})

        res = self.service.cleanup_all()
        self.assertEqual(res["count"], 2)
        self.assertEqual(len(res["cleaned"]), 2)


if __name__ == "__main__":
    unittest.main()
