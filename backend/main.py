from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

import database
import models
import schema

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
                user = models.User(
                    id=1,
                    name="wei",
                    email="wei@gmail.com",
                    password="password",
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176"],  # Frontend URLs
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
        user.password = payload.password
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
    video = models.Video(video_link=payload.video_link)
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
