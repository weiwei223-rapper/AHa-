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

# --- Pydantic Models for ECPay ---

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
    MerchantTradeNo: str
    MerchantTradeDate: str

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

# --- ECPay Routes ---

class EcpayCheckoutResponse(BaseModel):
    CheckMacValue: str
    MerchantTradeNo: str
    MerchantTradeDate: str

@app.post("/api/ecpay/checkout", response_model=EcpayCheckoutResponse)
def ecpay_checkout(payload: Dict[str, Any], db: Session = Depends(database.get_db)):
    """產生綠界支付所需的 CheckMacValue 與訂單資訊"""
    import time
    merchant_trade_no = f"AHA{int(time.time())}"
    merchant_trade_date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    
    ecpay_params = {
        "MerchantID": ECPAY_MERCHANT_ID,
        "MerchantTradeNo": merchant_trade_no,
        "MerchantTradeDate": merchant_trade_date,
        "PaymentType": "aio",
        "TotalAmount": payload.get("TotalAmount"),
        "TradeDesc": "AHa AI 點數儲值",
        "ItemName": payload.get("ItemName"),
        "ReturnURL": payload.get("ReturnURL"),
        "ClientBackURL": payload.get("ClientBackURL"),
        "ChoosePayment": "ALL",
        "EncryptType": 1,
        "CustomField1": str(payload.get("user_id")),
        "CustomField2": payload.get("plan_id"),
    }
    
    mac = generate_ecpay_check_mac_value(ecpay_params)
    return EcpayCheckoutResponse(
        CheckMacValue=mac,
        MerchantTradeNo=merchant_trade_no,
        MerchantTradeDate=merchant_trade_date
    )

@app.post("/ecpay/return")
async def ecpay_return(request: Request, db: Session = Depends(database.get_db)):
    # ... existing background webhook logic ...
    return await process_ecpay_payment(request, db)

@app.post("/ecpay/return-client")
async def ecpay_return_client(request: Request, db: Session = Depends(database.get_db)):
    """接收綠界付款結果通知 (前端跳轉用，縮短入帳時間)"""
    await process_ecpay_payment(request, db)
    # 付款完後引導使用者回個人頁面
    from fastapi.responses import RedirectResponse
    return HTMLResponse(content="""
        <html>
            <head><title>付款成功</title></head>
            <body style="background:#080c16;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1 style="color:#2bc1f1;">付款完成！</h1>
                    <p>正在為您同步點數，請稍候...</p>
                    <script>
                        setTimeout(() => { window.location.href = '/profile'; }, 2000);
                    </script>
                </div>
            </body>
        </html>
    """)

async def process_ecpay_payment(request: Request, db: Session):
    form_data = await request.form()
    params = dict(form_data)
    
    received_mac = params.get("CheckMacValue")
    calculated_mac = generate_ecpay_check_mac_value(params)
    
    if received_mac != calculated_mac:
        return PlainTextResponse("0|CheckMacValueVerifyFail")
    
    if params.get("RtnCode") == "1":
        try:
            user_id = int(params.get("CustomField1"))
            amount = int(params.get("TradeAmt", 0))
            merchant_trade_no = params.get("MerchantTradeNo")
            
            # Check if record already exists to prevent double entry
            existing = db.query(models.RechargeRecord).filter(models.RechargeRecord.order_id == merchant_trade_no).first()
            if existing: return PlainTextResponse("1|OK")

            if amount >= 999: points_to_add = 1100
            elif amount >= 599: points_to_add = 650
            elif amount >= 299: points_to_add = 300
            else: points_to_add = amount
            
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user.points += points_to_add
                record = models.RechargeRecord(
                    user_id=user.id,
                    date=datetime.now().strftime("%Y/%m/%d"),
                    order_id=merchant_trade_no,
                    amount=amount,
                    points=points_to_add,
                    balance_after=user.points,
                    plan_content=f"綠界儲值: {params.get('ItemName')}",
                    payment_method="ECPay",
                    plan_id=params.get("CustomField2")
                )
                db.add(record)
                db.commit()
                return PlainTextResponse("1|OK")
        except Exception:
            db.rollback()
    return PlainTextResponse("0|Fail")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:5173", "http://localhost:5174",
        "http://localhost:5175", "http://localhost:5176", "http://localhost:5177",
        "http://localhost:5178", "http://127.0.0.1:5173", "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ECPay Config ---
ECPAY_MERCHANT_ID = "2000132"
ECPAY_HASH_KEY = "5294y06JbISpM5x9"
ECPAY_HASH_IV = "v77hoKGq4kWxNNIS"

