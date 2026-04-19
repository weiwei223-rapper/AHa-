import base64
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Quiz as QuizModel
from models import User as UserModel
from models import Video as VideoModel

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "aha-dev-secret")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


setup_logging()
logger = logging.getLogger("aha.api")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        try:
            seed_data_if_empty(db)
        except OperationalError:
            # Dev fallback: reset old incompatible schema to current models.
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            seed_data_if_empty(db)
    logger.info("Application startup complete")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_timing(request: Request, call_next) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"
    logger.info("%s %s -> %s (%.2fms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


class VideoPayload(BaseModel):
    name: str
    recognized: bool = False
    outline: bool = False
    pts: str = "-50"
    date: str


class QuizPayload(BaseModel):
    name: str
    source: str
    questions: list[dict]
    lastRate: str = "—"
    rateColor: str = "#7a90a8"
    done: bool = False


class RegisterPayload(BaseModel):
    email: str
    password: str
    name: str


class LoginPayload(BaseModel):
    email: str
    password: str


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_jwt(payload: dict[str, Any], exp_seconds: int = 60 * 60 * 24) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = {**payload, "exp": int(time.time()) + exp_seconds}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url_encode(json.dumps(body, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        expected = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(encoded_signature)):
            raise ValueError("invalid signature")
        payload = json.loads(_b64url_decode(encoded_payload))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> UserModel:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.replace("Bearer ", "", 1)
    payload = decode_jwt(token)
    user_id = payload.get("uid")
    user = db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def seed_data_if_empty(db: Session) -> None:
    if db.query(VideoModel).count() == 0:
        default_videos = [
            VideoModel(name="Python 基礎語法入門", recognized=True, outline=True, pts="-50", date="2026/03/20"),
            VideoModel(name="資料結構 - 陣列與串列", recognized=True, outline=True, pts="-50", date="2026/03/18"),
            VideoModel(name="演算法 - 排序方法比較", recognized=False, outline=False, pts="-50", date="2026/03/24"),
        ]
        db.add_all(default_videos)
    if db.query(QuizModel).count() == 0:
        default_quizzes = [
            QuizModel(
                name="Python 變數與資料型別",
                source="Python 基礎語法入門",
                questions=[
                    {"q": "下列哪個關鍵字用於在 Python 中定義一個函式？", "opts": ["function", "void", "def", "lambda"], "ans": 2},
                    {"q": "Python 中用來迭代一個序列的關鍵字是？", "opts": ["loop", "for", "each", "iterate"], "ans": 1},
                ],
                last_rate="90%",
                rate_color="#10b981",
                done=True,
            ),
            QuizModel(
                name="迴圈與條件判斷",
                source="Python 基礎語法入門",
                questions=[
                    {"q": "以下哪個關鍵字可以跳出迴圈？", "opts": ["skip", "exit", "break", "stop"], "ans": 2},
                    {"q": "Python 的 range(3) 會產生哪些數值？", "opts": ["1,2,3", "0,1,2,3", "0,1,2", "1,2"], "ans": 2},
                ],
                last_rate="73%",
                rate_color="#f59e0b",
                done=True,
            ),
        ]
        db.add_all(default_quizzes)
    db.commit()


@app.get("/")
def return_root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/videos")
def get_videos(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    videos = db.query(VideoModel).order_by(VideoModel.id.desc()).all()
    return [{"name": v.name, "recognized": v.recognized, "outline": v.outline, "pts": v.pts, "date": v.date} for v in videos]


@app.post("/videos", status_code=status.HTTP_201_CREATED)
def add_video(video: VideoPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    db_video = VideoModel(**video.model_dump())
    db.add(db_video)
    db.commit()
    return {"message": "Video added"}


@app.put("/videos/{index}")
def update_video(index: int, video: VideoPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    videos = db.query(VideoModel).order_by(VideoModel.id.desc()).all()
    if not (0 <= index < len(videos)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index out of range")
    target = videos[index]
    for key, value in video.model_dump().items():
        setattr(target, key, value)
    db.commit()
    return {"message": "Video updated"}


@app.get("/quizzes")
def get_quizzes(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    quizzes = db.query(QuizModel).order_by(QuizModel.id.desc()).all()
    return [
        {
            "name": q.name,
            "source": q.source,
            "questions": q.questions,
            "lastRate": q.last_rate,
            "rateColor": q.rate_color,
            "done": q.done,
        }
        for q in quizzes
    ]


@app.post("/quizzes", status_code=status.HTTP_201_CREATED)
def add_quiz(quiz: QuizPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    db_quiz = QuizModel(
        name=quiz.name,
        source=quiz.source,
        questions=quiz.questions,
        last_rate=quiz.lastRate,
        rate_color=quiz.rateColor,
        done=quiz.done,
    )
    db.add(db_quiz)
    db.commit()
    return {"message": "Quiz added"}


@app.put("/quizzes/{index}")
def update_quiz(index: int, quiz: QuizPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    quizzes = db.query(QuizModel).order_by(QuizModel.id.desc()).all()
    if not (0 <= index < len(quizzes)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index out of range")
    target = quizzes[index]
    target.name = quiz.name
    target.source = quiz.source
    target.questions = quiz.questions
    target.last_rate = quiz.lastRate
    target.rate_color = quiz.rateColor
    target.done = quiz.done
    db.commit()
    return {"message": "Quiz updated"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password too short")
    if db.query(UserModel).filter(UserModel.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = UserModel(email=payload.email, name=payload.name, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_jwt({"uid": user.id, "email": user.email})
    return {"token": token, "user": {"email": user.email, "name": user.name}}


@app.post("/auth/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user or user.hashed_password != hash_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_jwt({"uid": user.id, "email": user.email})
    return {"token": token, "user": {"email": user.email, "name": user.name}}


@app.post("/auth/logout")
def logout(_current_user: UserModel = Depends(get_current_user)) -> dict[str, str]:
    return {"message": "Logged out"}


@app.get("/auth/me")
def auth_me(current_user: UserModel = Depends(get_current_user)) -> dict[str, Any]:
    return {"email": current_user.email, "name": current_user.name}


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)