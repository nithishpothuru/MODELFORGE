import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestMainAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("docs_url", data)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_create_and_get_project(self):
        # 1. Create project
        create_payload = {
            "title": "Test Vision Model",
            "description": "PyTorch vision classifier",
            "framework": "PyTorch",
            "version": "1.0.0",
        }
        create_res = self.client.post("/api/v1/projects", json=create_payload)
        self.assertEqual(create_res.status_code, 201)
        created_data = create_res.json()
        self.assertEqual(created_data["title"], "Test Vision Model")
        project_id = created_data["id"]

        # 2. Get project by ID
        get_res = self.client.get(f"/api/v1/projects/{project_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["id"], project_id)

        # 3. List projects
        list_res = self.client.get("/api/v1/projects")
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(p["id"] == project_id for p in list_res.json()))


if __name__ == "__main__":
    unittest.main()
