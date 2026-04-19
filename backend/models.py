from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    recognized: Mapped[bool] = mapped_column(Boolean, default=False)
    outline: Mapped[bool] = mapped_column(Boolean, default=False)
    pts: Mapped[str] = mapped_column(String(20), default="-50")
    date: Mapped[str] = mapped_column(String(32))


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(255), default="")
    questions: Mapped[list] = mapped_column(JSON)
    last_rate: Mapped[str] = mapped_column(String(32), default="—")
    rate_color: Mapped[str] = mapped_column(String(32), default="#7a90a8")
    done: Mapped[bool] = mapped_column(Boolean, default=False)