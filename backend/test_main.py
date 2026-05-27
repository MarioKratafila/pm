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


class UserRegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = pathlib.Path(tempfile.mkdtemp())
        main.DB_PATH = cls.temp_dir / "pm_reg_test.db"
        main.init_db()
        cls.client = TestClient(main.app)

    def test_register_and_login(self):
        response = self.client.post(
            "/api/register", json={"username": "newuser", "password": "securepass"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], "newuser")

        main._sessions.clear()
        response = self.client.post(
            "/api/login", json={"username": "newuser", "password": "securepass"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())

    def test_register_wrong_password_fails(self):
        self.client.post("/api/register", json={"username": "user2", "password": "mypassword"})
        main._sessions.clear()
        response = self.client.post(
            "/api/login", json={"username": "user2", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 401)

    def test_register_duplicate_username(self):
        self.client.post("/api/register", json={"username": "dupuser", "password": "pass123"})
        response = self.client.post(
            "/api/register", json={"username": "dupuser", "password": "other123"}
        )
        self.assertEqual(response.status_code, 409)

    def test_register_short_password(self):
        response = self.client.post(
            "/api/register", json={"username": "shortpass", "password": "abc"}
        )
        self.assertEqual(response.status_code, 400)

    def test_register_short_username(self):
        response = self.client.post(
            "/api/register", json={"username": "ab", "password": "validpass"}
        )
        self.assertEqual(response.status_code, 400)

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


class MultiBoardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = pathlib.Path(tempfile.mkdtemp())
        main.DB_PATH = cls.temp_dir / "pm_multi_test.db"
        main.init_db()
        cls.client = TestClient(main.app)
        response = cls.client.post(
            "/api/register", json={"username": "boarduser", "password": "testpass"}
        )
        assert response.status_code == 200
        cls.token = response.json()["token"]
        cls.auth = {"Authorization": f"Bearer {cls.token}"}

    def test_list_boards_after_register(self):
        response = self.client.get("/api/boards", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        boards = response.json()
        self.assertGreaterEqual(len(boards), 1)
        names = [b["name"] for b in boards]
        self.assertIn("My Board", names)
        self.assertIn("id", boards[0])
        self.assertIn("card_count", boards[0])

    def test_create_board(self):
        response = self.client.post(
            "/api/boards", headers=self.auth, json={"name": "Sprint 1"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Sprint 1")

        list_response = self.client.get("/api/boards", headers=self.auth)
        names = [b["name"] for b in list_response.json()]
        self.assertIn("Sprint 1", names)

    def test_get_board_by_id(self):
        list_response = self.client.get("/api/boards", headers=self.auth)
        board_id = list_response.json()[0]["id"]

        response = self.client.get(f"/api/boards/{board_id}", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        board = response.json()
        self.assertIn("columns", board)
        self.assertIn("cards", board)

    def test_update_board_by_id(self):
        list_response = self.client.get("/api/boards", headers=self.auth)
        board_id = list_response.json()[0]["id"]

        board = self.client.get(f"/api/boards/{board_id}", headers=self.auth).json()
        board["columns"][0]["title"] = "Renamed Backlog"

        response = self.client.put(f"/api/boards/{board_id}", headers=self.auth, json=board)
        self.assertEqual(response.status_code, 200)

        refreshed = self.client.get(f"/api/boards/{board_id}", headers=self.auth).json()
        self.assertEqual(refreshed["columns"][0]["title"], "Renamed Backlog")

    def test_rename_board(self):
        list_response = self.client.get("/api/boards", headers=self.auth)
        board_id = list_response.json()[0]["id"]

        response = self.client.patch(
            f"/api/boards/{board_id}", headers=self.auth, json={"name": "Renamed Board"}
        )
        self.assertEqual(response.status_code, 200)

        boards = self.client.get("/api/boards", headers=self.auth).json()
        board_names = [b["name"] for b in boards]
        self.assertIn("Renamed Board", board_names)

    def test_delete_board_not_last(self):
        create_response = self.client.post(
            "/api/boards", headers=self.auth, json={"name": "Temp Board"}
        )
        board_id = create_response.json()["id"]

        response = self.client.delete(f"/api/boards/{board_id}", headers=self.auth)
        self.assertEqual(response.status_code, 200)

        boards = self.client.get("/api/boards", headers=self.auth).json()
        self.assertNotIn(board_id, [b["id"] for b in boards])

    def test_cannot_delete_last_board(self):
        list_response = self.client.get("/api/boards", headers=self.auth)
        boards = list_response.json()
        if len(boards) != 1:
            for b in boards[1:]:
                self.client.delete(f"/api/boards/{b['id']}", headers=self.auth)

        list_response = self.client.get("/api/boards", headers=self.auth)
        last_id = list_response.json()[0]["id"]

        response = self.client.delete(f"/api/boards/{last_id}", headers=self.auth)
        self.assertEqual(response.status_code, 400)

    def test_board_not_found_returns_404(self):
        response = self.client.get("/api/boards/999999", headers=self.auth)
        self.assertEqual(response.status_code, 404)

    def test_cannot_access_another_users_board(self):
        self.client.post(
            "/api/register", json={"username": "otheruser", "password": "testpass"}
        )
        other_login = self.client.post(
            "/api/login", json={"username": "otheruser", "password": "testpass"}
        )
        other_auth = {"Authorization": f"Bearer {other_login.json()['token']}"}

        other_boards = self.client.get("/api/boards", headers=other_auth).json()
        other_board_id = other_boards[0]["id"]

        response = self.client.get(f"/api/boards/{other_board_id}", headers=self.auth)
        self.assertEqual(response.status_code, 404)

    def test_create_board_empty_name(self):
        response = self.client.post(
            "/api/boards", headers=self.auth, json={"name": "   "}
        )
        self.assertEqual(response.status_code, 400)

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
