from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import json

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

load_dotenv()

try:
    from . import ai_analyzer, code_compiler, database, learning_pipeline, models, schema
except ImportError:
    import ai_analyzer
    import code_compiler
    import database
    import learning_pipeline
    import models
    import schema


def extract_youtube_title(url: str) -> str:
    try:
        if "youtube.com/watch?v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
            return f"YouTube Video - {video_id}"
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
            return f"YouTube Video - {video_id}"
        if "youtube.com/playlist?list=" in url:
            playlist_id = url.split("list=")[1].split("&")[0]
            return f"YouTube Playlist - {playlist_id}"
        return "YouTube Video"
    except Exception:
        return "YouTube Video"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        models.Base.metadata.create_all(bind=database.engine)
        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == 1).first()
            if user is None:
                user = models.User(
                    id=1,
                    name="wei",
                    email="wei@gmail.com",
                    password=hash_password("password"),
                    uid="UID-20260419",
                    points=10000,
                )
                db.add(user)
                db.commit()
        finally:
            db.close()
    except Exception as exc:
        print(f"Error during startup: {exc}")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Global exception caught: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    uid: str
    points: int

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None


class RechargeRequest(BaseModel):
    points: int
    price: int
    plan_content: Optional[str] = None
    payment_method: Optional[str] = None
    plan_id: Optional[str] = None


class RechargeRecordResponse(BaseModel):
    date: str
    order_id: str
    amount: int
    points: int
    plan_content: Optional[str] = None
    payment_method: Optional[str] = None
    plan_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user: UserResponse
    message: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    user_id: Optional[int] = None
    selected_video_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str


class CodeExecutionRequest(BaseModel):
    code: str


class CodeExecutionResponse(BaseModel):
    output: str
    error: str


class GeminiHealthResponse(BaseModel):
    ok: bool
    model: str
    reply: str


@app.get("/")
def read_root():
    return {"message": "AHa AI API Server is running", "status": "ok"}


@app.get("/api/health/gemini", response_model=GeminiHealthResponse)
def gemini_health_check():
    try:
        result = ai_analyzer.test_gemini_connection()
        return GeminiHealthResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Gemini connection failed: {exc}")


@app.post("/auth/register", response_model=UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    uid = f"UID-{datetime.utcnow():%Y%m%d%H%M}"
    new_user = models.User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        uid=uid,
        points=0,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user": user, "message": f"Welcome back, {user.name}"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest, db: Session = Depends(database.get_db)):
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    selected_video = None
    if payload.selected_video_id is not None:
        selected_video_query = db.query(models.Video).filter(models.Video.id == payload.selected_video_id)
        if payload.user_id is not None:
            selected_video_query = selected_video_query.filter(models.Video.user_id == payload.user_id)
        selected_video = selected_video_query.first()

    if selected_video is not None:
        context_videos = [selected_video]
    else:
        recent_video_query = db.query(models.Video)
        if payload.user_id is not None:
            recent_video_query = recent_video_query.filter(models.Video.user_id == payload.user_id)
        context_videos = recent_video_query.order_by(models.Video.created_at.desc()).limit(3).all()

    video_context = [{"title": video.title, "video_link": video.video_link} for video in context_videos]

    try:
        reply = ai_analyzer.generate_chat_reply(
            user_message,
            [{"role": item.role, "content": item.content} for item in payload.history],
            video_context,
        )
        return ChatResponse(reply=reply)
    except Exception as exc:
        print(f"Error chatting with Gemini: {exc}")
        return ChatResponse(reply=ai_analyzer.generate_transcript_fallback_reply(user_message, video_context))


@app.post("/api/execute-code", response_model=CodeExecutionResponse)
def execute_code(payload: CodeExecutionRequest):
    if not payload.code or not payload.code.strip():
        return CodeExecutionResponse(output="", error="Code cannot be empty")
    output, error = code_compiler.execute_python_code(
        payload.code,
        timeout=10,
        enable_security_check=True,
    )
    return CodeExecutionResponse(output=output, error=error)


@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = payload.name
    user.email = payload.email
    if payload.password:
        user.password = hash_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}/recharge-records", response_model=List[RechargeRecordResponse])
