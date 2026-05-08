from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib
import html
import json
import re
from urllib.parse import quote, quote_plus

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import text

ECPAY_MERCHANT_ID = "2000132"
ECPAY_HASH_KEY = "5294y06JbISpM5x9"
ECPAY_HASH_IV = "v77hoKGq4kWxNNIS"

load_dotenv()

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
    ]
    with database.engine.begin() as connection:
        for statement in schema_updates:
            connection.execute(text(statement))


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
                    date=datetime.utcnow().strftime("%Y/%m/%d"),
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    uid: str
    points: int

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None


class RechargeRequest(BaseModel):
    points: Optional[int] = None
    price: Optional[int] = 0
    plan_content: Optional[str] = None
    payment_method: Optional[str] = None
    plan_id: Optional[str] = None


class EcpayCheckoutRequest(BaseModel):
    MerchantID: Optional[str] = None
    MerchantTradeNo: str
    MerchantTradeDate: str
    PaymentType: str
    TotalAmount: int
    TradeDesc: str
    ItemName: str
    ReturnURL: str
    ClientBackURL: str
    ChoosePayment: str
    EncryptType: int


class EcpayCheckoutResponse(BaseModel):
    CheckMacValue: str

    model_config = ConfigDict(from_attributes=True)


def build_ecpay_check_mac_debug(params: Dict[str, Any]) -> tuple[str, str, str]:
    filtered = {
        key: str(value)
        for key, value in params.items()
        if key != "CheckMacValue" and value is not None and str(value) != ""
    }
    if "MerchantID" not in filtered or filtered["MerchantID"] in (None, ""):
        filtered["MerchantID"] = ECPAY_MERCHANT_ID

    ordered = sorted(filtered.items(), key=lambda item: item[0])
    encoded = "&".join(f"{key}={value}" for key, value in ordered)
    raw = f"HashKey={ECPAY_HASH_KEY}&{encoded}&HashIV={ECPAY_HASH_IV}"
    encoded_raw = quote(raw, safe="").lower()
    encoded_raw = encoded_raw.replace("%2d", "-")
    encoded_raw = encoded_raw.replace("%5f", "_")
    encoded_raw = encoded_raw.replace("%2e", ".")
    encoded_raw = encoded_raw.replace("%21", "!")
    encoded_raw = encoded_raw.replace("%2a", "*")
    encoded_raw = encoded_raw.replace("%28", "(")
    encoded_raw = encoded_raw.replace("%29", ")")
    encoded_raw = encoded_raw.replace("%7e", "~")
    encoded_raw = encoded_raw.replace("%20", "+")
    check_mac_value = hashlib.sha256(encoded_raw.encode("utf-8")).hexdigest().upper()
    return raw, encoded_raw, check_mac_value


def generate_ecpay_check_mac_value(params: Dict[str, Any]) -> str:
    _, _, check_mac_value = build_ecpay_check_mac_debug(params)
    return check_mac_value


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


def get_or_update_video_transcript(video: models.Video, db: Session) -> tuple[str, str]:
    if video.transcript:
        return video.transcript, video.transcript_source or "database"

    transcript_result = learning_pipeline.load_transcript(video.video_link)
    if transcript_result.transcript:
        video.transcript = transcript_result.transcript
        video.transcript_source = transcript_result.source
        video.transcript_updated_at = datetime.utcnow()
        db.add(video)
        db.commit()
        db.refresh(video)
    return video.transcript or "", video.transcript_source or transcript_result.source


