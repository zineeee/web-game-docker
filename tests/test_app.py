import os
import tempfile
import unittest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key")
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(prefix="arcade-hub-tests-"), "test.db")

import app as app_module


class ArcadeHubTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app_module.app.test_client()
        with app_module.get_db_connection() as conn:
            conn.execute("DELETE FROM game_scores")
            conn.execute("DELETE FROM feedback")
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM leaderboard")
            conn.commit()

    def register_and_login(self):
        response = self.client.post(
            "/register",
            data={
                "username": "test_player",
                "email": "player@example.com",
                "password": "secure-test-password",
                "confirm_password": "secure-test-password",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            "/login",
            data={"identity": "test_player", "password": "secure-test-password"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Arcade Hub", response.data)

    def test_registration_login_and_dashboard(self):
        self.register_and_login()
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"test_player", response.data)

    def test_games_require_login(self):
        response = self.client.get("/guess_game")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_guess_game_saves_completed_score(self):
        self.register_and_login()
        with self.client.session_transaction() as session:
            session["guess_secret"] = 42
            session["guess_attempts"] = 0
            session["guess_completed"] = False

        response = self.client.post("/guess_game", data={"guess": "42"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chính xác".encode("utf-8"), response.data)
        with app_module.get_db_connection() as conn:
            row = conn.execute(
                "SELECT game_name, score FROM game_scores"
            ).fetchone()
        self.assertEqual(row["game_name"], "Đoán số")
        self.assertEqual(row["score"], 100)

    def test_golf_saves_score_after_five_shots(self):
        self.register_and_login()
        for _ in range(5):
            response = self.client.post("/golf_game", data={"action": "hit"}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
        with app_module.get_db_connection() as conn:
            row = conn.execute(
                "SELECT game_name, score FROM game_scores"
            ).fetchone()
        self.assertEqual(row["game_name"], "Golf mini")
        self.assertGreaterEqual(row["score"], 250)
        self.assertLessEqual(row["score"], 1500)

    def test_feedback_is_saved(self):
        response = self.client.post(
            "/feedback",
            data={"message": "Them game moi nhe"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with app_module.get_db_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
