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

    def test_board_read_and_update(self):
        username = "user"

        response = self.client.get("/api/board", params={"username": username})
        self.assertEqual(response.status_code, 200)
        board_data = response.json()
        self.assertIn("columns", board_data)
        self.assertIn("cards", board_data)
        self.assertEqual(board_data["columns"][0]["id"], "col-backlog")

        updated_title = "Backlog Updated"
        board_data["columns"][0]["title"] = updated_title

        response = self.client.put(
            "/api/board",
            params={"username": username},
            json=board_data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        response = self.client.get("/api/board", params={"username": username})
        self.assertEqual(response.status_code, 200)
        refreshed_data = response.json()
        self.assertEqual(refreshed_data["columns"][0]["title"], updated_title)

    def test_ai_proxy_route(self):
        username = "user"
        response = self.client.get("/api/board", params={"username": username})
        self.assertEqual(response.status_code, 200)
        board_data = response.json()

        updated_title = "Backlog Updated"
        updated_board = board_data.copy()
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
                params={"username": username},
                json={"prompt": "Rename the first column to Backlog Updated", "board": board_data},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["structured"]["updatedBoard"]["columns"][0]["title"], updated_title)
            self.assertEqual(data["updatedBoard"]["columns"][0]["title"], updated_title)

            refreshed = self.client.get("/api/board", params={"username": username}).json()
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
