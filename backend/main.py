from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
import os
import json

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

try:
    from . import ai_analyzer, database, models, schema, code_compiler
except ImportError:
    import ai_analyzer
    import database
    import models
    import schema
    import code_compiler

def extract_youtube_title(url: str) -> str:
    """Extract a meaningful title from YouTube URL"""
    try:
        if "youtube.com/watch?v=" in url:
            # Extract video ID from standard YouTube URL
            video_id = url.split("v=")[1].split("&")[0]
            return f"YouTube 影片 - {video_id}"
        elif "youtu.be/" in url:
            # Extract video ID from short YouTube URL
            video_id = url.split("youtu.be/")[1].split("?")[0]
            return f"YouTube 影片 - {video_id}"
        elif "youtube.com/playlist?list=" in url:
            # Handle playlist URLs
            playlist_id = url.split("list=")[1].split("&")[0]
            return f"YouTube 播放清單 - {playlist_id}"
        else:
            return "YouTube 影片"
    except:
        return "YouTube 影片"

# Password hashing functions - define early so they can be used in startup
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - create tables and initial data
    try:
        models.Base.metadata.create_all(bind=database.engine)
        # Create initial user if not exists
        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == 1).first()
            if user is None:
                hashed_pwd = hash_password("password")
                user = models.User(
                    id=1,
                    name="wei",
                    email="wei@gmail.com",
                    password=hashed_pwd,
                    uid="UID-20260419",
                    points=10000,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print("Initial user created")
        finally:
            db.close()
    except Exception as e:
        print(f"Error during startup: {e}")
    yield

    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5173/", "http://localhost:5174", "http://localhost:5174/", "http://localhost:5175", "http://localhost:5175/", "http://localhost:5176", "http://localhost:5176/", "http://localhost:5177", "http://localhost:5177/", "http://localhost:3000", "http://localhost:3000/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.get("/")
def read_root():
    return {"message": "AHa AI API Server is running", "status": "ok"}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str

class CodeExecutionRequest(BaseModel):
    code: str

class CodeExecutionResponse(BaseModel):
    output: str
    error: str

@app.post("/auth/register", response_model=UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(database.get_db)):
    # Check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="該電子郵件已被使用")
    
    # Generate UID with current date
    uid = f"UID-{datetime.utcnow():%Y%m%d%H%M}"
    
    # Hash the password
    hashed_password = hash_password(payload.password)
    
    new_user = models.User(
        name=payload.name,
        email=payload.email,
        password=hashed_password,
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
    
    if not user:
        raise HTTPException(status_code=401, detail="電子郵件或密碼錯誤")
    
    # Verify the password using bcrypt
    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="電子郵件或密碼錯誤")
    
    return {
        "user": user,
        "message": f"歡迎回來，{user.name}！"
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest, db: Session = Depends(database.get_db)):
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    recent_videos = (
        db.query(models.Video)
        .order_by(models.Video.created_at.desc())
        .limit(3)
        .all()
    )
    video_context = [
        {
            "title": video.title,
            "video_link": video.video_link,
        }
        for video in recent_videos
    ]

    print(f"Chat request: {user_message[:50]}...")
    try:
        reply = ai_analyzer.generate_chat_reply(
            user_message,
            [{"role": item.role, "content": item.content} for item in payload.history],
            video_context,
        )
        print(f"Chat reply: {reply[:50]}...")
        return ChatResponse(reply=reply)
    except Exception as e:
        print(f"Error chatting with AI: {e}")
        # Use fallback reply instead of transcript fallback
        reply = "抱歉，AI 聊天服務目前無法使用。請稍後再試。"
        return ChatResponse(reply=reply)

@app.post("/api/execute-code", response_model=CodeExecutionResponse)
def execute_code(payload: CodeExecutionRequest):
    """Execute Python code and return output with validation"""
    if not payload.code or not payload.code.strip():
        return CodeExecutionResponse(output="", error="Code cannot be empty")
    
    # Use the improved compiler
    output, error = code_compiler.execute_python_code(
        payload.code,
        timeout=10,
        enable_security_check=True
    )
    
    return CodeExecutionResponse(output=output, error=error)

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    user.name = payload.name
    user.email = payload.email
    if payload.password:
        # Hash the password before updating
        user.password = hash_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/users/{user_id}/recharge-records", response_model=List[RechargeRecordResponse])
def read_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    records = (
        db.query(models.RechargeRecord)
        .filter(models.RechargeRecord.user_id == user_id)
        .order_by(models.RechargeRecord.id.desc())
        .all()
    )
    return records

@app.post("/users/{user_id}/recharge", response_model=RechargeRecordResponse)
def recharge_user(user_id: int, payload: RechargeRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    order_id = f"A{datetime.utcnow():%Y%m%d%H%M%S}"
    record = models.RechargeRecord(
        user_id=user.id,
        date=datetime.utcnow().strftime("%Y/%m/%d"),
        order_id=order_id,
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
    db.refresh(user)
    return record

# Videos API
@app.get("/api/videos", response_model=List[schema.VideoResponse])
def get_videos(user_id: int, db: Session = Depends(database.get_db)):
    videos = db.query(models.Video).filter(models.Video.user_id == user_id).order_by(models.Video.id.desc()).all()
    return videos

@app.post("/api/videos", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, db: Session = Depends(database.get_db)):
    raw_link = (payload.video_link or "").strip()
    if not raw_link:
        raise HTTPException(status_code=400, detail="請輸入影片連結")

    # Extract title from URL if not provided
    title = (payload.title or "").strip() or None
    if not title:
        # Try to extract a meaningful title from YouTube URL
        if "youtube.com" in raw_link or "youtu.be" in raw_link:
            title = extract_youtube_title(raw_link)
        else:
            title = "未命名影片"

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
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating video: {e}")
        raise HTTPException(status_code=500, detail="資料庫寫入失敗，請稍後再試")
    except Exception as e:
        db.rollback()
        print(f"Unexpected error creating video: {e}")
        raise HTTPException(status_code=500, detail="新增影片時發生未預期錯誤")

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="找不到該影片")
    db.delete(video)
    db.commit()
    return {"message": "影片已刪除"}

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

# Quiz API
@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz(video_id: int, user_id: int = 1, db: Session = Depends(database.get_db)):
    """Generate AI-powered quiz questions based on video content analysis"""
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="找不到該影片")

    try:
        title = video.title or "未命名影片"
        video_link = video.video_link
        
        # Use AI analyzer to generate quiz questions based on video content
        questions = ai_analyzer.analyze_video_content_with_ai(video_link, title)

        saved_questions = []
        for item in questions:
            correct_option = item.options[item.correct_answer] if 0 <= item.correct_answer < len(item.options) else ""
            question_record = models.QuizQuestion(
                user_id=user_id,
                video_id=video.id,
                question_content=item.question,
                reference_answer=correct_option,
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
            quiz_type="ai-coding",
            questions=questions
        )
    except Exception as e:
        print(f"Error generating quiz: {e}")
        # Fallback to basic questions if AI fails
        questions = ai_analyzer.generate_fallback_questions(title)
        return schema.QuizResponse(
            video_id=video.id,
            video_title=title,
            quiz_type="ai-coding",
            questions=questions
        )


# Quiz Results API
@app.post("/api/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, db: Session = Depends(database.get_db)):
    user_id = payload.user_id or 1

    quiz_result = models.QuizResult(
        user_id=user_id,
        video_id=payload.video_id,
        score=payload.score,
        total_questions=payload.total_questions
    )
    db.add(quiz_result)
    db.commit()
    db.refresh(quiz_result)
    return quiz_result

@app.get("/users/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, db: Session = Depends(database.get_db)):
    # Get video count created by this user
    video_count = db.query(models.Video).filter(models.Video.user_id == user_id).count()

    # Get user points
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    remaining_points = user.points

    # Get completed quizzes count
    completed_quizzes = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).count()

    # Calculate average accuracy
    quiz_results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    if quiz_results:
        total_accuracy = sum(result.score / result.total_questions * 100 for result in quiz_results)
        average_accuracy = total_accuracy / len(quiz_results)
    else:
        average_accuracy = 0.0

    return schema.UserStatsResponse(
        video_count=video_count,
        remaining_points=remaining_points,
        completed_quizzes=completed_quizzes,
        average_accuracy=round(average_accuracy, 1)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
