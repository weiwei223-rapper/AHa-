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
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

load_dotenv()  # Load standard .env
load_dotenv("API_key.env")  # Load AI API key if in separate file

try:
    from . import ai_analyzer, code_compiler, database, learning_pipeline, models, schema
except ImportError:
    import ai_analyzer
    import code_compiler
    import database
    import learning_pipeline
    import models
    import schema


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
        "ALTER TABLE recharge_records ADD COLUMN IF NOT EXISTS balance_after INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_quiz_draft TEXT",
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
                db.flush()  # To get the user ID if needed, though it's set to 1
                
                # Create initial recharge record
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ECPay Configuration ---
ECPAY_MERCHANT_ID = "2000132" # 測試特店編號
ECPAY_HASH_KEY = "5294y06JbISpM5x9"
ECPAY_HASH_IV = "v77hoKGq4kWxNNIS"


def generate_ecpay_check_mac_value(params: Dict[str, Any]) -> str:
    """
    產生綠界科技的 CheckMacValue。
    規則：
    1. 篩選：排除 CheckMacValue，且排除值為 None 或空字串的參數。
    2. 排序：依參數名稱的 ASCII 碼由小到大排序。
    3. 組合：前後加上 HashKey 和 HashIV。
    4. URL Encode：轉小寫，並進行特定的字元替換。
    5. 雜湊：根據 EncryptType 使用 SHA256 (1) 或 MD5 (0)。
    """
    # 1. 篩選並排序 (ECPay 規定空值不參加雜湊)
    filtered_params = {
        k: str(v) for k, v in params.items() 
        if k != "CheckMacValue" and v is not None and str(v).strip() != ""
    }
    
    # 如果 params 中沒有 MerchantID，則補上預設值
    if "MerchantID" not in filtered_params:
        filtered_params["MerchantID"] = ECPAY_MERCHANT_ID
        
    sorted_keys = sorted(filtered_params.keys())
    
    # 2. 組合字串
    raw_list = [f"{k}={filtered_params[k]}" for k in sorted_keys]
    raw_str = f"HashKey={ECPAY_HASH_KEY}&{'&'.join(raw_list)}&HashIV={ECPAY_HASH_IV}"
    
    # 3. URL Encode
    # 綠界要求的 URL Encode 規則：
    # - 使用 quote_plus (將空格轉為 +)
    # - 轉為小寫
    # - 取代特定的符號為原始字元
    encoded_str = quote_plus(raw_str).lower()
    encoded_str = (
        encoded_str.replace("%2d", "-")
        .replace("%5f", "_")
        .replace("%2e", ".")
        .replace("%21", "!")
        .replace("%2a", "*")
        .replace("%28", "(")
        .replace("%29", ")")
        .replace("%7e", "~")  # 補上 tilde
    )
    
    # 4. 雜湊
    import hashlib
    encrypt_type = params.get("EncryptType", 1)
    
    # 偵錯記錄 (可選)
    # print(f"DEBUG - Raw Str: {raw_str}")
    # print(f"DEBUG - Encoded Str: {encoded_str}")
    
    if str(encrypt_type) == "0":
        return hashlib.md5(encoded_str.encode("utf-8")).hexdigest().upper()
    return hashlib.sha256(encoded_str.encode("utf-8")).hexdigest().upper()
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

# --- Schemas ---

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    uid: str
    points: int
    last_login_date: Optional[str] = None
    consecutive_login_days: int = 0
    total_login_days: int = 0
    current_quiz_draft: Optional[str] = None # 新增此欄位以回傳草稿
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    current_quiz_draft: Optional[str] = None


class RechargeRequest(BaseModel):
    points: Optional[int] = None
    price: Optional[int] = 0
    plan_content: Optional[str] = None
    payment_method: Optional[str] = None
    plan_id: Optional[str] = None


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
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user: UserResponse
    message: str


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


class GeminiHealthResponse(BaseModel):
    ok: bool
    model: str
    reply: str


@app.get("/")
def read_root():
    return {"message": "AHa AI API Server is running", "status": "ok"}