def generate_ecpay_check_mac_value(params: Dict[str, Any]) -> str:
    # 1. 過濾掉 CheckMacValue (綠界規則：此欄位不參與加密)
    # 注意：綠界回傳的空字串 (例如 CustomField3="") 必須保留並參與加密
    filtered_params = {k: str(v) for k, v in params.items() if k.lower() != "checkmacvalue"}
    
    if "MerchantID" not in filtered_params: filtered_params["MerchantID"] = ECPAY_MERCHANT_ID
    
    # 2. 排序
    sorted_keys = sorted(filtered_params.keys())
    raw_list = [f"{k}={filtered_params[k]}" for k in sorted_keys]
    
    # 3. 組合原始字串
    raw_str = f"HashKey={ECPAY_HASH_KEY}&{'&'.join(raw_list)}&HashIV={ECPAY_HASH_IV}"
    
    # 4. URL Encode 並轉小寫，僅處理 ~ 符號 (根據 verify_mac.py 的成功經驗)
    encoded_str = quote_plus(raw_str).lower().replace("%7e", "~")
    
    # 5. 生成雜湊值
    import hashlib
    encrypt_type = params.get("EncryptType", 1)
    if str(encrypt_type) == "0":
        mac = hashlib.md5(encoded_str.encode("utf-8")).hexdigest().upper()
    else:
        mac = hashlib.sha256(encoded_str.encode("utf-8")).hexdigest().upper()
    
    # Debug 用：在伺服器日誌顯示原始字串（正式上線後可移除）
    print(f"DEBUG: MAC Raw String: {raw_str}")
    print(f"DEBUG: MAC Encoded: {encoded_str}")
    
    return mac

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

