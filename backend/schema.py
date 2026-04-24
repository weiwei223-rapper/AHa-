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
    explanation: Optional[str] = None

class QuizResponse(BaseModel):
    video_id: int
    video_title: str
    quiz_type: str = "ai-coding"
    questions: List[QuizQuestion]

class QuizResultCreate(BaseModel):
    video_id: int
    score: int
    total_questions: int = 5

class QuizResultResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    score: int
    total_questions: int
    completed_at: datetime

    class Config:
        from_attributes = True

class UserStatsResponse(BaseModel):
    video_count: int
    remaining_points: int
    completed_quizzes: int
    average_accuracy: float
