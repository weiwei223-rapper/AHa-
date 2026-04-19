# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models
import database
import schema   # ← 你原本的 import 名稱

app = FastAPI(title="學習平台 - 影片上傳")

# CORS（讓 React 前端可以呼叫）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 啟動時建立資料表
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== 新增 GET：取得所有影片 ====================
@app.get("/api/videos", response_model=List[schema.VideoResponse])
def get_all_videos(db: Session = Depends(get_db)):
    videos = db.query(models.Video).all()
    return videos

# ==================== POST：上傳影片連結 ====================
@app.post("/api/videos", response_model=schema.VideoResponse)
def upload_video(video: schema.VideoCreate, db: Session = Depends(get_db)):
    if not video.video_link or not video.video_link.strip():
        raise HTTPException(status_code=400, detail="請提供有效影片連結")

    new_video = models.Video(
        video_link=video.video_link,
        # title 之後可以擴充自動抓取 YouTube 標題
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return new_video

# （你原本的 /users 路由保留，如果你之後還要用）
@app.get("/users/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="找不到該用戶")
    return {"id": user.id, "email": user.email, "name": user.name}