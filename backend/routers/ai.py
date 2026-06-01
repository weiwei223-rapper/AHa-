from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import models
import database
import schema
import ai_analyzer
import code_compiler
from report_utils import process_error_report_task
from auth_utils import get_current_user

router = APIRouter(tags=["ai"])

@router.post("/api/feedbacks", response_model=schema.AIFeedbackResponse)
def create_feedback(payload: schema.AIFeedbackCreate, background_tasks: BackgroundTasks, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    feedback = models.AIFeedback(
        user_id=current_user.id,
        video_id=payload.video_id,
        document_id=payload.document_id,
        ai_message=payload.ai_message,
        user_message=payload.user_message,
        error_report=payload.error_report
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    if payload.user_message == "USER_ERROR_REPORT" and payload.error_report:
        background_tasks.add_task(process_error_report_task, feedback.id, "feedback", current_user.id)
        
    return feedback

@router.get("/api/feedbacks", response_model=List[schema.AIFeedbackResponse])
def get_feedbacks(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    # 這裡可以考慮是否只回傳該使用者的回饋，但根據 ChatDB.tsx 的邏輯，它在 frontend 過濾 user_id
    # 為了效能與隱私，最好在後端過濾
    return db.query(models.AIFeedback).filter(models.AIFeedback.user_id == current_user.id).all()

@router.delete("/api/feedbacks/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # 根據 frontend 邏輯，conversation_id 儲存在 error_report 中，格式為 "chat-session:{id}"
    prefix = f"chat-session:{conversation_id}"
    db.query(models.AIFeedback).filter(
        models.AIFeedback.user_id == current_user.id,
        models.AIFeedback.error_report.like(f"{prefix}%")
    ).delete(synchronize_session=False)
    db.commit()
    return {"message": "Conversation deleted"}

@router.get("/api/health/gemini", response_model=schema.GeminiHealthResponse)
def gemini_health_check():
    try: return schema.GeminiHealthResponse(**ai_analyzer.test_gemini_connection())
    except Exception as exc: raise HTTPException(status_code=503, detail=f"Gemini connection failed: {exc}")

@router.post("/api/chat", response_model=schema.ChatResponse)
def chat_with_ai(payload: schema.ChatRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
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
        if video:
            system_content += f"\n\n目前討論影片標題：{video.title}"
            if video.outline:
                system_content += f"\n影片大綱：\n{video.outline}"
            if video.transcript:
                system_content += f"\n影片逐字稿：\n{video.transcript[:3000]}"
    
    if payload.document_id:
        doc = db.query(models.Document).filter(models.Document.id == payload.document_id).first()
        if doc:
            system_content += f"\n\n目前討論教材(PDF)標題：{doc.title}"
            if doc.outline:
                system_content += f"\n教材大綱：\n{doc.outline}"
            if doc.content_text:
                system_content += f"\n教材內容全文：\n{doc.content_text[:3000]}"

    history = [{"role": "system", "content": system_content}]
    for item in payload.history: history.append({"role": item.role, "content": item.content})
    if not payload.history or payload.history[-1].content != payload.message: history.append({"role": "user", "content": payload.message})
    try: return schema.ChatResponse(reply=ai_analyzer.get_chat_response(history))
    except Exception: return schema.ChatResponse(reply="AI 服務暫時無法連線。")

@router.post("/api/execute-code", response_model=schema.CodeExecutionResponse)
def execute_code(payload: schema.CodeExecutionRequest):
    out, err = code_compiler.execute_python_code(payload.code, timeout=10, enable_security_check=True)
    return schema.CodeExecutionResponse(output=out, error=err)
