from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import database
import schema
import ai_analyzer
import code_compiler
from auth_utils import get_current_user

router = APIRouter(tags=["ai"])

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
        if video: system_content += f"\n\n目前討論影片標題：{video.title}"
    history = [{"role": "system", "content": system_content}]
    for item in payload.history: history.append({"role": item.role, "content": item.content})
    if not payload.history or payload.history[-1].content != payload.message: history.append({"role": "user", "content": payload.message})
    try: return schema.ChatResponse(reply=ai_analyzer.get_chat_response(history))
    except Exception: return schema.ChatResponse(reply="AI 服務暫時無法連線。")

@router.post("/api/execute-code", response_model=schema.CodeExecutionResponse)
def execute_code(payload: schema.CodeExecutionRequest):
    out, err = code_compiler.execute_python_code(payload.code, timeout=10, enable_security_check=True)
    return schema.CodeExecutionResponse(output=out, error=err)