def build_chat_video_context(video: models.Video, db: Session, query: str, user_id: Optional[int]) -> dict:
    transcript, transcript_source = get_or_update_video_transcript(video, db)
    retrieved_chunks, retrieval_backend = learning_pipeline.retrieve_chunks(query, transcript)

    questions_query = db.query(models.QuizQuestion).filter(models.QuizQuestion.video_id == video.id)
    if user_id is not None:
        questions_query = questions_query.filter(models.QuizQuestion.user_id == user_id)
    questions = questions_query.order_by(models.QuizQuestion.created_at.desc()).limit(8).all()

    return {
        "id": video.id,
        "title": video.title or "Untitled Video",
        "video_link": video.video_link,
        "outline": video.outline or "",
        "transcript": transcript,
        "transcript_source": transcript_source,
        "retrieval_backend": retrieval_backend,
        "retrieved_chunks": [
            {"index": chunk.index, "content": chunk.content, "score": round(chunk.score, 4)}
            for chunk in retrieved_chunks
        ],
        "questions": [
            {
                "question": question.question_content,
                "reference_answer": question.reference_answer,
                "answer_record": question.answer_record,
                "accuracy": question.accuracy,
            }
            for question in questions
        ],
    }


@app.post("/auth/register", response_model=UserResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    uid = f"UID-{datetime.utcnow():%Y%m%d%H%M}"
    new_user = models.User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        uid=uid,
        points=0,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"user": user, "message": f"Welcome back, {user.name}"}


@app.post("/ecpay/create-checkmac", response_model=EcpayCheckoutResponse)
def create_ecpay_checkmac(payload: EcpayCheckoutRequest):
    params = payload.model_dump()
    return EcpayCheckoutResponse(CheckMacValue=generate_ecpay_check_mac_value(params))


@app.post("/ecpay/debug-checkmac")
def debug_ecpay_checkmac(payload: Dict[str, Any]):
    raw, encoded_raw, check_mac_value = build_ecpay_check_mac_debug(payload)
    return {
        "raw": raw,
        "encoded_raw": encoded_raw,
        "CheckMacValue": check_mac_value,
    }


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
                date=datetime.utcnow().strftime("%Y/%m/%d"),
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

    video_context: dict | list[dict]
    if payload.video_id is not None:
        video_query = db.query(models.Video).filter(models.Video.id == payload.video_id)
        if payload.user_id is not None:
            video_query = video_query.filter(models.Video.user_id == payload.user_id)
        video = video_query.first()
        if video is None:
            raise HTTPException(status_code=404, detail="Video not found")
        video_context = build_chat_video_context(video, db, user_message, payload.user_id)
    else:
        recent_videos_query = db.query(models.Video)
        if payload.user_id is not None:
            recent_videos_query = recent_videos_query.filter(models.Video.user_id == payload.user_id)
        recent_videos = recent_videos_query.order_by(models.Video.created_at.desc()).limit(3).all()
        video_context = [
            {
                "id": video.id,
                "title": video.title,
                "video_link": video.video_link,
                "outline": video.outline,
            }
            for video in recent_videos
        ]

    try:
        reply = ai_analyzer.generate_chat_reply(
            user_message,
            [{"role": item.role, "content": item.content} for item in payload.history],
            video_context,
        )
        return ChatResponse(reply=reply)
    except Exception as exc:
        print(f"Error chatting with Gemini: {exc}")
        return ChatResponse(reply=ai_analyzer.generate_transcript_fallback_reply(user_message, video_context))


@app.post("/api/execute-code", response_model=CodeExecutionResponse)
def execute_code(payload: CodeExecutionRequest):
    if not payload.code or not payload.code.strip():
        return CodeExecutionResponse(output="", error="Code cannot be empty")
    output, error = code_compiler.execute_python_code(
        payload.code,
        timeout=10,
        enable_security_check=True,
    )
    return CodeExecutionResponse(output=output, error=error)


@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = payload.name
    user.email = payload.email
    if payload.password:
        user.password = hash_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}/recharge-records", response_model=List[RechargeRecordResponse])
def read_recharge_records(user_id: int, db: Session = Depends(database.get_db)):
    return (
        db.query(models.RechargeRecord)
        .filter(models.RechargeRecord.user_id == user_id)
        .order_by(models.RechargeRecord.id.desc())
        .all()
    )


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
        date=datetime.utcnow().strftime("%Y/%m/%d"),
        order_id=f"A{datetime.utcnow():%Y%m%d%H%M%S}",
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
def analyze_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    try:
        title = video.title or "Untitled Video"
        analysis = learning_pipeline.analyze_video(video.id, title, video.video_link)
        if analysis.outline_markdown and analysis.outline_markdown != video.outline:
            video.outline = analysis.outline_markdown
            db.add(video)
            db.commit()
            db.refresh(video)
        return analysis
    except Exception as exc:
        print(f"Error analyzing video: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze video: {exc}")


