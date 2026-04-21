from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import bcrypt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

import database
import models
import schema

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
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"],  # Frontend URLs
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

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None

class RechargeRequest(BaseModel):
    points: int
    price: int

class RechargeRecordResponse(BaseModel):
    date: str
    order_id: str
    amount: int

    class Config:
        from_attributes = True

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
def get_videos(db: Session = Depends(database.get_db)):
    videos = db.query(models.Video).order_by(models.Video.id.desc()).all()
    return videos

@app.post("/api/videos", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, db: Session = Depends(database.get_db)):
    # Extract title from URL if not provided
    title = payload.title
    if not title:
        # Try to extract a meaningful title from YouTube URL
        if "youtube.com" in payload.video_link or "youtu.be" in payload.video_link:
            title = extract_youtube_title(payload.video_link)
        else:
            title = "未命名影片"

    video = models.Video(video_link=payload.video_link, title=title)
    db.add(video)
    db.commit()
    db.refresh(video)
    return video

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="找不到該影片")
    db.delete(video)
    db.commit()
    return {"message": "影片已刪除"}

# Quiz API
@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="找不到該影片")

    # Generate quiz questions based on video content analysis
    title = video.title or "未命名影片"
    video_link = video.video_link

    questions = generate_content_based_questions(title, video_link)

    return schema.QuizResponse(
        video_id=video.id,
        video_title=title,
        questions=questions
    )

def generate_content_based_questions(title: str, video_link: str) -> List[schema.QuizQuestion]:
    """Generate 5 quiz questions based on video content analysis"""
    questions = []

    # Analyze video type and content
    is_youtube = "youtube.com" in video_link or "youtu.be" in video_link
    is_playlist = "playlist" in video_link
    is_tutorial = any(keyword in title.lower() for keyword in ["教學", "指南", "介紹", "基礎", "入門", "學習", "課程", "tutorial", "guide", "introduction", "basic", "learn", "course"])

    if is_youtube:
        if is_playlist:
            # Questions for playlist/course content
            questions = [
                schema.QuizQuestion(
                    question=f"這個播放清單 '{title}' 的主要學習目標是什麼？",
                    options=["掌握基礎概念", "學習進階技巧", "了解實務應用", "複習重要知識"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"在 '{title}' 系列中，你最想學習哪個主題？",
                    options=["理論基礎", "實作練習", "案例分析", "問題解決"],
                    correct_answer=1
                ),
                schema.QuizQuestion(
                    question=f"這個 '{title}' 播放清單適合什麼程度的學習者？",
                    options=["完全新手", "有基礎者", "進階學習者", "專家複習"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"學習 '{title}' 後，你希望能應用在哪些方面？",
                    options=["個人興趣", "工作技能", "學業提升", "創業專案"],
                    correct_answer=1
                ),
                schema.QuizQuestion(
                    question=f"這個 '{title}' 系列的教學風格如何？",
                    options=["理論講解", "實作示範", "互動討論", "綜合教學"],
                    correct_answer=1
                )
            ]
        elif is_tutorial:
            # Questions for tutorial videos
            questions = [
                schema.QuizQuestion(
                    question=f"這個教學影片 '{title}' 主要教什麼？",
                    options=["基礎概念", "進階技巧", "實作方法", "理論知識"],
                    correct_answer=2
                ),
                schema.QuizQuestion(
                    question=f"學習 '{title}' 之前需要具備什麼基礎？",
                    options=["完全不需要", "基本概念", "相關經驗", "專業知識"],
                    correct_answer=1
                ),
                schema.QuizQuestion(
                    question=f"這個 '{title}' 教學的難度等級？",
                    options=["入門級", "中級", "進階級", "專家級"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"看完 '{title}' 後，你覺得最有收穫的是？",
                    options=["新知識", "實作技能", "問題解決", "靈感啟發"],
                    correct_answer=1
                ),
                schema.QuizQuestion(
                    question=f"這個 '{title}' 教學的呈現方式？",
                    options=["文字講解", "視覺示範", "互動練習", "綜合展示"],
                    correct_answer=1
                )
            ]
        else:
            # General YouTube video questions
            questions = [
                schema.QuizQuestion(
                    question=f"這個影片 '{title}' 的內容類型是？",
                    options=["教育內容", "娛樂內容", "新聞資訊", "個人分享"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"你對 '{title}' 的主題感興趣嗎？",
                    options=["非常感興趣", "有點感興趣", "普通", "不太感興趣"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"這個 '{title}' 影片適合什麼場合觀看？",
                    options=["學習時間", "休閒娛樂", "工作休息", "通勤路上"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"看完 '{title}' 後，你想進一步了解什麼？",
                    options=["相關主題", "創作者其他作品", "類似內容", "不需了解"],
                    correct_answer=0
                ),
                schema.QuizQuestion(
                    question=f"這個 '{title}' 影片的品質如何？",
                    options=["內容豐富", "製作精良", "資訊準確", "以上皆是"],
                    correct_answer=3
                )
            ]
    else:
        # General video questions for non-YouTube content
        questions = [
            schema.QuizQuestion(
                question=f"這個影片 '{title}' 包含什麼內容？",
                options=["教學內容", "娛樂內容", "資訊內容", "其他"],
                correct_answer=0
            ),
            schema.QuizQuestion(
                question=f"你對 '{title}' 的評價是？",
                options=["非常喜歡", "喜歡", "普通", "不喜歡"],
                correct_answer=1
            ),
            schema.QuizQuestion(
                question=f"這個 '{title}' 影片的長度大約是？",
                options=["少於5分鐘", "5-15分鐘", "15-30分鐘", "超過30分鐘"],
                correct_answer=1
            ),
            schema.QuizQuestion(
                question=f"看完 '{title}' 後，你學到了什麼？",
                options=["新知識", "新技能", "新觀點", "沒有收穫"],
                correct_answer=0
            ),
            schema.QuizQuestion(
                question=f"你會推薦 '{title}' 給其他人嗎？",
                options=["會", "可能會", "不會", "視情況而定"],
                correct_answer=0
            )
        ]

    return questions