@app.post("/users/{user_id}/claim-achievement-points", response_model=schema.UserResponse)
def claim_achievement_points(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    total_unlocked = calculate_total_achievement_points(user, db)
    already_claimed = user.claimed_achievement_points or 0
    if total_unlocked <= already_claimed: raise HTTPException(status_code=400, detail="目前沒有新的成就獎勵可以領取。")
    user.points += (total_unlocked - already_claimed)
    user.claimed_achievement_points = total_unlocked
    db.commit(); db.refresh(user)
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
    system_content = """你是 AHa!! 的 AI 程式家教，專門輔導 Python 程式初學者。
        你的教學風格遵循「鷹架理論」與「蘇格拉底式引導」：
        - 【絕對禁止】直接給出任何程式碼片段
        - 【絕對禁止】出現任何簡體中文
        - 【必須】先分析使用者的思路或錯誤，再提供邏輯提示或類比
        - 【必須】以繁體中文回答，語氣親切、鼓勵
        - 若使用者請求給出完整程式碼，請婉拒並解釋這樣做不利於學習，並提供引導提示幫助他們自己找到答案。
        - 當使用者多次答錯時，提供更具體的語法提示或類比範例
        - 當使用者快答對時，引導其思考更佳的時間複雜度或寫法"""
    
    if payload.video_id:
        video = db.query(models.Video).filter(models.Video.id == payload.video_id).first()
        if video: system_content += f"\n\n目前討論影片標題：{video.title}"
    history = [{"role": "system", "content": system_content}]
    for item in payload.history: history.append({"role": item.role, "content": item.content})
    if not payload.history or payload.history[-1].content != payload.message: history.append({"role": "user", "content": payload.message})
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

@app.get("/users/{user_id}/recharge-records")
def get_user_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    records = db.query(models.RechargeRecord).filter(models.RechargeRecord.user_id == user_id).order_by(models.RechargeRecord.id.desc()).all()
    return records

@app.put("/users/{user_id}", response_model=schema.UserResponse)
def update_user(user_id: int, payload: schema.UserUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user.name = payload.name; user.email = payload.email
    if payload.password: user.password = hash_password(payload.password)
    if payload.current_quiz_draft is not None: user.current_quiz_draft = payload.current_quiz_draft
    db.commit(); db.refresh(user)
    return user

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
    video = models.Video(video_link=payload.video_link, title=payload.title or title, user_id=payload.user_id)
    db.add(video); db.commit(); db.refresh(video)
    return video

@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz_api(video_id: int, user_id: int = 1, count: int = Query(5, ge=1, le=10), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    try:
        res = learning_pipeline.generate_quiz(video.id, video.title or "Video", video.video_link, count=count)
        user.points -= len(res.questions) * 50
        for item in res.questions:
            q = models.QuizQuestion(user_id=user_id, video_id=video.id, question_content=item.question, reference_answer=item.correct_answer, starter_code=item.starter_code, test_cases_json=json.dumps(item.test_cases), explanation=item.explanation)
            db.add(q); db.flush()
            db.add(models.GenerationRecord(user_id=user.id, quiz_question_id=q.id, consumed_points=50))
        db.commit(); return res
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quizzes/{video_id}/grade", response_model=schema.GradeResponse)
def grade_quiz(video_id: int, payload: schema.GradeRequest, db: Session = Depends(database.get_db)):
    answer_count = len(payload.answers)
    q_list = db.query(models.QuizQuestion).filter(models.QuizQuestion.user_id == payload.user_id)
    if video_id > 0: q_list = q_list.filter(models.QuizQuestion.video_id == video_id)
    elif payload.document_id: q_list = q_list.filter(models.QuizQuestion.document_id == payload.document_id)
    questions = q_list.order_by(models.QuizQuestion.id.desc()).limit(answer_count).all()
    questions.reverse()
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
    return schema.GradeResponse(total_score=round(correct/len(questions)*100) if questions else 0, details=details)

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

@app.delete("/api/quiz-drafts/{video_id}")
def delete_quiz_draft(video_id: int, user_id: int = Query(...), db: Session = Depends(database.get_db)):
    db.query(models.QuizDraft).filter(models.QuizDraft.user_id == user_id, or_(models.QuizDraft.video_id == video_id, models.QuizDraft.document_id == video_id)).delete()
    db.commit(); return {"message": "Deleted"}

@app.post("/api/documents", response_model=schema.DocumentResponse)
async def upload_document(file: UploadFile = File(...), user_id: int = Form(...), db: Session = Depends(database.get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅支援 PDF 檔案格式")
    try:
        content = await file.read()
        text_content = ""
        if fitz:
            try:
                with fitz.open(stream=content, filetype="pdf") as doc:
                    for page in doc:
                        text_content += page.get_text()
            except Exception as fe:
                raise ValueError(f"PDF 解析失敗: {str(fe)}")
        else:
            raise ValueError("伺服器尚未安裝 PDF 解析組件 (PyMuPDF)")
            
        if not text_content.strip():
            raise ValueError("無法從此 PDF 中提取文字內容。請確認該 PDF 並非純圖片掃描檔，或是具備可搜尋文字。")

        doc_model = models.Document(
            filename=file.filename,
            title=file.filename.rsplit(".", 1)[0],
            content_text=text_content,
            user_id=user_id
        )
        db.add(doc_model)
        db.commit()
        db.refresh(doc_model)
        return doc_model
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/api/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, db: Session = Depends(database.get_db)):
    res = models.QuizResult(user_id=payload.user_id, video_id=payload.video_id, document_id=payload.document_id, score=payload.score, total_questions=payload.total_questions, title=payload.title, details_json=payload.details_json)
    db.add(res); db.commit(); db.refresh(res); return res

@app.get("/api/quiz-results", response_model=List[schema.QuizResultResponse])
def get_quiz_results(user_id: int = 1, db: Session = Depends(database.get_db)):
    return db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).order_by(models.QuizResult.completed_at.desc()).all()

@app.get("/api/documents/{doc_id}/analysis", response_model=schema.VideoAnalysisResponse)
def analyze_document(doc_id: int, user_id: int = 1, db: Session = Depends(database.get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    try:
        # 使用現有的 generate_outline 邏輯
        outline, usage = learning_pipeline.generate_outline(doc.content_text, doc.title)
        pts = math.ceil(((usage.get("totalTokenCount", 0)) / 2000) * 100 / 10) * 10
        user.points -= pts
        db.add(models.UploadRecord(user_id=user.id, document_id=doc.id, consumed_points=pts))
        doc.outline = outline
        db.commit(); db.refresh(doc)
        return schema.VideoAnalysisResponse(
            video_id=doc.id, video_title=doc.title, transcript_source="pdf_extract",
            transcript_excerpt=doc.content_text[:1000], outline_markdown=outline,
            key_topics=learning_pipeline._parse_bullets(outline), retrieved_chunks=[],
            vector_backend="none", generated_at=datetime.utcnow(),
            token_usage=learning_pipeline._to_token_usage_schema(usage)
        )
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, db: Session = Depends(database.get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    v_c = db.query(models.Video).filter(models.Video.user_id == user_id).count()
    d_c = db.query(models.Document).filter(models.Document.user_id == user_id).count()
    
    # 統計已分析的資源 (影片或文件)
    v_ana = db.query(models.Video).filter(models.Video.user_id == user_id, models.Video.outline != None).count()
    d_ana = db.query(models.Document).filter(models.Document.user_id == user_id, models.Document.outline != None).count()
    
    return schema.UserStatsResponse(
        video_count=v_c + d_c, 
        analyzed_video_count=v_ana + d_ana, 
        total_questions_count=sum(r.total_questions for r in results), 
        remaining_points=u.points, 
        completed_quizzes=len(results), 
        average_accuracy=round(sum(r.score for r in results)/len(results)) if results else 0
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