@app.get("/api/health/gemini", response_model=GeminiHealthResponse)
def gemini_health_check():
    try:
        result = ai_analyzer.test_gemini_connection()
        return GeminiHealthResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Gemini connection failed: {exc}")


@app.post("/auth/register", response_model=UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    uid = f"UID-{datetime.now():%Y%m%d%H%M}"
    new_user = models.User(name=payload.name, email=payload.email, password=hash_password(payload.password), uid=uid,
                           points=0)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 更新登入元數據
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    
    if user.last_login_date == today:
        # 今天已經登入過，不更新
        pass
    else:
        consecutive_days = user.consecutive_login_days + 1 if user.last_login_date == yesterday else 1
        total_days = user.total_login_days + 1
        user.last_login_date = today
        user.consecutive_login_days = consecutive_days
        user.total_login_days = total_days
        db.commit()
    
    return {"user": user, "message": f"Welcome back, {user.name}"}


@app.post("/ecpay/create-checkmac", response_model=EcpayCheckoutResponse)
def create_ecpay_checkmac(payload: EcpayCheckoutRequest):
    params = payload.model_dump()
    return EcpayCheckoutResponse(CheckMacValue=generate_ecpay_check_mac_value(params))


@app.post("/ecpay/checkout", response_class=HTMLResponse)
async def checkout_ecpay(request: Request):
    form_data = await request.form()
    params = {key: form_data[key] for key in form_data}
    params["MerchantID"] = ECPAY_MERCHANT_ID
    params["CheckMacValue"] = generate_ecpay_check_mac_value(params)

    fields = []
    for key, value in params.items():
        escaped_value = html.escape(str(value), quote=True)
        fields.append(f'<input type="hidden" name="{html.escape(key)}" value="{escaped_value}" />')

    form_html = """
<html>
  <body>
    <form id="ecpayForm" method="post" action="https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5">
      {fields}
    </form>
    <script>document.getElementById('ecpayForm').submit();</script>
  </body>
</html>
""".replace("{fields}", "\n      ".join(fields))

    return HTMLResponse(content=form_html, status_code=200)


def calculate_points_from_amount(amount: int) -> int:
    """根據金額計算點數 (含優惠方案)"""
    if amount == 299:
        return 300
    elif amount == 599:
        return 650
    elif amount == 999:
        return 1100
    return amount


def get_plan_description(amount: int) -> str:
    """根據金額獲取方案描述"""
    if amount == 299:
        return "NT$ 299 方案 (300 點)"
    elif amount == 599:
        return "NT$ 599 方案 (650 點)"
    elif amount == 999:
        return "NT$ 999 方案 (1100 點)"
    return f"儲值 NT$ {amount}"


@app.post("/ecpay/return", response_class=PlainTextResponse)
async def ecpay_return(request: Request, db: Session = Depends(database.get_db)):
    form_data = await request.form()
    params = dict(form_data)
    print("收到綠界付款結果回傳：", params)
    
    # 驗證 CheckMacValue
    received_mac = params.get("CheckMacValue")
    calculated_mac = generate_ecpay_check_mac_value(params)
    
    if received_mac != calculated_mac:
        print("❌ CheckMacValue 驗證失敗！可能是偽造請求。")
        return PlainTextResponse(content="0|CheckMacValue Error", status_code=200)

    rtn_code = params.get("RtnCode")
    merchant_trade_no = params.get("MerchantTradeNo")
    total_amount = int(params.get("TotalAmount", 0))

    if rtn_code == "1":
        print(f"✅ 訂單 {merchant_trade_no} 付款成功！")
        if not merchant_trade_no:
            print("❌ MerchantTradeNo 缺失，無法處理充值。")
            return PlainTextResponse(content="1|OK", status_code=200)

        try:
            match = re.match(r"^AHA(\d+)(\d{10})$", merchant_trade_no)
            if not match:
                raise ValueError("MerchantTradeNo 格式不正確")

            user_id = int(match.group(1))
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                print(f"❌ 找不到使用者 ID={user_id}，無法記錄充值。")
                return PlainTextResponse(content="1|OK", status_code=200)

            # 已存在相同訂單號時不重複計入
            existing_record = (
                db.query(models.RechargeRecord)
                .filter(models.RechargeRecord.order_id == merchant_trade_no)
                .first()
            )
            if existing_record:
                print(f"ℹ️ 訂單 {merchant_trade_no} 已存在，跳過重複紀錄。")
                return PlainTextResponse(content="1|OK", status_code=200)

            points_to_add = calculate_points_from_amount(total_amount)

            user.points += points_to_add

            record = models.RechargeRecord(
                user_id=user.id,
                date=datetime.now().strftime("%Y/%m/%d"),
                order_id=merchant_trade_no,
                amount=total_amount,
                points=points_to_add,
                balance_after=user.points,
                plan_content=get_plan_description(total_amount),
                payment_method=params.get("PaymentType", "ECPay"),
            )
            db.add(user)
            db.add(record)
            db.commit()
            print(f"💰 已為使用者 {user.name} (ID: {user.id}) 增加 {points_to_add} 點數。")
        except Exception as e:
            db.rollback()
            print(f"❌ 解析訂單編號或更新點數失敗: {e}")
    else:
        print(f"❌ 訂單 {merchant_trade_no} 付款失敗，RtnCode={rtn_code}")

    return PlainTextResponse(content="1|OK", status_code=200)


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest, db: Session = Depends(database.get_db)):
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    system_content = "你是一個專業的 AI 學習助理，負責協助使用者理解影片內容、解答疑問並提供延伸學習建議。"
    
    if payload.video_id:
        video = db.query(models.Video).filter(models.Video.id == payload.video_id).first()
        if video:
            video_context = f"目前討論的影片標題是「{video.title}」。\n"
            if video.outline:
                video_context += f"影片大綱：\n{video.outline}\n"
            if video.transcript:
                # 限制逐字稿長度以避免超出 Token 限制，優先取前 8000 字
                video_context += f"影片逐字稿內容：\n{video.transcript[:8000]}\n"
            
            system_content += f"\n\n{video_context}\n請務必根據以上提供的影片資訊來回答使用者的問題。如果問題與影片無關，請先嘗試從影片角度切入，或禮貌地提醒使用者該對話是圍繞著此影片展開的。"

    history_payload = []
    # 加入系統指令
    history_payload.append({"role": "system", "content": system_content})
    
    # 加入歷史對話
    for item in payload.history:
        history_payload.append({"role": item.role, "content": item.content})
    
    # 加入最新訊息（如果 history 最後一筆不是最新訊息）
    if not payload.history or payload.history[-1].content != user_message:
        history_payload.append({"role": "user", "content": user_message})

    try:
        reply = ai_analyzer.get_chat_response(history_payload)
        return ChatResponse(reply=reply)
    except Exception as exc:
        print(f"Chat error: {exc}")
        return ChatResponse(reply="抱歉，我目前無法連線到 AI 服務。請稍後再試。")


