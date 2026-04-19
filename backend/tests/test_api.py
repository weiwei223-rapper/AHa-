import os
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


TEST_DB = Path(__file__).resolve().parent / "test_aha.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"

if TEST_DB.exists():
    TEST_DB.unlink()

from main import app  # noqa: E402


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_endpoints_return_success() -> None:
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/videos").status_code == 200
        assert client.get("/quizzes").status_code == 200


def test_auth_register_login_and_me() -> None:
    with TestClient(app) as client:
        email = f"{uuid.uuid4().hex[:8]}@example.com"
        payload = {"email": email, "password": "password123", "name": "Test User"}

        reg = client.post("/auth/register", json=payload)
        assert reg.status_code == 201
        token = reg.json()["token"]
        assert token

        login = client.post("/auth/login", json={"email": email, "password": "password123"})
        assert login.status_code == 200
        login_token = login.json()["token"]
        assert login_token

        me = client.get("/auth/me", headers=_auth_headers(login_token))
        assert me.status_code == 200
        assert me.json()["email"] == email


def test_videos_and_quizzes_create_update_flow() -> None:
    with TestClient(app) as client:
        before_videos = client.get("/videos").json()
        before_quizzes = client.get("/quizzes").json()

        video_payload = {
            "name": "測試影片",
            "recognized": True,
            "outline": False,
            "pts": "-50",
            "date": "2026/04/16",
        }
        quiz_payload = {
            "name": "測試測驗",
            "source": "測試影片",
            "questions": [{"q": "Q1", "opts": ["A", "B", "C", "D"], "ans": 1}],
            "lastRate": "—",
            "rateColor": "#7a90a8",
            "done": False,
        }

        created_video = client.post("/videos", json=video_payload)
        created_quiz = client.post("/quizzes", json=quiz_payload)
        assert created_video.status_code == 201
        assert created_quiz.status_code == 201

        videos_after_create = client.get("/videos").json()
        quizzes_after_create = client.get("/quizzes").json()
        assert len(videos_after_create) == len(before_videos) + 1
        assert len(quizzes_after_create) == len(before_quizzes) + 1

        updated_video = {**video_payload, "outline": True}
        updated_quiz = {**quiz_payload, "done": True, "lastRate": "100%", "rateColor": "#10b981"}
        assert client.put("/videos/0", json=updated_video).status_code == 200
        assert client.put("/quizzes/0", json=updated_quiz).status_code == 200
