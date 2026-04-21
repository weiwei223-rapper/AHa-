from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password = Column(String)
    uid = Column(String, unique=True, index=True)
    points = Column(Integer, default=0)

    recharge_records = relationship(
        "RechargeRecord",
        back_populates="user",
        cascade="all, delete-orphan",
    )

class RechargeRecord(Base):
    __tablename__ = "recharge_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)
    order_id = Column(String, unique=True, index=True)
    amount = Column(Integer)

    user = relationship("User", back_populates="recharge_records")

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    video_link = Column(String, nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"))
    score = Column(Integer)  # Score out of total questions (e.g., 3 out of 5)
    total_questions = Column(Integer, default=5)
    completed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    video = relationship("Video")