@app.post("/api/execute-code", response_model=CodeExecutionResponse)
def execute_code(payload: CodeExecutionRequest):
    if not payload.code or not payload.code.strip():
        return CodeExecutionResponse(output="", error="Code cannot be empty")
    output, error = code_compiler.execute_python_code(payload.code, timeout=10, enable_security_check=True)
    return CodeExecutionResponse(output=output, error=error)


@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(database.get_db)):
    print(f"DEBUG: Updating user {user_id}. Draft present: {payload.current_quiz_draft is not None}")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = payload.name
    user.email = payload.email
    if payload.password:
        user.password = hash_password(payload.password)
    if payload.current_quiz_draft is not None:
        print(f"DEBUG: Setting draft (len={len(payload.current_quiz_draft)})")
        user.current_quiz_draft = payload.current_quiz_draft
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}/recharge-records", response_model=List[RechargeRecordResponse])
def read_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.RechargeRecord).filter(models.RechargeRecord.user_id == user_id).order_by(
        models.RechargeRecord.id.desc()).all()


@app.post("/users/{user_id}/recharge", response_model=RechargeRecordResponse)
def recharge_user(user_id: int, payload: RechargeRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    points_to_add = payload.points
    if points_to_add is None:
        points_to_add = calculate_points_from_amount(payload.price)
        
    user.points += points_to_add
        
    record = models.RechargeRecord(
        user_id=user.id,
        date=datetime.now().strftime("%Y/%m/%d"),
        order_id=f"A{datetime.now():%Y%m%d%H%M%S}",
        amount=payload.price,
        points=points_to_add,
        balance_after=user.points,
        plan_content=payload.plan_content or get_plan_description(payload.price),
        payment_method=payload.payment_method,
        plan_id=payload.plan_id,
    )
    db.add(record)
    db.add(user)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/videos", response_model=List[schema.VideoResponse])
def get_videos(user_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    query = db.query(models.Video)
    if user_id is not None:
        query = query.filter(models.Video.user_id == user_id)
    return query.order_by(models.Video.id.desc()).all()


@app.get("/api/videos/{video_id}/analysis", response_model=schema.VideoAnalysisResponse)
def analyze_video(video_id: int, user_id: int = 1, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        title = video.title or "Untitled Video"
        print(f"DEBUG: Analyzing video {video_id}: {title}")
        analysis = learning_pipeline.analyze_video(video.id, title, video.video_link)
        
        # 計算扣除點數：("單次呼叫的token數"/2000)*100，無條件進位到十位數
        total_tokens = analysis.token_usage.total_tokens if analysis.token_usage else 0
        consumed_points = 0
        if total_tokens > 0:
            raw_points = (total_tokens / 2000) * 100
            # 無條件進位到十位數
            consumed_points = math.ceil(raw_points / 10) * 10
        
        if user.points < consumed_points:
            raise HTTPException(status_code=403, detail=f"點數不足。分析需要 {consumed_points} 點，剩餘 {user.points} 點。")
        
        # 扣除點數
        user.points -= consumed_points
        analysis.consumed_points = consumed_points
        
        # 紀錄交易
        db.add(models.UploadRecord(user_id=user.id, video_id=video.id, consumed_points=consumed_points))

        if analysis.outline_markdown and analysis.outline_markdown != video.outline:
            video.outline = analysis.outline_markdown
            db.add(video)
        
        db.commit()
        db.refresh(video)
        return analysis
    except HTTPException:
        raise
    except Exception as exc:
        print(f"CRITICAL ERROR in analyze_video: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(exc)}")


@app.post("/api/videos", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, db: Session = Depends(database.get_db)):
    raw_link = (payload.video_link or "").strip()
    if not raw_link:
        raise HTTPException(status_code=400, detail="Please provide a video link")
    
    # 1. 獲取原始資訊進行內容校驗
    original_title = ai_analyzer.get_video_title(raw_link) or payload.title or "Untitled Video"
    transcript_snippet = ai_analyzer.fetch_video_transcript(raw_link)[:1500]
    
    # 2. 強制內容校驗：必須與 Python 相關
    print(f"DEBUG: Validating content for: {original_title}")
    if not ai_analyzer.is_python_related(original_title, transcript_snippet):
        print(f"REJECTED: Video is not Python related.")
        raise HTTPException(
            status_code=400, 
            detail="上傳失敗：本平台目前僅支援 Python 相關教學影片。請上傳正確的學習資源。"
        )

    title = (payload.title or "").strip() or original_title
    try:
        video = models.Video(video_link=raw_link, title=title, outline=payload.outline, user_id=payload.user_id,
                             cost_points=payload.cost_points or 0)
        db.add(video)
        db.commit()
        db.refresh(video)
        return video
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create video")


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return {"message": "Video deleted"}


@app.post("/api/videos/{video_id}/report-error")
def report_video_error(video_id: int, payload: schema.ErrorReportRequest, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.error_report:
        video.error_report = f"{video.error_report}\n---\n{payload.error_report}"
    else:
        video.error_report = payload.error_report
        
    db.commit()
    return {"message": "Error report saved"}


@app.post("/api/feedbacks", response_model=schema.AIFeedbackResponse)
def create_ai_feedback(payload: schema.AIFeedbackCreate, db: Session = Depends(database.get_db)):
    feedback = models.AIFeedback(user_id=payload.user_id, ai_message=payload.ai_message,
                                 user_message=payload.user_message, error_report=payload.error_report)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@app.delete("/api/feedbacks/conversations/{conversation_id}")
def delete_chat_conversation(conversation_id: str, user_id: int = Query(...), db: Session = Depends(database.get_db)):
    token = f"chat-session:{conversation_id}"
    db.query(models.AIFeedback).filter(models.AIFeedback.user_id == user_id,
                                       models.AIFeedback.error_report == token).delete(synchronize_session=False)
    db.commit()
    return {"message": "Conversation deleted"}


class GradeRequest(BaseModel):
    user_id: int
    answers: List[str]


class GradeResponse(BaseModel):
    total_score: int
    details: List[dict]


@app.post("/api/quizzes/{video_id}/grade", response_model=GradeResponse)
def grade_quiz(video_id: int, payload: GradeRequest, db: Session = Depends(database.get_db)):
    try:
        answer_count = len(payload.answers)
        # 增加 user_id 過濾，並抓取最新的題目紀錄
        questions = (
            db.query(models.QuizQuestion)
            .filter(models.QuizQuestion.video_id == video_id)
            .filter(models.QuizQuestion.user_id == payload.user_id)
            .order_by(models.QuizQuestion.id.desc())
            .limit(answer_count)
            .all()
        )
        questions.reverse()
        
        if not questions:
            raise HTTPException(status_code=404, detail="找不到對應的測驗紀錄，請重新產生測驗。")
        
        details = []
        correct_count = 0
        
        for idx, q in enumerate(questions):
            try:
                user_answer_code = payload.answers[idx] if idx < len(payload.answers) else ""
                correct_answer_str = (q.reference_answer or "").strip()
                starter_code = q.starter_code or ""
                
                # 安全解析測試案例
                tc_str = q.test_cases_json
                test_cases = []
                if tc_str:
                    try:
                        parsed = json.loads(tc_str)
                        test_cases = parsed if isinstance(parsed, list) else [str(parsed)]
                    except:
                        test_cases = [tc_str]
                
                if not test_cases:
                    test_cases = ["print('No tests')"]
                
                ref_full_code = starter_code.replace("___", correct_answer_str)
                user_full_code = user_answer_code
                
                is_all_passed = True
                q_results = []
                
                # 執行測試
                first_failure_msg = None
                for test_case in test_cases[:3]:
                    # 效能優化：若已失敗則跳過後續執行，但保留第一個失敗的訊息
                    if not is_all_passed:
                        q_results.append({"test_case": test_case, "expected": "SKIPPED", "actual": "SKIPPED", "passed": False})
                        continue

                    ref_out, ref_err = code_compiler.execute_python_code(f"{ref_full_code}\n\n{test_case}", timeout=4)
                    user_out, user_err = code_compiler.execute_python_code(f"{user_full_code}\n\n{test_case}", timeout=4)
                    
                    is_match = (ref_out.strip() == user_out.strip()) and not user_err
                    if not is_match:
                        is_all_passed = False
                        if user_err:
                            first_failure_msg = f"執行錯誤：{user_err.splitlines()[-1]}"
                        else:
                            first_failure_msg = f"輸出不符：執行「{test_case}」時預期為『{ref_out.strip()}』但得到『{user_out.strip()}』"
                    
                    q_results.append({
                        "test_case": test_case,
                        "expected": ref_out.strip() or ("ERROR: " + ref_err if ref_err else "None"),
                        "actual": user_out.strip() or ("ERROR: " + user_err if user_err else "None"),
                        "passed": is_match
                    })
                
                if is_all_passed and q_results:
                    correct_count += 1

                details.append({
                    "question_id": q.id,
                    "question_text": q.question_content, 
                    "user_answer": user_answer_code,     
                    "passed": is_all_passed,
                    "diagnostic": first_failure_msg or "邏輯正確，通過所有測試案例。", # 新增診斷欄位
                    "test_results": q_results
                })
            except Exception as e:
                details.append({
                    "question_id": q.id,
                    "question_text": q.question_content,
                    "user_answer": user_answer_code,
                    "passed": False,
                    "error": f"批改異常: {str(e)}"
                })
        
        total_score = round((correct_count / len(questions)) * 100) if questions else 0
        return GradeResponse(total_score=total_score, details=details)
    except HTTPException:
        raise
    except Exception as e:
        print(f"CRITICAL GRADING ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"系統批改模組發生嚴重錯誤: {str(e)}")


@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz_api(video_id: int, user_id: int = 1, count: int = Query(5, ge=1, le=10), db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None: raise HTTPException(status_code=404, detail="Video not found")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None: raise HTTPException(status_code=404, detail="User not found")

    # 先計算應消耗點數 (預期 "題數" * 50 點)
    expected_points = count * 50
    if user.points < expected_points:
        raise HTTPException(status_code=403, detail=f"點數不足。生成測驗預計需要 {expected_points} 點，剩餘 {user.points} 點。")

    try:
        quiz_response = learning_pipeline.generate_quiz(video.id, video.title or "Video", video.video_link, count=count)
        
        # 實際計算扣除點數："題數"*50
        num_questions = len(quiz_response.questions)
        consumed_points = num_questions * 50
        
        # 二次確認點數
        if user.points < consumed_points:
            raise HTTPException(status_code=403, detail=f"點數不足。生成測驗需要 {consumed_points} 點，剩餘 {user.points} 點。")
            
        # 扣除點數
        user.points -= consumed_points
        quiz_response.consumed_points = consumed_points

        for item in quiz_response.questions:
            q_model = models.QuizQuestion(user_id=user_id, video_id=video.id, question_content=item.question,
                                       reference_answer=item.correct_answer, accuracy=0,
                                       options_json=json.dumps(item.options, ensure_ascii=False),
                                       starter_code=item.starter_code,
                                       test_cases_json=json.dumps(item.test_cases, ensure_ascii=False),
                                       explanation=item.explanation, reference_concept=item.reference_concept,
                                       source_time=item.source_time, source_excerpt=item.source_excerpt)
            db.add(q_model)
            db.flush() # 取得 q_model.id
            db.add(models.GenerationRecord(user_id=user.id, quiz_question_id=q_model.id, consumed_points=50))
            
        db.commit()
        return quiz_response
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, db: Session = Depends(database.get_db)):
    user_id = payload.user_id or 1
    # 如果沒給標題，預設使用影片標題
    title = payload.title
    if not title:
        video = db.query(models.Video).filter(models.Video.id == payload.video_id).first()
        title = video.title if video else f"Quiz Result {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    quiz_result = models.QuizResult(
        user_id=user_id,
        video_id=payload.video_id,
        score=payload.score,
        total_questions=payload.total_questions,
        title=title,
        details_json=payload.details_json,
        error_report=payload.error_report
    )

    db.add(quiz_result)
    db.commit()
    db.refresh(quiz_result)
    return quiz_result


@app.delete("/api/quiz-results/{result_id}")
def delete_quiz_result(result_id: int, db: Session = Depends(database.get_db)):
    result = db.query(models.QuizResult).filter(models.QuizResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    db.delete(result)
    db.commit()
    return {"message": "Result deleted successfully"}


@app.patch("/api/quiz-results/{result_id}", response_model=schema.QuizResultResponse)
def update_quiz_result(result_id: int, payload: schema.QuizResultUpdate, db: Session = Depends(database.get_db)):
    result = db.query(models.QuizResult).filter(models.QuizResult.id == result_id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Quiz result not found")
    
    if payload.title is not None:
        result.title = payload.title
    if payload.score is not None:
        result.score = payload.score
    if payload.details_json is not None:
        result.details_json = payload.details_json
    if payload.error_report is not None:
        if result.error_report:
            result.error_report = f"{result.error_report}\n---\n{payload.error_report}"
        else:
            result.error_report = payload.error_report
        
    db.commit()
    db.refresh(result)
    return result


@app.post("/api/quiz-results/{result_id}/report-error")
def report_quiz_error(result_id: int, payload: schema.ErrorReportRequest, db: Session = Depends(database.get_db)):
    result = db.query(models.QuizResult).filter(models.QuizResult.id == result_id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Quiz result not found")
    
    if result.error_report:
        result.error_report = f"{result.error_report}\n---\n{payload.error_report}"
    else:
        result.error_report = payload.error_report
        
    db.commit()
    return {"message": "Quiz error report saved"}


@app.get("/api/quiz-results", response_model=List[schema.QuizResultResponse])
def get_quiz_results(user_id: int = 1, db: Session = Depends(database.get_db)):
    results = (
        db.query(models.QuizResult)
        .filter(models.QuizResult.user_id == user_id)
        .order_by(models.QuizResult.completed_at.desc())
        .all()
    )
    # 由於 schema 需要 video_title，我們可以動態補齊或修改 schema
    # 這裡直接回傳，Pydantic 會處理關聯 (如果 models 有設定)
    return results


# --- Quiz Drafts ---

class QuizDraftBase(BaseModel):
    user_id: int
    video_id: int
    draft_json: str

class QuizDraftResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    draft_json: str
    updated_at: datetime
    video_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

@app.get("/api/quiz-drafts", response_model=List[QuizDraftResponse])
def get_all_drafts(user_id: int = 1, db: Session = Depends(database.get_db)):
    drafts = db.query(models.QuizDraft).filter(models.QuizDraft.user_id == user_id).all()
    # 補上影片標題方便前端顯示
    for d in drafts:
        d.video_title = d.video.title if d.video else "Unknown Video"
    return drafts

@app.post("/api/quiz-drafts", response_model=QuizDraftResponse)
def upsert_quiz_draft(payload: QuizDraftBase, db: Session = Depends(database.get_db)):
    # 檢查是否已有該影片的草稿
    draft = db.query(models.QuizDraft).filter(
        models.QuizDraft.user_id == payload.user_id,
        models.QuizDraft.video_id == payload.video_id
    ).first()

    if draft:
        draft.draft_json = payload.draft_json
        draft.updated_at = datetime.now()
    else:
        draft = models.QuizDraft(
            user_id=payload.user_id,
            video_id=payload.video_id,
            draft_json=payload.draft_json
        )
        db.add(draft)

    db.commit()
    db.refresh(draft)
    draft.video_title = draft.video.title if draft.video else "Unknown Video"
    return draft

@app.delete("/api/quiz-drafts/{video_id}")
def delete_quiz_draft(video_id: int, user_id: int = Query(...), db: Session = Depends(database.get_db)):
    db.query(models.QuizDraft).filter(
        models.QuizDraft.user_id == user_id,
        models.QuizDraft.video_id == video_id
    ).delete()
    db.commit()
    return {"message": "Draft deleted"}



@app.get("/users/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    quiz_results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    
    # 因為 r.score 已經是百分比 (0-100)，直接取平均值即可
    avg_acc = (sum(r.score for r in quiz_results) / len(quiz_results)) if quiz_results else 0.0
    
    # 已回答題數：加總所有已完成測驗的題目數量
    total_answered_questions = sum(r.total_questions for r in quiz_results) if quiz_results else 0

    total_videos = db.query(models.Video).filter(models.Video.user_id == user_id).count()
    analyzed_videos = db.query(models.Video).filter(
        models.Video.user_id == user_id,
        or_(models.Video.outline != None, models.Video.transcript != None)
    ).count()

    return schema.UserStatsResponse(
        video_count=total_videos,
        analyzed_video_count=analyzed_videos,
        total_questions_count=total_answered_questions,
        remaining_points=user.points,
        completed_quizzes=len(quiz_results),
        average_accuracy=round(avg_acc, 1)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
