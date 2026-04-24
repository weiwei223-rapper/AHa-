#!/usr/bin/env python3
"""
Migration script to move data from SQLite to PostgreSQL
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URLs
SQLITE_URL = "sqlite:///./aha_app.db"
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@104.199.238.198/postgres")

def migrate_data():
    # Import models after database setup
    try:
        from models import User, Video, QuizResult, RechargeRecord, Base
    except ImportError:
        import models
        User = models.User
        Video = models.Video
        QuizResult = models.QuizResult
        RechargeRecord = models.RechargeRecord
        Base = models.Base

    # Create engines
    sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    postgres_engine = create_engine(POSTGRES_URL)

    # Create PostgreSQL tables
    Base.metadata.create_all(bind=postgres_engine)

    # Create sessions
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()

    try:
        # Migrate Users
        print("Migrating users...")
        users = sqlite_session.query(User).all()
        for user in users:
            # Check if user already exists
            existing = postgres_session.query(User).filter(User.id == user.id).first()
            if not existing:
                postgres_session.add(User(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    password=user.password,
                    uid=user.uid,
                    points=user.points
                ))
        postgres_session.commit()
        print(f"Migrated {len(users)} users")

        # Migrate Videos
        print("Migrating videos...")
        videos = sqlite_session.query(Video).all()
        for video in videos:
            existing = postgres_session.query(Video).filter(Video.id == video.id).first()
            if not existing:
                postgres_session.add(Video(
                    id=video.id,
                    video_link=video.video_link,
                    title=video.title,
                    created_at=video.created_at
                ))
        postgres_session.commit()
        print(f"Migrated {len(videos)} videos")

        # Migrate Recharge Records
        print("Migrating recharge records...")
        records = sqlite_session.query(RechargeRecord).all()
        for record in records:
            existing = postgres_session.query(RechargeRecord).filter(RechargeRecord.id == record.id).first()
            if not existing:
                postgres_session.add(RechargeRecord(
                    id=record.id,
                    user_id=record.user_id,
                    date=record.date,
                    order_id=record.order_id,
                    amount=record.amount
                ))
        postgres_session.commit()
        print(f"Migrated {len(records)} recharge records")

        # Migrate Quiz Results
        print("Migrating quiz results...")
        results = sqlite_session.query(QuizResult).all()
        for result in results:
            existing = postgres_session.query(QuizResult).filter(QuizResult.id == result.id).first()
            if not existing:
                postgres_session.add(QuizResult(
                    id=result.id,
                    user_id=result.user_id,
                    video_id=result.video_id,
                    score=result.score,
                    total_questions=result.total_questions,
                    completed_at=result.completed_at
                ))
        postgres_session.commit()
        print(f"Migrated {len(results)} quiz results")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        postgres_session.rollback()
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    migrate_data()