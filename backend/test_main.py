import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main as main


class BackendBoardApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = pathlib.Path(tempfile.mkdtemp())
        main.DB_PATH = cls.temp_dir / "pm_test.db"
        main.init_db()
        cls.client = TestClient(main.app)
        # Log in once and reuse the token for all tests.
        response = cls.client.post("/api/login", json={"username": "user", "password": "password"})
        assert response.status_code == 200
        data = response.json()
        cls.token = data["token"]
        cls.auth = {"Authorization": f"Bearer {cls.token}"}

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_login_invalid_credentials(self):
        response = self.client.post("/api/login", json={"username": "user", "password": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_board_requires_auth(self):
        response = self.client.get("/api/board")
        self.assertEqual(response.status_code, 401)

    def test_board_read_and_update(self):
        response = self.client.get("/api/board", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        board_data = response.json()
        self.assertIn("columns", board_data)
        self.assertIn("cards", board_data)
        self.assertEqual(board_data["columns"][0]["id"], "col-backlog")

        updated_title = "Backlog Updated"
        board_data["columns"][0]["title"] = updated_title

        response = self.client.put("/api/board", headers=self.auth, json=board_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        response = self.client.get("/api/board", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        refreshed_data = response.json()
        self.assertEqual(refreshed_data["columns"][0]["title"], updated_title)

    def test_ai_proxy_route(self):
        response = self.client.get("/api/board", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        board_data = response.json()

        updated_title = "Backlog Updated Again"
        updated_board = json.loads(json.dumps(board_data))
        updated_board["columns"][0]["title"] = updated_title

        mock_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "response": "Board updated",
                                "updatedBoard": updated_board,
                            }
                        )
                    }
                }
            ]
        }

        class FakeResponse:
            status_code = 200

            def json(self):
                return mock_body

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch("main.httpx.AsyncClient", return_value=FakeClient()):
            response = self.client.post(
                "/api/ai",
                headers=self.auth,
                json={"prompt": "Rename the first column", "board": board_data},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["structured"]["updatedBoard"]["columns"][0]["title"], updated_title)
            self.assertEqual(data["updatedBoard"]["columns"][0]["title"], updated_title)

            refreshed = self.client.get("/api/board", headers=self.auth).json()
            self.assertEqual(refreshed["columns"][0]["title"], updated_title)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        import gc

        gc.collect()
        for child in cls.temp_dir.iterdir():
            try:
                child.unlink()
            except PermissionError:
                pass
        try:
            cls.temp_dir.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main()