def read_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    return (
        db.query(models.RechargeRecord)
        .filter(models.RechargeRecord.user_id == user_id)
        .order_by(models.RechargeRecord.id.desc())
        .all()
    )


@app.post("/users/{user_id}/recharge", response_model=RechargeRecordResponse)
def recharge_user(user_id: int, payload: RechargeRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    record = models.RechargeRecord(
        user_id=user.id,
        date=datetime.utcnow().strftime("%Y/%m/%d"),
        order_id=f"A{datetime.utcnow():%Y%m%d%H%M%S}",
        amount=payload.price,
        points=payload.points,
        plan_content=payload.plan_content,
        payment_method=payload.payment_method,
        plan_id=payload.plan_id,
    )
    user.points += payload.points
    db.add(record)
    db.add(user)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/videos", response_model=List[schema.VideoResponse])
def get_videos(user_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    query = db.query(models.Video)
    if user_id is not None:
        query = query.filter(models.Video.user_id == user_id)
    return query.order_by(models.Video.id.desc()).all()


@app.get("/api/videos/{video_id}/analysis", response_model=schema.VideoAnalysisResponse)
def analyze_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    try:
        title = video.title or "Untitled Video"
        analysis = learning_pipeline.analyze_video(video.id, title, video.video_link)
        if analysis.outline_markdown and analysis.outline_markdown != video.outline:
            video.outline = analysis.outline_markdown
            db.add(video)
            db.commit()
            db.refresh(video)
        return analysis
    except Exception as exc:
        print(f"Error analyzing video: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze video: {exc}")


@app.post("/api/videos", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, db: Session = Depends(database.get_db)):
    raw_link = (payload.video_link or "").strip()
    if not raw_link:
        raise HTTPException(status_code=400, detail="Please provide a video link")

    title = (payload.title or "").strip() or None
    if not title:
        title = extract_youtube_title(raw_link) if ("youtube.com" in raw_link or "youtu.be" in raw_link) else "Uploaded Video"

    try:
        video = models.Video(
            video_link=raw_link,
            title=title,
            outline=payload.outline,
            user_id=payload.user_id,
            cost_points=payload.cost_points or 0,
            error_report=payload.error_report,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        if payload.user_id is not None:
            upload = models.UploadRecord(
                user_id=payload.user_id,
                video_id=video.id,
                consumed_points=payload.cost_points or 0,
            )
            db.add(upload)
            db.commit()
        return video
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Database error creating video: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create video")


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return {"message": "Video deleted"}


@app.post("/api/feedbacks", response_model=schema.AIFeedbackResponse)
def create_ai_feedback(payload: schema.AIFeedbackCreate, db: Session = Depends(database.get_db)):
    feedback = models.AIFeedback(
        user_id=payload.user_id,
        ai_message=payload.ai_message,
        user_message=payload.user_message,
        error_report=payload.error_report,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@app.get("/api/feedbacks", response_model=List[schema.AIFeedbackResponse])
def get_ai_feedbacks(db: Session = Depends(database.get_db)):
    return db.query(models.AIFeedback).order_by(models.AIFeedback.id.desc()).all()


@app.delete("/api/feedbacks/conversations/{conversation_id}")
def delete_chat_conversation(
    conversation_id: str,
    user_id: int = Query(..., description="User id"),
    db: Session = Depends(database.get_db),
):
    """
    Delete all ai_feedback rows that belong to a single chat conversation.

    Note: the frontend stores the conversation token in `error_report` as:
      `chat-session:{conversation_id}`
    """

    token = f"chat-session:{conversation_id}"
    q = (
        db.query(models.AIFeedback)
        .filter(models.AIFeedback.user_id == user_id)
        .filter(models.AIFeedback.error_report == token)
    )
    deleted_count = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return {"message": "Conversation deleted", "deleted_count": deleted_count}


@app.post("/api/quiz-questions", response_model=schema.QuizQuestionResponse)
def create_quiz_question(payload: schema.QuizQuestionCreate, db: Session = Depends(database.get_db)):
    question = models.QuizQuestion(
        user_id=payload.user_id,
        video_id=payload.video_id,
        question_content=payload.question_content,
        reference_answer=payload.reference_answer,
        answer_record=payload.answer_record,
        accuracy=payload.accuracy or 0,
        options_json=json.dumps(payload.options, ensure_ascii=False),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return schema.QuizQuestionResponse(
        id=question.id,
        user_id=question.user_id,
        video_id=question.video_id,
        question_content=question.question_content,
        reference_answer=question.reference_answer,
        answer_record=question.answer_record,
        accuracy=question.accuracy,
        options=payload.options,
        created_at=question.created_at,
    )


@app.get("/api/quiz-questions", response_model=List[schema.QuizQuestionResponse])
def get_quiz_questions(db: Session = Depends(database.get_db)):
    questions = db.query(models.QuizQuestion).order_by(models.QuizQuestion.id.desc()).all()
    return [
        schema.QuizQuestionResponse(
            id=q.id,
            user_id=q.user_id,
            video_id=q.video_id,
            question_content=q.question_content,
            reference_answer=q.reference_answer,
            answer_record=q.answer_record,
            accuracy=q.accuracy,
            options=json.loads(q.options_json or "[]"),
            created_at=q.created_at,
        )
        for q in questions
    ]


@app.post("/api/uploads", response_model=schema.UploadRecordResponse)
def create_upload(payload: schema.UploadRecordCreate, db: Session = Depends(database.get_db)):
    upload = models.UploadRecord(
        user_id=payload.user_id,
        video_id=payload.video_id,
        consumed_points=payload.consumed_points,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


@app.post("/api/generations", response_model=schema.GenerationRecordResponse)
def create_generation(payload: schema.GenerationRecordCreate, db: Session = Depends(database.get_db)):
    generation = models.GenerationRecord(
        user_id=payload.user_id,
        quiz_question_id=payload.quiz_question_id,
        consumed_points=payload.consumed_points,
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz(
    video_id: int,
    user_id: int = 1,
    outline: Optional[str] = None,
    db: Session = Depends(database.get_db),
):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    title = video.title or "Untitled Video"
    try:
        quiz_response = learning_pipeline.generate_quiz(
            video.id,
            title,
            video.video_link,
            outline=(outline or video.outline),
        )
        questions = quiz_response.questions
        saved_questions = []
        for item in questions:
            question_record = models.QuizQuestion(
                user_id=user_id,
                video_id=video.id,
                question_content=item.question,
                reference_answer=item.correct_answer,
                answer_record=None,
                accuracy=0,
                options_json=json.dumps(item.options, ensure_ascii=False),
            )
            db.add(question_record)
            saved_questions.append(question_record)

        db.commit()

        if saved_questions:
            db.refresh(saved_questions[0])
            generation_record = models.GenerationRecord(
                user_id=user_id,
                quiz_question_id=saved_questions[0].id,
                consumed_points=video.cost_points or 0,
            )
            db.add(generation_record)
            db.commit()

        return schema.QuizResponse(
            video_id=video.id,
            video_title=title,
            quiz_type=quiz_response.quiz_type,
            questions=questions,
        )
    except Exception as exc:
        print(f"Error generating quiz: {exc}")
        questions = ai_analyzer.generate_fallback_questions(title)
        return schema.QuizResponse(
            video_id=video.id,
            video_title=title,
            quiz_type="fallback-coding",
            questions=questions,
        )


@app.post("/api/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, db: Session = Depends(database.get_db)):
    user_id = payload.user_id or 1
    quiz_result = models.QuizResult(
        user_id=user_id,
        video_id=payload.video_id,
        score=payload.score,
        total_questions=payload.total_questions,
    )
    db.add(quiz_result)
    db.commit()
    db.refresh(quiz_result)
    return quiz_result


@app.get("/users/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, db: Session = Depends(database.get_db)):
    video_count = db.query(models.Video).filter(models.Video.user_id == user_id).count()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    completed_quizzes = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).count()
    quiz_results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    average_accuracy = (
        sum(result.score / result.total_questions * 100 for result in quiz_results) / len(quiz_results)
        if quiz_results
        else 0.0
    )
    return schema.UserStatsResponse(
        video_count=video_count,
        remaining_points=user.points,
        completed_quizzes=completed_quizzes,
        average_accuracy=round(average_accuracy, 1),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
