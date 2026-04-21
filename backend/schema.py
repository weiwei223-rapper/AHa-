from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class VideoCreate(BaseModel):
    video_link: str
    title: Optional[str] = None

class VideoResponse(BaseModel):
    id: int
    video_link: str
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True   # Pydantic v2

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int  # Index of correct option

class QuizResponse(BaseModel):
    video_id: int
    video_title: str
    questions: List[QuizQuestion]