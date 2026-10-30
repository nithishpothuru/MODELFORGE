"""
Unit tests for Sprint 10 MonitoringService.
Verifies active deployment monitoring, unhealthy container detection,
automated restarts with attempt limits, repository updates,
metrics generation, and future scaling support.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.services.deployment.services.monitoring_service import MonitoringService
from app.services.deployment.core.health_manager import HealthStatus
from app.services.deployment.models.deployment_status import DeploymentStatus
from app.services.deployment.database.deployment_repository import DeploymentRepository


class TestMonitoringService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_monitoring.db"
        self.repo = DeploymentRepository(db_path=self.db_path, sync_supabase=False)

        self.mock_docker_mgr = MagicMock()
        self.mock_health_mgr = MagicMock()

        self.service = MonitoringService(
            docker_manager=self.mock_docker_mgr,
            health_manager=self.mock_health_mgr,
            repository=self.repo,
            max_workers=2,
            max_restart_attempts=2
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_get_deployment_health_healthy(self):
        self.repo.save({
            "deployment_id": "dep_mon_01",
            "project_id": "proj_1",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8080
        })

        self.mock_docker_mgr.inspect_container.return_value = {
            "status": "running",
            "running": True
        }
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.HEALTHY,
            "healthy": True,
            "message": "Service healthy"
        }

        res = self.service.get_deployment_health("dep_mon_01")
        self.assertTrue(res["found"])
        self.assertTrue(res["container_running"])
        self.assertEqual(res["health_status"], HealthStatus.HEALTHY)

    def test_detect_unhealthy_containers(self):
        # 1 healthy deployment
        self.repo.save({
            "deployment_id": "dep_healthy",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8081
        })
        # 1 stopped container
        self.repo.save({
            "deployment_id": "dep_unhealthy",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8082
        })

        def inspect_mock(name):
            if "dep_healthy" in name:
                return {"status": "running", "running": True}
            return {"status": "exited", "running": False}

        self.mock_docker_mgr.inspect_container.side_effect = inspect_mock

        def health_mock(**kwargs):
            url = kwargs.get("url", "")
            if "8081" in url:
                return {"health_status": HealthStatus.HEALTHY}
            return {"health_status": HealthStatus.FAILED}

        self.mock_health_mgr.wait_for_ready.side_effect = health_mock

        unhealthy = self.service.detect_unhealthy_containers()
        self.assertEqual(len(unhealthy), 1)
        self.assertEqual(unhealthy[0]["deployment_id"], "dep_unhealthy")
        self.assertFalse(unhealthy[0]["container_running"])

    def test_restart_failed_containers_success(self):
        self.repo.save({
            "deployment_id": "dep_restart_ok",
            "deployment_status": DeploymentStatus.RUNNING.value,
            "allocated_port": 8083
        })

        # Initially container is not running
        self.mock_docker_mgr.inspect_container.side_effect = [
            {"status": "exited", "running": False},  # first check
            {"status": "running", "running": True}   # post-restart check
        ]
        self.mock_docker_mgr.restart_container.return_value = True
        self.mock_health_mgr.wait_for_ready.return_value = {
            "health_status": HealthStatus.HEALTHY,
            "healthy": True
        }

        restarts = self.service.restart_failed_containers([
            {"deployment_id": "dep_restart_ok", "container_running": False}
        ])

        self.assertEqual(len(restarts), 1)
        self.assertTrue(restarts[0]["restarted"])
        self.assertEqual(restarts[0]["status"], DeploymentStatus.RUNNING.value)

        saved = self.repo.get("dep_restart_ok")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.RUNNING.value)
        self.assertEqual(saved["health_status"], HealthStatus.HEALTHY)

    def test_restart_max_attempts_exceeded(self):
        self.repo.save({
            "deployment_id": "dep_restart_max",
            "deployment_status": DeploymentStatus.RUNNING.value
        })

        # Set attempts to max (2)
        self.service._restart_counts["dep_restart_max"] = 2

        restarts = self.service.restart_failed_containers([
            {"deployment_id": "dep_restart_max", "container_running": False}
        ])

        self.assertEqual(len(restarts), 1)
        self.assertFalse(restarts[0]["restarted"])
        self.assertIn("Max restart attempts", restarts[0]["error"])

        saved = self.repo.get("dep_restart_max")
        self.assertEqual(saved["deployment_status"], DeploymentStatus.FAILED.value)
        self.mock_docker_mgr.restart_container.assert_not_called()

    def test_monitor_active_deployments_concurrent(self):
        self.repo.save({"deployment_id": "dep_act_1", "deployment_status": DeploymentStatus.RUNNING.value})
        self.repo.save({"deployment_id": "dep_act_2", "deployment_status": DeploymentStatus.RUNNING.value})

        self.mock_docker_mgr.inspect_container.return_value = {"status": "running", "running": True}
        self.mock_health_mgr.wait_for_ready.return_value = {"health_status": HealthStatus.HEALTHY}

        results = self.service.monitor_active_deployments(auto_restart=False)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r["deployment_status"], DeploymentStatus.RUNNING.value)
            self.assertEqual(r["health_status"], HealthStatus.HEALTHY)

    def test_generate_deployment_metrics(self):
        self.repo.save({"deployment_id": "m1", "deployment_status": DeploymentStatus.RUNNING.value, "health_status": HealthStatus.HEALTHY, "framework": "fastapi"})
        self.repo.save({"deployment_id": "m2", "deployment_status": DeploymentStatus.RUNNING.value, "health_status": HealthStatus.FAILED, "framework": "flask"})
        self.repo.save({"deployment_id": "m3", "deployment_status": DeploymentStatus.STOPPED.value, "health_status": "stopped", "framework": "fastapi"})

        # Platform metrics
        metrics = self.service.generate_deployment_metrics()
        self.assertEqual(metrics["total_deployments"], 3)
        self.assertEqual(metrics["active_deployments"], 2)
        self.assertEqual(metrics["healthy_deployments"], 1)
        self.assertEqual(metrics["health_ratio_percentage"], 50.0)
        self.assertEqual(metrics["framework_breakdown"]["fastapi"], 2)

        # Single deployment metrics
        self.mock_docker_mgr.inspect_container.return_value = {"running": True}
        m1_metrics = self.service.generate_deployment_metrics("m1")
        self.assertEqual(m1_metrics["deployment_id"], "m1")
        self.assertEqual(m1_metrics["status"], DeploymentStatus.RUNNING.value)
        self.assertEqual(m1_metrics["health"], HealthStatus.HEALTHY)

    def test_scaling_support(self):
        # Initial evaluation
        rec = self.service.evaluate_scaling("dep_scale", current_load=90.0, threshold=80.0)
        self.assertEqual(rec["scale_action"], "SCALE_UP")
        self.assertEqual(rec["desired_replicas"], 2)

        # Scale action
        scale_res = self.service.scale_deployment("dep_scale", target_replicas=3)
        self.assertTrue(scale_res["scaled"])
        self.assertEqual(scale_res["current_replicas"], 3)

        # Evaluation with low load -> scale down
        rec_down = self.service.evaluate_scaling("dep_scale", current_load=20.0, threshold=80.0)
        self.assertEqual(rec_down["scale_action"], "SCALE_DOWN")
        self.assertEqual(rec_down["desired_replicas"], 2)


if __name__ == "__main__":
    unittest.main()
