"""
Unit tests for DockerManager.
Verifies low-level Docker engine interactions via Docker SDK for Python.
"""

import tempfile
import unittest
from unittest.mock import MagicMock
from pathlib import Path

from docker.errors import BuildError, APIError
from app.services.deployment.core.docker_manager import DockerManager


class TestDockerManager(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.docker_mgr = DockerManager(client=self.mock_client)

    def test_is_connected(self):
        self.mock_client.ping.return_value = True
        self.assertTrue(self.docker_mgr.is_connected())

        self.mock_client.ping.side_effect = Exception("Daemon unavailable")
        self.assertFalse(self.docker_mgr.is_connected())

    def test_disconnected_manager(self):
        disconnected_mgr = DockerManager(client=None)
        disconnected_mgr.client = None
        self.assertFalse(disconnected_mgr.is_connected())

        build_res = disconnected_mgr.build_image(workspace_path="/tmp", tag="test")
        self.assertEqual(build_res["status"], "failed")

        run_res = disconnected_mgr.run_container(image_name="test", container_name="test", host_port=8000)
        self.assertEqual(run_res["status"], "failed")

        self.assertFalse(disconnected_mgr.stop_container("test"))
        self.assertFalse(disconnected_mgr.restart_container("test"))
        self.assertFalse(disconnected_mgr.remove_container("test"))
        self.assertFalse(disconnected_mgr.remove_image("test"))
        self.assertIsNone(disconnected_mgr.inspect_container("test"))
        self.assertEqual(disconnected_mgr.container_logs("test"), "")

    def test_build_image_success(self):
        mock_image = MagicMock()
        mock_image.id = "sha256:1234567890abcdef"
        mock_image.short_id = "1234567890ab"
        mock_image.tags = ["modelforge_test:latest"]
        
        build_stream = [
            {"stream": "Step 1/5 : FROM python:3.11-slim\n"},
            {"stream": "Step 2/5 : WORKDIR /app\n"},
            {"stream": "Successfully built 1234567890ab\n"},
        ]
        self.mock_client.images.build.return_value = (mock_image, build_stream)

        with tempfile.TemporaryDirectory() as td:
            df = Path(td) / "Dockerfile"
            df.write_text("FROM alpine\n", encoding="utf-8")

            res = self.docker_mgr.build_image(workspace_path=td, tag="ModelForge_Test")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["image_name"], "modelforge_test")
            self.assertEqual(res["image_id"], "sha256:1234567890abcdef")
            self.assertIn("Step 1/5 : FROM python:3.11-slim", res["build_logs"])

    def test_build_image_failure_with_logs(self):
        build_log = [
            {"stream": "Step 1/3 : FROM python:3.11-slim\n"},
            {"stream": "ERROR: Could not find a version that satisfies the requirement invalid-pkg\n"}
        ]
        build_err = BuildError(reason="Pip failed", build_log=build_log)
        self.mock_client.images.build.side_effect = build_err

        with tempfile.TemporaryDirectory() as td:
            df = Path(td) / "Dockerfile"
            df.write_text("FROM alpine\n", encoding="utf-8")

            res = self.docker_mgr.build_image(workspace_path=td, tag="fail_test")
            self.assertEqual(res["status"], "failed")
            self.assertEqual(res["stage"], "docker_build")
            self.assertIn("Could not find a version", res["details"])
            self.assertEqual(len(res["build_logs"]), 2)

    def test_run_container_success(self):
        mock_container = MagicMock()
        mock_container.id = "cont_123"
        mock_container.name = "modelforge_test"
        self.mock_client.containers.run.return_value = mock_container

        res = self.docker_mgr.run_container(
            image_name="test_image",
            container_name="modelforge_test",
            host_port=8001,
            target_port=8000,
            env_vars={"MODEL_PATH": "/app/model.pkl"},
            labels={"modelforge.deployment_id": "001"}
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["container_id"], "cont_123")
        self.assertEqual(res["host_port"], 8001)
        self.assertEqual(res["url"], "http://localhost:8001")

    def test_run_container_cli_mode_no_port(self):
        """CLI ML container runs without host_port binding."""
        mock_container = MagicMock()
        mock_container.id = "cont_cli_999"
        mock_container.name = "modelforge_cli"
        self.mock_client.containers.run.return_value = mock_container

        res = self.docker_mgr.run_container(
            image_name="cli_image",
            container_name="modelforge_cli",
            host_port=None
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["container_id"], "cont_cli_999")
        self.assertIsNone(res.get("host_port"))
        self.assertNotIn("url", res)

    def test_stop_container(self):
        mock_container = MagicMock()
        self.mock_client.containers.get.return_value = mock_container
        self.assertTrue(self.docker_mgr.stop_container("cont_123"))
        mock_container.stop.assert_called_once_with(timeout=10)

    def test_restart_container(self):
        mock_container = MagicMock()
        self.mock_client.containers.get.return_value = mock_container
        self.assertTrue(self.docker_mgr.restart_container("cont_123"))
        mock_container.restart.assert_called_once()

    def test_remove_container(self):
        mock_container = MagicMock()
        self.mock_client.containers.get.return_value = mock_container
        self.assertTrue(self.docker_mgr.remove_container("cont_123"))
        mock_container.remove.assert_called_once_with(force=True)

    def test_remove_image(self):
        self.assertTrue(self.docker_mgr.remove_image("test_image"))
        self.mock_client.images.remove.assert_called_once_with(image="test_image", force=False)

    def test_inspect_container(self):
        mock_container = MagicMock()
        mock_container.id = "cont_abc"
        mock_container.name = "cont_abc_name"
        mock_container.status = "running"
        mock_container.attrs = {
            "State": {"Running": True, "ExitCode": 0, "StartedAt": "2026-10-29T10:00:00Z"},
            "NetworkSettings": {"Ports": {"8000/tcp": [{"HostPort": "8005"}]}},
            "Config": {"Labels": {"modelforge.deployment_id": "dep_1"}}
        }
        self.mock_client.containers.get.return_value = mock_container

        info = self.docker_mgr.inspect_container("cont_abc")
        self.assertIsNotNone(info)
        self.assertEqual(info["id"], "cont_abc")
        self.assertEqual(info["status"], "running")
        self.assertTrue(info["running"])
        self.assertEqual(info["exit_code"], 0)

    def test_container_logs(self):
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Application startup complete.\nUvicorn running on http://0.0.0.0:8000"
        self.mock_client.containers.get.return_value = mock_container

        logs = self.docker_mgr.container_logs("cont_abc", tail=50)
        self.assertIn("Application startup complete", logs)


if __name__ == "__main__":
    unittest.main()
