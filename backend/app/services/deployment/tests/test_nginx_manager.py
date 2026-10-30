"""
Unit tests for Sprint 6 NginxManager.
Verifies config generation, upstreams, locations, reload, deletion,
localhost, custom domain support, and public URL construction.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.deployment.core.nginx_manager import NginxManager


class TestNginxManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.conf_dir = Path(self.temp_dir.name)
        self.nginx_mgr = NginxManager(
            conf_dir=self.conf_dir,
            base_domain="modelforge.internal",
            public_base_url="http://gateway.modelforge.internal"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_config(self):
        conf = self.nginx_mgr.generate_config(
            deployment_id="dep123",
            host_port=8050,
            domain_name="dep123.modelforge.internal"
        )
        self.assertIn("upstream upstream_modelforge_dep123", conf)
        self.assertIn("server 127.0.0.1:8050;", conf)
        self.assertIn("server_name dep123.modelforge.internal;", conf)
        self.assertIn("proxy_pass http://upstream_modelforge_dep123;", conf)

    def test_generate_upstream(self):
        upstream = self.nginx_mgr.generate_upstream("dep_up_1", 8090)
        self.assertIn("upstream upstream_modelforge_dep_up_1", upstream)
        self.assertIn("server 127.0.0.1:8090;", upstream)
        self.assertIn("keepalive 32;", upstream)

    def test_generate_location(self):
        location = self.nginx_mgr.generate_location(
            upstream_name="upstream_modelforge_dep_up_1",
            path_prefix="api/v1",
            enable_websocket=True
        )
        self.assertIn("location /api/v1/", location)
        self.assertIn("proxy_pass http://upstream_modelforge_dep_up_1;", location)
        self.assertIn("Upgrade $http_upgrade;", location)

    def test_create_and_delete_routing(self):
        conf_file = self.nginx_mgr.create_routing(
            deployment_id="dep456",
            host_port=8051,
            trigger_reload=False
        )
        self.assertTrue(conf_file.exists())
        self.assertTrue(conf_file.is_file())
        self.assertIn("upstream_modelforge_dep456", conf_file.read_text(encoding="utf-8"))

        deleted = self.nginx_mgr.delete_routes("dep456", trigger_reload=False)
        self.assertTrue(deleted)
        self.assertFalse(conf_file.exists())

    def test_get_public_url_with_base_url(self):
        url = self.nginx_mgr.get_public_url(deployment_id="dep789")
        self.assertEqual(url, "http://gateway.modelforge.internal/deployments/dep789")
        # Ensure raw container port is not exposed
        self.assertNotIn("8050", url)

    def test_get_public_url_with_custom_domain(self):
        mgr_no_base = NginxManager(conf_dir=self.conf_dir, base_domain="modelforge.local", public_base_url=None)
        url = mgr_no_base.get_public_url(deployment_id="dep999", custom_domain="ml-model.mydomain.com")
        self.assertEqual(url, "http://ml-model.mydomain.com")

    def test_custom_domain_config_generation(self):
        conf = self.nginx_mgr.generate_config(
            deployment_id="dep_custom",
            host_port=8060,
            custom_domain="custom-ai.company.org"
        )
        self.assertIn("server_name custom-ai.company.org;", conf)
        self.assertIn("server 127.0.0.1:8060;", conf)

    def test_localhost_support(self):
        mgr_local = NginxManager(conf_dir=self.conf_dir, base_domain="localhost", public_base_url=None)
        conf = mgr_local.generate_config(deployment_id="dep_local", host_port=8070)
        self.assertIn("localhost", conf)
        url = mgr_local.get_public_url(deployment_id="dep_local")
        self.assertEqual(url, "http://localhost/deployments/dep_local")

    def test_get_public_url_subdomain(self):
        mgr_sub = NginxManager(conf_dir=self.conf_dir, base_domain="modelforge.local", public_base_url=None)
        url = mgr_sub.get_public_url(deployment_id="dep999")
        self.assertEqual(url, "http://dep999.modelforge.local")

    @patch("shutil.which", return_value="C:\\nginx\\nginx.exe")
    @patch("subprocess.run")
    def test_reload_nginx_success(self, mock_run, mock_which):
        # mock test (-t) and reload (-s reload)
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        success = self.nginx_mgr.reload_nginx()
        self.assertTrue(success)
        self.assertEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
