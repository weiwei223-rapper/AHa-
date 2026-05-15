from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import re
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

try:
    from . import ai_analyzer, code_compiler, database, learning_pipeline, models, schema
except ImportError:
    import ai_analyzer
    import code_compiler
    import database
    import learning_pipeline
    import models
    import schema

# --- Helper Functions ---

def extract_youtube_title(url: str) -> str:
    try:
        if "youtube.com/watch?v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
            return f"YouTube Video - {video_id}"
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
            return f"YouTube Video - {video_id}"
        if "youtube.com/playlist?list=" in url:
            playlist_id = url.split("list=")[1].split("&")[0]
            return f"YouTube Playlist - {playlist_id}"
        return "YouTube Video"
    except Exception:
        return "YouTube Video"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


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

# --- Pydantic Models for ECPay & Local use ---

class EcpayCheckoutRequest(BaseModel):
    MerchantTradeNo: str
    MerchantTradeDate: str
    TotalAmount: int
    TradeDesc: str
    ItemName: str
    ReturnURL: str
    ClientBackURL: Optional[str] = None
    CustomField1: Optional[str] = None
    CustomField2: Optional[str] = None

class EcpayCheckoutResponse(BaseModel):
    CheckMacValue: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    user: schema.UserResponse
    message: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

# --- FastAPI Initialization ---

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
                    password=hash_password("password"),
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
    allow_origins=["*"], # Simplified for internal/dev use, adjust if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ECPay Config ---
ECPAY_MERCHANT_ID = "2000132"
ECPAY_HASH_KEY = "5294y06JbISpM5x9"
ECPAY_HASH_IV = "v77hoKGq4kWxNNIS"

def generate_ecpay_check_mac_value(params: Dict[str, Any]) -> str:
    filtered_params = {k: str(v) for k, v in params.items() if k != "CheckMacValue" and v is not None and str(v).strip() != ""}
    if "MerchantID" not in filtered_params: filtered_params["MerchantID"] = ECPAY_MERCHANT_ID
    sorted_keys = sorted(filtered_params.keys())
    raw_list = [f"{k}={filtered_params[k]}" for k in sorted_keys]
    raw_str = f"HashKey={ECPAY_HASH_KEY}&{'&'.join(raw_list)}&HashIV={ECPAY_HASH_IV}"
    encoded_str = quote_plus(raw_str).lower().replace("%2d", "-").replace("%5f", "_").replace("%2e", ".").replace("%21", "!").replace("%2a", "*").replace("%28", "(").replace("%29", ")").replace("%7e", "~")
    import hashlib
    encrypt_type = params.get("EncryptType", 1)
    if str(encrypt_type) == "0": return hashlib.md5(encoded_str.encode("utf-8")).hexdigest().upper()
    return hashlib.sha256(encoded_str.encode("utf-8")).hexdigest().upper()

# --- Achievement Logic ---

def calculate_total_achievement_points(user: models.User, db: Session) -> int:
    video_count = db.query(models.Video).filter(models.Video.user_id == user.id, models.Video.outline != None).count()
    quiz_results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user.id).all()
    question_count = sum(r.total_questions for r in quiz_results) if quiz_results else 0
    total = 0
    for threshold in [1, 5, 10]:
        if video_count >= threshold: total += 200
    for threshold in [1, 5, 15, 30, 50, 100]:
        if question_count >= threshold: total += 30
    for threshold, pts in {1: 20, 7: 30, 30: 100, 60: 200, 100: 300}.items():
        if threshold == 7:
            if user.consecutive_login_days >= 7: total += pts
        elif user.total_login_days >= threshold: total += pts
    return total

@app.post("/api/users/claim-achievement-points", response_model=schema.UserResponse)
def claim_achievement_points(payload: dict, db: Session = Depends(database.get_db)):
    user_id = payload.get("user_id")
    if not user_id: raise HTTPException(status_code=400, detail="Missing user_id")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    
    total_unlocked = calculate_total_achievement_points(user, db)
    already_claimed = user.claimed_achievement_points or 0
    if total_unlocked <= already_claimed: raise HTTPException(status_code=400, detail="目前沒有新的成就獎勵可以領取。")
    
    claimable = total_unlocked - already_claimed
    user.points += claimable
    user.claimed_achievement_points = total_unlocked
    
    record = models.RechargeRecord(
        user_id=user.id,
        date=datetime.now().strftime("%Y/%m/%d"),
        order_id=f"CLAIM{datetime.now():%Y%m%d%H%M%S}",
        amount=0,
        points=claimable,
        balance_after=user.points,
        plan_content="成就獎勵領取",
        payment_method="Achievement",
    )
    db.add(record)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# --- Routes ---