@app.post("/api/videos", response_model=schema.VideoResponse)
def create_video(payload: schema.VideoCreate, db: Session = Depends(database.get_db)):
    raw_link = (payload.video_link or "").strip()
    if not raw_link:
        raise HTTPException(status_code=400, detail="Please provide a video link")

    title = (payload.title or "").strip() or None
    if not title:
        title = extract_youtube_title(raw_link) if ("youtube.com" in raw_link or "youtu.be" in raw_link) else "Uploaded Video"

    try:
        video = models.Video(
            video_link=raw_link,
            title=title,
            outline=payload.outline,
            transcript=payload.transcript,
            transcript_source=payload.transcript_source,
            transcript_updated_at=datetime.utcnow() if payload.transcript else None,
            user_id=payload.user_id,
            cost_points=payload.cost_points or 0,
            error_report=payload.error_report,
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        if payload.user_id is not None:
            upload = models.UploadRecord(
                user_id=payload.user_id,
                video_id=video.id,
                consumed_points=payload.cost_points or 0,
            )
            db.add(upload)
            db.commit()
        return video
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Database error creating video: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create video")


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return {"message": "Video deleted"}


@app.post("/api/feedbacks", response_model=schema.AIFeedbackResponse)
def create_ai_feedback(payload: schema.AIFeedbackCreate, db: Session = Depends(database.get_db)):
    feedback = models.AIFeedback(
        user_id=payload.user_id,
        video_id=payload.video_id,
        ai_message=payload.ai_message,
        user_message=payload.user_message,
        error_report=payload.error_report,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@app.get("/api/feedbacks", response_model=List[schema.AIFeedbackResponse])
def get_ai_feedbacks(db: Session = Depends(database.get_db)):
    return db.query(models.AIFeedback).order_by(models.AIFeedback.id.desc()).all()


@app.delete("/api/feedbacks/conversations/{conversation_id}")
def delete_chat_conversation(
    conversation_id: str,
    user_id: int = Query(..., description="User id"),
    db: Session = Depends(database.get_db),
):
    """
    Delete all ai_feedback rows that belong to a single chat conversation.

    Note: the frontend stores the conversation token in `error_report` as:
      `chat-session:{conversation_id}`
    """

    token = f"chat-session:{conversation_id}"
    q = (
        db.query(models.AIFeedback)
        .filter(models.AIFeedback.user_id == user_id)
        .filter(models.AIFeedback.error_report == token)
    )
    deleted_count = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return {"message": "Conversation deleted", "deleted_count": deleted_count}


@app.post("/api/quiz-questions", response_model=schema.QuizQuestionResponse)
def create_quiz_question(payload: schema.QuizQuestionCreate, db: Session = Depends(database.get_db)):
    question = models.QuizQuestion(
        user_id=payload.user_id,
        video_id=payload.video_id,
        question_content=payload.question_content,
        reference_answer=payload.reference_answer,
        answer_record=payload.answer_record,
        accuracy=payload.accuracy or 0,
        options_json=json.dumps(payload.options, ensure_ascii=False),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return schema.QuizQuestionResponse(
        id=question.id,
        user_id=question.user_id,
        video_id=question.video_id,
        question_content=question.question_content,
        reference_answer=question.reference_answer,
        answer_record=question.answer_record,
        accuracy=question.accuracy,
        options=payload.options,
        created_at=question.created_at,
    )


@app.get("/api/quiz-questions", response_model=List[schema.QuizQuestionResponse])
def get_quiz_questions(db: Session = Depends(database.get_db)):
    questions = db.query(models.QuizQuestion).order_by(models.QuizQuestion.id.desc()).all()
    return [
        schema.QuizQuestionResponse(
            id=q.id,
            user_id=q.user_id,
            video_id=q.video_id,
            question_content=q.question_content,
            reference_answer=q.reference_answer,
            answer_record=q.answer_record,
            accuracy=q.accuracy,
            options=json.loads(q.options_json or "[]"),
            created_at=q.created_at,
        )
        for q in questions
    ]


@app.post("/api/uploads", response_model=schema.UploadRecordResponse)
def create_upload(payload: schema.UploadRecordCreate, db: Session = Depends(database.get_db)):
    upload = models.UploadRecord(
        user_id=payload.user_id,
        video_id=payload.video_id,
        consumed_points=payload.consumed_points,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


@app.post("/api/generations", response_model=schema.GenerationRecordResponse)
def create_generation(payload: schema.GenerationRecordCreate, db: Session = Depends(database.get_db)):
    generation = models.GenerationRecord(
        user_id=payload.user_id,
        quiz_question_id=payload.quiz_question_id,
        consumed_points=payload.consumed_points,
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


@app.get("/api/videos/{video_id}/quiz", response_model=schema.QuizResponse)
def generate_quiz(video_id: int, user_id: int = 1, db: Session = Depends(database.get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    title = video.title or "Untitled Video"
    try:
        quiz_response = learning_pipeline.generate_quiz(video.id, title, video.video_link)
        questions = quiz_response.questions
        saved_questions = []
        for item in questions:
            question_record = models.QuizQuestion(
                user_id=user_id,
                video_id=video.id,
                question_content=item.question,
                reference_answer=item.correct_answer,
                answer_record=None,
                accuracy=0,
                options_json=json.dumps(item.options, ensure_ascii=False),
            )
            db.add(question_record)
            saved_questions.append(question_record)

        db.commit()

        if saved_questions:
            db.refresh(saved_questions[0])
            generation_record = models.GenerationRecord(
                user_id=user_id,
                quiz_question_id=saved_questions[0].id,
                consumed_points=video.cost_points or 0,
            )
            db.add(generation_record)
            db.commit()

        return schema.QuizResponse(
            video_id=video.id,
            video_title=title,
            quiz_type=quiz_response.quiz_type,
            questions=questions,
        )
    except Exception as exc:
        print(f"Error generating quiz: {exc}")
        questions = ai_analyzer.generate_fallback_questions(title)
        return schema.QuizResponse(
            video_id=video.id,
            video_title=title,
            quiz_type="fallback-coding",
            questions=questions,
        )


@app.post("/api/quiz-results", response_model=schema.QuizResultResponse)
def create_quiz_result(payload: schema.QuizResultCreate, db: Session = Depends(database.get_db)):
    user_id = payload.user_id or 1
    quiz_result = models.QuizResult(
        user_id=user_id,
        video_id=payload.video_id,
        score=payload.score,
        total_questions=payload.total_questions,
    )
    db.add(quiz_result)
    db.commit()
    db.refresh(quiz_result)
    return quiz_result


@app.get("/users/{user_id}/stats", response_model=schema.UserStatsResponse)
def get_user_stats(user_id: int, db: Session = Depends(database.get_db)):
    video_count = db.query(models.Video).filter(models.Video.user_id == user_id).count()
    analyzed_video_count = (
        db.query(models.Video)
        .filter(models.Video.user_id == user_id)
        .filter(models.Video.outline.isnot(None))
        .count()
    )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    quiz_results = db.query(models.QuizResult).filter(models.QuizResult.user_id == user_id).all()
    completed_quizzes = len(quiz_results)
    total_questions_count = sum(result.total_questions for result in quiz_results)
    
    average_accuracy = (
        sum(result.score / result.total_questions * 100 for result in quiz_results) / len(quiz_results)
        if quiz_results
        else 0.0
    )
    return schema.UserStatsResponse(
        video_count=video_count,
        analyzed_video_count=analyzed_video_count,
        remaining_points=user.points,
        completed_quizzes=completed_quizzes,
        total_questions_count=total_questions_count,
        average_accuracy=round(average_accuracy, 1),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
