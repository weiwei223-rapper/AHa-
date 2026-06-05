from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import os
import re
import sys
import html
import math
from urllib.parse import quote, quote_plus

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

load_dotenv()  # Load standard .env
load_dotenv("API_key.env")  # Load AI API key if in separate file

try:
    import fitz  # PyMuPDF
except ImportError:
    try:
        import pymupdf as fitz
    except ImportError:
        fitz = None

# Ensure backend root is in sys.path
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.append(backend_path)

import database
import models
import auth_schemas
import schema
import ai_analyzer
import code_compiler
from routers import auth, users, videos, documents, quizzes, payments, ai

load_dotenv()
load_dotenv("API_key.env")

def ensure_database_columns() -> None:
    schema_updates = [
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS transcript TEXT",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS transcript_source VARCHAR",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS transcript_updated_at TIMESTAMP",
        "ALTER TABLE ai_feedbacks ADD COLUMN IF NOT EXISTS video_id INTEGER",
        "ALTER TABLE ai_feedbacks ADD COLUMN IF NOT EXISTS document_id INTEGER",
        "ALTER TABLE recharge_records ADD COLUMN IF NOT EXISTS balance_after INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_quiz_draft TEXT",
        "ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS document_id INTEGER",
        "ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS document_id INTEGER",
        "ALTER TABLE quiz_drafts ADD COLUMN IF NOT EXISTS document_id INTEGER",
        "ALTER TABLE upload_records ADD COLUMN IF NOT EXISTS document_id INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS claimed_achievement_points INTEGER DEFAULT 0",
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS error_report VARCHAR",
        "ALTER TABLE quiz_results ADD COLUMN IF NOT EXISTS error_report VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_report VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_checkin_date VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS consecutive_login_days INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_login_days INTEGER DEFAULT 0",
    ]
    with database.engine.begin() as connection:
        for update in schema_updates:
            try:
                connection.execute(text(update))
            except Exception as e:
                print(f"Update failed: {update}, error: {e}")
        
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role INTEGER DEFAULT 1"))
        connection.execute(text("UPDATE users SET role = 1 WHERE role IS NULL"))
        connection.execute(text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 1"))
        connection.execute(text("ALTER TABLE users ALTER COLUMN role SET NOT NULL"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        models.Base.metadata.create_all(bind=database.engine)
        ensure_database_columns()
        db = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.id == 1).first()
            if user is None:
                user = models.User(
                    id=1,
                    name="wei",
                    email="wei@gmail.com",
                    password=auth_schemas.hash_password("password"),
                    uid="UID-20260419",
                    points=10000,
                )
                db.add(user)
                db.flush()
                
                record = models.RechargeRecord(
                    user_id=1,
                    date=datetime.now().strftime("%Y/%m/%d"),
                    order_id="INITIAL_POINTS",
                    amount=0,
                    points=10000,
                    balance_after=10000,
                    plan_content="Initial Welcome Points",
                    payment_method="System",
                )
                db.add(record)
                db.commit()
        finally:
            db.close()
    except Exception as exc:
        print(f"Error during startup: {exc}")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(videos.router)
app.include_router(documents.router)
app.include_router(quizzes.router)
app.include_router(payments.router)
app.include_router(ai.router)

@app.get("/")
def read_root(): 
    return {"message": "AHa AI API Server is running", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
