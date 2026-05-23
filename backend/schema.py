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
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    filename: str
    title: str
    content_text: Optional[str] = None
    outline: Optional[str] = None
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    uid: str
    points: int
    last_login_date: Optional[str] = None
    consecutive_login_days: int = 0
    total_login_days: int = 0
    current_quiz_draft: Optional[str] = None
    claimed_achievement_points: int = 0

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    current_quiz_draft: Optional[str] = None

class AIFeedbackCreate(BaseModel):
    user_id: int
    ai_message: str
    user_message: str
    error_report: Optional[str] = None
    video_id: Optional[int] = None
    document_id: Optional[int] = None

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
    balance_after: Optional[int] = None
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
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    question_content: str
    reference_answer: str
    options: List[str] = []
    answer_record: Optional[str] = None
    accuracy: Optional[int] = 0

class QuizQuestionResponse(BaseModel):
    id: int
    user_id: int
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    question_content: str
    reference_answer: str
    answer_record: Optional[str] = None
    accuracy: int
    options: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class QuizResponse(BaseModel):
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    video_title: str
    quiz_type: str = "ai-coding"
    questions: List[QuizQuestion]
    token_usage: Optional[TokenUsage] = None
    consumed_points: Optional[int] = 0


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
    token_usage: Optional[TokenUsage] = None
    consumed_points: Optional[int] = 0

class QuizResultCreate(BaseModel):
    user_id: int = 1
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    score: int
    total_questions: int = 5
    title: Optional[str] = None
    details_json: Optional[str] = None
    error_report: Optional[str] = None

class QuizResultUpdate(BaseModel):
    title: Optional[str] = None
    score: Optional[int] = None
    details_json: Optional[str] = None
    error_report: Optional[str] = None

class QuizResultResponse(BaseModel):
    id: int
    user_id: int
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    score: int
    total_questions: int = 5
    title: Optional[str] = None
    details_json: Optional[str] = None
    error_report: Optional[str] = None
    completed_at: datetime

    class Config:
        from_attributes = True

class QuizDraftBase(BaseModel):
    user_id: int
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    draft_json: str

class QuizDraftResponse(BaseModel):
    id: int
    user_id: int
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    draft_json: str
    updated_at: datetime
    video_title: Optional[str] = None

    class Config:
        from_attributes = True

class GradeRequest(BaseModel):
    user_id: int
    answers: List[str]
    document_id: Optional[int] = None

class GradeResponse(BaseModel):
    total_score: int
    details: List[dict]

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
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    consumed_points: int

class UploadRecordResponse(BaseModel):
    id: int
    user_id: int
    video_id: Optional[int] = None
    document_id: Optional[int] = None
    consumed_points: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserStatsResponse(BaseModel):
    video_count: int
    analyzed_video_count: int
    total_questions_count: int
    remaining_points: int
    completed_quizzes: int
    average_accuracy: float

class ErrorReportRequest(BaseModel):
    error_report: str

class GeminiHealthResponse(BaseModel):
    ok: bool
    model: str
    reply: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    user_id: Optional[int] = None
    video_id: Optional[int] = None

class ChatResponse(BaseModel):
    reply: str

class CodeExecutionRequest(BaseModel):
    code: str

class CodeExecutionResponse(BaseModel):
    output: str
    error: str


class SignInDay(BaseModel):
    day: int
    points: int
    checked: bool


class SignInStatusResponse(BaseModel):
    user_id: int
    points: int
    last_login_date: Optional[str] = None
    consecutive_login_days: int = 0
    cycle_day: int = 0
    signed_today: bool = False
    rewards: List[SignInDay] = []


class SignInResponse(BaseModel):
    user_id: int
    points_awarded: int
    points_total: int
    consecutive_login_days: int
    cycle_day: int
    last_login_date: Optional[str] = None
