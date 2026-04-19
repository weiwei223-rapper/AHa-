from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, database

app = FastAPI(title="影片連結上傳 API")

# CORS（讓前端 React 可以呼叫）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 你的 React port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 建立資料表
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/videos", response_model=schemas.VideoResponse)
def upload_video(video: schemas.VideoCreate, db: Session = Depends(get_db)):
    if not video.video_link or not video.video_link.strip():
        raise HTTPException(status_code=400, detail="請提供有效影片連結")

    new_video = models.Video(
        video_link=video.video_link,
        # title 可自行擴充自動抓取（之後再教）
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return new_video   # 自動轉成 schemas.VideoResponse 格式