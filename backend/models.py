from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

try:
    from .database import Base
except ImportError:
    from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password = Column(String)
    uid = Column(String, unique=True, index=True)
    points = Column(Integer, default=0)
    role = Column(Integer, default=1, nullable=False)
    last_login_date = Column(String, nullable=True)
    last_checkin_date = Column(String, nullable=True)
    consecutive_login_days = Column(Integer, default=0)
    total_login_days = Column(Integer, default=0)
    claimed_achievement_points = Column(Integer, default=0)
    current_quiz_draft = Column(Text, nullable=True)

    videos = relationship("Video", back_populates="uploader", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    recharge_records = relationship("RechargeRecord", back_populates="user", cascade="all, delete-orphan")
    ai_feedbacks = relationship("AIFeedback", back_populates="user", cascade="all, delete-orphan")
    quiz_questions = relationship("QuizQuestion", back_populates="user", cascade="all, delete-orphan")
    quiz_results = relationship("QuizResult", back_populates="user", cascade="all, delete-orphan")
    generation_records = relationship("GenerationRecord", back_populates="user", cascade="all, delete-orphan")
    upload_records = relationship("UploadRecord", back_populates="user", cascade="all, delete-orphan")
    quiz_drafts = relationship("QuizDraft", back_populates="user", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    video_link = Column(String, nullable=False)
    title = Column(String, nullable=True)
    outline = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    transcript_source = Column(String, nullable=True)
    transcript_updated_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cost_points = Column(Integer, default=0)
    error_report = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    uploader = relationship("User", back_populates="videos")
    quiz_questions = relationship("QuizQuestion", back_populates="video", cascade="all, delete-orphan")
    quiz_results = relationship("QuizResult", back_populates="video", cascade="all, delete-orphan")
    upload_records = relationship("UploadRecord", back_populates="video", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content_text = Column(Text, nullable=True)
    outline = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_report = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    uploader = relationship("User", back_populates="documents")
    quiz_questions = relationship("QuizQuestion", back_populates="document", cascade="all, delete-orphan")
    quiz_results = relationship("QuizResult", back_populates="document", cascade="all, delete-orphan")
    upload_records = relationship("UploadRecord", back_populates="document", cascade="all, delete-orphan")


class AIFeedback(Base):
    __tablename__ = "ai_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    ai_message = Column(String)
    user_message = Column(String)
    error_report = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="ai_feedbacks")


class RechargeRecord(Base):
    __tablename__ = "recharge_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)
    order_id = Column(String, unique=True, index=True)
    amount = Column(Integer)
    points = Column(Integer, default=0)
    balance_after = Column(Integer, nullable=True)
    plan_content = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    plan_id = Column(String, nullable=True)

    user = relationship("User", back_populates="recharge_records")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    question_content = Column(String)
    reference_answer = Column(String)
    answer_record = Column(String, nullable=True)
    accuracy = Column(Integer, default=0)
    options_json = Column(String, nullable=True)
    
    starter_code = Column(String, nullable=True)
    test_cases_json = Column(String, nullable=True)
    explanation = Column(String, nullable=True)
    reference_concept = Column(String, nullable=True)
    source_time = Column(String, nullable=True)
    source_excerpt = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="quiz_questions")
    video = relationship("Video", back_populates="quiz_questions")
    document = relationship("Document", back_populates="quiz_questions")
    generation_records = relationship("GenerationRecord", back_populates="quiz_question", cascade="all, delete-orphan")


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_question_id = Column(Integer, ForeignKey("quiz_questions.id"))
    consumed_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="generation_records")
    quiz_question = relationship("QuizQuestion", back_populates="generation_records")


class UploadRecord(Base):
    __tablename__ = "upload_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    consumed_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="upload_records")
    video = relationship("Video", back_populates="upload_records")
    document = relationship("Document", back_populates="upload_records")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    title = Column(String, nullable=True)
    score = Column(Integer)
    total_questions = Column(Integer, default=5)
    details_json = Column(String, nullable=True)
    error_report = Column(String, nullable=True)
    completed_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="quiz_results")
    video = relationship("Video", back_populates="quiz_results")
    document = relationship("Document", back_populates="quiz_results")


class QuizDraft(Base):
    __tablename__ = "quiz_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    draft_json = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="quiz_drafts")
    video = relationship("Video")
    document = relationship("Document")