@app.get("/")
def read_root(): return {"message": "AHa AI API Server is running", "status": "ok"}

@app.get("/api/health/gemini", response_model=schema.GeminiHealthResponse)
def gemini_health_check():
    try: return schema.GeminiHealthResponse(**ai_analyzer.test_gemini_connection())
    except Exception as exc: raise HTTPException(status_code=503, detail=f"Gemini connection failed: {exc}")

@app.post("/auth/register", response_model=schema.UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first(): raise HTTPException(status_code=400, detail="Email exists")
    new_user = models.User(name=payload.name, email=payload.email, password=hash_password(payload.password), uid=f"UID-{datetime.now():%Y%m%d%H%M}", points=0)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password): raise HTTPException(status_code=401, detail="Invalid email/password")
    today = datetime.now().date().isoformat()
    if user.last_login_date != today:
        if user.last_login_date == (datetime.now().date() - timedelta(days=1)).isoformat(): user.consecutive_login_days += 1
        else: user.consecutive_login_days = 1
        user.total_login_days += 1
        user.last_login_date = today
        db.commit()
    return {"user": user, "message": f"Welcome back, {user.name}"}

@app.post("/api/chat", response_model=schema.ChatResponse)
def chat_with_ai(payload: schema.ChatRequest, db: Session = Depends(database.get_db)):
    user_message = payload.message.strip()
    if not user_message: raise HTTPException(status_code=400, detail="Message empty")

    system_content = "你是一個專業的 AI 學習助理。"
    if payload.video_id:
        video = db.query(models.Video).filter(models.Video.id == payload.video_id).first()
        if video:
            system_content += f"\n討論影片：{video.title}\n大綱：\n{video.outline or ''}\n逐字稿片段：\n{(video.transcript or '')[:5000]}"
            
    history = [{"role": "system", "content": system_content}]
    for item in payload.history: history.append({"role": item.role, "content": item.content})
    if not payload.history or payload.history[-1].content != user_message: history.append({"role": "user", "content": user_message})
    try: return schema.ChatResponse(reply=ai_analyzer.get_chat_response(history))
    except Exception: return schema.ChatResponse(reply="AI 服務暫時無法連線。")

@app.post("/api/execute-code", response_model=schema.CodeExecutionResponse)
def execute_code(payload: schema.CodeExecutionRequest):
    out, err = code_compiler.execute_python_code(payload.code, timeout=10, enable_security_check=True)
    return schema.CodeExecutionResponse(output=out, error=err)

@app.get("/users/{user_id}", response_model=schema.UserResponse)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=schema.UserResponse)
def update_user(user_id: int, payload: schema.UserUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user.name = payload.name; user.email = payload.email
    if payload.password: user.password = hash_password(payload.password)
    if payload.current_quiz_draft is not None: user.current_quiz_draft = payload.current_quiz_draft
    db.commit(); db.refresh(user)
    return user

@app.get("/users/{user_id}/recharge-records", response_model=List[schema.RechargeRecordResponse])
def read_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.RechargeRecord).filter(models.RechargeRecord.user_id == user_id).order_by(models.RechargeRecord.id.desc()).all()

