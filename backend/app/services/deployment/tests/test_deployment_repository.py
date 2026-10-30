"""
Unit tests for Sprint 7 DeploymentRepository.
Verifies storage of all required fields, CRUD operations, status updates,
and integration with existing backend persistence (Supabase).
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.deployment.database.deployment_repository import DeploymentRepository
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.models.deployment_result import DeploymentResult


class TestDeploymentRepository(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_deployments.db"
        # Disable automatic Supabase calls during basic unit tests
        self.repo = DeploymentRepository(db_path=self.db_path, sync_supabase=False)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except OSError:
            pass

    def test_create_and_get_all_fields(self):
        """Test storing and retrieving all fields required by Sprint 7."""
        record = {
            "deployment_id": "dep_test_001",
            "project_id": "proj_123",
            "container_id": "cont_abc_456",
            "image_id": "img_modelforge:v1",
            "allocated_port": 8080,
            "deployment_status": DeploymentStatus.RUNNING.value,
            "health_status": "Healthy",
            "public_url": "http://localhost/deployments/dep_test_001"
        }
        dep_id = self.repo.create(record)
        self.assertEqual(dep_id, "dep_test_001")

        data = self.repo.get("dep_test_001")
        self.assertIsNotNone(data)
        self.assertEqual(data["deployment_id"], "dep_test_001")
        self.assertEqual(data["project_id"], "proj_123")
        self.assertEqual(data["container_id"], "cont_abc_456")
        self.assertEqual(data["image_id"], "img_modelforge:v1")
        self.assertEqual(data["allocated_port"], 8080)
        self.assertEqual(data["deployment_status"], DeploymentStatus.RUNNING.value)
        self.assertEqual(data["status"], DeploymentStatus.RUNNING.value)
        self.assertEqual(data["health_status"], "Healthy")
        self.assertEqual(data["health"], "Healthy")
        self.assertEqual(data["public_url"], "http://localhost/deployments/dep_test_001")
        self.assertIn("created_at", data)
        self.assertIn("created_time", data)
        self.assertIn("updated_at", data)
        self.assertIn("updated_time", data)

    def test_create_with_deployment_result_model(self):
        """Test saving a typed DeploymentResult model instance."""
        res_model = DeploymentResult(
            deployment_id="dep_res_002",
            project_id="proj_xyz",
            container_id="cont_xyz",
            image_name="modelforge_proj_xyz:latest",
            image_id="sha256:1234567890",
            allocated_port=8085,
            deployment_status=DeploymentStatus.CONTAINER_RUNNING.value,
            health_status="pending",
            public_url="http://localhost/deployments/dep_res_002"
        )
        saved_id = self.repo.save(res_model)
        self.assertEqual(saved_id, "dep_res_002")

        data = self.repo.get("dep_res_002")
        self.assertIsNotNone(data)
        self.assertEqual(data["container_id"], "cont_xyz")
        self.assertEqual(data["allocated_port"], 8085)
        self.assertEqual(data["status"], DeploymentStatus.CONTAINER_RUNNING.value)

    def test_update_status(self):
        """Test updating deployment status."""
        self.repo.create({
            "deployment_id": "dep_status_003",
            "project_id": "proj_1",
            "deployment_status": DeploymentStatus.PENDING.value
        })

        # Update to HEALTH_CHECKING with message
        updated = self.repo.update_status(
            "dep_status_003",
            DeploymentStatus.HEALTH_CHECKING,
            message="Health probe in progress"
        )
        self.assertTrue(updated)

        rec = self.repo.get("dep_status_003")
        self.assertEqual(rec["deployment_status"], DeploymentStatus.HEALTH_CHECKING.value)
        self.assertEqual(rec["message"], "Health probe in progress")

    def test_update_health(self):
        """Test updating health state."""
        self.repo.create({
            "deployment_id": "dep_health_004",
            "project_id": "proj_2",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "health_status": "pending"
        })

        updated = self.repo.update_health("dep_health_004", "Healthy")
        self.assertTrue(updated)

        rec = self.repo.get("dep_health_004")
        self.assertEqual(rec["health"], "Healthy")

    def test_update_generic_fields(self):
        """Test updating multiple fields at once."""
        self.repo.create({
            "deployment_id": "dep_gen_005",
            "project_id": "proj_3",
            "deployment_status": DeploymentStatus.CONTAINER_STARTING.value
        })

        success = self.repo.update("dep_gen_005", {
            "container_id": "new_cont_id_789",
            "allocated_port": 8099,
            "public_url": "http://example.com/deployments/dep_gen_005",
            "status": DeploymentStatus.RUNNING.value
        })
        self.assertTrue(success)

        rec = self.repo.get("dep_gen_005")
        self.assertEqual(rec["container_id"], "new_cont_id_789")
        self.assertEqual(rec["allocated_port"], 8099)
        self.assertEqual(rec["status"], DeploymentStatus.RUNNING.value)

    def test_get_by_project(self):
        """Test retrieving all deployments for a project."""
        self.repo.create({"deployment_id": "d1", "project_id": "proj_shared", "deployment_status": "RUNNING"})
        self.repo.create({"deployment_id": "d2", "project_id": "proj_shared", "deployment_status": "STOPPED"})
        self.repo.create({"deployment_id": "d3", "project_id": "proj_other", "deployment_status": "RUNNING"})

        results = self.repo.get_by_project("proj_shared")
        self.assertEqual(len(results), 2)
        ids = [r["deployment_id"] for r in results]
        self.assertIn("d1", ids)
        self.assertIn("d2", ids)
        self.assertNotIn("d3", ids)

    def test_list_all_and_filtering(self):
        """Test listing all deployments with status filtering."""
        self.repo.create({"deployment_id": "d10", "deployment_status": "RUNNING"})
        self.repo.create({"deployment_id": "d20", "deployment_status": "STOPPED"})
        self.repo.create({"deployment_id": "d30", "deployment_status": "RUNNING"})

        all_records = self.repo.list_all()
        self.assertEqual(len(all_records), 3)

        running_records = self.repo.list_all(status="RUNNING")
        self.assertEqual(len(running_records), 2)

    def test_delete(self):
        """Test deleting a deployment."""
        self.repo.create({"deployment_id": "dep_del_006", "deployment_status": "REMOVED"})
        self.assertIsNotNone(self.repo.get("dep_del_006"))

        deleted = self.repo.delete("dep_del_006")
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get("dep_del_006"))

    @patch("app.services.supabase_client.get_supabase_client")
    def test_backend_persistence_sync(self, mock_get_client):
        """Test integration with existing backend persistence (Supabase)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        repo_with_sync = DeploymentRepository(db_path=self.db_path, sync_supabase=True)

        repo_with_sync.create({
            "deployment_id": "dep_sync_007",
            "project_id": "proj_sync",
            "container_id": "c_sync",
            "image_id": "img_sync",
            "allocated_port": 8091,
            "deployment_status": "RUNNING",
            "health_status": "Healthy",
            "public_url": "http://localhost/deployments/dep_sync_007"
        })

        # Verify Supabase client was called to upsert deployment
        mock_client.table.assert_any_call("deployments")

        # Update status and verify sync
        repo_with_sync.update_status("dep_sync_007", DeploymentStatus.STOPPED)
        mock_client.table.assert_any_call("deployments")

        # Delete and verify sync
        repo_with_sync.delete("dep_sync_007")
        mock_client.table.assert_any_call("deployments")


if __name__ == "__main__":
    unittest.main()
