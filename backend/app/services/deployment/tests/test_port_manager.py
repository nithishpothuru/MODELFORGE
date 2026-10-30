"""
Unit tests for Sprint 4 PortManager.
Verifies thread-safety, concurrency, persistence, and duplicate allocation prevention.
"""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.deployment.core.port_manager import PortManager


class TestPortManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "test_ports.json"
        PortManager._set_state_file(self.state_file)
        PortManager.clear_all()

    def tearDown(self):
        PortManager.clear_all()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    @patch.object(PortManager, "is_port_available", return_value=True)
    def test_allocate_port_range(self, mock_available):
        port = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_001")
        self.assertEqual(port, 8050)
        self.assertIn(8050, PortManager.get_allocated_ports())
        self.assertEqual(PortManager.get_port_for_deployment("dep_001"), 8050)

    @patch.object(PortManager, "is_port_available", return_value=True)
    def test_prevent_duplicate_allocation(self, mock_available):
        p1 = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_1")
        p2 = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_2")
        self.assertNotEqual(p1, p2)
        self.assertEqual(p1, 8050)
        self.assertEqual(p2, 8051)
        self.assertTrue(PortManager.is_port_allocated(8050))
        self.assertTrue(PortManager.is_port_allocated(8051))

    @patch.object(PortManager, "is_port_available", return_value=True)
    def test_preferred_port_allocation(self, mock_available):
        port = PortManager.allocate_port(start_port=8050, end_port=8060, preferred_port=8055, deployment_id="dep_pref")
        self.assertEqual(port, 8055)
        self.assertIn(8055, PortManager.get_allocated_ports())

    @patch.object(PortManager, "is_port_available", return_value=True)
    def test_release_port(self, mock_available):
        port = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_rel")
        self.assertTrue(PortManager.is_port_allocated(port))

        PortManager.release_port(port)
        self.assertFalse(PortManager.is_port_allocated(port))
        self.assertIsNone(PortManager.get_port_for_deployment("dep_rel"))

        # Re-allocation should now succeed on the released port
        reallocated = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_new")
        self.assertEqual(reallocated, port)

    @patch.object(PortManager, "is_port_available", return_value=True)
    def test_persist_active_port_mappings(self, mock_available):
        """Verify active port allocations persist across manager reloads."""
        p1 = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_persist_1")
        p2 = PortManager.allocate_port(start_port=8050, end_port=8060, deployment_id="dep_persist_2")

        # Verify state file was written
        self.assertTrue(self.state_file.exists())

        # Simulate fresh reload by clearing in-memory dict and re-triggering load
        PortManager._active_mappings.clear()
        PortManager._load_state()

        self.assertTrue(PortManager.is_port_allocated(p1))
        self.assertTrue(PortManager.is_port_allocated(p2))
        self.assertEqual(PortManager.get_port_for_deployment("dep_persist_1"), p1)

    @patch.object(PortManager, "is_port_available", return_value=True)
    def test_concurrent_port_allocations(self, mock_available):
        """Verify concurrent threads do not produce colliding port allocations."""
        allocated_results = []
        errors = []

        def worker(dep_id):
            try:
                p = PortManager.allocate_port(start_port=8100, end_port=8200, deployment_id=dep_id)
                allocated_results.append(p)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"dep_concurrent_{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(allocated_results), 20)
        # All 20 ports must be unique
        self.assertEqual(len(set(allocated_results)), 20)

    @patch.object(PortManager, "is_port_available", return_value=False)
    def test_exhausted_range_raises_error(self, mock_available):
        with self.assertRaises(RuntimeError):
            PortManager.allocate_port(start_port=8050, end_port=8052)


if __name__ == "__main__":
    unittest.main()
