from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

class VideoCreate(BaseModel):
    video_link: str
    title: Optional[str] = None
    outline: Optional[str] = None
    user_id: Optional[int] = None
    cost_points: Optional[int] = 0
    error_report: Optional[str] = None

class VideoResponse(BaseModel):
    id: int
    video_link: str
    title: Optional[str] = None
    outline: Optional[str] = None
    user_id: Optional[int] = None
    cost_points: int
    error_report: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True   # Pydantic v2

class AIFeedbackCreate(BaseModel):
    user_id: int
    ai_message: str
    user_message: str
    error_report: Optional[str] = None

class AIFeedbackResponse(BaseModel):
    id: int
    user_id: int
    ai_message: str
    user_message: str
    error_report: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RechargeRecordResponse(BaseModel):
    id: int
    date: str
    order_id: str
    amount: int
    points: int
    plan_content: Optional[str] = None
    payment_method: Optional[str] = None
    plan_id: Optional[str] = None

    class Config:
        from_attributes = True

class QuizQuestion(BaseModel):
    question: str
    correct_answer: str
    options: List[str] = []
    question_type: str = "fill-in-the-blank"
    explanation: Optional[str] = None
    reference_concept: Optional[str] = None
    source_time: Optional[str] = None
    source_excerpt: Optional[str] = None
    starter_code: Optional[str] = None
    test_cases: List[str] = []

class QuizQuestionCreate(BaseModel):
    user_id: int
    video_id: int
    question_content: str
    reference_answer: str
    options: List[str] = []
    answer_record: Optional[str] = None
    accuracy: Optional[int] = 0

class QuizQuestionResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    question_content: str
    reference_answer: str
    answer_record: Optional[str] = None
    accuracy: int
    options: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True

class QuizResponse(BaseModel):
    video_id: int
    video_title: str
    quiz_type: str = "ai-coding"
    questions: List[QuizQuestion]


class TranscriptChunk(BaseModel):
    index: int
    content: str
    score: Optional[float] = None


class VideoAnalysisResponse(BaseModel):
    video_id: int
    video_title: str
    transcript_source: str
    transcript_excerpt: str
    outline_markdown: str
    key_topics: List[str]
    retrieved_chunks: List[TranscriptChunk]
    vector_backend: str
    generated_at: datetime

class QuizResultCreate(BaseModel):
    user_id: int = 1
    video_id: int
    score: int
    total_questions: int = 5
    title: Optional[str] = None # 新增標題欄位
    details_json: Optional[str] = None # 儲存詳細批改細節

class QuizResultUpdate(BaseModel):
    title: str

class QuizResultResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    score: int
    total_questions: int
    title: Optional[str] = None
    details_json: Optional[str] = None
    completed_at: datetime

    class Config:
        from_attributes = True

class GenerationRecordCreate(BaseModel):
    user_id: int
    quiz_question_id: int
    consumed_points: int

class GenerationRecordResponse(BaseModel):
    id: int
    user_id: int
    quiz_question_id: int
    consumed_points: int
    created_at: datetime

    class Config:
        from_attributes = True

class UploadRecordCreate(BaseModel):
    user_id: int
    video_id: int
    consumed_points: int

class UploadRecordResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    consumed_points: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserStatsResponse(BaseModel):
    video_count: int
    remaining_points: int
    completed_quizzes: int
    average_accuracy: float