@app.post("/users/{user_id}/recharge", response_model=schema.RechargeRecordResponse)
def recharge_user(user_id: int, payload: schema.RechargeRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    pts = payload.points or (300 if payload.price == 299 else (650 if payload.price == 599 else (1100 if payload.price == 999 else payload.price)))
    user.points += pts
    record = models.RechargeRecord(user_id=user.id, date=datetime.now().strftime("%Y/%m/%d"), order_id=f"A{datetime.now():%Y%m%d%H%M%S}", amount=payload.price, points=pts, balance_after=user.points, plan_content=payload.plan_content, payment_method=payload.payment_method, plan_id=payload.plan_id)
    db.add(record); db.add(user); db.commit(); db.refresh(record)
    return record

@app.get("/api/videos", response_model=List[schema.VideoResponse])
def get_videos(user_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    q = db.query(models.Video)
    if user_id: q = q.filter(models.Video.user_id == user_id)
    return q.order_by(models.Video.id.desc()).all()

@app.get("/api/videos/{video_id}/analysis", response_model=schema.VideoAnalysisResponse)
def analyze_video(video_id: int, user_id: int = 1, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    try:
        analysis = learning_pipeline.analyze_video(video.id, video.title or "Video", video.video_link)
        pts = math.ceil(((analysis.token_usage.total_tokens if analysis.token_usage else 0) / 2000) * 100 / 10) * 10
        user.points -= pts
        db.add(models.UploadRecord(user_id=user.id, video_id=video.id, consumed_points=pts))
        if analysis.outline_markdown: video.outline = analysis.outline_markdown
        db.commit(); db.refresh(video)
        return analysis
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/videos", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, db: Session = Depends(database.get_db)):
    title = ai_analyzer.get_video_title(payload.video_link) or "Untitled"
    if not ai_analyzer.is_python_related(title, ai_analyzer.fetch_video_transcript(payload.video_link)[:1500]):
        raise HTTPException(status_code=400, detail="僅支援 Python 相關影片")
    video = models.Video(video_link=payload.video_link, title=payload.title or title, user_id=payload.user_id, cost_points=payload.cost_points or 0)
    db.add(video); db.commit(); db.refresh(video)
    return video

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="Not found")
    db.delete(video); db.commit(); return {"message": "Deleted"}

@app.post("/api/videos/{video_id}/report-error")
def report_video_error(video_id: int, payload: schema.ErrorReportRequest, db: Session = Depends(database.get_db)):
    v = db.query(models.Video).filter(models.Video.id == video_id).first()
    v.error_report = f"{v.error_report}\n---\n{payload.error_report}" if v.error_report else payload.error_report
    db.commit(); return {"message": "Saved"}

@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz_api(video_id: int, user_id: int = 1, count: int = Query(5, ge=1, le=10), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user.points < count * 50: raise HTTPException(status_code=403, detail="點數不足")
    try:
        res = learning_pipeline.generate_quiz(video.id, video.title or "Video", video.video_link, count=count)
        user.points -= len(res.questions) * 50
        for item in res.questions:
            q = models.QuizQuestion(user_id=user_id, video_id=video.id, question_content=item.question, reference_answer=item.correct_answer, starter_code=item.starter_code, test_cases_json=json.dumps(item.test_cases), explanation=item.explanation, reference_concept=item.reference_concept)
            db.add(q); db.flush()
            db.add(models.GenerationRecord(user_id=user.id, quiz_question_id=q.id, consumed_points=50))
        db.commit(); return res
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quizzes/{video_id}/grade", response_model=schema.GradeResponse)
def grade_quiz(video_id: int, payload: schema.GradeRequest, db: Session = Depends(database.get_db)):
    answer_count = len(payload.answers)
    q_list = db.query(models.QuizQuestion).filter(models.QuizQuestion.user_id == payload.user_id)
    if video_id > 0: q_list = q_list.filter(models.QuizQuestion.video_id == video_id)
    elif payload.document_id: q_list = q_list.filter(models.QuizQuestion.document_id == payload.document_id)
    questions = q_list.order_by(models.QuizQuestion.id.desc()).limit(answer_count).all()
    questions.reverse()
    if not questions: raise HTTPException(status_code=404, detail="No questions found")
    details = []; correct = 0
    for idx, q in enumerate(questions):
        user_code = payload.answers[idx]; test_cases = json.loads(q.test_cases_json or "[]")
        passed = True; q_res = []
        for tc in test_cases:
            ref_out, _ = code_compiler.execute_python_code(f"{q.starter_code.replace('___', q.reference_answer)}\n{tc}")
            user_out, _ = code_compiler.execute_python_code(f"{user_code}\n{tc}")
            match = ref_out.strip() == user_out.strip()
            if not match: passed = False
            q_res.append({"test_case": tc, "passed": match, "expected": ref_out.strip(), "actual": user_out.strip()})
        if passed: correct += 1
        details.append({"question_id": q.id, "passed": passed, "test_results": q_res})
    return schema.GradeResponse(total_score=round(correct/len(questions)*100), details=details)

@app.post("/api/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, db: Session = Depends(database.get_db)):
    res = models.QuizResult(user_id=payload.user_id, video_id=payload.video_id, document_id=payload.document_id, score=payload.score, total_questions=payload.total_questions, title=payload.title, details_json=payload.details_json)
    db.add(res); db.commit(); db.refresh(res); return res

@app.get("/api/quiz-results", response_model=List[schema.QuizResultResponse])
def get_quiz_results(user_id: int = 1, db: Session = Depends(database.get_db)):
    return db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).order_by(models.QuizResult.completed_at.desc()).all()

@app.get("/api/quiz-drafts", response_model=List[schema.QuizDraftResponse])
def get_all_drafts(user_id: int = 1, db: Session = Depends(database.get_db)):
    drafts = db.query(models.QuizDraft).filter(models.QuizDraft.user_id == user_id).all()
    for d in drafts: d.video_title = d.video.title if d.video else (d.document.title if d.document else "Unknown")
    return drafts

@app.post("/api/quiz-drafts", response_model=schema.QuizDraftResponse)
def upsert_quiz_draft(payload: schema.QuizDraftBase, db: Session = Depends(database.get_db)):
    q = db.query(models.QuizDraft).filter(models.QuizDraft.user_id == payload.user_id)
    if payload.video_id: q = q.filter(models.QuizDraft.video_id == payload.video_id)
    elif payload.document_id: q = q.filter(models.QuizDraft.document_id == payload.document_id)
    draft = q.first()
    if draft: draft.draft_json = payload.draft_json; draft.updated_at = datetime.now()
    else:
        draft = models.QuizDraft(user_id=payload.user_id, video_id=payload.video_id, document_id=payload.document_id, draft_json=payload.draft_json)
        db.add(draft)
    db.commit(); db.refresh(draft); return draft

@app.delete("/api/quiz-drafts/{id}")
def delete_quiz_draft(id: int, user_id: int = Query(...), db: Session = Depends(database.get_db)):
    db.query(models.QuizDraft).filter(models.QuizDraft.user_id == user_id, or_(models.QuizDraft.video_id == id, models.QuizDraft.document_id == id)).delete()
    db.commit(); return {"message": "Deleted"}

@app.post("/api/documents", response_model=schema.DocumentResponse)
async def upload_document(file: UploadFile = File(...), user_id: int = Form(...), db: Session = Depends(database.get_db)):
    if not file.filename.lower().endswith(".pdf"): raise HTTPException(status_code=400, detail="PDF only")
    try:
        content = await file.read(); text_content = ""
        if fitz:
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page in doc: text_content += page.get_text()
        else: raise ValueError("No PDF parser")
        if not text_content.strip(): raise ValueError("Empty PDF")
        doc_model = models.Document(filename=file.filename, title=file.filename.rsplit(".", 1)[0], content_text=text_content, user_id=user_id)
        db.add(doc_model); db.commit(); db.refresh(doc_model); return doc_model
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=List[schema.DocumentResponse])
def get_documents(user_id: int = 1, db: Session = Depends(database.get_db)):
    return db.query(models.Document).filter(models.Document.user_id == user_id).all()

@app.get("/api/documents/{doc_id}/quiz", response_model=schema.QuizResponse)
def generate_doc_quiz(doc_id: int, user_id: int = 1, count: int = Query(5), db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    res = learning_pipeline.generate_quiz_from_document(doc.id, doc.title, doc.content_text, count=count)
    user.points -= len(res.questions) * 50
    for item in res.questions:
        db.add(models.QuizQuestion(user_id=user_id, document_id=doc.id, question_content=item.question, reference_answer=item.correct_answer, starter_code=item.starter_code, test_cases_json=json.dumps(item.test_cases), explanation=item.explanation))
    db.commit(); return res

@app.get("/users/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, db: Session = Depends(database.get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    v_c = db.query(models.Video).filter(models.Video.user_id == user_id).count()
    d_c = db.query(models.Document).filter(models.Document.user_id == user_id).count()
    acc = round(sum(r.score for r in results)/len(results)) if results else 0
    return schema.UserStatsResponse(video_count=v_c + d_c, analyzed_video_count=0, total_questions_count=sum(r.total_questions for r in results), remaining_points=u.points, completed_quizzes=len(results), average_accuracy=acc)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
