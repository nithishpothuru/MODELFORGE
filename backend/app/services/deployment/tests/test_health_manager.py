"""
Unit tests for Sprint 5 HealthManager.
Verifies connection retries, startup failure detection, framework support,
state determination (Healthy, Failed, Timeout), and health state storage.
"""

import unittest
from unittest.mock import patch, MagicMock

from app.services.deployment.core.health_manager import HealthManager, HealthStatus


class TestHealthManager(unittest.TestCase):
    def setUp(self):
        self.health_mgr = HealthManager(default_timeout=1.0, default_retries=3, default_delay=0.01)
        HealthManager.clear_health_records()

    def tearDown(self):
        HealthManager.clear_health_records()

    @patch("requests.get")
    def test_http_endpoint_healthy(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_resp

        res = self.health_mgr.check_http_endpoint("http://localhost:8000", "/health")
        self.assertEqual(res["health_status"], HealthStatus.HEALTHY)
        self.assertTrue(res["healthy"])
        self.assertEqual(res["status_code"], 200)

    @patch("requests.get")
    def test_http_endpoint_failed(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get.return_value = mock_resp

        res = self.health_mgr.check_http_endpoint("http://localhost:8000", "/health")
        self.assertEqual(res["health_status"], HealthStatus.FAILED)
        self.assertFalse(res["healthy"])
        self.assertEqual(res["status_code"], 500)

    @patch("requests.get")
    def test_retry_connections_eventual_success(self, mock_get):
        """Service fails first 2 attempts, then succeeds on 3rd."""
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        fail_resp.text = "Starting..."

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"status": "ready"}

        mock_get.side_effect = [fail_resp, fail_resp, success_resp]

        res = self.health_mgr.wait_for_ready(
            framework="fastapi",
            url="http://localhost:8000",
            retries=5,
            delay=0.01,
            deployment_id="dep_retry_ok"
        )
        self.assertEqual(res["health_status"], HealthStatus.HEALTHY)
        self.assertTrue(res["healthy"])
        self.assertEqual(res["attempts"], 3)

        # Verify stored health state
        stored = HealthManager.get_health_state("dep_retry_ok")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["health_status"], HealthStatus.HEALTHY)

    @patch("requests.get")
    def test_timeout_when_retries_exhausted(self, mock_get):
        """All attempts fail -> status must be Timeout."""
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        mock_get.return_value = fail_resp

        res = self.health_mgr.wait_for_ready(
            framework="flask",
            url="http://localhost:5000",
            retries=3,
            delay=0.01,
            deployment_id="dep_timeout"
        )
        self.assertEqual(res["health_status"], HealthStatus.TIMEOUT)
        self.assertFalse(res["healthy"])
        self.assertEqual(res["attempts"], 3)

        # Verify stored health state
        stored = HealthManager.get_health_state("dep_timeout")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["health_status"], HealthStatus.TIMEOUT)

    def test_cli_health_running(self):
        inspect_data = {
            "status": "running",
            "running": True,
            "exit_code": None,
            "state": {"Running": True, "ExitCode": 0}
        }
        res = self.health_mgr.check_cli_health(inspect_data)
        self.assertEqual(res["health_status"], HealthStatus.HEALTHY)
        self.assertTrue(res["healthy"])

    def test_cli_health_exited_success(self):
        inspect_data = {
            "status": "exited",
            "running": False,
            "exit_code": 0,
            "state": {"Running": False, "ExitCode": 0}
        }
        res = self.health_mgr.check_cli_health(inspect_data)
        self.assertEqual(res["health_status"], HealthStatus.HEALTHY)
        self.assertTrue(res["healthy"])

    def test_cli_health_exited_failure(self):
        inspect_data = {
            "status": "exited",
            "running": False,
            "exit_code": 1,
            "state": {"Running": False, "ExitCode": 1, "Error": "OOMKilled"}
        }
        res = self.health_mgr.check_cli_health(inspect_data)
        self.assertEqual(res["health_status"], HealthStatus.FAILED)
        self.assertFalse(res["healthy"])

    @patch("requests.get")
    def test_wait_for_ready_fast_fail_on_container_crash(self, mock_get):
        """If container process crashes/exits, immediately fail without waiting out timeout."""
        def inspect_fn():
            return {"status": "exited", "state": {"Running": False, "ExitCode": 137}}

        res = self.health_mgr.wait_for_ready(
            framework="fastapi",
            url="http://localhost:8000",
            retries=5,
            delay=0.01,
            deployment_id="dep_crash",
            container_inspect_fn=inspect_fn
        )
        self.assertEqual(res["health_status"], HealthStatus.FAILED)
        self.assertFalse(res["healthy"])
        self.assertEqual(res["attempts"], 1)
        self.assertIn("terminated unexpectedly", res["message"])

        stored = HealthManager.get_health_state("dep_crash")
        self.assertEqual(stored["health_status"], HealthStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
